"""Shared Medium browser automation: session, editor, Unsplash cover, publish dialog.

Medium has no usable public API; everything goes through a headed Chromium
window (Cloudflare blocks headless). Selectors here were verified against
the live editor (2026-10-20); if Medium changes its DOM, fix them here once.

Session lives at repo-root medium-session.json (git-ignored). First run opens
a browser window: log in once, the session is reused afterwards.

Offline self-test of the Markdown converter: uv run python tools/medium_common.py
"""

import contextlib
import json
import mimetypes
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_PATH = REPO_ROOT / "medium-session.json"
LOCAL_DIR = REPO_ROOT / ".aiblog"  # git-ignored tool state (scratch draft id)
SCRATCH_PATH = LOCAL_DIR / "scratch.json"
SCRATCH_TITLE = "aiblog scratch - used for cover and topic search, do not publish"

EDITOR_SELECTOR = '.postArticle-content[contenteditable="true"]'
FIRST_BLOCK = f"{EDITOR_SELECTOR} .section-inner > .graf:first-child"
IMAGE_SELECTOR = ".postArticle-content img.graf-image"
TOPIC_INPUT = 'input[role="combobox"][aria-controls="tagMultiSelectMenu"]'
SUBTITLE_INPUT = 'textarea[aria-label="Story preview subtitle"]'
COVER_TOKEN = "IMGTOKENCOVERX"

# Local images in post Markdown: ![alt](/absolute/path.png)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((\/[^)\s]+\.(?:png|jpe?g|gif|webp))\)", re.IGNORECASE)

LOGIN_SELECTORS = [
    '[data-testid="headerUserIcon"]',
    '[data-testid="headerNotificationButton"]',
    '[data-testid="headerWriteButton"]',
    # legacy selectors (kept for back-compat)
    '[data-testid="headerUserButton"]',
    '[data-testid="write-button"]',
    'a[href="/me/stories"]',
]

STORY_TABS = {
    "drafts": "drafts",
    "published": "posts-published",
    "unlisted": "posts-unlisted",
    "scheduled": "posts-scheduled",
}

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def tokenize_images(content: str):
    """Replace local image markdown with IMGTOKEN placeholders.

    Returns (content_with_tokens, [image_paths]). Raises if a file is missing.
    """
    images: list[str] = []

    def sub(m: re.Match) -> str:
        path = m.group(1)
        if not Path(path).exists():
            raise FileNotFoundError(f"Image not found: {path}")
        images.append(path)
        return f"\n\nIMGTOKEN{len(images) - 1}X\n\n"

    return IMAGE_RE.sub(sub, content), images


def markdown_to_editor_html(markdown_text: str) -> str:
    """Markdown -> HTML shaped for Medium's paste handler.

    Medium splits a pasted <pre> at every blank line, so blank lines inside
    code get a single space; a blockquote must hold bare text (inner
    <p>/newlines render as empty quote blocks).
    """
    import markdown as md

    html = md.markdown(markdown_text, extensions=["fenced_code", "tables"])
    html = re.sub(
        r"<pre>[\s\S]*?</pre>",
        lambda m: re.sub(r"\n(?=\n)", "\n ", m.group(0)),  # every blank line, incl. runs
        html,
    )
    html = re.sub(
        r"<blockquote>\s*<p>([\s\S]*?)</p>\s*</blockquote>",
        r"<blockquote>\1</blockquote>",
        html,
    )
    return html


# ---------------------------------------------------------------- browser ---

def launch(playwright):
    """Launch headed Chromium with anti-automation flags. Returns (browser, context, page)."""
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
        args=[
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            f"--user-agent={UA}",
        ],
    )
    options: dict = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": UA,
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
    }
    if SESSION_PATH.exists():
        try:
            json.loads(SESSION_PATH.read_text())  # validate before handing to playwright
            options["storage_state"] = str(SESSION_PATH)
        except Exception as e:
            log(f"Saved session is corrupt ({e}); starting fresh.")
    context = browser.new_context(**options)
    context.add_init_script(
        "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
    )
    return browser, context, context.new_page()


