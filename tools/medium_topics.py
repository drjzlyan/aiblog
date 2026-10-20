"""Research Medium topics (tags) before choosing a post's `tags:`.

Usage:
  uv run python tools/medium_topics.py "<term>" ["<term2>" ...]

Types each term into Medium's real topic box (inside the reusable scratch
draft; nothing is published or saved) and prints Medium's suggestions with
their story counts, e.g. "Statistics (9.7K)". Prefer established topics with
real readership that precisely match the post; Medium allows 5 per story.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc


def main() -> int:
    terms = sys.argv[1:]
    if not terms or "--help" in terms or "-h" in terms:
        print(__doc__.strip())
        return 0
    with mc.medium_session() as page:
        mc.open_scratch(page)
        mc.open_publish_dialog(page)
        try:
            for term in terms:
                print(f"== {term}")
                for s in mc.topic_suggestions(page, term) or ["(no suggestions)"]:
                    print(f"   {s}")
        finally:
            page.locator(mc.TOPIC_INPUT).fill("")
            page.locator('[data-testid="close-button"]').click()
    return 0


if __name__ == "__main__":
    sys.exit(main())
