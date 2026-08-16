# Prompts — Versioned Agent System Prompts

This directory is the version registry for any AI-agent system prompts this project defines
(i.e. prompts that get sent to a model as `system_prompt`/instructions for an agent *this
project runs* — not Claude Code's own `.claude/agents/` subagent definitions, which are
config, not versioned prompt artifacts).

**This file is the registry** — one `##` section per agent below, listing its current version,
model, last updated, and a changelog. Never gitignore `prompts/` — these are versioned source
artifacts, not build output or session scratch.

## Structure per agent

```
prompts/{agent-name}/
  current.md      # active prompt — MUST start with a "# Version: X.Y.Z" header
  v{X.Y.Z}.md      # versioned snapshot — required, not a stub
  .gitkeep
```

No per-subdirectory `CHANGELOG.md` — history lives in this file, under the agent's section.

## Versioning rules

| Part  | When to bump                                          |
|-------|--------------------------------------------------------|
| MAJOR | Behavior change, full rewrite, model swap              |
| MINOR | New tool, guardrail added/modified, scope change       |
| PATCH | Wording tweak, tone adjustment, token optimization      |

## Agents

_(none yet — this project doesn't currently run its own LLM agent with a system prompt; it's
an MCP tool server invoked by whatever agent is using it. Add a `##` section here, and a
`prompts/{agent-name}/` directory per the structure above, the first time one is introduced.)_
