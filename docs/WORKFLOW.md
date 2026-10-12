# Blog workflow (self-sufficient: no MCP servers, no skills)

Everything in this repo. The agent running this workflow needs only this file,
`STATE.md`, `ROADMAP.md`, and the `tools/` scripts. Medium is driven through
`tools/medium_*.py` (headed Chromium via Playwright); the repo is the source
of truth and every published word is reproducible from it.

## Concepts

- **Series**: a sequence of posts on one topic, tracked by a roadmap file in
  `roadmaps/<series>.md` (phases, topics, `todo`/`drafted`/`published` rows).
  Series are registered in the `ROADMAP.md` index.
- **Standalone post**: a one-off post on any topic, no series required. Tracked
  in the standalone table in `ROADMAP.md` so nothing published is ever lost.
- **Post directory**: `posts/NN-slug/{post.md,code/,images/}`. `NN` is a global
  creation counter (next number via `tools/new_post.py`), not roadmap order.
- **Source of truth**: the repo. Medium drafts are disposable copies; edits
  always start locally and are pushed to the same draft URL.

## Public template, private content

This repo is public and generic. Personal content is git-ignored and never
pushed: `posts/`, `STATE.md`, your own `roadmaps/*.md` (only
`roadmaps/example-series.md` is tracked), `CUSTOM.md`, `.env`,
`.mcp.json`, `medium-session.json`.

- `ROADMAP.md` tracks shared/example content. Record private progress in your
  (ignored) `STATE.md` and series file instead.
- Templates ship as `*.example.md` (`STATE.example.md`, `CUSTOM.example.md`);
  `./scripts/setup.sh` materialises your private copies on first run.

## Session start / end (every session)

1. Read `STATE.md` (where we left off, open TODOs), then `ROADMAP.md`, then the
   relevant `roadmaps/<series>.md`. Continue from there. If repo-root
   `CUSTOM.md` exists, apply it as overrides (see `CUSTOM.example.md`).
   The repo ships two skills: `grilling` (settle decisions before drafting)
   and `medium` (own a post end to end). No MCP servers ship with the repo;
   add your own via `.mcp.json` (see `.mcp.json.example`).
2. At the end of every task, update `STATE.md` and the roadmap/index so the
   next session (any machine) resumes cleanly.
3. New machine: `git clone <repo> && cd <repo> && ./scripts/setup.sh`.

## Starting a new series from any topic

When the user names a topic (e.g. "sourdough baking", "Rust for ML"):

1. Ask at most 2-3 questions if the topic/audience is genuinely ambiguous
   (who is it for, how deep, how many posts). Otherwise proceed.
2. Draft `roadmaps/<topic-slug>.md`: 3-8 phases, each with ordered topics as
   rows (`| # | Topic | Status | Link |`, all `todo`). Order follows
   prerequisites. Note planned Medium tags per row where known.
3. Register it in `ROADMAP.md` (series table) and `STATE.md`.
4. Do NOT write posts yet. Present the roadmap; the user picks what to write.

## Writing the next post ("publish a blog" / "write the next blog")

1. **Topic:** if the user names one, do that (add it to the series roadmap if
   missing). Otherwise take the first `todo` row of the active series.
2. If anything is genuinely ambiguous, ask. Don't assume.
3. Scaffold: `uv run python tools/new_post.py <slug> --title "<title>"`.
4. **Every code example is a real file in `code/`** and must be run:
   `uv run python tools/run_example.py posts/NN-slug/code/x.py` (writes
   `x.out.txt`; non-zero exit = fix the code first). Plots are saved as PNGs
   into `../images/`. Verify claims in the prose against the actual output
   (run a quick check for any number or threshold you state).
   Non-technical posts may have no code (precedent: `posts/05-*`).
5. **Screenshot of every output:**
   `uv run python tools/render_output.py posts/NN-slug/code/x.py posts/NN-slug/images/output_x.png`
   then view each PNG to check it. Images are rendered from the real `.out.txt`.
