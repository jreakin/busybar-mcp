# Plans

Every plan lives in its own `docs/plans/{NNNN}-{slug}/` folder. Numbers are sequential and
never reused, mirroring `docs/adr/`'s numbering.

```text
docs/plans/{NNNN}-{slug}/
  PLAN.md      # the plan itself
  STATUS.md    # draft | in-progress | complete | abandoned
```

No loose `.md` plan files directly in `docs/plans/` root — only numbered subfolders.

**Not** root `plans/`, not `docs/superpowers/plans/`, not a root `SPEC.md` — those are
superseded locations (ADR-0060). This is the current source of truth for execution-stage plans.
UI scratch plans live in `.cursor/plans/` (gitignored, never source of truth).

## Active / recent plans

_(none yet)_
