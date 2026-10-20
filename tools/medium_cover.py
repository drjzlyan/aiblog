"""Pick the Unsplash cover (= Medium thumbnail) for a post.

Usage:
  uv run python tools/medium_cover.py posts/NN-slug search "<query>" ["<query2>" ...]
  uv run python tools/medium_cover.py posts/NN-slug pick <N|photo-id>
  uv run python tools/medium_cover.py posts/NN-slug none

search  runs each query through Medium's built-in Unsplash picker (no API
        key needed; done inside one reusable scratch draft), then writes
        posts/NN-slug/cover_candidates.png (numbered contact sheet - VIEW IT)
        and cover_candidates.json. Queries are capped at 30 characters.
pick    records the choice in post.md frontmatter (cover_query, cover_id,
        cover_author). Publish/edit then insert that photo under the title.
none    removes the cover from frontmatter.

Choosing well: the thumbnail is what readers see in feeds. Prefer an image
that is clearly on-topic, uncluttered, landscape, and readable when small.
"""

import json
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc
import postlib

THUMB_W, THUMB_H, LABEL_H, COLS = 400, 267, 34, 3


def contact_sheet(cands: list[dict], out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    rows = (len(cands) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * THUMB_W, rows * (THUMB_H + LABEL_H)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    except Exception:
        font = ImageFont.load_default()
    for i, c in enumerate(cands):
        x, y = (i % COLS) * THUMB_W, (i // COLS) * (THUMB_H + LABEL_H)
        try:
            url = c["thumb"].replace("w=200", f"w={THUMB_W}")
            req = urllib.request.Request(url, headers={"User-Agent": mc.UA})
            img = Image.open(BytesIO(urllib.request.urlopen(req, timeout=30).read()))
            img = img.convert("RGB")
            img.thumbnail((THUMB_W - 6, THUMB_H - 6))
            sheet.paste(img, (x + (THUMB_W - img.width) // 2, y + (THUMB_H - img.height) // 2))
        except Exception as e:
            draw.text((x + 10, y + 10), f"thumb failed: {e}"[:40], fill="red", font=font)
        draw.text((x + 8, y + THUMB_H + 6), f"{i + 1}. {c['id']}  {c['author']}"[:38],
                  fill="black", font=font)
    sheet.save(out)


def search(post_dir: Path, queries: list[str]) -> int:
    cands: list[dict] = []
    with mc.medium_session() as page:
        mc.open_scratch(page)
        for q in queries:
            mc.caret_on_new_empty_paragraph(page)
            results = mc.open_unsplash_search(page, q)
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            mc.log(f"{q!r}: {len(results)} results")
            seen = {c["id"] for c in cands}
            cands += [dict(r, query=q[:30]) for r in results if r["id"] not in seen]
    if not cands:
        print("No results; try other keywords.", file=sys.stderr)
        return 1
    (post_dir / "cover_candidates.json").write_text(json.dumps(cands, indent=2) + "\n")
    sheet = post_dir / "cover_candidates.png"
    contact_sheet(cands, sheet)
    for i, c in enumerate(cands, 1):
        print(f"{i:2d}. {c['id']}  by {c['author']}  (query: {c['query']})")
    print(f"\nContact sheet: {sheet}\nView it, then: medium_cover.py {post_dir} pick <N|id>")
    return 0


def pick(post_dir: Path, choice: str) -> int:
    path = post_dir / "cover_candidates.json"
    if not path.exists():
        print("Run `search` first.", file=sys.stderr)
        return 1
    cands = json.loads(path.read_text())
    c = None
    if choice.isdigit() and 1 <= int(choice) <= len(cands):
        c = cands[int(choice) - 1]
    else:
        c = next((x for x in cands if x["id"] == choice), None)
    if not c:
        print(f"No candidate {choice!r}.", file=sys.stderr)
        return 1
    postlib.update_frontmatter(post_dir, cover_query=c["query"], cover_id=c["id"],
                               cover_author=c["author"])
    print(f"Cover set: {c['id']} by {c['author']} (query {c['query']!r}). "
          "Rebuild, then publish/edit to apply.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2 or "--help" in args or "-h" in args:
        print(__doc__.strip())
        return 0
    post_dir, cmd, rest = Path(args[0]), args[1], args[2:]
    if not (post_dir / "post.md").exists():
        print(f"{post_dir}/post.md not found.", file=sys.stderr)
        return 1
    if cmd == "search" and rest:
        return search(post_dir, rest)
    if cmd == "pick" and len(rest) == 1:
        return pick(post_dir, rest[0])
    if cmd == "none":
        postlib.update_frontmatter(post_dir, cover_query=None, cover_id=None, cover_author=None)
        print("Cover removed.")
        return 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
