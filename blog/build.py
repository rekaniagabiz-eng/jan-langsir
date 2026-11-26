#!/usr/bin/env python3
"""
Penjana blog Jan Langsir (tanpa pakej tambahan, Python 3 sahaja).

Cara guna:
  1. Tulis artikel baru dalam  blog/posts/  sebagai fail .md
  2. Jalankan:  python3 blog/build.py
     (atau biar GitHub Actions jalankan secara automatik bila anda push)

Setiap artikel dijadikan halaman HTML sendiri supaya apabila dikongsi di
Facebook / WhatsApp / Telegram / X, tajuk + gambar + ringkasan terpapar elok.
"""
import datetime
import html
import re
import shutil
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote

# ============ TETAPAN: TUKAR BAHAGIAN INI SAHAJA ============
# Alamat penuh laman anda, TANPA garis condong di hujung.
# Contoh GitHub Pages : https://namaanda.github.io/nama-repo
# Contoh domain sendiri: https://www.janlangsir.com
SITE_URL = "https://USERNAME.github.io/REPO"
SITE_NAME = "Jan Langsir"
BLOG_TITLE = "Blog Jan Langsir"
BLOG_DESC = "Tip, idea dan panduan memilih langsir & bidai untuk rumah dan premis anda."
WA = "60194477867"
DEFAULT_IMAGE = "images/hero.jpeg"   # gambar kongsi jika artikel tiada gambar
PIXEL_ID = "1456977869632692"
# =============================================================

BLOG = Path(__file__).resolve().parent
ROOT = BLOG.parent
POSTS = BLOG / "posts"
MARK = "<!-- generated-by-build.py -->"
BULAN = ["Januari", "Februari", "Mac", "April", "Mei", "Jun", "Julai",
         "Ogos", "September", "Oktober", "November", "Disember"]


# ---------- Markdown mini ----------
def fix_url(u, root):
    if re.match(r"^(https?:|mailto:|tel:|#|/)", u):
        return u
    return root + u


def inline(s, root):
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
               lambda m: f'<img src="{fix_url(m.group(2), root)}" alt="{m.group(1)}" loading="lazy">', s)

    def link(m):
        u = fix_url(m.group(2), root)
        ext = ' target="_blank" rel="noopener"' if u.startswith("http") else ""
        return f'<a href="{u}"{ext}>{m.group(1)}</a>'
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md(text, root):
    lines = text.replace("\r\n", "\n").split("\n")
    out, i = [], 0
    block_start = re.compile(r"^(#{1,3}\s|[-*]\s|\d+\.\s|>|\||---+\s*$)")
    while i < len(lines):
        l = lines[i]
        if not l.strip():
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", l)
        if m:
            lv = len(m.group(1)) + 1
            out.append(f"<h{lv}>{inline(m.group(2).strip(), root)}</h{lv}>")
            i += 1
        elif re.match(r"^---+\s*$", l):
            out.append("<hr>")
            i += 1
        elif re.match(r"^[-*]\s+", l) or re.match(r"^\d+\.\s+", l):
            ordered = bool(re.match(r"^\d+\.\s+", l))
            pat = r"^\d+\.\s+" if ordered else r"^[-*]\s+"
            items = []
            while i < len(lines) and re.match(pat, lines[i]):
                items.append(f"<li>{inline(re.sub(pat, '', lines[i]).strip(), root)}</li>")
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
        elif l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [r for r in rows if not all(re.match(r"^:?-+:?$", c) for c in r)]
            head_r, body_r = rows[0], rows[1:]
            t = "<thead><tr>" + "".join(f"<th>{inline(c, root)}</th>" for c in head_r) + "</tr></thead>"
            t += "<tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c, root)}</td>" for c in r) + "</tr>" for r in body_r) + "</tbody>"
            out.append(f'<div class="tbl"><table>{t}</table></div>')
        elif l.startswith(">"):
            q = []
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i].lstrip("> ").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(q), root)}</p></blockquote>")
        else:
            p = []
            while i < len(lines) and lines[i].strip() and not block_start.match(lines[i]):
                p.append(lines[i].strip())
                i += 1
            if not p:  # elak gelung tak berakhir
                p, i = [lines[i].strip()], i + 1
            out.append(f"<p>{inline(' '.join(p), root)}</p>")
    return "\n".join(out)


