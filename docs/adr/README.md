# AI Decision Records (ADRs)

Documents *why* a specific tool, library, or architectural approach was chosen — not *how* to
operate something (that's a RUNBOOK entry, which this project doesn't have yet since there's no
production ops surface). Append-only: accepted records are never edited; superseded ones are
marked `Superseded by ADR-{NNN}`, not deleted.

## File naming

`{NNNN}-{slug}.md` — e.g. `0001-initial-tool-selection.md`.

## Template

```markdown
# ADR-{NNNN}: {title}

**Date:** {YYYY-MM-DD}
**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-{NNNN}

## Context
What problem or decision point prompted this record?

## Decision
What was chosen, and for what?

## Rationale
Why this over the alternatives considered?

## Consequences
What changes, constraints, or downstream dependencies result from this decision?
```

## Index

- [0001 — Initial tool selection](0001-initial-tool-selection.md) — fastmcp, busylib, pytest/httpx.MockTransport