@contextlib.contextmanager
def medium_session():
    """Yield a logged-in page; closes the browser on exit.

    Raises SystemExit(1) when login does not complete.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, context, page = launch(pw)
        try:
            if not ensure_logged_in(page, context):
                raise SystemExit(1)
            yield page
            save_session(context)
        finally:
            browser.close()


def save_session(context) -> None:
    SESSION_PATH.write_text(json.dumps(context.storage_state(), indent=2))


def is_logged_in(page) -> bool:
    try:
        page.wait_for_selector(", ".join(LOGIN_SELECTORS), timeout=8000)
        return True
    except Exception:
        return False


def ensure_logged_in(page, context) -> bool:
    """Return True once logged in. Blocks up to 5 min for a manual login."""
    page.goto("https://medium.com")
    page.wait_for_load_state("domcontentloaded")
    if is_logged_in(page):
        save_session(context)
        return True
    log("Not logged in. Opening sign-in; log in once in the browser window...")
    page.goto("https://medium.com/m/signin")
    try:
        page.wait_for_selector(", ".join(LOGIN_SELECTORS), timeout=300000)
        log("Login successful.")
        save_session(context)
        return True
    except Exception:
        log("Login timed out. Run again after logging in.")
        return False


# ---------------------------------------------------------------- editor ----

def wait_for_editor(page) -> None:
    """Wait for Medium's editor to mount (reload once if it fails).

    Waits on the first block, not h3.graf--title: an empty draft's title is
    a plain placeholder paragraph until something is typed.
    """
    try:
        page.wait_for_selector(FIRST_BLOCK, timeout=20000)
    except Exception:
        page.reload()
        page.wait_for_selector(FIRST_BLOCK, timeout=30000)
    page.wait_for_timeout(1000)


def open_story(page, sid: str) -> None:
    page.goto(f"https://medium.com/p/{sid}/edit")
    wait_for_editor(page)


def is_published(page) -> bool:
    """On an edit page: published stories show 'Save and publish' (republish)."""
    return page.locator('button[data-action="republish"]').count() > 0


def select_node(page, js_find: str, arg=None) -> bool:
    """Select the contents of the element returned by js_find (a JS arrow fn body)."""
    return page.evaluate(
        f"""(arg) => {{
            const editor = document.querySelector('{EDITOR_SELECTOR}');
            const el = ({js_find})(arg);
            if (!editor || !el) return false;
            editor.focus();
            el.scrollIntoView({{ block: 'center' }});
            const range = document.createRange();
            range.selectNodeContents(el);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            return true;
        }}""",
        arg,
    )


def clear_editor(page) -> None:
    """Delete the whole story (title, body, images) leaving an empty editor."""
    # A DOM Range selection is ignored when the story holds figures; the
    # editor's own select-all (keyboard) is what Medium honours.
    page.click(FIRST_BLOCK)
    page.keyboard.press("ControlOrMeta+a")
    page.wait_for_timeout(300)
    page.keyboard.press("Backspace")
    page.wait_for_function(
        """() => document.querySelectorAll('.postArticle-content img.graf-image').length === 0
              && document.querySelector('.postArticle-content').innerText.trim().split(/\\s+/).length < 10""",
        timeout=15000,
    )


def type_title(page, title: str) -> None:
    page.click(FIRST_BLOCK)
    select_node(page, f"() => document.querySelector('{FIRST_BLOCK}')")
    page.keyboard.type(title)
    page.keyboard.press("Enter")


def paste_html(page, html: str) -> None:
    """Paste HTML into the focused editor via a synthetic ClipboardEvent."""
    page.evaluate(
        """(h) => {
            const dt = new DataTransfer();
            dt.setData('text/html', h);
            dt.setData('text/plain', h.replace(/<[^>]+>/g, ''));
            document.activeElement.dispatchEvent(
                new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
        }""",
        html,
    )
    page.wait_for_timeout(1000)


def paste_image(page, path: str) -> None:
    """Paste an image file; waits until Medium serves it from its own CDN."""
    import base64

    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    mime = mimetypes.guess_type(path)[0] or "image/png"
    before = page.locator(IMAGE_SELECTOR).count()
    page.evaluate(
        """({ b64, name, mime }) => {
            const bin = atob(b64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const dt = new DataTransfer();
            dt.items.add(new File([bytes], name, { type: mime }));
            document.activeElement.dispatchEvent(
                new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
        }""",
        {"b64": b64, "name": Path(path).name, "mime": mime},
    )
    page.wait_for_function(
        """(n) => {
            const imgs = Array.from(document.querySelectorAll('.postArticle-content img.graf-image'));
            return imgs.length > n && imgs.every(i => i.src.includes('cdn-images'));
        }""",
        arg=before,
        timeout=60000,
    )


def select_token(page, token: str) -> None:
    found = select_node(
        page,
        """(tok) => Array.from(document.querySelectorAll('.postArticle-content p.graf'))
                .find(p => p.textContent.trim() === tok)""",
        token,
    )
    if not found:
        raise RuntimeError(f"Placeholder {token} not found in editor")


# ---------------------------------------------------------------- unsplash --

def open_unsplash_search(page, query: str) -> list[dict]:
    """With the caret on an EMPTY paragraph, open Medium's Unsplash picker and search.

    Returns [{id, author, author_url, thumb}] in the picker's order.
    """
    page.locator('[data-action="inline-menu"]').click()
    page.locator('[data-action="inline-menu-unsplash-image"]').click()
    box = page.locator(".js-unsplashImageInput").last
    box.wait_for(state="visible", timeout=10000)
    for attempt in range(2):
        box.click()  # typing before the box has focus lands in the story instead
        page.keyboard.press("ControlOrMeta+a")
        page.keyboard.type(query[:30])  # Medium caps the query at 30 chars
        page.keyboard.press("Enter")
        try:
            # Tile overlays are hidden until hovered: wait for attached, not visible.
            page.wait_for_selector('[data-action="unsplash-select-image"]',
                                   state="attached", timeout=15000)
            break
        except Exception:
            if attempt:
                return []
    page.wait_for_timeout(1500)
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('.unsplashImage')).map(tile => {
            const meta = tile.querySelector('[data-action="unsplash-select-image"]');
            const a = tile.querySelector('a[data-action="unsplash-open-author-link"]');
            const img = tile.querySelector('img');
            return meta && {
                id: meta.getAttribute('data-action-value'),
                author: a ? a.textContent.trim() : '',
                author_url: a ? a.getAttribute('data-action-value') : '',
                thumb: img ? img.src : '',
            };
        }).filter(Boolean)"""
    )


def insert_unsplash(page, query: str, photo_id: str) -> None:
    """Insert Unsplash photo `photo_id` (found via `query`) at the empty caret paragraph.

    Medium uploads it to its CDN and adds the "Photo by X on Unsplash" caption.
    """
    results = open_unsplash_search(page, query)
    if photo_id not in [r["id"] for r in results]:
        page.keyboard.press("Escape")
        raise RuntimeError(
            f"Unsplash photo {photo_id} not in results for {query!r} "
            f"(got {[r['id'] for r in results]}). Re-pick with tools/medium_cover.py."
        )
    tile = page.locator(f'[data-action="unsplash-select-image"][data-action-value="{photo_id}"]')
    tile.locator("xpath=..").hover()  # reveals the clickable overlay
    tile.click()
    page.wait_for_function(
        """(id) => {
            const img = document.querySelector(`.postArticle-content img[data-unsplash-photo-id="${id}"]`);
            return img && img.src.includes('cdn-images');
        }""",
        arg=photo_id,
        timeout=60000,
    )
    page.wait_for_timeout(1000)


def first_image_unsplash_id(page) -> str | None:
    return page.evaluate(
        "() => { const i = document.querySelector('.postArticle-content img.graf-image');"
        " return i ? i.getAttribute('data-unsplash-photo-id') : null; }"
    )


# ---------------------------------------------------------------- fill ------

def fill_story(page, post: dict) -> None:
    """Type title, paste body, upload local images, insert the Unsplash cover.

    The cover goes directly under the title, so it is the story's first image
    and therefore Medium's default preview (thumbnail) image.
    """
    meta = post["meta"]
    type_title(page, post["title"])
    body = post["body"]
    if meta.get("cover_id"):
        body = f"{COVER_TOKEN}\n\n{body}"
    with_tokens, images = tokenize_images(body)
    paste_html(page, markdown_to_editor_html(with_tokens))
    page.wait_for_timeout(1500)
    if meta.get("cover_id"):
        select_token(page, COVER_TOKEN)
        page.keyboard.press("Backspace")
        page.wait_for_timeout(500)
        insert_unsplash(page, meta["cover_query"], meta["cover_id"])
    for i, path in enumerate(images):
        select_token(page, f"IMGTOKEN{i}X")
        page.keyboard.press("Backspace")
        paste_image(page, path)
    verify_story(page, post, len(images))


def verify_story(page, post: dict, n_local_images: int) -> None:
    """Check the editor really holds what we meant to put there."""
    stats = page.evaluate(
        """(token) => {
            const ed = document.querySelector('.postArticle-content');
            return {
                images: ed.querySelectorAll('img.graf-image').length,
                pres: ed.querySelectorAll('pre').length,
                leftover: Array.from(ed.querySelectorAll('p.graf'))
                    .filter(p => /^IMGTOKEN/.test(p.textContent.trim())).length,
                title: (ed.querySelector('h3.graf--title, .graf:first-child') || {}).textContent || '',
            };
        }""",
        COVER_TOKEN,
    )
    want_images = n_local_images + (1 if post["meta"].get("cover_id") else 0)
    problems = []
    if stats["images"] != want_images:
        problems.append(f"images {stats['images']} != {want_images}")
    if stats["leftover"]:
        problems.append(f"{stats['leftover']} unreplaced image placeholders")
    if stats["title"].strip() != post["title"]:
        problems.append(f"title mismatch: {stats['title']!r}")
    want_pres = post["body"].count("\n```") // 2 if post["body"] else 0
    if stats["pres"] != want_pres:
        problems.append(f"code blocks {stats['pres']} != {want_pres} (Medium split or merged one)")
    if post["meta"].get("cover_id") and first_image_unsplash_id(page) != post["meta"]["cover_id"]:
        problems.append("first image is not the Unsplash cover")
    if problems:
        raise RuntimeError("Editor verification failed: " + "; ".join(problems))
    log(f"Verified: title, {stats['images']} images, {stats['pres']} code blocks.")


def wait_for_autosave(page, ms: int = 6000) -> None:
    page.wait_for_timeout(ms)


def wait_for_story_id(page) -> str:
    page.wait_for_url(re.compile(r"/p/[0-9a-f]+/edit"), timeout=30000)
    return re.search(r"/p/([0-9a-f]+)/edit", page.url).group(1)


# ---------------------------------------------------------- publish dialog --

def open_publish_dialog(page) -> None:
    page.locator('button[data-action="show-prepublish"]').click()
    # Not TOPIC_INPUT: Medium hides it once a story already has 5 topics.
    page.wait_for_selector(SUBTITLE_INPUT, timeout=20000)
    page.wait_for_timeout(1000)


def topic_suggestions(page, term: str) -> list[str]:
    """Type `term` in the (open) dialog's topic box; return suggestions like 'Statistics (9.7K)'."""
    box = page.locator(TOPIC_INPUT)
    box.focus()  # the open suggestion menu overlays the input, so no click
    box.fill("")
    page.keyboard.type(term, delay=40)
    try:
        page.wait_for_selector("#tagMultiSelectMenu button", timeout=5000)
        page.wait_for_timeout(800)
    except Exception:
        return []
    return [s.strip() for s in page.locator("#tagMultiSelectMenu button").all_inner_texts()]


def current_topics(page) -> list[str]:
    labels = page.locator('button[aria-label^="Remove "]').evaluate_all(
        "els => els.map(e => e.getAttribute('aria-label'))"
    )
    return [label[len("Remove "):] for label in labels]


def set_topics(page, tags: list[str]) -> list[str]:
    """Replace the dialog's topics with `tags` (max 5); returns what Medium shows."""
    for t in current_topics(page):
        page.locator(f'button[aria-label="Remove {t}"]').click()
        page.wait_for_timeout(300)
    for tag in tags[:5]:
        # Type the exact topic and press Enter. Clicking a suggestion is flaky:
        # the list re-renders under the cursor and the click is swallowed.
        topic_suggestions(page, tag)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1200)
    got = current_topics(page)
    missing = [t for t in tags[:5] if t.lower() not in [g.lower() for g in got]]
    if missing:
        raise RuntimeError(f"Topics not accepted by Medium: {missing} (dialog shows {got})")
    return got


def set_subtitle(page, subtitle: str) -> None:
    box = page.locator(SUBTITLE_INPUT)
    box.fill(subtitle[:140])
    if box.input_value() != subtitle[:140]:
        raise RuntimeError("Preview subtitle did not stick")


def has_preview_image(page) -> bool:
    return page.locator('button:text-is("Change preview image")').count() > 0


def click_final_publish(page) -> str:
    """Click the dialog's Publish button; return the live story URL."""
    sid = re.search(r"/p/([0-9a-f]+)", page.url).group(1)
    page.locator('button:text-is("Publish")').filter(visible=True).last.click()
    page.wait_for_url(lambda url: "/edit" not in url and "new-story" not in url, timeout=90000)
    return canonical_url(page, sid)


def canonical_url(page, sid: str) -> str:
    """Public URL of a story (Medium may land on /p/<id>/submission after publishing)."""
    page.goto(f"https://medium.com/p/{sid}")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)
    return page.url.split("?")[0]