def parse_post(path):
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip('"').strip("'")
        body = m.group(2)
    stem = path.stem
    dm = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", stem)
    slug = dm.group(2) if dm else stem
    date_s = meta.get("date") or (dm.group(1) if dm else "")
    try:
        date = datetime.date.fromisoformat(date_s)
    except ValueError:
        raise SystemExit(f"Tarikh tidak sah dalam {path.name}. Guna format 2026-11-26")
    title = meta.get("title") or slug.replace("-", " ").title()
    plain = re.sub(r"[#*>\[\]()!_`-]", " ", body)
    desc = meta.get("description") or " ".join(plain.split())[:155].rstrip() + "…"
    words = len(plain.split())
    return {
        "slug": slug, "title": title, "date": date, "desc": desc,
        "image": meta.get("image", ""), "draft": meta.get("draft", "").lower() == "true",
        "body": body, "mins": max(1, round(words / 200)),
    }


def fmt_date(d):
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


# ---------- Templat HTML ----------
def head(root, title, desc, url, image, kind="website", extra=""):
    t = html.escape(title)
    d = html.escape(desc)
    img = image if image.startswith("http") else f"{SITE_URL}/{image}"
    return f"""<!DOCTYPE html>
<html lang="ms">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{MARK}
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<link rel="icon" href="{root}favicon.ico" sizes="any">
<link rel="alternate" type="application/rss+xml" title="{BLOG_TITLE}" href="{SITE_URL}/blog/feed.xml">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="ms_MY">
<meta property="og:type" content="{kind}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{img}">
{extra}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700&family=Figtree:wght@400;600&display=swap" rel="stylesheet">
<script>
!function(f,b,e,v,n,t,s){{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}}(window,
document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{PIXEL_ID}');
fbq('track', 'PageView');
</script>
<link rel="stylesheet" href="{root}blog/blog.css">
</head>
<body>
<nav>
  <div class="wrap">
    <a class="logo" href="{root}">{SITE_NAME}</a>
    <ul>
      <li><a href="{root}#produk">Produk</a></li>
      <li><a href="{root}#promosi">Promosi</a></li>
      <li><a href="{root}blog/" aria-current="page">Blog</a></li>
      <li><a class="btn wa-link" href="https://wa.me/{WA}?text=Hi%2C%20saya%20berminat%20dengan%20langsir" target="_blank" rel="noopener">WhatsApp</a></li>
    </ul>
  </div>
</nav>
"""


def foot(root):
    return f"""<footer><p style="margin:0 0 6px"><a href="{root}">Laman utama</a> &middot; <a href="{root}blog/">Blog</a></p>&copy; {datetime.date.today().year} {SITE_NAME}. Semua hak terpelihara.</footer>
<a class="wa wa-link" href="https://wa.me/{WA}?text=Hi%2C%20saya%20berminat%20dengan%20langsir" target="_blank" rel="noopener" aria-label="WhatsApp">WhatsApp</a>
<script>
document.querySelectorAll('.wa-link').forEach(function(a){{a.addEventListener('click',function(){{if(window.fbq)fbq('track','Contact');}});}});
var cp=document.getElementById('copylink');
if(cp){{cp.addEventListener('click',function(){{
  var u=cp.getAttribute('data-url');
  function ok(){{cp.textContent='Pautan disalin ✓';setTimeout(function(){{cp.textContent='Salin pautan';}},2200);}}
  if(navigator.clipboard){{navigator.clipboard.writeText(u).then(ok);}}
  else{{var t=document.createElement('textarea');t.value=u;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove();ok();}}
}});}}
var nb=document.getElementById('nativeshare');
if(nb){{if(navigator.share){{nb.hidden=false;nb.addEventListener('click',function(){{navigator.share({{title:nb.getAttribute('data-title'),url:nb.getAttribute('data-url')}}).catch(function(){{}});}});}}}}
</script>
</body>
</html>
"""


