"""Publish a post to Medium: new draft (default) or live with tags.

Usage:
  uv run python tools/medium_publish.py posts/NN-slug [--live --tags Python,ML]

Reads title from the `# ` line of post.built.md and publishes the rest.
Rebuild first: uv run python tools/build_post.py posts/NN-slug
Draft path cannot set tags (Medium's tag input only exists in the live
publish dialog); pass --live --tags when going live. Opens a headed browser;
log in once, the session is reused.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args:
        print(__doc__.strip())
        return 0
    live = "--live" in args
    args = [a for a in args if a != "--live"]
    tags: list[str] = []
    if "--tags" in args:
        i = args.index("--tags")
        tags = [t.strip() for t in args[i + 1].split(",") if t.strip()]
        args = args[:i] + args[i + 2 :]
    post_dir = Path(args[0])
    built = post_dir / "post.built.md"
    if not built.exists():
        print(f"{built} missing - run tools/build_post.py first", file=sys.stderr)
        return 1
    lines = built.read_text().splitlines()
    title = lines[0].lstrip("# ").strip()
    content = "\n".join(lines[1:]).strip()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, context, page = mc.launch(pw)
        try:
            if not mc.ensure_logged_in(page, context):
                return 1
            page.goto("https://medium.com/new-story")
            mc.wait_for_editor(page)
            mc.type_title(page, title)
            mc.fill_body_and_images(page, content)

            page.wait_for_url(re.compile(r"/p/[0-9a-f]+/edit"), timeout=30000)
            page.wait_for_timeout(3000)
            draft_url = page.url
            print(f"Draft saved: {draft_url}")

            if not live:
                print(draft_url)
                return 0
            page.locator('button:has-text("Publish")').first.click()
            page.wait_for_timeout(2000)
            for tag in tags[:5]:
                tag_input = page.locator(
                    '[data-testid="publishTopicsInput"], '
                    'input[placeholder*="topic" i], input[placeholder*="tag" i]'
                ).first
                tag_input.fill(tag)
                page.keyboard.press("Enter")
            page.locator('button:has-text("Publish now")').first.click()
            page.wait_for_load_state("networkidle")
            print(f"Published live: {page.url}")
            print(page.url)
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
