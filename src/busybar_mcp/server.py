"""MCP server for building BUSY Bar apps.

Scope is deliberately narrow: the *authoring* loop, not the runtime. Anything
that needs to run continuously (status daemons, presence, timers) belongs in a
normal long-lived process driving `busylib` directly — MCP is request/response
and is the wrong shape for that. What an agent genuinely can't do well without
help is the draw → look → adjust cycle, and the fiddly asset conversion around
it. That's what this covers.

Built on the official `busylib` rather than raw HTTP, so it tracks the vendor's
own compatibility handling instead of duplicating it.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Any, Literal

from busylib import BusyBar, converter, display as bbdisplay, exceptions, types
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from PIL import Image as PILImage

mcp = FastMCP(
    name="busybar",
    instructions=(
        "Tools for building BUSY Bar apps. The front display is a 72x16 RGB LED "
        "matrix; the back is 160x80 with 16 grey levels. Elements drawn outside "
        "those bounds silently do not render, so use `preview` after `draw` to "
        "confirm what actually appeared rather than assuming."
    ),
)

DEFAULT_HOST = os.environ.get("BUSYBAR_HOST", "10.0.4.20")
DEFAULT_TOKEN = os.environ.get("BUSYBAR_TOKEN") or None
DEFAULT_APP = os.environ.get("BUSYBAR_APP", "mcp-scratch")


# ---------------------------------------------------------------------------
# Client handling
# ---------------------------------------------------------------------------


@dataclass
class _Conn:
    host: str = DEFAULT_HOST
    token: str | None = DEFAULT_TOKEN
    client: BusyBar | None = None

    def get(self) -> BusyBar:
        if self.client is None:
            self.client = BusyBar(self.host, token=self.token, compatibility_mode="warn")
        return self.client

    def reset(self) -> None:
        if self.client is not None:
            try:
                self.client.close()
            except Exception:  # noqa: BLE001 - closing must never mask the real error
                pass
        self.client = None


_conn = _Conn()


class ToolError(RuntimeError):
    """Surfaced to the agent as a readable message rather than a traceback."""


def _client() -> BusyBar:
    try:
        return _conn.get()
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"Could not create a client for {_conn.host}: {exc}") from exc


def _wrap(exc: Exception) -> ToolError:
    """Turn library/transport errors into something an agent can act on.

    The three failure modes need genuinely different advice, and conflating
    them wastes an agent's time: a schema mismatch reported as "check the
    cable" sends it chasing a network problem that does not exist.

    Never include the token in a message — AGENTS.md rule, and these strings go
    straight into a model's context.
    """
    if isinstance(exc, exceptions.BusyBarAPIError):
        if getattr(exc, "status_code", None) == 403:
            return ToolError(
                "403 Forbidden: the bar has an access key set. Provide it via the "
                "BUSYBAR_TOKEN environment variable (a 4-10 digit PIN). Note that "
                "current firmware only enforces the key over Wi-Fi, not USB."
            )
        return ToolError(f"Device rejected the request: {exc}")

    if isinstance(
        exc,
        (
            exceptions.BusyBarResponseValidationError,
            exceptions.BusyBarProtocolError,
            exceptions.BusyBarAPIVersionError,
            exceptions.BusyBarRemovedEndpointError,
        ),
    ):
        return ToolError(
            f"The bar answered, but not in the shape busylib expected: {exc}. This is "
            "a firmware/library mismatch rather than a connection problem — check "
            "`device_status` for the firmware version and confirm the installed "
            "busylib targets it."
        )

    return ToolError(
        f"Could not reach a BUSY Bar at {_conn.host}: {exc}. Check it is powered on "
        "and plugged in over USB (default 10.0.4.20), or pass its Wi-Fi address to "
        "`connect`."
    )


# ---------------------------------------------------------------------------
# Bounds validation
#
# The device silently drops out-of-bounds elements. An agent then sees a
# successful response and a blank display and has no idea why. Catching it here
# converts a confusing no-op into an actionable message.
# ---------------------------------------------------------------------------


def _spec(name: str) -> bbdisplay.DisplaySpec:
    return bbdisplay.get_display_spec(
        types.DisplayName.BACK if str(name).lower() == "back" else types.DisplayName.FRONT
    )


def _check_bounds(elements: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for el in elements:
        spec = _spec(el.get("display", "front"))
        x, y = int(el.get("x", 0)), int(el.get("y", 0))
        if not (0 <= x < spec.width and 0 <= y < spec.height):
            warnings.append(
                f"element {el.get('id', '?')!r} at ({x},{y}) is outside the "
                f"{spec.name.value} display ({spec.width}x{spec.height}) and will not render"
            )
    return warnings


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
def connect(host: str, token: str | None = None) -> dict[str, Any]:
    """Point at a BUSY Bar and report what it is.

    host: `10.0.4.20` over USB, or the bar's Wi-Fi address.
    token: access key (4-10 digit PIN) if one is set. Only needed over Wi-Fi.
    """
    _conn.reset()
    _conn.host, _conn.token = host, token or None
    bb = _client()
    try:
        v = bb.version()
        return {
            "host": host,
            "firmware": getattr(v, "version", None),
            "api_semver": getattr(v, "api_semver", None),
            "authenticated": token is not None,
        }
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc


@mcp.tool
def device_status() -> dict[str, Any]:
    """Firmware, uptime, battery, brightness and volume for the connected bar."""
    bb = _client()
    try:
        v, st = bb.version(), bb.status()
        out: dict[str, Any] = {"firmware": getattr(v, "version", None)}
        if getattr(st, "system", None):
            out["uptime"] = getattr(st.system, "uptime", None)
        if getattr(st, "power", None):
            out["battery_charge"] = getattr(st.power, "battery_charge", None)
        try:
            b = bb.display_brightness()
            out["brightness"] = {"front": b.front, "back": b.back}
        except Exception:  # noqa: BLE001 - optional detail, never fail the whole call
            pass
        try:
            out["volume"] = bb.audio_volume().volume
        except Exception:  # noqa: BLE001
            pass
        return out
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc


@mcp.tool
def draw(
    elements: list[dict[str, Any]],
    application_name: str = DEFAULT_APP,
    clear_before_draw: bool = True,
) -> dict[str, Any]:
    """Draw elements on the bar.

    Each element is a dict needing at least `id`, `type`, `x`, `y` and
    `display` ("front" or "back"). Supported `type` values include "text",
    "image", "rectangle", "countdown" and "animation".

    Text example:
        {"id": "status", "type": "text", "x": 2, "y": 4, "display": "front",
         "text": "BUILDING", "font": "small"}

    Fonts: tiny, small, normal, condensed, bold, large, extra_large, global.

    Out-of-bounds elements are reported back rather than silently dropped.
    Call `preview` afterwards to see the actual result.
    """
    if not elements:
        raise ToolError("`elements` must not be empty.")

    warnings = _check_bounds(elements)
    bb = _client()
    try:
        payload = types.DisplayElements(
            application_name=application_name,
            elements=elements,  # type: ignore[arg-type]  # pydantic discriminates on `type`
        )
    except Exception as exc:  # noqa: BLE001
        raise ToolError(
            f"Invalid element payload: {exc}. Every element needs `id` and `type`; "
            "check field names against the element type you chose."
        ) from exc

    try:
        bb.display_draw(payload, clear_before_draw=clear_before_draw)
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc

    return {
        "drawn": len(elements),
        "application_name": application_name,
        "warnings": warnings,
        "next": "Call `preview` to confirm what rendered.",
    }


@mcp.tool
def preview(which: Literal["front", "back"] = "front", scale: int = 6) -> Image:
    """Read back what is actually on the display, as a PNG you can look at.

    This is the point of the server: draw, look, adjust. The device reports
    success for draws that render nothing (bad coordinates, missing asset,
    another app at higher priority), so reading the framebuffer back is the
    only reliable confirmation.
    """
    spec = _spec(which)
    bb = _client()
    try:
        raw = bb.screen(spec.name)
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc

    px = spec.width * spec.height
    if len(raw) == px * 3:
        img = PILImage.frombytes("RGB", (spec.width, spec.height), raw)
    elif len(raw) == px:
        img = PILImage.frombytes("L", (spec.width, spec.height), raw).convert("RGB")
    else:
        raise ToolError(
            f"Unexpected framebuffer size for the {spec.name.value} display: got "
            f"{len(raw)} bytes, expected {px * 3} (RGB888) or {px} (8-bit grey)."
        )

    # Nearest-neighbour: these are 72x16 pixel-art panels and smoothing would
    # misrepresent which pixels are actually lit.
    scale = max(1, min(int(scale), 20))
    img = img.resize((spec.width * scale, spec.height * scale), PILImage.NEAREST)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Image(data=buf.getvalue(), format="png")


@mcp.tool
def clear() -> dict[str, str]:
    """Clear both displays."""
    bb = _client()
    try:
        bb.display_clear()
        return {"status": "cleared"}
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc


@mcp.tool
def upload_asset(
    local_path: str,
    application_name: str = DEFAULT_APP,
) -> dict[str, Any]:
    """Convert a local image or audio file for the device and upload it.

    Handles the resize/re-encode step, which is easy to get wrong by hand:
    `assets_upload` sends bytes as-is and will happily store a file the bar
    cannot render. Returns the on-device filename to use as an element `path`.
    """
    try:
        with open(local_path, "rb") as fh:
            filename, payload = converter.convert_for_storage(local_path, fh.read())
    except FileNotFoundError as exc:
        raise ToolError(f"No such file: {local_path}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"Could not convert {local_path} for the device: {exc}") from exc

    bb = _client()
    try:
        bb.assets_upload(
            application_name=application_name, filename=filename, data=payload
        )
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc

    return {
        "filename": filename,
        "bytes": len(payload),
        "application_name": application_name,
        "usage": f'reference it as {{"type": "image", "path": "{filename}"}}',
    }


@mcp.tool
def play_audio(path: str, application_name: str = DEFAULT_APP) -> dict[str, str]:
    """Play an audio asset already uploaded to the bar. Stop with `stop_audio`."""
    bb = _client()
    try:
        bb.audio_play(path=path)
        return {"status": "playing", "path": path, "application_name": application_name}
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc


@mcp.tool
def stop_audio() -> dict[str, str]:
    """Stop audio playback."""
    bb = _client()
    try:
        bb.audio_stop()
        return {"status": "stopped"}
    except Exception as exc:  # noqa: BLE001
        raise _wrap(exc) from exc


@mcp.tool
def displays() -> dict[str, Any]:
    """Exact dimensions and capabilities of both displays.

    Worth calling before laying anything out — 72x16 is far smaller than most
    guesses, and text that "should fit" usually does not.
    """
    return {
        d.name.value: {
            "width": d.width,
            "height": d.height,
            "description": d.description,
        }
        for d in (bbdisplay.FRONT_DISPLAY, bbdisplay.BACK_DISPLAY)
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