def share_block(title, url):
    u, t = quote(url, safe=""), quote(title, safe="")
    return f"""<div class="share">
  <p class="share-t">Kongsi artikel ini</p>
  <div class="share-row">
    <button type="button" id="nativeshare" class="sbtn" data-url="{url}" data-title="{html.escape(title)}" hidden>Kongsi…</button>
    <a class="sbtn s-wa" href="https://wa.me/?text={t}%20{u}" target="_blank" rel="noopener">WhatsApp</a>
    <a class="sbtn s-fb" href="https://www.facebook.com/sharer/sharer.php?u={u}" target="_blank" rel="noopener">Facebook</a>
    <a class="sbtn s-tg" href="https://t.me/share/url?url={u}&amp;text={t}" target="_blank" rel="noopener">Telegram</a>
    <a class="sbtn s-x" href="https://twitter.com/intent/tweet?url={u}&amp;text={t}" target="_blank" rel="noopener">X</a>
    <button type="button" id="copylink" class="sbtn" data-url="{url}">Salin pautan</button>
  </div>
</div>"""


def render_post(p, prev_p, next_p):
    root = "../../"
    url = f"{SITE_URL}/blog/{p['slug']}/"
    image = p["image"] or DEFAULT_IMAGE
    abs_img = image if image.startswith("http") else f"{SITE_URL}/{image}"
    ld = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"BlogPosting",'
          f'"headline":{html_json(p["title"])},"datePublished":"{p["date"].isoformat()}",'
          f'"image":"{abs_img}","mainEntityOfPage":"{url}",'
          f'"author":{{"@type":"Organization","name":"{SITE_NAME}"}},'
          f'"publisher":{{"@type":"Organization","name":"{SITE_NAME}"}}}}</script>\n')
    meta_extra = f'<meta property="article:published_time" content="{p["date"].isoformat()}">\n' + ld
    hero = ""
    if p["image"]:
        hero = f'<img class="cover" src="{fix_url(p["image"], root)}" alt="{html.escape(p["title"])}">'
    nav = ""
    if prev_p or next_p:
        a = f'<a href="../{prev_p["slug"]}/">&larr; {html.escape(prev_p["title"])}</a>' if prev_p else "<span></span>"
        b = f'<a href="../{next_p["slug"]}/">{html.escape(next_p["title"])} &rarr;</a>' if next_p else "<span></span>"
        nav = f'<div class="pn">{a}{b}</div>'
    wa_msg = quote(f"Hi, saya baca artikel anda: {p['title']}. Saya berminat untuk dapatkan sebut harga.")
    return (head(root, f"{p['title']} | {SITE_NAME}", p["desc"], url, image, "article", meta_extra) + f"""<main class="wrap post">
  <p class="crumb"><a href="../">&larr; Semua artikel</a></p>
  <h1>{html.escape(p['title'])}</h1>
  <p class="meta">{fmt_date(p['date'])} &middot; {p['mins']} minit bacaan</p>
  {hero}
  <article class="prose">
{md(p['body'], root)}
  </article>
  <aside class="cta">
    <h2>Nak langsir yang sesuai untuk rumah anda?</h2>
    <p>Kami ukur dan beri sebut harga terus di tapak, tanpa caj tersembunyi.</p>
    <a class="btn wa-link" href="https://wa.me/{WA}?text={wa_msg}" target="_blank" rel="noopener">WhatsApp kami sekarang</a>
  </aside>
  {share_block(p['title'], url)}
  {nav}
</main>
""" + foot(root))


def html_json(s):
    import json
    return json.dumps(s, ensure_ascii=False)


