"""Build the README demo: docs/demo.gif + docs/demo.mp4 from real artifacts.

Usage: uv run python tools/make_demo.py

Frames use real screenshots from posts/06-vectors-norms-similarity and the
real commands/URLs from this repo's history. No output is fabricated: the
edit frame shows the command shape, not a fake result line.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
POST = REPO / "posts" / "06-vectors-norms-similarity" / "images"

W, H = 1280, 800
BG, CARD, FG, DIM, ACCENT = "#16161e", "#1e1e2e", "#cdd6f4", "#8a8fa3", "#a6e3a1"
TITLE_FONT = "/System/Library/Fonts/Menlo.ttc"


def font(size: int):
    return ImageFont.truetype(TITLE_FONT, size)


def base_frame(caption: str, step: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 96], fill="#11111b")
    d.text((48, 28), step, fill=ACCENT, font=font(34))
    d.text((48, H - 72), caption, fill=DIM, font=font(26))
    return img, d


def centered_text(d: ImageDraw.ImageDraw, y: int, text: str, size: int, color=FG):
    f = font(size)
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, fill=color, font=f)


def term_card(img: Image.Image, d: ImageDraw.ImageDraw, lines: list[str], top: int = 170):
    f = font(30)
    lh = 46
    box_h = lh * len(lines) + 60
    d.rounded_rectangle([140, top, W - 140, top + box_h], radius=18, fill=CARD)
    for i, line in enumerate(lines):
        color = ACCENT if line.startswith("$") else FG
        d.text((180, top + 30 + i * lh), line, fill=color, font=f)


def shot_card(img: Image.Image, path: Path, top: int = 130, max_h: int = 560):
    shot = Image.open(path).convert("RGB")
    scale = min((W - 280) / shot.width, max_h / shot.height)
    shot = shot.resize((int(shot.width * scale), int(shot.height * scale)))
    img.paste(shot, ((W - shot.width) // 2, top))


def build_frames(tmp: Path) -> list[Path]:
    frames: list[Path] = []

    def save(img: Image.Image, name: str):
        p = tmp / name
        img.save(p)
        frames.append(p)

    # 1. title
    img, d = base_frame("clone, ask the agent, publish — no MCP servers, no skills needed",
                        "aiblog")
    centered_text(d, 250, "Idea  →  Draft  →  Update", 64)
    centered_text(d, 360, "a self-sufficient repo for Medium blogs", 34, DIM)
    centered_text(d, 470, "uv · python · playwright · markdown", 30, DIM)
    save(img, "f01.png")

    # 2. ideate
    img, d = base_frame("grilling settles topic, reader, and angle before a word is drafted",
                        "1 · ideate")
    term_card(img, d, [
        "$ ask: \"write a post on vectors and similarity\"",
        "Q1 topic?  Q2 reader?  Q3 angle?",
        "→ outline agreed, series row added",
    ])
    save(img, "f02.png")

    # 3. create
    img, d = base_frame("every example is a real file, run for real — never pasted by hand",
                        "2 · create")
    term_card(img, d, [
        "$ uv run python tools/new_post.py vectors --title \"...\"",
        "$ uv run python tools/run_example.py code/01_vectors.py",
        "  d1 . d2 = 2   (2 shared words)      ← real output",
    ], top=140)
    shot_card(img, POST / "output_vectors.png", top=440, max_h=250)
    save(img, "f03.png")

    # 4. verify
    img, d = base_frame("screenshots and plots render from the actual run output",
                        "3 · verify")
    shot_card(img, POST / "search_scores.png", top=130, max_h=540)
    save(img, "f04.png")

    # 5. publish (shape of the real flow — placeholder id, not a real draft)
    img, d = base_frame("one command → draft URL back, roadmap and state updated",
                        "4 · publish")
    term_card(img, d, [
        "$ uv run python tools/medium_publish.py posts/NN-slug",
        "  Draft saved: medium.com/p/<draft-id>/edit",
    ])
    save(img, "f05.png")

    # 6. update (command shape only — no fabricated result)
    img, d = base_frame("edits go local-first, then land on the same draft URL — no duplicates",
                        "5 · update")
    term_card(img, d, [
        "$ uv run python tools/medium_edit.py <draft-id> posts/NN-slug",
        "  → same /p/<draft-id>/edit URL, rewritten in place",
    ])
    save(img, "f06.png")

    return frames


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="demo"))
    try:
        frames = build_frames(tmp)
        gif_out = REPO / "docs" / "demo.gif"
        mp4_out = REPO / "docs" / "demo.mp4"
        imgs = [Image.open(f) for f in frames]
        small = [im.resize((960, 600)) for im in imgs]
        small[0].save(gif_out, save_all=True, append_images=small[1:],
                      duration=2000, loop=0)
        print(f"wrote {gif_out} ({gif_out.stat().st_size // 1024} KB)")
        ff = shutil.which("ffmpeg")
        if ff:
            subprocess.run(
                [ff, "-y", "-framerate", "1/2", "-i", str(tmp / "f%02d.png"),
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=1280:800",
                 str(mp4_out)],
                check=True, capture_output=True,
            )
            print(f"wrote {mp4_out} ({mp4_out.stat().st_size // 1024} KB)")
        else:
            print("ffmpeg not found; GIF only.", file=sys.stderr)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
