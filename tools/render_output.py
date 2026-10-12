"""Render a code file plus its real output as a terminal-style PNG.

Usage: uv run python tools/render_output.py <example.py> <out.png>

Reads <example>.out.txt (produced by run_example.py), so the image can only
show output that was actually produced by running the code.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Menlo.ttc"
BG, FG, DIM, PROMPT = "#1e1e2e", "#cdd6f4", "#6c7086", "#a6e3a1"


def render(script: Path, out: Path) -> None:
    output = script.with_suffix(".out.txt").read_text().rstrip("\n")
    lines = [(f"$ python {script.name}", PROMPT)] + [(l, FG) for l in output.split("\n")]
    font = ImageFont.truetype(FONT, 26)
    char_w = font.getlength("M")
    line_h, pad, bar = 38, 36, 56
    width = int(max(len(t) for t, _ in lines) * char_w) + 2 * pad
    width = max(width, 900)
    img = Image.new("RGB", (width, bar + pad + line_h * len(lines) + pad), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, bar], fill="#11111b")
    for i, c in enumerate(["#f38ba8", "#f9e2af", "#a6e3a1"]):
        d.ellipse([24 + i * 36, 18, 44 + i * 36, 38], fill=c)
    d.text((width // 2 - 60, 14), "Terminal", fill=DIM, font=font)
    for i, (text, color) in enumerate(lines):
        d.text((pad, bar + pad + i * line_h), text, fill=color, font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


if __name__ == "__main__":
    render(Path(sys.argv[1]), Path(sys.argv[2]))
