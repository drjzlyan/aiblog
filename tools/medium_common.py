"""Shared Medium browser automation: session, login, paste helpers, markdown conversion.

Ported from the retired mcp/medium-mcp-server fork (our own aiblog-patches
branch) so this repo needs no MCP server. Medium has no usable public API;
everything goes through a headed Chromium window (Cloudflare blocks headless).

Session lives at repo-root medium-session.json (git-ignored). First run opens
a browser window: log in once, the session is reused afterwards.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_PATH = REPO_ROOT / "medium-session.json"

TITLE_SELECTOR = '.postArticle-content[contenteditable="true"] h3.graf--title'
EDITOR_SELECTOR = '.postArticle-content[contenteditable="true"]'

# Local images in post Markdown: ![alt](/absolute/path.png)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((\/[^)\s]+\.(?:png|jpe?g|gif))\)", re.IGNORECASE)

LOGIN_SELECTORS = [
    '[data-testid="headerUserButton"]',
    '[data-testid="write-button"]',
    'a[href="/me/stories"]',
]

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


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

    Port of markdownToEditorHtml: Medium splits a pasted <pre> at every blank
    line, so blank lines inside code get a single space; a blockquote must
    hold bare text (inner <p>/newlines render as empty quote blocks).
    """
    import markdown as md

    html = md.markdown(markdown_text, extensions=["fenced_code", "tables"])
    html = re.sub(
        r"<pre>[\s\S]*?</pre>",
        lambda m: m.group(0).replace("\n\n", "\n \n"),
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
        "viewport": {"width": 1280, "height": 720},
        "user_agent": UA,
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
    }
    if SESSION_PATH.exists():
        try:
            import json

            json.loads(SESSION_PATH.read_text())  # validate before handing to playwright
            options["storage_state"] = str(SESSION_PATH)
        except Exception as e:
            print(f"Saved session is corrupt ({e}); starting fresh.", file=sys.stderr)
    context = browser.new_context(**options)
    context.add_init_script(
        "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
    )
    return browser, context, context.new_page()


def save_session(context) -> None:
    SESSION_PATH.write_text(
        __import__("json").dumps(context.storage_state(), indent=2)
    )
    print("Session saved.", file=sys.stderr)


def is_logged_in(page) -> bool:
    for sel in LOGIN_SELECTORS:
        try:
            page.wait_for_selector(sel, timeout=3000)
            return True
        except Exception:
            continue
    return False


def ensure_logged_in(page, context) -> bool:
    """Return True once logged in. Blocks up to 5 min for a manual login."""
    page.goto("https://medium.com")
    page.wait_for_load_state("networkidle")
    if SESSION_PATH.exists():
        print("Found existing session file, testing login status...", file=sys.stderr)
    if is_logged_in(page):
        print("Already logged in to Medium.", file=sys.stderr)
        save_session(context)
        return True
    print("Not logged in. Opening sign-in; log in once in the browser window...",
          file=sys.stderr)
    page.goto("https://medium.com/m/signin")
    try:
        page.wait_for_selector(
            ", ".join(LOGIN_SELECTORS), timeout=300000
        )
        print("Login successful.", file=sys.stderr)
        save_session(context)
        return True
    except Exception:
        print("Login timed out. Run again after logging in.", file=sys.stderr)
        return False


# ---------------------------------------------------------------- editor ----

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
    before = page.locator(".postArticle-content img.graf-image").count()
    page.evaluate(
        """({ b64, name }) => {
            const bin = atob(b64);
            const bytes = new Uint8Array(bin.length);
            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            const dt = new DataTransfer();
            dt.items.add(new File([bytes], name, { type: 'image/png' }));
            document.activeElement.dispatchEvent(
                new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
        }""",
        {"b64": b64, "name": Path(path).name},
    )
    page.wait_for_function(
        """(n) => {
            const imgs = Array.from(
                document.querySelectorAll('.postArticle-content img.graf-image'));
            return imgs.length > n && imgs.every(i => i.src.includes('cdn-images'));
        }""",
        arg=before,
        timeout=60000,
    )


def wait_for_editor(page) -> None:
    """Wait for Medium's editor to mount (reload once if it fails)."""
    try:
        page.wait_for_selector(TITLE_SELECTOR, timeout=20000)
    except Exception:
        page.reload()
        page.wait_for_selector(TITLE_SELECTOR, timeout=30000)


def fill_body_and_images(page, content: str) -> None:
    """Paste Markdown body (with local images) at the caret; swap in uploads."""
    with_tokens, images = tokenize_images(content)
    paste_html(page, markdown_to_editor_html(with_tokens))
    page.wait_for_timeout(1500)
    for i, path in enumerate(images):
        found = page.evaluate(
            """(tok) => {
                const editor = document.querySelector('.postArticle-content[contenteditable="true"]');
                const el = Array.from(
                    document.querySelectorAll('.postArticle-content p.graf'))
                    .find(p => p.textContent.trim() === tok);
                if (!editor || !el) return false;
                editor.focus();
                el.scrollIntoView({ block: 'center' });
                const range = document.createRange();
                range.selectNodeContents(el);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                return true;
            }""",
            f"IMGTOKEN{i}X",
        )
        if not found:
            raise RuntimeError(f"Image placeholder {i} not found in editor")
        page.keyboard.press("Backspace")
        paste_image(page, path)


def type_title(page, title: str) -> None:
    page.click(TITLE_SELECTOR)
    page.keyboard.press("ControlOrMeta+a")
    page.keyboard.type(title)
    page.keyboard.press("Enter")


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

    html = markdown_to_editor_html("> quoted line")
    check("blockquote has bare text", "<blockquote>" in html and "<p>" not in html, html)

    html = markdown_to_editor_html("# Hi\n\nplain **bold**")
    check("heading converted", "<h1>Hi</h1>" in html)
    check("bold converted", "<strong>bold</strong>" in html)

    md_text = "a ![x](/tmp/does-not-exist.png) b"
    try:
        tokenize_images(md_text)
        check("missing image raises", False)
    except FileNotFoundError:
        check("missing image raises", True)

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        toks, imgs = tokenize_images(f"a ![x]({f.name}) b")
        check("image tokenized", "IMGTOKEN0X" in toks and imgs == [f.name], toks)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(selftest())
