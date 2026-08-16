# busybar-mcp

An MCP server for **building** [BUSY Bar](https://busy.app/) apps — draw to the displays, see what
actually rendered, upload converted assets, and inspect the device, all from an AI coding agent.

> Unofficial and community-built. The device, firmware and the official
> [`busylib`](https://github.com/busy-app/busylib-py) Python library are made by
> [Flipper Devices](https://busy.app/). This server is a thin layer on top of `busylib`, not a
> replacement for it.

## Why this exists

The BUSY Bar front display is a **72×16** RGB LED matrix. That's smaller than almost anyone's mental
model, and the device **silently ignores elements drawn outside its bounds** — you get a success
response and a blank bar, with nothing to tell you why.

So the loop that actually matters when building bar apps is *draw → look → adjust*, and an agent
can't close it without eyes. This server gives it eyes:

- **`preview`** reads the framebuffer back off the device and returns it as a PNG. The agent sees what
  rendered, not what it hoped would render.
- **`draw`** validates coordinates against the real display geometry first, so out-of-bounds elements
  come back as a warning instead of a silent no-op.
- **`upload_asset`** runs the image/audio conversion for you. `assets_upload` sends bytes as-is and
  will happily store a file the bar cannot display.

## What it deliberately doesn't do

This covers the **authoring** loop only. Anything that needs to run continuously — presence detection,
status daemons, Pomodoro timers, smart-home reactions — should be a normal long-lived process driving
`busylib` directly, or should use the device's MQTT and Matter support. MCP is request/response and
invoked by a model inside a conversation; it is the wrong shape for a thing that has to update a
display every fifteen seconds forever.

## Install

```bash
uv tool install busybar-mcp     # or: pipx install busybar-mcp
```

Register it with your agent:

```json
{
  "mcpServers": {
    "busybar": {
      "command": "busybar-mcp",
      "env": { "BUSYBAR_HOST": "10.0.4.20" }
    }
  }
}
```

| Env var | Default | Meaning |
|---|---|---|
| `BUSYBAR_HOST` | `10.0.4.20` | USB address, or the bar's Wi-Fi IP |
| `BUSYBAR_TOKEN` | unset | Access key (4–10 digit PIN). Only enforced over Wi-Fi |
| `BUSYBAR_APP` | `mcp-scratch` | Default `application_name` for draws and assets |

A bar plugged in over USB comes up at `10.0.4.20` with no Wi-Fi setup needed.

## Tools

| Tool | Purpose |
|---|---|
| `connect` | Point at a bar, report firmware and API version |
| `device_status` | Firmware, uptime, battery, brightness, volume |
| `displays` | Exact geometry of both displays — call before laying anything out |
| `draw` | Draw elements, with bounds validation |
| `preview` | Read the display back as a PNG |
| `clear` | Clear both displays |
| `upload_asset` | Convert a local image/audio file and upload it |
| `play_audio` / `stop_audio` | Play an uploaded asset |

Supported element types come from `busylib`: `text`, `image`, `rectangle`, `countdown`, `animation`.
Fonts: `tiny`, `small`, `normal`, `condensed`, `bold`, `large`, `extra_large`, `global`.

## Example

> "Put BUILDING on the front display and show me how it looks."

```python
draw(elements=[{
    "id": "status", "type": "text", "x": 2, "y": 4, "display": "front",
    "text": "BUILDING", "font": "small",
}])
preview(which="front")
```

The agent gets the PNG back and can see the text was clipped, then shorten it — instead of guessing.

## Development

```bash
git clone https://github.com/jreakin/busybar-mcp && cd busybar-mcp
uv venv && uv pip install -e ".[dev]"
uv run pytest -q
```

The whole suite runs against `httpx.MockTransport`, so **no hardware is needed** to develop or to
verify a change. Device response shapes in the mock are taken from `busylib`'s own pydantic models
rather than guessed — notably `SuccessResponse` requires `result`, `StatusSystem.uptime` is a string,
and `/api/screen` returns L4-packed bytes for the back display (two pixels per byte).

## Compatibility

Built against `busylib` 1.3.0. Bars ship on firmware 1.0.2, which serves API `24.3.0`; update the
firmware early (`python -m examples.setup.main` in the `busylib-py` repo) since the library targets
`25.0.0`. Errors distinguish between three cases so you know which one you have: device rejected the
request, firmware/library schema mismatch, or genuinely unreachable.

## License

MIT
