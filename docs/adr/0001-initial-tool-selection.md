# ADR-0001: Initial tool selection

**Date:** 2026-08-16
**Status:** Accepted

## Context

busybar-mcp needed an MCP server framework, a way to talk to the BUSY Bar device, and a testing
approach that doesn't require physical hardware to develop or run in CI.

## Decision

- **`fastmcp`** for the MCP server framework and tool registration (`@mcp.tool` decorators).
- **`busylib`** (the vendor's official Python library) for all device communication, rather than
  raw HTTP calls.
- **`pytest` + `httpx.MockTransport`** for the entire test suite — no real device in tests.

## Rationale

- `busylib` over raw HTTP: tracks the vendor's own compatibility handling (retries, response
  parsing, error types) instead of duplicating and re-diverging from it. The cost is inheriting
  `busylib`'s API-version target (25.0.0) even though shipped firmware only serves 24.3.0 — see
  `docs/GUARDRAILS.md` SIGN #2. Alternatives considered: hand-rolled `httpx` client directly
  against the documented REST API — rejected because it would mean re-solving problems `busylib`
  already solves (response validation, framebuffer unpacking) with no compatibility benefit.
- `httpx.MockTransport` over a real-device integration tier: `busylib` supports transport
  injection natively, so tests can mock at the HTTP boundary using `busylib`'s own pydantic
  response models as the source of truth for shape — meaning a shape drift between the mocks and
  reality shows up the same way a real device answering unexpectedly would (as a schema-mismatch
  `ToolError`, not a silent pass). This gets most of the confidence of a real integration test
  without needing hardware plugged into CI. See `docs/TESTING.md` for the full reasoning.
- `fastmcp`: it's the framework the project already targets in `pyproject.toml` and is what the
  tool-decorator pattern (`@mcp.tool`) in `server.py` is built on; no alternative was seriously
  evaluated since this was a from-scratch choice at project start, not a migration.

## Consequences

- Any new tool must go through `busylib`'s API surface, not raw HTTP — keeps the compatibility
  benefit but means waiting on `busylib` if the device exposes something it doesn't wrap yet.
- The test suite's fidelity is bounded by how well `httpx.MockTransport`'s handler mirrors real
  device responses — mock shape changes must be checked against `busylib`'s pydantic models, not
  assumed (see `docs/GUARDRAILS.md`).
- No real-hardware CI tier exists or is planned; if one is ever added, it must be a separate,
  manually-triggered suite, not folded into `uv run pytest` (see `docs/TESTING.md`).
