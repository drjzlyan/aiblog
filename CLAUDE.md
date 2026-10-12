# Blog repo (self-sufficient: no MCP servers, no skills)

Your Medium blog, run from one repo. Everything needed lives here: workflow
docs, roadmaps, and `tools/` automation. Identity (handle, voice, tags) comes
from `.env` (`MEDIUM_HANDLE`, set by `./scripts/setup.sh`) and `CUSTOM.md`.

## Session start (do this first, every session)

1. Read `STATE.md` (where we left off, open TODOs), then `ROADMAP.md` (index),
   then the relevant `roadmaps/<series>.md`. Continue from there.
   If repo-root `CUSTOM.md` exists, read it too and treat it as overrides
   (voice, account, tags, user MCP/skills notes). See `CUSTOM.example.md`.
2. Full workflow (create / edit / publish / new series / standalone):
   `docs/WORKFLOW.md`.
3. At the end of every task, update `STATE.md` and the roadmap/index so the
   next session (any machine) resumes cleanly.
4. New machine: `git clone <repo> && cd <repo> && ./scripts/setup.sh`.

## Quick reference

- New post scaffold: `uv run python tools/new_post.py <slug> --title "<title>"`
- Run code: `uv run python tools/run_example.py posts/NN-slug/code/x.py`
- Screenshot output: `uv run python tools/render_output.py posts/NN-slug/code/x.py posts/NN-slug/images/output_x.png` (then view the PNG)
- Build: `uv run python tools/build_post.py posts/NN-slug`
- Publish draft: `uv run python tools/medium_publish.py posts/NN-slug`
- Edit draft in place: `uv run python tools/medium_edit.py <draft-id> posts/NN-slug`
- Go live: add `--live --tags Tag1,Tag2` to the publish command
- List published: `uv run python tools/medium_list.py`

First Medium run opens a headed browser window: log in once (session saved to
`medium-session.json`, git-ignored). If a script hangs, the window is waiting
for login.

## Rules

- Draft by default; live only when the user says so for that post.
- Never publish code that was not run. Never claim output that was not produced.
- Environment: `uv`, Python 3.12 (pinned). Add deps with `uv add`.
- Secrets (`.env`, `medium-session.json`) are never committed.
