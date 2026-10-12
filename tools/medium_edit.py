"""Edit an existing Medium draft in place (same URL preserved).

Usage:
  uv run python tools/medium_edit.py <draft-id-or-url> posts/NN-slug

Rewrites the draft's title and body from post.built.md (rebuild first:
uv run python tools/build_post.py posts/NN-slug). The repo is the source of
truth: the editor is cleared, then refilled exactly like a fresh publish,
so the draft ends up identical to what a new publish would produce, minus
a duplicate draft. Old images are removed with their blocks.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc


def draft_id(arg: str) -> str:
    m = re.search(r"/p/([0-9a-f]+)", arg)
    return m.group(1) if m else arg


def main() -> int:
    if len(sys.argv) != 3 or "--help" in sys.argv:
        print(__doc__.strip())
        return 0 if "--help" in sys.argv else 1
    did = draft_id(sys.argv[1])
    post_dir = Path(sys.argv[2])
    built = post_dir / "post.built.md"
    if not built.exists():
        print(f"{built} missing - run tools/build_post.py first", file=sys.stderr)
        return 1
    lines = built.read_text().splitlines()
    title = lines[0].lstrip("# ").strip()
    content = "\n".join(lines[1:]).strip()
    url = f"https://medium.com/p/{did}/edit"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, context, page = mc.launch(pw)
        try:
            if not mc.ensure_logged_in(page, context):
                return 1
            page.goto(url)
            mc.wait_for_editor(page)

            # Clear the whole editor (title + body + old images), then refill.
            cleared = page.evaluate(
                """() => {
                    const editor = document.querySelector(
                        '.postArticle-content[contenteditable="true"]');
                    if (!editor) return false;
                    editor.focus();
                    const range = document.createRange();
                    range.selectNodeContents(editor);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                    return true;
                }"""
            )
            if not cleared:
                print("Editor not found on draft page.", file=sys.stderr)
                return 1
            page.keyboard.press("Backspace")
            page.wait_for_timeout(500)

            mc.type_title(page, title)
            mc.fill_body_and_images(page, content)

            # Same draft URL: no navigation happens, so wait for autosave.
            page.wait_for_timeout(5000)
            final_url = page.url
            print(f"Draft updated: {final_url}")
            print(final_url)
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
