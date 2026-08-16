# GUARDRAILS.md
# Version: 1.0.0
# Last Updated: 2026-08-16
# Total Signs: 3

Persistent safety constraints for this codebase. Kept intentionally short — most of the
enterprise GUARDRAILS.md template (PII handling, moderation, multi-agent escalation, financial
operation gates) doesn't apply to a single-device MCP tool server with no user data and no
destructive operations. The real risks here are narrower.

## Privilege boundaries

```
Allowed:
  - Read:  src/, tests/, README.md, UPSTREAM-ISSUE.md
  - Write: src/, tests/

Forbidden without asking first:
  - Publishing to PyPI, tagging a release, editing LICENSE (see AGENTS.md Agent Scope)
  - Committing BUSYBAR_TOKEN or any device host IP into source, tests, or examples
```

## SIGN #1: Silent no-op on out-of-bounds draws

**Trigger:** Writing or modifying anything that calls `bb.display_draw(...)` without going
through `_check_bounds()` first.
**Instruction:** Every draw path must validate element coordinates against the real display
geometry before sending to the device, and surface violations as warnings in the response — never
let an out-of-bounds element silently vanish and report success.
**Reason:** The device itself returns HTTP 200 for draws that render nothing. Without this check,
an agent sees success and a blank bar with no way to know why (see README "Why this exists").
**Provenance:** Design decision, encoded in `_check_bounds` / `draw()` — see
`test_draw_flags_out_of_bounds_instead_of_silently_dropping`.

## SIGN #2: Firmware/library API version drift

**Trigger:** Any change to response parsing, or any test failure that looks like a schema
mismatch rather than a logic bug.
**Instruction:** Check `device_status`'s firmware field against the installed `busylib` version
before assuming a bug in this codebase. Report schema mismatches via `_wrap()`'s dedicated branch
— never let them surface as "could not reach the bar."
**Reason:** Shipped firmware serves API 24.3.0; `busylib` targets 25.0.0. This is a live,
ongoing gap, not a one-time migration — it will keep causing shape mismatches until firmware
catches up.
**Provenance:** README "Compatibility" section; `_wrap()`'s three-way classification;
`test_schema_mismatch_is_not_reported_as_a_connection_problem`.

## SIGN #3: BUSYBAR_TOKEN handling

**Trigger:** Adding logging, error messages, examples, or test fixtures that touch `BUSYBAR_TOKEN`
or any device host/IP.
**Instruction:** Never log, print, or hardcode the token. Error messages may reference *that* a
token is required, never its value. Tests use fixed placeholder hosts (`10.0.4.20`), never a
real Wi-Fi address.
**Reason:** It's a PIN-style access key, enforced over Wi-Fi. `_wrap()` already follows this rule
in its 403 branch — keep new code consistent with it.
**Provenance:** AGENTS.md "Conventions already established"; `_wrap()`'s 403 handling.

## Escalation

Stop and ask before: adding a new external dependency, changing the error-classification
boundaries in `_wrap()`, or touching anything under `Off-limits` in AGENTS.md's Agent Scope.

## Agent-learned Signs

*None yet.* Append here (same Trigger/Instruction/Reason/Provenance format) if a new failure
pattern shows up during development.
