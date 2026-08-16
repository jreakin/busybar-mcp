# NOTES.md

Cross-platform context for anyone (human or agent) picking this project up cold.

## What this is

An MCP server that lets an AI coding agent draw to, preview, and inspect a BUSY Bar LED device.
Authoring-loop only — not a runtime status daemon (see README "What it deliberately doesn't do").

## Where to look for what

- **README.md** — install, tool list, env vars, quickstart example.
- **docs/ARCHITECTURE.md** — components, tool registry, the `_wrap()` error-classification design.
- **docs/TESTING.md** — test strategy, why there's no real-hardware integration tier.
- **docs/GUARDRAILS.md** — the three real risks (silent no-ops, firmware/API drift, token handling).
- **docs/adr/** — why fastmcp/busylib/pytest+MockTransport were chosen.
- **AGENTS.md** — agent scope, conventions, Definition of Done.
- **UPSTREAM-ISSUE.md** — a known bug in upstream `busylib`, not this project.

## The three gotchas that have already bitten this codebase

1. **Bundle IDs, not names** — n/a here (that's the sibling `jre-busy-bar` project's activity
   detector, not this one). Don't confuse the two repos' gotchas.
2. **Silent out-of-bounds drop** — the device returns HTTP 200 for draws that render nothing.
   Never trust a draw response alone; `preview` is the only real confirmation.
3. **Firmware/library version drift** — shipped firmware serves API 24.3.0, `busylib` targets
   25.0.0. Schema mismatches are a live, ongoing risk, not a one-time migration to fix and forget.

## Repo relationship

This package is vendored into the `jre-busy-bar` repo as a git submodule but is otherwise fully
independent — own GitHub repo (`jreakin/busybar-mcp`), own MIT license, own `AGENTS.md`. Changes
here are committed in this repo, not the parent.
