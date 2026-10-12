# Resume state (update at the end of every task)

Last updated: YYYY-MM-DD

## Where we are

- Active series: <name> (`roadmaps/<series>.md`). Next `todo`: **<topic>**.
- Drafts awaiting the author's review (not live): none yet.

## Open TODOs

- (Add rows here as they come up.)

## Gotchas

- Medium scripts need a headed browser; if a call hangs, the window is waiting for login.
- Session is repo-root `medium-session.json` (git-ignored).
- Prefer `medium_edit.py` (same draft URL) over re-publishing when fixing drafts.
- `*.built.md` is generated; rebuild with `uv run python tools/build_post.py posts/NN-slug`.

Note: this file is git-ignored on purpose — resume state (draft URLs, local
paths) is personal and is never pushed. See `STATE.example.md`.
