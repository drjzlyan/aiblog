"""Scaffold a new post directory with the next global number.

Usage:
  uv run python tools/new_post.py <slug> [--title "Working title"]

Creates posts/NN-slug/{post.md,code/,images/} where NN is one past the
highest existing number (NN is a global creation counter, not roadmap order).
post.md starts with a frontmatter block (subtitle, tags, cover) for the
agent to fill in. Prints the new directory. Does not touch roadmaps.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import postlib

TEMPLATE = """---
subtitle: One sentence that sells the post in feeds (max 140 chars)
tags: Topic One, Topic Two
---
# {title}

Write the post here. Use {{{{code:file.py}}}} and {{{{img:file.png|alt}}}}; never paste code by hand.
"""


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__.strip())
        return 0
    slug = args[0]
    title = args[args.index("--title") + 1] if "--title" in args else "Working title"
    post_dir = postlib.next_post_dir(slug)
    (post_dir / "code").mkdir(parents=True)
    (post_dir / "images").mkdir(parents=True)
    (post_dir / "post.md").write_text(TEMPLATE.format(title=title))
    print(post_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
