"""Verify every tool against a mocked device, so no hardware is required.

Follows busylib's own testing guidance: exercise display payloads through
httpx.MockTransport before touching a real bar.
"""

from __future__ import annotations

import base64

import httpx
import pytest
from busylib import BusyBar
from busylib import display as bbdisplay

from busybar_mcp import server

FRONT_PX = bbdisplay.FRONT_DISPLAY.width * bbdisplay.FRONT_DISPLAY.height
BACK_PX = bbdisplay.BACK_DISPLAY.width * bbdisplay.BACK_DISPLAY.height

drawn: list[dict] = []


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/version":
        return httpx.Response(200, json={"version": "1.0.3", "api_semver": "25.0.0"})
    if path == "/api/status":
        # uptime is a str in StatusSystem, not an int.
        return httpx.Response(
            200, json={"system": {"uptime": "1234"}, "power": {"battery_charge": 88}}
        )
    # Note: display_clear() is DELETE on this same path, not a /clear endpoint.
    if path == "/api/display/draw":
        if request.method == "POST":
            import json

            drawn.append(json.loads(request.content))
        return httpx.Response(200, json={"result": "ok"})
    if path == "/api/screen":
        # Wire format: front is RGB888 (3 bytes/px); back is L4-packed, i.e. two
        # pixels per byte, which busylib unpacks to L8 before we see it.
        idx = request.url.params.get("display")
        n = FRONT_PX * 3 if idx in ("0", None) else BACK_PX // 2
        return httpx.Response(200, content=base64.b64encode(bytes(n)))
    return httpx.Response(200, json={"success": True})


@pytest.fixture(autouse=True)
def mock_bar(monkeypatch):
    drawn.clear()
    # busylib supports transport injection directly, so no private attributes.
    # max_retries=0 keeps a failing assertion from costing three backoff waits.
    client = BusyBar(
        "10.0.4.20",
        transport=httpx.MockTransport(handler),
        compatibility_mode="none",
        max_retries=0,
    )
    monkeypatch.setattr(server, "_client", lambda: client)
    yield client
    client.close()


def call(tool, **kw):
    """Invoke the underlying function of a FastMCP tool."""
    return (getattr(tool, "fn", None) or tool)(**kw)


def test_displays_reports_real_geometry():
    out = call(server.displays)
    assert out["front"]["width"] == 72 and out["front"]["height"] == 16
    assert out["back"]["width"] == 160 and out["back"]["height"] == 80


def test_device_status_reads_power_and_system():
    out = call(server.device_status)
    assert out["firmware"] == "1.0.3"
    assert out["battery_charge"] == 88


def test_draw_sends_expected_payload():
    out = call(
        server.draw,
        elements=[
            {
                "id": "status",
                "type": "text",
                "x": 2,
                "y": 4,
                "display": "front",
                "text": "BUILDING",
                "font": "small",
            }
        ],
        application_name="test-app",
    )
    assert out["drawn"] == 1
    assert out["warnings"] == []
    assert drawn[0]["application_name"] == "test-app"
    assert drawn[0]["elements"][0]["text"] == "BUILDING"


def test_draw_flags_out_of_bounds_instead_of_silently_dropping():
    """The device accepts these and renders nothing. That must not look like success."""
    out = call(
        server.draw,
        elements=[
            {
                "id": "oops",
                "type": "text",
                "x": 200,  # past the 72px front display
                "y": 4,
                "display": "front",
                "text": "X",
                "font": "small",
            }
        ],
    )
    assert len(out["warnings"]) == 1
    assert "outside the front display" in out["warnings"][0]


def test_draw_rejects_empty_elements():
    with pytest.raises(server.ToolError):
        call(server.draw, elements=[])


def test_draw_rejects_malformed_element():
    with pytest.raises(server.ToolError):
        call(server.draw, elements=[{"nope": True}])


def test_preview_front_returns_scaled_png():
    img = call(server.preview, which="front", scale=4)
    assert img.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_preview_back_handles_greyscale_framebuffer():
    img = call(server.preview, which="back", scale=2)
    assert img.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_preview_scale_is_clamped():
    # Guards against a 72x16 panel being blown up to something absurd.
    assert call(server.preview, which="front", scale=999).data[:4] == b"\x89PNG"
    assert call(server.preview, which="front", scale=0).data[:4] == b"\x89PNG"


def test_clear():
    assert call(server.clear)["status"] == "cleared"


def test_upload_asset_missing_file_is_readable():
    with pytest.raises(server.ToolError) as exc:
        call(server.upload_asset, local_path="/definitely/not/here.png")
    assert "No such file" in str(exc.value)


def test_schema_mismatch_is_not_reported_as_a_connection_problem(monkeypatch):
    """A bar that answers in an unexpected shape is a firmware/library mismatch.

    Reporting it as "could not reach the bar" sends an agent off checking cables
    for a problem that has nothing to do with the network.
    """

    def bad(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "1.0.3"})
        return httpx.Response(200, json={"totally": "unexpected"})

    client = BusyBar(
        "10.0.4.20",
        transport=httpx.MockTransport(bad),
        compatibility_mode="none",
        max_retries=0,
    )
    monkeypatch.setattr(server, "_client", lambda: client)
    with pytest.raises(server.ToolError) as exc:
        call(server.clear)
    msg = str(exc.value)
    assert "not in the shape busylib expected" in msg
    assert "Could not reach" not in msg
    client.close()


def test_server_registers_expected_tools():
    import asyncio

    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert {
        "connect",
        "device_status",
        "draw",
        "preview",
        "clear",
        "upload_asset",
        "play_audio",
        "stop_audio",
        "displays",
    } <= names
