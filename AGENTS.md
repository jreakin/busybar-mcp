# AGENTS.md
# Version: 1.0.0
# Last Updated: 2026-08-16
# Environment: dev
# Project: busybar-mcp
# Maintainer: jreakin

You are working on **busybar-mcp** — an unofficial MCP server that lets an AI coding agent
draw to, preview, and inspect a BUSY Bar LED device (`busylib` + `fastmcp`). See `README.md`
for the tool list and device model; see `UPSTREAM-ISSUE.md` for a known upstream `busylib` bug.

## Agent Scope
Reads:      src/, tests/, docs/, prompts/, README.md, UPSTREAM-ISSUE.md
Writes:     src/, tests/, docs/, prompts/
Executes:   uv, ruff, pytest, git, gh (read + PR creation)
Off-limits: publishing to PyPI, tagging releases, editing LICENSE — ask first

## Commands
```bash
uv venv && uv pip install -e ".[dev]"   # setup
uv run pytest -q                        # all tests — pure httpx.MockTransport, no hardware needed
ruff check .                            # lint
```

## Conventions already established in this codebase — don't restate, just follow
- Tools live in `src/busybar_mcp/server.py`; response shapes are validated against `busylib`'s
  own pydantic models in tests, not guessed (see README "Development" section for the specific
  gotchas: `SuccessResponse.result`, `StatusSystem.uptime` as string, L4-packed back-display bytes).
- Match BUSY Bar device errors to one of three causes (device rejected / schema mismatch /
  unreachable) — see `test_schema_mismatch_is_not_reported_as_a_connection_problem`. Don't
  collapse these into a generic exception.
- `BUSYBAR_TOKEN` is a PIN-style access key, only enforced over Wi-Fi — never log it, never
  hardcode it in tests or examples.

## Documentation Priority
Before writing code against `busylib`, `fastmcp`, or `pillow` APIs: try Context7 MCP
(`resolve-library-id` → `get-library-docs`) first. Fall back to the real docs
(`docs.busy.app/bar/dev`, `busylib-py` on GitHub) before relying on training-data memory —
`busylib` targets device API 25.0.0 while shipped firmware serves 24.3.0, so version drift is
a real, current risk here, not a hypothetical.

## Definition of Done
- [ ] `ruff check .` clean
- [ ] `uv run pytest -q` passes
- [ ] New tools/behavior reflected in the README tool table if user-facing
- [ ] No secrets (`BUSYBAR_TOKEN`, host IPs) committed

## Notion References
N/A — recorded: independent open-source project (own GitHub repo, MIT license), not an
Abstract Data client engagement. No Client/Project Notion entries apply.
