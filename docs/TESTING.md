# TESTING.md

**Version:** 1.0.0 | **Last Updated:** 2026-08-16

## Strategy

All 13 tests live in `tests/test_tools.py` and run entirely against `httpx.MockTransport` — no
BUSY Bar hardware is required to develop or verify a change. Mock response shapes are taken from
`busylib`'s own pydantic models rather than guessed (see README "Development" for the specific
gotchas: `SuccessResponse.result`, `StatusSystem.uptime` as a string, L4-packed back-display
bytes). Shared device-mocking setup lives in the `mock_bar` fixture in `tests/conftest.py`.

```bash
uv run pytest -q       # all tests, ~5-6s
ruff check .            # lint
```

## Why there's no `tests/integration/`

The canonical Python project layout splits `tests/unit/` (pure, no I/O) from `tests/integration/`
(real services, env-var-guarded). That split doesn't apply here: the only external I/O this
project does is talk to physical BUSY Bar hardware over HTTP, and there is no safe way to run
that in CI or on a machine without the device plugged in. `httpx.MockTransport` isn't a
lower-fidelity substitute for a real integration test here — the mock response shapes are pinned
directly to `busylib`'s pydantic models, so a shape drift between installed `busylib` and the
mocks would show up as a schema mismatch the same way a real device answering unexpectedly would
(see `test_schema_mismatch_is_not_reported_as_a_connection_problem`). If real-hardware testing is
ever added, it should be a separate, manually-triggered suite — not folded into `uv run pytest`.

## What's actually being verified

- Real display geometry (`test_displays_reports_real_geometry`) — 72×16 front, 160×80 back.
- The device's silent-drop failure mode is caught and surfaced as a warning, not swallowed
  (`test_draw_flags_out_of_bounds_instead_of_silently_dropping`).
- Both framebuffer wire formats decode correctly — RGB888 front, L4-packed-then-unpacked back
  (`test_preview_front_returns_scaled_png`, `test_preview_back_handles_greyscale_framebuffer`).
- The three-way error classification in `_wrap()` doesn't collapse a schema mismatch into "check
  your cable" (`test_schema_mismatch_is_not_reported_as_a_connection_problem`).
- The full MCP tool registry is actually exposed (`test_server_registers_expected_tools`).

## Adding a new tool

1. Add the mock endpoint response to `handler()` in `tests/test_tools.py` (or `conftest.py` if
   the fixture needs new device-response shapes).
2. Write the test using the existing `call(tool, **kw)` helper, which invokes a `FastMCP` tool's
   underlying function directly.
3. If the tool writes to the device, assert on the captured payload (see `drawn` list pattern in
   `test_draw_sends_expected_payload`) — not just that the call didn't raise.
4. Update the README tool table — the AGENTS.md Definition of Done checks for this.