6. In `post.md` use `{{code:x.py}}` and `{{img:file.png|alt}}`, never paste code
   by hand. Build: `uv run python tools/build_post.py posts/NN-slug`.
7. **Publish** as draft:
   `uv run python tools/medium_publish.py posts/NN-slug`
   (prints the draft edit URL). First run opens a browser window: log in once.
8. Update the series roadmap (status + draft URL) or the standalone table, plus
   `STATE.md`, and report the URL.

## Writing a standalone post (ignores any roadmap)

"Write a standalone post on X" follows the same steps 3-8 above, except: no
roadmap row is required. Add one row to the standalone table in `ROADMAP.md`
(status + draft URL + local path) so it stays resumable.

## Editing an existing post

The repo is the source of truth, so edits flow local -> Medium, never the
reverse:

1. Apply the requested change in `posts/NN-slug/` (`post.md` and/or `code/`).
2. If code changed: re-run it (`run_example.py`), re-render its screenshot
   (`render_output.py`), view the PNG. If only prose changed, skip this.
3. Rebuild (`build_post.py`), then push to the **same** draft URL:
   `uv run python tools/medium_edit.py <draft-id-or-url> posts/NN-slug`
   No duplicate draft is created; old images are removed with their blocks.
4. If the draft id was lost (URL not in the roadmap), publish fresh with
   `medium_publish.py` and record the new URL; note the orphaned draft for
   manual deletion in the browser (`/p/<id>/edit`).
5. Update roadmap/`STATE.md`.

## Going live

Drafts are the default. Publish live only when the user says so for that post:

`uv run python tools/medium_publish.py posts/NN-slug --live --tags Tag1,Tag2`

Draft publishing cannot set tags (Medium's tag input only exists in the live
dialog), so planned tags live in the roadmap row until go-live.

## Rules

- **Draft by default.** Only publish live when the user says so for that post.
- Never publish code that was not run. Never claim output that was not produced.
- Voice (match existing posts): problem-first hook, short sections each with a
  "Why it matters" line, short code blocks, practical closing, 8-12 min read,
  beginner-to-intermediate. End with "What's next" + series footer. (A new
  series may define its own voice in its roadmap file header.)
- Environment: `uv`, Python 3.12 (pinned). Add deps with `uv add`.
- Secrets (`medium-session.json`, `.env`) are never committed.

## Tool reference

| Script | Purpose |
|---|---|
| `tools/new_post.py <slug>` | Scaffold `posts/NN-slug/` with next global number |
| `tools/run_example.py <code.py>` | Run example, save real output to `.out.txt` |
| `tools/render_output.py <code.py> <png>` | Terminal-style PNG from the real output |
| `tools/build_post.py posts/NN-slug` | Expand `{{code}}`/`{{img}}` into `post.built.md` |
| `tools/medium_publish.py posts/NN-slug [--live --tags ..]` | New draft (default) or live publish |
| `tools/medium_edit.py <draft-id> posts/NN-slug` | Rewrite a draft in place, same URL |
| `tools/medium_list.py` | List published posts (title, url, date) |
| `tools/medium_common.py` | Shared browser/session/converter (`--selftest` for converter unit test) |

## Known Medium behaviour (verified)

- Medium browser automation needs a headed window (Cloudflare blocks headless).
  If a script hangs, the browser window is waiting for login.
- Medium splits pasted code at blank lines and wraps blockquotes in empty
  quotes; `medium_common.markdown_to_editor_html` normalises this. If
  formatting regresses, re-verify a draft in the editor (image count, `pre`
  count, blockquote text) before reporting success.
- Duplicate drafts can share a title; delete by draft id (`/p/<id>/edit`),
  never by title. Deletion is manual in the browser (no automation for it).
- Length target is 8-12 min read; short posts read as thin — aim longer.
