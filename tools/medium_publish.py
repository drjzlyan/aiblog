"""Create a NEW Medium story from a post: draft by default, or straight to live.

Usage:
  uv run python tools/medium_publish.py posts/NN-slug [--live] [--dry-run]
                                        [--new] [--allow-no-cover]

Reads post.built.md (rebuild first: tools/build_post.py) and the frontmatter
of post.md (tags, subtitle, cover_query/cover_id). The Unsplash cover is
inserted under the title through Medium's own Unsplash picker, so it becomes
the story thumbnail with a proper "Photo by X on Unsplash" credit.

Records the story id/URL/status in posts/NN-slug/medium.json. Refuses to
create a second story for a post that already has one (that is how
duplicates happen): use medium_edit.py to update it, medium_golive.py to
publish it, or --new to deliberately start over.

--live      publish after drafting, with the frontmatter tags (required)
--dry-run   with --live: fill the publish dialog, screenshot it, don't publish
--allow-no-cover  create the story without an Unsplash cover (refused by default)
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
    flags = {a for a in args if a.startswith("--")}
    unknown = flags - {"--live", "--dry-run", "--new", "--allow-no-cover"}
    if unknown:
        print(f"Unknown option(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    post_dir = Path(next(a for a in args if not a.startswith("--")))
    post = postlib.load_post(post_dir)
    state = post["state"]
    if state.get("id") and "--new" not in flags:
        print(
            f"{post_dir} is already on Medium as {state['id']} ({state.get('status')}).\n"
            f"  update it:  uv run python tools/medium_edit.py {post_dir}\n"
            f"  go live:    uv run python tools/medium_golive.py {post_dir}\n"
            f"  or pass --new to create another story on purpose.",
            file=sys.stderr,
        )
        return 1
    if not post["meta"].get("cover_id") and "--allow-no-cover" not in flags:
        print("No Unsplash cover (the story thumbnail). Pick one first:\n"
              f"  uv run python tools/medium_cover.py {post_dir} search \"<query>\"\n"
              "or pass --allow-no-cover.", file=sys.stderr)
        return 1
    live = "--live" in flags
    tags = post["meta"].get("tags", [])
    if live and not tags:
        print("--live needs `tags:` in post.md frontmatter (max 5).", file=sys.stderr)
        return 1

    with mc.medium_session() as page:
        page.goto("https://medium.com/new-story")
        mc.wait_for_editor(page)
        mc.fill_story(page, post)
        sid = mc.wait_for_story_id(page)
        mc.wait_for_autosave(page)
        edit_url = f"https://medium.com/p/{sid}/edit"
        postlib.save_state(post_dir, id=sid, edit_url=edit_url, status="draft",
                           title=post["title"])
        print(f"Draft saved: {edit_url}")
        if not live:
            return 0
        url = mc.go_live(
            page, tags, post["meta"].get("subtitle"),
            require_image="--allow-no-cover" not in flags,
            dry_run="--dry-run" in flags,
            screenshot=post_dir / "publish_dialog.png",
        )
        if url:
            postlib.save_state(post_dir, status="published", url=url, tags=tags)
            print(f"Published live: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