def go_live(page, tags: list[str], subtitle: str | None, require_image: bool = True,
            dry_run: bool = False, screenshot: Path | None = None) -> str | None:
    """From an open draft's edit page: fill the publish dialog and publish."""
    if is_published(page):
        raise RuntimeError("Story is already published (use medium_edit.py --republish)")
    if require_image and not first_image_unsplash_id(page):
        raise RuntimeError("The story's first image is not an Unsplash cover, so it would "
                           "not get one as thumbnail. Pick one (medium_cover.py) and sync "
                           "(--sync), or pass --allow-no-cover.")
    open_publish_dialog(page)
    got = set_topics(page, tags)
    log(f"Topics set: {got}")
    if subtitle:
        set_subtitle(page, subtitle)
    if require_image and not has_preview_image(page):
        raise RuntimeError("Publish dialog shows no preview image.")
    if screenshot:
        page.screenshot(path=str(screenshot))
        log(f"Publish dialog screenshot: {screenshot}")
    if dry_run:
        log("Dry run: stopped before clicking Publish.")
        return None
    return click_final_publish(page)


def republish(page) -> str:
    """On a published story's edit page: click 'Save and publish'."""
    sid = re.search(r"/p/([0-9a-f]+)", page.url).group(1)
    page.locator('button[data-action="republish"]').click()
    page.wait_for_url(lambda url: "/edit" not in url, timeout=90000)
    return canonical_url(page, sid)


