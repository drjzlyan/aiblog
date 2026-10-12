"""Expand a post template into publish-ready Markdown.

Usage: uv run python tools/build_post.py posts/NN-slug

post.md may contain:
  {{code:file.py}}   -> the file's source in a fenced python block (tested code)
  {{img:file.png|alt}} -> ![alt](/absolute/path/to/images/file.png)
Writes posts/NN-slug/post.built.md. Fails if any referenced file is missing,
or if a code file has no matching .out.txt (i.e. it was never run).
"""
import re
import sys
from pathlib import Path


def build(post_dir: Path) -> Path:
    text = (post_dir / "post.md").read_text()

    def code(m):
        src = post_dir / "code" / m.group(1)
        if not src.with_suffix(".out.txt").exists():
            sys.exit(f"{src.name} has no .out.txt - run tools/run_example.py first")
        return f"```python\n{src.read_text().rstrip()}\n```"

    def img(m):
        path = (post_dir / "images" / m.group(1)).resolve()
        if not path.exists():
            sys.exit(f"missing image {path}")
        return f"![{m.group(2) or ''}]({path})"

    text = re.sub(r"\{\{code:([^}]+)\}\}", code, text)
    text = re.sub(r"\{\{img:([^|}]+)\|?([^}]*)\}\}", img, text)
    out = post_dir / "post.built.md"
    out.write_text(text)
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
