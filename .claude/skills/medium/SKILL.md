---
name: medium
description: >
  Write, publish, and update Medium blog posts in this repo — ideate the post,
  draft it with verified code and screenshots, publish it as a draft, or edit
  an existing draft in place. Use when the user wants to write, publish, or
  edit a Medium blog post here.
---

# Medium (repo-owned)

End-to-end owner of a blog post in this repo: from idea to draft URL to
in-place updates. The procedure source of truth is `docs/WORKFLOW.md` — this
skill is the trigger and the quality bar, not a second procedure.

## When to use

- "write a post on X", "publish a blog", "next post in <series>"
- "edit / update / fix the draft", "revise the post", "revise my old post"
- "publish it live", "list my drafts", "publish that older draft"
- "ideate / brainstorm a post" (then grill first, draft second)

Hand ambiguous *decisions* to the **grilling** skill (audience, angle, scope,
series vs standalone) before drafting. Never guess at those.

## Execution protocol

1. **Orient.** Read `STATE.md`, `ROADMAP.md`, the relevant `roadmaps/<series>.md`.
   If repo-root `CUSTOM.md` exists, it overrides defaults (voice, topics,
   account, tags) — apply it.
2. **Ideate (grill).** Settle topic, reader, promise, and outline via grilling.
   Settle the authority mode for the piece: Explainer / Argument / Insight /
   Framework / Memo.
3. **Draft.** Scaffold with `tools/new_post.py`. Write `post.md` using
   `{{code:}}` / `{{img:}}` placeholders — never paste code or output by hand.
4. **Verify.** Every code file is run (`tools/run_example.py`), every output
   screenshotted (`tools/render_output.py`, PNGs viewed), every number in the
   prose checked against real output. Then `tools/build_post.py`.
5. **Package.** Decide `subtitle` and up to 5 `tags` in the post.md
   frontmatter (research with `tools/medium_topics.py`). Choose the cover:
   `tools/medium_cover.py posts/NN-slug search "<query>"`, VIEW the contact
   sheet, `pick <N>`. Rebuild.
6. **Publish.** Draft by default: `tools/medium_publish.py posts/NN-slug`.
   Live only when the user says so for that post:
   `tools/medium_golive.py posts/NN-slug --dry-run`, view
   `publish_dialog.png`, then run it without `--dry-run`.
7. **Edit.** Local change first, re-run + re-render if code changed, rebuild,
   then `tools/medium_edit.py posts/NN-slug` (same URL, no duplicate;
   published posts need `--republish` and the author's OK). Stories not in
   the repo: `tools/medium_list.py` for ids, `tools/medium_pull.py <id>`.
8. **Record.** Update roadmap/index + `STATE.md`. Report: draft URL, local path,
   what changed, and what still needs the author's eyes.

## Writing bar (distilled from the retired third-party Medium skill)

A post should feel worth reading slowly — clarity plus depth, not difficulty:

- **Thesis first:** one idea per post, stated in the opening. If it can't be
  said in a sentence, grill again.
- **Intellectual spine:** sections build on each other; each ends having earned
  the next. Problem-first hook, short sections, every section earns its keep
  (this repo's convention: a "Why it matters" line per section).
- **Density with guidance:** long-form readers reward structure, not just
  insight. Cut drag (long setup, abstract claims without payoff), keep depth.
- **Authority is earned:** claims grounded in run code and real output, never
  asserted. No invented certainty; flag what needs the author's review.
- **Momentum:** strong opening, practical closing, "What's next" + series
  footer. Target 8-12 min read.

## Thought-architecture check (before publishing)

- What is this piece really building toward — one sentence?
- Does the structure carry the argument, or must the reader carry it alone?
- Which passages are deep, which merely heavy?
- Would a careful reader save, quote, or send this?

## Boundaries

- Does not replace fact-checking, citation review, or subject-matter expertise.
- No SEO spinning, no short-form hooks, no keyword stuffing.
- Never publish unrun code or unproduced output.