# ---------------------------------------------------------------- stories ---

def list_stories(page, tab: str) -> list[dict]:
    """Rows of /me/stories for one tab: {id, title, status, info, edit_url, url}."""
    page.goto(f"https://medium.com/me/stories?tab={STORY_TABS[tab]}")
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_selector("table tbody tr", timeout=12000)
    except Exception:
        return []
    last = -1
    while page.locator("table tbody tr").count() != last:  # lazy-loaded pages
        last = page.locator("table tbody tr").count()
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(1500)
    rows = page.evaluate(
        """() => Array.from(document.querySelectorAll('table tbody tr')).map(tr => {
            const links = Array.from(tr.querySelectorAll('a[href]')).map(a => a.href);
            const href = links.find(h => /\\/p\\/[0-9a-f]+|-[0-9a-f]{10,16}(\\?|$)/.test(h)) || '';
            const h2 = tr.querySelector('h2, h3');
            const lines = tr.innerText.split('\\n').map(s => s.trim()).filter(s => s && s !== '·');
            return { href, title: h2 ? h2.textContent.trim() : (lines[0] || ''), lines };
        })"""
    )
    out = []
    for r in rows:
        if not r["href"]:
            continue
        clean = r["href"].split("?")[0]
        m = re.search(r"/p/([0-9a-f]+)", clean) or re.search(r"-([0-9a-f]{10,16})$", clean)
        sid = m.group(1) if m else ""
        info = " · ".join(l for l in r["lines"][1:] if re.search(r"[A-Za-z]", l))
        out.append({
            "id": sid,
            "title": r["title"],
            "status": tab,
            "info": info,
            "edit_url": f"https://medium.com/p/{sid}/edit",
            "url": clean if tab != "drafts" else f"https://medium.com/p/{sid}/edit",
        })
    return out


