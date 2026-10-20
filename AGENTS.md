# Blog repo (self-sufficient: no MCP servers needed)

Your Medium blog, run from one repo, usable by any coding agent (Codex,
Gemini CLI, Cursor, Claude Code...). This file is the single source of agent
instructions; `CLAUDE.md` imports it. Everything
needed lives here: workflow docs, roadmaps, and `tools/` automation. Identity
(handle, voice, tags) comes from `.env` (`MEDIUM_HANDLE`, set by
`./scripts/setup.sh`) and `CUSTOM.md`.

## Session start (do this first, every session)

1. Read `STATE.md` (where we left off, open TODOs), then `ROADMAP.md` (index),
   then the relevant `roadmaps/<series>.md`. Continue from there.
   If repo-root `CUSTOM.md` exists, read it too and treat it as overrides
   (voice, account, tags, user MCP/skills notes). See `CUSTOM.example.md`.
2. Full workflow (create / cover / tags / draft / go live / revise / import):
   `docs/WORKFLOW.md`.
3. At the end of every task, update `STATE.md` and the roadmap/index so the
   next session (any machine) resumes cleanly.
4. New machine: `git clone <repo> && cd <repo> && ./scripts/setup.sh`.

## Quick reference

Every post is `posts/NN-slug/`: `post.md` (frontmatter: `subtitle`, `tags`,
`cover_*`), `code/`, `images/`, and tool-written `medium.json` (story id,
status, URL). Tools take the post directory; ids are looked up for you.

- New post: `uv run python tools/new_post.py <slug> --title "<title>"`
- Run code: `uv run python tools/run_example.py posts/NN-slug/code/x.py`
- Screenshot output: `uv run python tools/render_output.py posts/NN-slug/code/x.py posts/NN-slug/images/output_x.png` (then view the PNG)
- Research tags: `uv run python tools/medium_topics.py "Term" "Term 2"`
- Pick thumbnail: `uv run python tools/medium_cover.py posts/NN-slug search "<query>" ...`,
  view `cover_candidates.png`, then `... pick <N>`
- Build: `uv run python tools/build_post.py posts/NN-slug`
- New draft: `uv run python tools/medium_publish.py posts/NN-slug`
- Revise draft in place: `uv run python tools/medium_edit.py posts/NN-slug`
  (published post: add `--republish`, only with the author's OK)
- Go live: `uv run python tools/medium_golive.py posts/NN-slug [--dry-run]`
  (older draft not in repo: `medium_golive.py <draft-id> --tags A,B`)
- List stories + ids: `uv run python tools/medium_list.py [--drafts|--published|--all]`
- Import an older story: `uv run python tools/medium_pull.py <id-or-url>`

First Medium run opens a headed browser window: log in once (session saved to
`medium-session.json`, git-ignored). If a script hangs, the window is waiting
for login.

## Rules

- Draft by default; live only when the user says so for that post.
- Never publish code that was not run. Never claim output that was not produced.
- View every image you publish (outputs, plots, the cover contact sheet, the
  publish-dialog screenshot) before reporting success.
- Never delete Medium stories; list leftovers for the user to delete by hand.
- Environment: `uv`, Python 3.12 (pinned). Add deps with `uv add`.
- Secrets (`.env`, `medium-session.json`) are never committed.
