"""Publish an EXISTING Medium draft live (tags, subtitle, thumbnail check).

Usage:
  uv run python tools/medium_golive.py posts/NN-slug [--sync] [--dry-run]
                                       [--tags A,B] [--subtitle "..."]
  uv run python tools/medium_golive.py <draft-id-or-url> --tags A,B [--subtitle "..."]

With a post directory, the draft id comes from medium.json and tags/subtitle
from post.md frontmatter (flags override). With a bare id/URL (an older
draft that is not in the repo; find ids with medium_list.py --drafts),
--tags is required.

--sync            first rewrite the draft from the repo (same as medium_edit.py),
                  so what goes live is exactly the local post
--dry-run         fill the dialog, screenshot it, stop before Publish
--allow-no-cover  publish even if the first image is not an Unsplash cover

The dialog is screenshotted (post dir: publish_dialog.png, else .aiblog/)
so the agent can check the thumbnail, title, subtitle and topics.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc
import postlib


def opt(args: list[str], name: str) -> str | None:
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            raise SystemExit(f"{name} needs a value")
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return None


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__.strip())
        return 0
    tags_arg = opt(args, "--tags")
    subtitle = opt(args, "--subtitle")
    flags = {a for a in args if a.startswith("--")}
    unknown = flags - {"--sync", "--dry-run", "--allow-no-cover"}
    if unknown:
        print(f"Unknown option(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    target = next(a for a in args if not a.startswith("--"))

    post = None
    post_dir = Path(target)
    if post_dir.is_dir():
        post = postlib.load_post(post_dir)
        sid = post["state"].get("id")
        if not sid:
            print(f"{post_dir} has no Medium story yet; run medium_publish.py first.",
                  file=sys.stderr)
            return 1
        tags = post["meta"].get("tags", [])
        subtitle = subtitle or post["meta"].get("subtitle")
        shot = post_dir / "publish_dialog.png"
    else:
        if "--sync" in flags:
            print("--sync needs a post directory.", file=sys.stderr)
            return 2
        sid = postlib.story_id(target)
        tags = []
        mc.LOCAL_DIR.mkdir(exist_ok=True)
        shot = mc.LOCAL_DIR / f"publish_dialog_{sid}.png"
    if tags_arg:
        tags = [t.strip() for t in tags_arg.split(",") if t.strip()]
    if not tags:
        print("No tags: set `tags:` in post.md frontmatter or pass --tags A,B (max 5).",
              file=sys.stderr)
        return 1
    if len(tags) > postlib.MAX_TAGS:
        print(f"Medium allows {postlib.MAX_TAGS} tags; got {len(tags)}.", file=sys.stderr)
        return 1

    with mc.medium_session() as page:
        mc.open_story(page, sid)
        if mc.is_published(page):
            print(f"{sid} is already published. To change it: medium_edit.py --republish.",
                  file=sys.stderr)
            return 1
        if "--sync" in flags:
            mc.clear_editor(page)
            mc.fill_story(page, post)
            mc.wait_for_autosave(page)
            print("Draft synced from repo.")
        url = mc.go_live(
            page, tags, subtitle,
            require_image="--allow-no-cover" not in flags,
            dry_run="--dry-run" in flags,
            screenshot=shot,
        )
    if url:
        if post:
            postlib.save_state(post_dir, status="published", url=url, tags=tags)
        print(f"Published live: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
