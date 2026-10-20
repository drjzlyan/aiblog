"""Revise an existing Medium story in place (same URL, no duplicate).

Usage:
  uv run python tools/medium_edit.py posts/NN-slug [--id <id-or-url>] [--republish]

The repo is the source of truth: the story's editor is cleared and refilled
from post.built.md exactly like a fresh publish (title, body, local images,
Unsplash cover under the title). Rebuild first: tools/build_post.py.

The story id comes from posts/NN-slug/medium.json; pass --id to attach a
post to a story it doesn't know yet (it is then recorded).

Drafts: the change is autosaved; the draft stays a draft.
Published stories: refused unless --republish is given, because the change
goes live immediately ("Save and publish"). Revising a live post is the
author's call, like going live.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc
import postlib


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__.strip())
        return 0
    sid = None
    if "--id" in args:
        i = args.index("--id")
        sid = postlib.story_id(args[i + 1])
        del args[i:i + 2]
    republish = "--republish" in args
    args = [a for a in args if a != "--republish"]
    if len(args) != 1 or args[0].startswith("--"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    post_dir = Path(args[0])
    post = postlib.load_post(post_dir)
    sid = sid or post["state"].get("id")
    if not sid:
        print(f"{post_dir} has no Medium story (medium.json). Publish it, or pass --id.",
              file=sys.stderr)
        return 1

    with mc.medium_session() as page:
        mc.open_story(page, sid)
        published = mc.is_published(page)
        if published and not republish:
            print(f"{sid} is published: edits go live on save. Re-run with --republish "
                  "once the author has approved the change.", file=sys.stderr)
            return 1
        live_cover = mc.first_image_unsplash_id(page)
        if live_cover and live_cover != post["meta"].get("cover_id"):
            print(
                f"The story's first image is Unsplash photo {live_cover}, but post.md has "
                f"cover_id={post['meta'].get('cover_id')}. The story was probably changed "
                "in Medium after the repo copy was made; refilling would drop that.\n"
                f"  Compare: uv run python tools/medium_pull.py {sid} --into /tmp/{sid}\n"
                f"  Then bring post.md up to date and set the cover "
                f"(tools/medium_cover.py {post_dir} search/pick).",
                file=sys.stderr,
            )
            return 1
        mc.clear_editor(page)
        mc.fill_story(page, post)
        mc.wait_for_autosave(page)
        edit_url = f"https://medium.com/p/{sid}/edit"
        if published:
            url = mc.republish(page)
            postlib.save_state(post_dir, id=sid, edit_url=edit_url, status="published",
                               url=url, title=post["title"])
            print(f"Published story updated: {url}")
        else:
            postlib.save_state(post_dir, id=sid, edit_url=edit_url, status="draft",
                               title=post["title"])
            print(f"Draft updated: {edit_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