def render_index(posts):
    root = "../"
    cards = []
    for p in posts:
        img = ""
        if p["image"]:
            img = f'<div class="ph"><img src="{fix_url(p["image"], root)}" alt="" loading="lazy"></div>'
        cards.append(f"""<article class="card">
  <a class="card-a" href="{p['slug']}/">
    {img}
    <div class="card-b">
      <p class="meta">{fmt_date(p['date'])} &middot; {p['mins']} min</p>
      <h2>{html.escape(p['title'])}</h2>
      <p>{html.escape(p['desc'])}</p>
      <span class="more">Baca selanjutnya &rarr;</span>
    </div>
  </a>
</article>""")
    body = "\n".join(cards) if cards else "<p>Artikel pertama akan diterbitkan tidak lama lagi.</p>"
    return (head(root, f"{BLOG_TITLE} | {SITE_NAME}", BLOG_DESC, f"{SITE_URL}/blog/", DEFAULT_IMAGE) + f"""<header class="bloghead">
  <div class="wrap">
    <h1>{BLOG_TITLE}</h1>
    <p>{BLOG_DESC}</p>
  </div>
</header>
<main class="wrap">
  <div class="cards">
{body}
  </div>
</main>
""" + foot(root))


def render_sitemap(posts):
    urls = [f"{SITE_URL}/", f"{SITE_URL}/blog/"] + [f"{SITE_URL}/blog/{p['slug']}/" for p in posts]
    dates = [None, posts[0]["date"] if posts else None] + [p["date"] for p in posts]
    items = []
    for u, d in zip(urls, dates):
        lm = f"<lastmod>{d.isoformat()}</lastmod>" if d else ""
        items.append(f"  <url><loc>{u}</loc>{lm}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(items) + "\n</urlset>\n")


def render_rss(posts):
    items = []
    for p in posts[:30]:
        dt = datetime.datetime.combine(p["date"], datetime.time(8, 0), tzinfo=datetime.timezone.utc)
        items.append(f"""    <item>
      <title>{html.escape(p['title'])}</title>
      <link>{SITE_URL}/blog/{p['slug']}/</link>
      <guid>{SITE_URL}/blog/{p['slug']}/</guid>
      <pubDate>{format_datetime(dt)}</pubDate>
      <description>{html.escape(p['desc'])}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{html.escape(BLOG_TITLE)}</title>
    <link>{SITE_URL}/blog/</link>
    <description>{html.escape(BLOG_DESC)}</description>
    <language>ms</language>
{chr(10).join(items)}
  </channel>
</rss>
"""


def main():
    today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date()  # waktu Malaysia
    all_posts = []
    for f in sorted(POSTS.glob("*.md")):
        if f.name.startswith("_"):
            continue
        all_posts.append(parse_post(f))

    posts = [p for p in all_posts if not p["draft"] and p["date"] <= today]
    skipped = len(all_posts) - len(posts)
    posts.sort(key=lambda p: p["date"], reverse=True)

    slugs = [p["slug"] for p in posts]
    if len(set(slugs)) != len(slugs):
        raise SystemExit("Ada dua artikel dengan slug (nama fail) yang sama.")

    # buang halaman lama yang artikelnya sudah dipadam
    for d in BLOG.iterdir():
        idx = d / "index.html"
        if d.is_dir() and d.name != "posts" and idx.exists() and MARK in idx.read_text(encoding="utf-8"):
            if d.name not in slugs:
                shutil.rmtree(d)

    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        d = BLOG / p["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(render_post(p, older, newer), encoding="utf-8")

    (BLOG / "index.html").write_text(render_index(posts), encoding="utf-8")
    (BLOG / "sitemap.xml").write_text(render_sitemap(posts), encoding="utf-8")
    (BLOG / "feed.xml").write_text(render_rss(posts), encoding="utf-8")
    print(f"Siap: {len(posts)} artikel diterbitkan, {skipped} dijadual/draf (dilangkau).")
    if "USERNAME" in SITE_URL:
        print("AMARAN: Tukar SITE_URL di bahagian atas build.py supaya pautan kongsi berfungsi.")


if __name__ == "__main__":
    main()
