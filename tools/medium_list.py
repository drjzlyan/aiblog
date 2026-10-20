"""List your Medium stories: drafts, published, unlisted, scheduled.

Usage:
  uv run python tools/medium_list.py [--drafts] [--published] [--unlisted]
                                     [--scheduled] [--all] [--json]

Default: drafts + published. Each row shows the story id (use it with
medium_golive.py / medium_pull.py / medium_edit.py --id) and, when a local
post is linked to it via medium.json, that post directory.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc
import postlib


def local_index() -> dict[str, str]:
    out = {}
    for f in postlib.POSTS_ROOT.glob("*/medium.json"):
        sid = json.loads(f.read_text()).get("id")
        if sid:
            out[sid] = str(f.parent.relative_to(postlib.REPO_ROOT))
    return out


def main() -> int:
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        print(__doc__.strip())
        return 0
    tabs = [t for t in mc.STORY_TABS if f"--{t}" in args]
    if "--all" in args:
        tabs = list(mc.STORY_TABS)
    tabs = tabs or ["drafts", "published"]
    with mc.medium_session() as page:
        stories = [s for tab in tabs for s in mc.list_stories(page, tab)]
    local = local_index()
    for s in stories:
        s["local"] = local.get(s["id"], "")
    if "--json" in args:
        print(json.dumps(stories, indent=2))
        return 0
    for tab in tabs:
        rows = [s for s in stories if s["status"] == tab]
        print(f"== {tab} ({len(rows)})")
        for s in rows:
            print(f"{s['id']}  {s['title']}")
            print(f"    {s['info']}")
            print(f"    {s['url']}" + (f"   local: {s['local']}" if s["local"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
