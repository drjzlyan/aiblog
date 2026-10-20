# Blog workflow (self-sufficient: no MCP servers, works with any coding agent)

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
- **Post directory**: `posts/NN-slug/`. `NN` is a global creation counter
  (next number via `tools/new_post.py`), not roadmap order.
  - `post.md`: the post, starting with frontmatter the agent decides:
    ```
    ---
    subtitle: One sentence shown under the title in feeds (max 140 chars)
    tags: Statistics, Machine Learning, Python      (max 5 Medium topics)
    cover_query: dice probability                   (set by medium_cover.py)
    cover_id: uKlneQRwaxY                           (Unsplash photo id)
    cover_author: Edge2Edge Media
    ---
    # Title
    ```
  - `code/`, `images/`: tested examples and their real outputs.
  - `medium.json`: written by the tools only (story id, edit URL, status,
    live URL, tags). It is how every command finds the story: never copy
    draft ids around by hand.
- **Source of truth**: the repo. Medium stories are copies; edits always
  start locally and are pushed to the same story.
- **Scratch draft**: Medium's Unsplash picker and topic box only exist inside
  a story, and any story you type in becomes a saved draft. The tools reuse
  one draft titled "aiblog scratch ..." (id in git-ignored `.aiblog/`).
  Keep it; never publish it.

## Public template, private content

This repo is public and generic. Personal content is git-ignored and never
pushed: `posts/`, `STATE.md`, your own `roadmaps/*.md` (only
`roadmaps/example-series.md` is tracked), `CUSTOM.md`, `.env`,
`.mcp.json`, `medium-session.json`, `.aiblog/`.

- `ROADMAP.md` tracks shared/example content. Record private progress in your
  (ignored) `STATE.md` and series file instead.
- Templates ship as `*.example.md` (`STATE.example.md`, `CUSTOM.example.md`);
  `./scripts/setup.sh` materialises your private copies on first run.

## Session start / end (every session)

1. Read `STATE.md` (where we left off, open TODOs), then `ROADMAP.md`, then the
   relevant `roadmaps/<series>.md`. Continue from there. If repo-root
   `CUSTOM.md` exists, apply it as overrides (see `CUSTOM.example.md`).
   The repo ships two skills: `grilling` (settle decisions before drafting)
   and `medium` (own a post end to end). No MCP servers are needed; add your
   own via `.mcp.json` (see `.mcp.json.example`).
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
   then view each PNG (and each plot) to check it.
6. In `post.md` use `{{code:x.py}}` and `{{img:file.png|alt}}`, never paste code
   by hand.
7. **Subtitle and tags** (the agent decides, frontmatter of `post.md`):
   research candidates with
   `uv run python tools/medium_topics.py "Term 1" "Term 2" ...`
   which prints Medium's real topics with story counts, e.g.
   `Statistics (9.7K)`. Pick up to 5: established topics that precisely
   match the post, mixing broad reach (Machine Learning, Python) with
   specific fit (Hypothesis Testing). Use Medium's exact spelling.
8. **Cover / thumbnail** (the agent decides):
   `uv run python tools/medium_cover.py posts/NN-slug search "<query>" "<query 2>"`
   searches Unsplash through Medium's own picker (no API key) and writes
   `cover_candidates.png`, a numbered contact sheet. **View it**, choose,
   then `... pick <N>`. Choose an image that is on-topic, uncluttered,
   landscape, and readable as a small thumbnail. Queries are capped at 30
   characters; concrete nouns ("dice", "neural network", "server rack")
   work better than abstract ones.
9. Build: `uv run python tools/build_post.py posts/NN-slug` (re-run after any
   change to `post.md` or code; the tools refuse a stale build).
10. **Draft:** `uv run python tools/medium_publish.py posts/NN-slug`. It types
    the title, inserts the Unsplash cover under it (which makes it the
    thumbnail, with Medium's "Photo by X on Unsplash" credit), pastes the
    body, uploads images, verifies the editor (title, image count, code
    block count), and records the story in `medium.json`. It refuses to
    create a second story for the same post. It also refuses a post
    without a cover (`--allow-no-cover` to override), and going live checks
    that the story's first image really is the Unsplash cover.
11. Update the series roadmap (status + URL) or the standalone table, plus
    `STATE.md`, and report the draft URL.

## Writing a standalone post (ignores any roadmap)

"Write a standalone post on X" follows the same steps 3-11 above, except: no
roadmap row is required. Add one row to the standalone table in `ROADMAP.md`
(status + URL + local path) so it stays resumable.

## Going live

Drafts are the default. Publish live only when the user says so for that post.

1. Dry run first: `uv run python tools/medium_golive.py posts/NN-slug --dry-run`
   opens the publish dialog, sets the topics (and reads them back), the
   preview subtitle, checks there is a preview image, and saves
   `publish_dialog.png`. **View it**: thumbnail, title, subtitle, topics.
2. Then: `uv run python tools/medium_golive.py posts/NN-slug`. Records the
   live URL in `medium.json`. Add `--sync` to rewrite the draft from the
   repo first, if local edits were made since the draft was pushed.
3. Older drafts that are not in the repo:
   `uv run python tools/medium_list.py --drafts` (ids), then
   `uv run python tools/medium_golive.py <draft-id> --tags A,B [--subtitle "..."]`
   (or import them first with `medium_pull.py` to revise before going live).
4. One step from a fresh post (draft + live) when the user asks for it:
   `uv run python tools/medium_publish.py posts/NN-slug --live`.

Medium's dialog defaults (paywall, notify subscribers) are left as they are.

## Revising a post (draft or published)

The repo is the source of truth, so edits flow local -> Medium, never the
reverse:

1. If the post isn't in the repo yet (written elsewhere, or before this
   repo), import it: `uv run python tools/medium_pull.py <id-or-url>`. It
   creates `posts/NN-slug/` with Markdown, downloaded images, tags (for
   published posts), the Unsplash cover id, and `medium.json`. Pulled code
   blocks were never run here: move them into `code/` and run them if you
   change them or quote their output. If it found an Unsplash cover, run
   `medium_cover.py ... search/pick` (re-pick the same photo or a new one).
