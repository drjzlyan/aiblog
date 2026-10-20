"""Post files: frontmatter (author/agent decisions) and medium.json (tool state).

No browser here, so everything in this module is unit-testable offline
(`uv run python tools/postlib.py` runs the self-test).

posts/NN-slug/post.md may start with a frontmatter block that the agent
decides and edits:

    ---
    subtitle: One-line preview subtitle shown in feeds (<=140 chars)
    tags: Statistics, Machine Learning, Python   (max 5, Medium "topics")
    cover_query: statistics chart                (Unsplash search via Medium)
    cover_id: fiXLQXAhCfk                        (Unsplash photo id to use)
    cover_author: Maxim Hopman                   (informational)
    ---
    # Title
    ...

posts/NN-slug/medium.json is written by the medium_* tools only: the Medium
story id, edit/live URLs, and status, so every later command can find the
story from the post directory alone (no draft ids copied around by hand).
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTS_ROOT = REPO_ROOT / "posts"
MAX_TAGS = 5
FM_KEYS = ("subtitle", "tags", "cover_query", "cover_id", "cover_author")

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


# ------------------------------------------------------------ frontmatter ---

def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta, body). Values are strings; `tags` becomes a list."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    if "tags" in meta:
        meta["tags"] = [t.strip() for t in meta["tags"].split(",") if t.strip()]
    return meta, text[m.end():]


def join_frontmatter(meta: dict, body: str) -> str:
    lines = []
    for key in list(FM_KEYS) + [k for k in meta if k not in FM_KEYS]:
        if key not in meta or meta[key] in (None, "", []):
            continue
        value = meta[key]
        if isinstance(value, list):
            value = ", ".join(value)
        lines.append(f"{key}: {value}")
    if not lines:
        return body
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def update_frontmatter(post_dir: Path, **changes) -> dict:
    """Set (or with value None, remove) frontmatter keys in post.md."""
    path = post_dir / "post.md"
    meta, body = split_frontmatter(path.read_text())
    for key, value in changes.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    path.write_text(join_frontmatter(meta, body))
    return meta


# ------------------------------------------------------------ medium.json ---

def load_state(post_dir: Path) -> dict:
    path = post_dir / "medium.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(post_dir: Path, **changes) -> dict:
    state = load_state(post_dir)
    state.update({k: v for k, v in changes.items() if v is not None})
    state["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (post_dir / "medium.json").write_text(json.dumps(state, indent=2) + "\n")
    return state


# ------------------------------------------------------------ whole post ----

def story_id(arg: str) -> str:
    """Accept an id, a /p/<id>/edit URL, or a public slug URL ending in -<id>."""
    arg = arg.strip().split("?")[0].rstrip("/")
    m = re.search(r"/p/([0-9a-f]{8,16})", arg) or re.search(r"-([0-9a-f]{10,16})$", arg)
    if m:
        return m.group(1)
    if re.fullmatch(r"[0-9a-f]{8,16}", arg):
        return arg
    raise ValueError(f"Not a Medium story id or URL: {arg}")


def load_post(post_dir: Path) -> dict:
    """Read a built post: title, body (Markdown after the title), meta, state.

    Requires post.built.md (run tools/build_post.py first). Frontmatter is
    taken from post.md, so build output never has to carry it.
    """
    post_dir = Path(post_dir)
    built = post_dir / "post.built.md"
    if not built.exists():
        raise FileNotFoundError(f"{built} missing - run tools/build_post.py {post_dir} first")
    src = post_dir / "post.md"
    if src.exists() and built.stat().st_mtime < src.stat().st_mtime:
        raise RuntimeError(f"{built} is older than post.md - rebuild with tools/build_post.py")
    meta, _ = split_frontmatter(src.read_text()) if src.exists() else ({}, "")
    _, text = split_frontmatter(built.read_text())  # tolerate old builds
    lines = text.strip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"{built}: first line must be '# Title'")
    tags = meta.get("tags", [])
    if len(tags) > MAX_TAGS:
        raise ValueError(f"{len(tags)} tags in frontmatter; Medium allows {MAX_TAGS}")
    if meta.get("cover_id") and not meta.get("cover_query"):
        raise ValueError("cover_id needs cover_query (pick with tools/medium_cover.py)")
    return {
        "dir": post_dir,
        "title": lines[0][2:].strip(),
        "body": "\n".join(lines[1:]).strip(),
        "meta": meta,
        "state": load_state(post_dir),
    }


def next_post_dir(slug: str) -> Path:
    POSTS_ROOT.mkdir(exist_ok=True)
    nums = [int(m.group(1)) for d in POSTS_ROOT.iterdir()
            if d.is_dir() and (m := re.match(r"(\d+)-", d.name))]
    return POSTS_ROOT / f"{max(nums, default=0) + 1:02d}-{slug}"


def selftest() -> int:
    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        print(f"{'ok' if cond else 'FAIL'}  {name} {detail}")
        failures += not cond

    text = "---\nsubtitle: Sub: with colon\ntags: A, B ,C\n---\n# T\n\nbody\n"
    meta, body = split_frontmatter(text)
    check("frontmatter parsed", meta == {"subtitle": "Sub: with colon", "tags": ["A", "B", "C"]}, meta)
    check("body after frontmatter", body == "# T\n\nbody\n", repr(body))
    check("roundtrip", split_frontmatter(join_frontmatter(meta, body)) == (meta, body))
    check("no frontmatter", split_frontmatter("# T\n") == ({}, "# T\n"))
    check("id from edit url", story_id("https://medium.com/p/37f43a1447e7/edit") == "37f43a1447e7")
    check("id from slug url", story_id("https://medium.com/@x/some-title-7bbff66fa1d1?source=a") == "7bbff66fa1d1")
    check("bare id", story_id("9a3a6e73c9cf") == "9a3a6e73c9cf")
    try:
        story_id("hello")
        check("bad id raises", False)
    except ValueError:
        check("bad id raises", True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(selftest())