# ---------------------------------------------------------------- scratch ---

def open_scratch(page) -> str:
    """Open the one reusable scratch draft (created on first use).

    Medium's Unsplash picker and topic box only exist inside a story, and
    any story you type in becomes a saved draft. Reusing one scratch draft
    keeps searches from littering your drafts list.
    """
    sid = None
    if SCRATCH_PATH.exists():
        sid = json.loads(SCRATCH_PATH.read_text()).get("id")
    if sid:
        try:
            open_story(page, sid)
            text = page.locator(FIRST_BLOCK).inner_text()
            if "aiblog scratch" in text and not is_published(page):
                return sid
        except Exception:
            pass
        log(f"Scratch draft {sid} unusable; creating a new one.")
    page.goto("https://medium.com/new-story")
    wait_for_editor(page)
    type_title(page, SCRATCH_TITLE)
    page.keyboard.type("Scratch.")
    sid = wait_for_story_id(page)
    wait_for_autosave(page, 3000)
    LOCAL_DIR.mkdir(exist_ok=True)
    SCRATCH_PATH.write_text(json.dumps({"id": sid}) + "\n")
    log(f"Created scratch draft {sid} (keep it; it is reused).")
    return sid


def caret_on_new_empty_paragraph(page) -> None:
    """Put the caret on a fresh empty paragraph at the end of the story."""
    select_node(page, f"""() => {{
        const g = document.querySelectorAll('{EDITOR_SELECTOR} .graf');
        return g[g.length - 1]; }}""")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.wait_for_timeout(600)


