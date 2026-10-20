"""Expand a post template into publish-ready Markdown.

Usage: uv run python tools/build_post.py posts/NN-slug

post.md may contain:
  {{code:file.py}}   -> the file's source in a fenced python block (tested code)
  {{img:file.png|alt}} -> ![alt](/absolute/path/to/images/file.png)
Writes posts/NN-slug/post.built.md (frontmatter stripped; the medium_* tools
read it from post.md). Fails if any referenced file is missing, if a code
file has no matching .out.txt (never run), or if the code changed after its
.out.txt was written (output is stale: re-run it).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import postlib


def build(post_dir: Path) -> Path:
    meta, text = postlib.split_frontmatter((post_dir / "post.md").read_text())
    if len(meta.get("tags", [])) > postlib.MAX_TAGS:
        sys.exit(f"{len(meta['tags'])} tags in frontmatter; Medium allows {postlib.MAX_TAGS}")

    def code(m):
        src = post_dir / "code" / m.group(1)
        out = src.with_suffix(".out.txt")
        if not src.exists():
            sys.exit(f"missing code file {src}")
        if not out.exists():
            sys.exit(f"{src.name} has no .out.txt - run tools/run_example.py first")
        if src.stat().st_mtime > out.stat().st_mtime:
            sys.exit(f"{src.name} changed after it was run - re-run tools/run_example.py")
        lang = {".py": "python", ".sh": "bash", ".js": "javascript"}.get(src.suffix, "")
        return f"```{lang}\n{src.read_text().rstrip()}\n```"

    def img(m):
        path = (post_dir / "images" / m.group(1)).resolve()
        if not path.exists():
            sys.exit(f"missing image {path}")
        return f"![{m.group(2) or ''}]({path})"

    text = re.sub(r"\{\{code:([^}]+)\}\}", code, text)
    text = re.sub(r"\{\{img:([^|}]+)\|?([^}]*)\}\}", img, text)
    if not text.lstrip().startswith("# "):
        sys.exit("post.md must start (after frontmatter) with a '# Title' line")
    out = post_dir / "post.built.md"
    out.write_text(text.lstrip())
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) == 2 else 2)
    print(build(Path(sys.argv[1])))
