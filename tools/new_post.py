"""Scaffold a new post directory with the next global number.

Usage:
  uv run python tools/new_post.py <slug> [--title "Working title"]

Creates posts/NN-slug/{post.md,code/,images/} where NN is one past the
highest existing number (NN is a global creation counter, not roadmap order).
Prints the new directory. Does not touch roadmaps (link the post there after).
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args:
        print(__doc__.strip())
        return 0
    slug = args[0]
    title = ""
    if "--title" in args:
        title = args[args.index("--title") + 1]
    nums = []
    posts_root = REPO_ROOT / "posts"
    posts_root.mkdir(exist_ok=True)  # fresh clones have no posts/ (git-ignored)
    for d in posts_root.iterdir():
        m = re.match(r"(\d+)-", d.name)
        if d.is_dir() and m:
            nums.append(int(m.group(1)))
    nn = max(nums, default=0) + 1
    post_dir = REPO_ROOT / "posts" / f"{nn:02d}-{slug}"
    (post_dir / "code").mkdir(parents=True)
    (post_dir / "images").mkdir(parents=True)
    (post_dir / "post.md").write_text(
        f"# {title or 'Working title'}\n\nWrite the post here. "
        "Use {{code:file.py}} and {{img:file.png|alt}}; never paste code by hand.\n"
    )
    print(post_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
