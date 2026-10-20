"""Import an existing Medium story (draft or published) into the repo.

Usage:
  uv run python tools/medium_pull.py <id-or-url> [--slug my-slug] [--into posts/NN-slug]

For older stories that were written outside this repo (find ids with
medium_list.py). Creates posts/NN-slug/ with post.md (Markdown converted
from the editor), images/ (downloaded from Medium's CDN, referenced via
{{img:}}), and medium.json (id, status, URL), so the normal loop applies:
edit post.md -> build_post.py -> medium_edit.py / medium_golive.py.

If the first image is an Unsplash photo it becomes the frontmatter cover
(cover_id, cover_author); set cover_query by running medium_cover.py
search/pick, since Medium's picker can only re-find a photo by keywords.
Published stories also get their current tags pulled into frontmatter.
Code blocks come in as plain fenced code: they were not run by this repo,
so move them into code/ and run them before claiming their output.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medium_common as mc
import postlib

EXTRACT_JS = r"""() => {
  const ed = document.querySelector('.postArticle-content');
  const inline = (node) => {
    let out = '';
    node.childNodes.forEach(n => {
      if (n.nodeType === 3) { out += n.textContent; return; }
      if (n.nodeType !== 1) return;
      const t = n.tagName.toLowerCase();
      if (n.classList.contains('defaultValue')) return;
      const inner = inline(n);
      if (t === 'br') out += '\n';
      else if (t === 'strong' || t === 'b') out += inner.trim() ? `**${inner}**` : inner;
      else if (t === 'em' || t === 'i') out += inner.trim() ? `*${inner}*` : inner;
      else if (t === 'code') out += '`' + inner + '`';
      else if (t === 'a') out += `[${inner}](${n.getAttribute('href') || ''})`;
      else out += inner;
    });
    return out;
  };
  const blocks = [];
  let title = null, sectionCount = 0;
  ed.querySelectorAll('section').forEach(section => {
    if (sectionCount++ > 0) blocks.push({ kind: 'md', text: '---' });
    section.querySelectorAll('.section-inner > *').forEach(el => {
      const t = el.tagName.toLowerCase();
      const cls = el.className || '';
      if (t === 'h3' && cls.includes('graf--title') && title === null) { title = el.textContent.trim(); return; }
      if (t === 'h3') blocks.push({ kind: 'md', text: '## ' + inline(el).trim() });
      else if (t === 'h4') blocks.push({ kind: 'md', text: '### ' + inline(el).trim() });
      else if (t === 'p') { const s = inline(el).trim(); if (s) blocks.push({ kind: 'md', text: s }); }
      else if (t === 'blockquote') blocks.push({ kind: 'md', text: '> ' + inline(el).trim() });
      else if (t === 'pre') {
        const c = el.cloneNode(true);
        c.querySelectorAll('.u-ignoreBlock, .codeBlockMenu-button').forEach(x => x.remove());
        c.querySelectorAll('br').forEach(br => br.replaceWith('\n'));  // Medium code lines are <br>s
        const lang = el.getAttribute('data-code-block-lang') || '';
        blocks.push({ kind: 'md', text: '```' + lang + '\n' + c.textContent.replace(/\n$/, '') + '\n```' });
      }
      else if (t === 'ul' || t === 'ol') {
        const items = Array.from(el.querySelectorAll('li')).map((li, i) =>
          (t === 'ul' ? '- ' : `${i + 1}. `) + inline(li).trim());
        blocks.push({ kind: 'md', text: items.join('\n') });
      } else if (t === 'figure') {
        const img = el.querySelector('img.graf-image');
        const cap = el.querySelector('figcaption');
        if (cap) cap.querySelectorAll('.defaultValue').forEach(x => x.remove());
        const iframe = el.querySelector('iframe');
        if (img) blocks.push({
          kind: 'img', id: img.getAttribute('data-image-id'),
          unsplash: img.getAttribute('data-unsplash-photo-id'),
          caption: cap ? cap.textContent.trim() : '',
          author: cap && cap.querySelector('a[rel="photo-creator"]')
                  ? cap.querySelector('a[rel="photo-creator"]').textContent.trim() : '',
        });
        else if (iframe) blocks.push({ kind: 'md', text: `<!-- embed not imported: ${iframe.src} -->` });
      }
    });
  });
  if (title === null) {
    const first = blocks.findIndex(b => b.kind === 'md');
    title = first >= 0 ? blocks.splice(first, 1)[0].text.replace(/^#+\s*/, '') : 'Untitled';
  }
  return { title, blocks };
}"""


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50].strip("-") or "post"


def download(image_id: str, dest_stem: Path) -> Path:
    url = f"https://cdn-images-1.medium.com/max/1600/{image_id}"
    req = urllib.request.Request(url, headers={"User-Agent": mc.UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get("Content-Type", "image/png")
        data = r.read()
    ext = {"image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}.get(ctype, ".png")
    path = dest_stem.with_suffix(ext)
    path.write_bytes(data)
    return path


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__.strip())
        return 0
    slug = into = None
    if "--slug" in args:
        i = args.index("--slug"); slug = args[i + 1]; del args[i:i + 2]
    if "--into" in args:
        i = args.index("--into"); into = Path(args[i + 1]); del args[i:i + 2]
    sid = postlib.story_id(args[0])

    for f in postlib.POSTS_ROOT.glob("*/medium.json"):
        if json.loads(f.read_text()).get("id") == sid:
            print(f"Already in repo: {f.parent}", file=sys.stderr)
            return 1

    with mc.medium_session() as page:
        mc.open_story(page, sid)
        published = mc.is_published(page)
        data = page.evaluate(EXTRACT_JS)
        url = f"https://medium.com/p/{sid}/edit"
        tags: list[str] = []
        if published:
            page.goto(f"https://medium.com/p/{sid}")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2500)
            url = page.url.split("?")[0]
            tags = page.evaluate(
                "() => [...new Set(Array.from(document.querySelectorAll('a[href*=\"/tag/\"]'))"
                ".map(a => a.textContent.trim()).filter(Boolean))].slice(0, 5)"
            )

    post_dir = into or postlib.next_post_dir(slug or slugify(data["title"]))
    (post_dir / "images").mkdir(parents=True, exist_ok=True)
    (post_dir / "code").mkdir(exist_ok=True)
    meta: dict = {}
    if tags:
        meta["tags"] = tags
    parts = [f"# {data['title']}", ""]
    n = 0
    for i, b in enumerate(data["blocks"]):
        if b["kind"] == "md":
            parts += [b["text"], ""]
            continue
        if b.get("unsplash") and not meta.get("cover_id") and n == 0:
            meta["cover_id"] = b["unsplash"]
            meta["cover_author"] = b["author"]
            n += 1
            continue  # re-inserted from frontmatter on publish/edit
        n += 1
        path = download(b["id"], post_dir / "images" / f"pulled_{n:02d}")
        alt = b["caption"].replace("|", "/").replace("}", ")")
        parts += [f"{{{{img:{path.name}|{alt}}}}}", ""]
    body = "\n".join(parts).rstrip() + "\n"
    (post_dir / "post.md").write_text(postlib.join_frontmatter(meta, body))
    postlib.save_state(post_dir, id=sid, edit_url=f"https://medium.com/p/{sid}/edit",
                       status="published" if published else "draft",
                       url=url, title=data["title"], pulled=True)
    print(f"Pulled {sid} ({'published' if published else 'draft'}) into {post_dir}")
    if meta.get("cover_id"):
        print(f"Unsplash cover {meta['cover_id']} found: set cover_query via "
              f"medium_cover.py {post_dir} search/pick before editing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
