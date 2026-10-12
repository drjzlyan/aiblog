"""List your published Medium posts (title, url, date).

Usage:
  uv run python tools/medium_list.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, context, page = mc.launch(pw)
        articles: list = []
        try:
            if not mc.ensure_logged_in(page, context):
                return 1
            page.goto("https://medium.com/me/stories?tab=posts-published")
            page.wait_for_load_state("domcontentloaded")
            try:
                page.wait_for_selector(
                    'a[href*="/@"][href*="-"], a[href*="/p/"]', timeout=15000
                )
            except Exception:
                pass  # empty list: extraction below just finds nothing
            articles = page.evaluate(
                """(selector) => {
                    const storyUrl = /\\/(@[^/]+\\/[^/?#]*-[0-9a-f]{10,12}|p\\/[0-9a-f]{10,12})(?:[/?#]|$)/;
                    const byUrl = new Map();
                    document.querySelectorAll(selector).forEach(link => {
                        const url = link.href.split('?')[0];
                        const title = link.innerText.trim().split('\\n')[0];
                        if (!storyUrl.test(url) || !title || byUrl.has(url)) return;
                        let row = link;
                        for (let i = 0; i < 4 && row.parentElement; i++)
                            row = row.parentElement;
                        const date = (row.innerText.match(
                            /(?:Published|Updated)\\s+([^\\n·]+)/) || [])[1] || '';
                        byUrl.set(url, { title, url, date: (date || '').trim() });
                    });
                    return [...byUrl.values()];
                }""",
                'a[href*="/@"][href*="-"], a[href*="/p/"]',
            )
        except Exception as e:
            print(f"Extraction failed: {e}", file=sys.stderr)
            return 1
        finally:
            browser.close()
    for a in articles:
        print(f"{a['date'] + '  ' if a['date'] else ''}{a['title']}\n  {a['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