# ---------------------------------------------------------------- selftest --

def selftest() -> int:
    """Unit-test the converter without a browser. Returns exit code."""
    failures = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        print(f"{'ok' if cond else 'FAIL'}  {name} {detail}")
        failures += not cond

    html = markdown_to_editor_html("```python\nx = 1\n\ny = 2\n```")
    check("code kept as one <pre>", html.count("<pre>") == 1, html[:80])
    check("blank line padded with space", "\n \n" in html)
    html = markdown_to_editor_html("```python\nimport x\n\n\ndef f():\n    pass\n```")
    check("double blank line fully padded", "\n\n" not in html.split("<pre>")[1], html)

    html = markdown_to_editor_html("> quoted line")
    check("blockquote has bare text", "<blockquote>" in html and "<p>" not in html, html)

    html = markdown_to_editor_html("# Hi\n\nplain **bold**")
    check("heading converted", "<h1>Hi</h1>" in html)
    check("bold converted", "<strong>bold</strong>" in html)

    try:
        tokenize_images("a ![x](/tmp/does-not-exist.png) b")
        check("missing image raises", False)
    except FileNotFoundError:
        check("missing image raises", True)

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
        toks, imgs = tokenize_images(f"a ![x]({f.name}) b")
        check("jpg image tokenized", "IMGTOKEN0X" in toks and imgs == [f.name], toks)
        check("jpg mime", mimetypes.guess_type(f.name)[0] == "image/jpeg")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(selftest())