2. Apply the requested change in `posts/NN-slug/` (`post.md` and/or `code/`).
3. If code changed: re-run it (`run_example.py`), re-render its screenshot
   (`render_output.py`), view the PNG. If only prose changed, skip this.
4. Rebuild (`build_post.py`), then push to the **same** story:
   `uv run python tools/medium_edit.py posts/NN-slug`
   The editor is cleared and refilled; no duplicate is created.
   For a **published** post this goes live immediately, so the tool refuses
   unless you pass `--republish`, which you do only when the user approved
   the change.
   It also refuses when the story's live Unsplash cover differs from
   `cover_id` in `post.md`: a sign the story was edited in Medium after the
   repo copy was made. Pull it to a temp dir (`medium_pull.py <id> --into
   /tmp/x`), reconcile `post.md`, and set the cover before retrying.
5. Update roadmap/`STATE.md`.

## Listing

`uv run python tools/medium_list.py` shows drafts and published stories with
ids and, where linked, the local post directory (`--all` adds unlisted and
scheduled; `--json` for machine use).

## Rules

- **Draft by default.** Only publish live, or republish a live post, when the
  user says so for that post.
- Never publish code that was not run. Never claim output that was not produced.
- View every image before publishing: outputs, plots, the cover contact
  sheet, and the publish-dialog screenshot.
- Never delete Medium stories from automation; list leftovers (by id) for the
  user to delete in the browser.
- Voice (match existing posts): problem-first hook, short sections each with a
  "Why it matters" line, short code blocks, practical closing, 8-12 min read,
  beginner-to-intermediate. End with "What's next" + series footer. (A new
  series may define its own voice in its roadmap file header.)
- Environment: `uv`, Python 3.12 (pinned). Add deps with `uv add`.
- Secrets (`medium-session.json`, `.env`) are never committed.

## Tool reference

| Script | Purpose |
|---|---|
| `tools/new_post.py <slug>` | Scaffold `posts/NN-slug/` (frontmatter template) |
| `tools/run_example.py <code.py>` | Run example, save real output to `.out.txt` |
| `tools/render_output.py <code.py> <png>` | Terminal-style PNG from the real output |
| `tools/build_post.py posts/NN-slug` | Expand `{{code}}`/`{{img}}` into `post.built.md`; rejects unrun/stale code |
| `tools/medium_topics.py "term" ...` | Medium's topic suggestions with story counts |
| `tools/medium_cover.py posts/NN-slug search\|pick\|none` | Choose the Unsplash cover/thumbnail |
| `tools/medium_publish.py posts/NN-slug [--live]` | Create the story (draft by default) |
| `tools/medium_golive.py posts/NN-slug\|<id> [--dry-run]` | Publish an existing draft live |
| `tools/medium_edit.py posts/NN-slug [--republish]` | Rewrite a story in place, same URL |
| `tools/medium_list.py [--drafts\|--published\|--all]` | List stories with ids |
| `tools/medium_pull.py <id-or-url>` | Import an existing story into `posts/` |
| `tools/medium_common.py` | Shared browser layer (run it for the converter self-test) |
| `tools/postlib.py` | Frontmatter + `medium.json` (run it for its self-test) |

## Known Medium behaviour (verified 2026-10-20)

- Browser automation needs a headed window (Cloudflare blocks headless).
  If a script hangs, the browser window is waiting for login.
- Medium splits pasted code at blank lines and wraps blockquotes in empty
  quotes; `markdown_to_editor_html` normalises this, and the tools verify
  the editor's code-block and image counts after filling.
- The first image in a story is its default preview image (thumbnail),
  which is why the cover goes directly under the title.
- The publish dialog's final button is "Publish" (not "Publish now"); after
  publishing Medium may land on `/p/<id>/submission`. The tools resolve the
  public URL themselves.
- Topics are added by typing + Enter (clicking suggestions is flaky); the
  topic box disappears once 5 topics are set; topics persist on a draft.
- Clearing a story needs the editor's own select-all (Cmd/Ctrl+A); a
  scripted DOM selection is ignored when the story contains figures.
- Unsplash picker tiles reveal their click target only on hover.
- Any story you type in (even untitled) is saved as a draft.
- Duplicate drafts can share a title; delete by id (`/p/<id>/edit`), never
  by title. Deletion is manual in the browser.
- Length target is 8-12 min read; short posts read as thin; aim longer.
