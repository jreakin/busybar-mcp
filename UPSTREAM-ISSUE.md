# Draft: issue to open on busy-app/busylib-py

Post this *early* — before publicising the repo anywhere else. A link from busy-app reaches the
Flipper audience; nothing you do on your own will. It also converts the main risk (they ship an
official MCP and yours is orphaned) into the main opportunity.

Keep the tone as an offer, not an announcement. Don't ask them to endorse it; ask whether they want
it upstream.

---

**Title:** MCP server for busylib — happy to upstream or hand over

Hi — I've built a small [Model Context Protocol](https://modelcontextprotocol.io) server on top of
`busylib` and wanted to check in before taking it any further, since it sits close to the agent
support you already ship in `AGENTS.md`.

Repo: https://github.com/jreakin/busybar-mcp

**What it does.** It's scoped strictly to the authoring loop, not runtime:

- `preview` fetches `/api/screen` and returns the framebuffer as a PNG, so a coding agent can see what
  it actually drew rather than assuming
- `draw` validates element coordinates against `FRONT_DISPLAY` / `BACK_DISPLAY` first, since
  out-of-bounds elements currently render nothing while still returning success — a confusing failure
  for anyone (human or agent) laying out a 72×16 display for the first time
- `upload_asset` runs `converter.convert_for_storage` before `assets_upload`
- `connect` / `device_status` / `displays` for orientation

It deliberately does **not** wrap the full API, and doesn't attempt anything long-running — presence,
timers and status daemons are a much better fit for MQTT or a plain `busylib` process, and I didn't
want to encourage people to build those over MCP.

**Why I'm opening this.** Two questions:

1. Is an MCP server something you'd want in-tree (either under `busy-app/` or as an
   `examples/mcp/`)? I'm happy to contribute it rather than maintain a parallel thing, and equally
   happy to hand it over outright.
2. If you'd rather keep it external, would you take a link from the README or docs so people can find
   it?

Either answer is genuinely fine — I'd just rather coordinate now than have two half-maintained
servers show up later.

**Two small things I ran into**, unrelated to the above and worth reporting on their own:

- The `/api/screen` docstring notes the `Content-Type: image/bmp` header is misleading. It might be
  worth surfacing the decoded-length expectations (front RGB888 3456 bytes; back L4-packed 6400 →
  unpacked 12800) in the docs, since that's the part that's easy to get wrong from outside.
- Silent no-op on out-of-bounds elements is the single most confusing behaviour I hit. Even a warning
  in `display_draw` when coordinates exceed the target `DisplaySpec` would save people a lot of time.

Thanks for `busylib` and for `AGENTS.md` — the latter is unusually good and made this straightforward
to build against.

---

## After they reply

- **Yes, upstream it** → best case. Move it, keep your name in the commit history.
- **No, but we'll link it** → also good. Get the link into the README, then post to the community app
  gallery (`maxswinkels/busybar-apps`), the Flipper forum/Discord, and the MCP registries.
- **No reply in ~2 weeks** → publish anyway and link *to* them prominently. Keep the "unofficial"
  wording in the README either way; the Flipper community is protective of the brand and the goodwill
  is worth more than the ambiguity.
