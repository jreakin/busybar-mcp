# ARCHITECTURE.md
# Version: 1.0.0
# Last Updated: 2026-08-16

## System overview

busybar-mcp is a single MCP server, not a multi-agent system — there's one process, one tool
registry, one connection to one device. `src/busybar_mcp/server.py` is the entire implementation.

```
Agent (Claude Code, etc.) → MCP tool call → server.py → busylib → BUSY Bar device (HTTP)
                                    ↑                                      │
                                    └──────────── preview (PNG) ───────────┘
```

The `draw → preview → adjust` loop is the point of the whole project (see README "Why this
exists"). `preview` reads the actual framebuffer back rather than trusting the draw response,
because the device returns success for draws that render nothing.

## Components

| Component | Responsibility |
|---|---|
| `mcp` (`FastMCP` instance) | Tool registry + MCP protocol handling |
| `_Conn` / `_client()` | Lazy, single-connection lifecycle to one `BusyBar` client per process. `connect()` resets and rebuilds it. |
| `_wrap(exc)` | Classifies every `busylib` exception into one of three causes — device rejected, schema/version mismatch, unreachable — each with different, actionable advice. See "Error architecture" below. |
| `_check_bounds(elements)` | Pre-flight validation against real display geometry (`bbdisplay.get_display_spec`), since the device silently drops out-of-bounds elements instead of erroring. |

## Tool registry

| Tool | Risk | I/O |
|---|---|---|
| `connect` | LOW | resets client, hits `/api/version` |
| `device_status` | LOW | reads firmware/uptime/battery/brightness/volume |
| `displays` | LOW | pure — no device call, returns static geometry |
| `draw` | LOW | writes to device display |
| `preview` | LOW | reads device framebuffer, returns PNG |
| `clear` | LOW | writes (clears both displays) |
| `upload_asset` | LOW | reads local file, converts, uploads to device |
| `play_audio` / `stop_audio` | LOW | writes (audio playback) |

Nothing here is destructive or reaches beyond one local/LAN device — there's no database, no
multi-tenant state, no financial or irreversible operation. All risk classification is LOW; see
`docs/GUARDRAILS.md` for the two real risks that exist (silent no-ops, firmware/API drift).

## Error architecture

`_wrap()` is the one piece of real design work in this codebase. Collapsing the three failure
modes below into a single exception type sends an agent chasing the wrong problem:

1. **Device rejected the request** (`BusyBarAPIError`) — e.g. wrong `BUSYBAR_TOKEN`. Advice:
   check the access key.
2. **Schema/version mismatch** (`BusyBarResponseValidationError` and friends) — the bar answered,
   but not in the shape `busylib` expected. Advice: check `device_status` firmware vs. the
   installed `busylib` version. This is the API-24.3.0-vs-25.0.0 drift risk from the README.
3. **Unreachable** — genuine network/connection failure. Advice: check power/USB/Wi-Fi address.

See `test_schema_mismatch_is_not_reported_as_a_connection_problem` for why this split is tested
directly, not just asserted in a docstring.

## AI Decision Records (ADRs)

Tool/library choices with real tradeoffs are documented in `docs/adr/` (append-only). See
`docs/adr/0001-initial-tool-selection.md` for why `fastmcp` + `busylib` + pytest/httpx.MockTransport
were chosen. New ADRs follow the same file, format, and process.
