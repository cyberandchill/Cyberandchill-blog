#!/usr/bin/env python3
"""Build static Pages output and connect related CyberAndChill articles."""
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, unquote
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
posts = json.loads((ROOT / "articles.json").read_text())
assert len(posts) >= 300, "Unexpected article index size"
assert len({p["url"] for p in posts}) == len(posts), "Duplicate URLs"
stop = set("the a an and or in for to of your you on it with how what why from that this can should is are be do i my one into when without before after which vs tech it iam".split())
def terms(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3 and w not in stop}
def esc(s):
    return html.escape(str(s), quote=True)
def key(p):
    return p["url"].strip("/").split("/")[-1]
by_slug = {key(p): p for p in posts}
# Existing article-to-article Kit links become local blog links.
pattern = re.compile(r'(href\s*=\s*["\'])(https?://(?:www\.)?cyberandchill\.com/posts/([^"\'?#/]+)(?:[/?#][^"\']*)?)(["\'])', re.I)
def relink(match):
    slug = unquote(match.group(3))
    target = by_slug.get(slug)
    return match.group(1) + (target["url"] if target else match.group(2)) + match.group(4)

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
for f in ROOT.iterdir():
    if f.is_file() and f.name not in {"README.md"}:
        shutil.copy2(f, OUT / f.name)
shutil.copytree(ROOT / "posts", OUT / "posts")

categories = sorted({p["category"] for p in posts})
hub_urls = {}
for category in categories:
    slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")
    hub_urls[category] = "/topics/" + slug + "/"
    dest = OUT / "topics" / slug
    dest.mkdir(parents=True, exist_ok=True)
    subset = [p for p in posts if p["category"] == category]
    cards = "".join(f'<li><a href="{esc(p["url"])}">{esc(p["title"])}</a></li>' for p in subset)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(category)} Articles | CyberAndChill</title><meta name="description" content="Explore {esc(category)} articles from CyberAndChill."><link rel="canonical" href="https://blog.cyberandchill.com/topics/{slug}/"><link rel="stylesheet" href="../../article.css"></head><body><header><nav><a href="/">CyberAndChill Blog</a><a href="https://cyberandchill.com/products/cyber-and-chill-premium-newsletter">Explore the Vault</a></nav></header><main><p><a href="/">← All articles</a></p><h1>{esc(category)}</h1><p>Browse {len(subset)} published articles.</p><ul>{cards}</ul></main></body></html>"""
    (dest / "index.html").write_text(page)

# Relevance-first recommendations. Hubs receive prominence without hundreds
# of repetitive, keyword-stuffed body links.
title_terms = [terms(p["title"]) for p in posts]
incoming = Counter()
replaced = 0
for i, post in enumerate(posts):
    path = OUT / post["url"].strip("/") / "index.html"
    source = path.read_text()
    source, n = pattern.subn(relink, source)
    replaced += n
    candidates = []
    for j, other in enumerate(posts):
        if i == j:
            continue
        common = len(title_terms[i] & title_terms[j])
        score = common * 5 + (3 if post["category"] == other["category"] else 0)
        if common >= 1 and score >= 8:
            candidates.append((score, j))
    candidates.sort(key=lambda x: (-x[0], incoming[x[1]], x[1]))
    selected = [j for _, j in candidates[:4]]
    for j in selected:
        incoming[j] += 1
    related = "".join(f'<li><a href="{esc(posts[j]["url"])}">{esc(posts[j]["title"])}</a></li>' for j in selected)
    hub = hub_urls[post["category"]]
    block = '<aside class="related" aria-label="Related reading"><h2>Keep reading</h2>'
    block += f'<p><a href="{esc(hub)}">Explore more {esc(post["category"])} articles</a></p>'
    if related:
        block += f'<ul>{related}</ul>'
    block += '</aside>'
    source = source.replace('</main>', block + '</main>')
    path.write_text(source)

# Link hubs from home navigation and keep SEO metadata accurate.
index = OUT / "index.html"
home = index.read_text()
links = " ".join(f'<a href="{esc(hub_urls[c])}">{esc(c)}</a>' for c in categories)
home = home.replace('<a href="https://cyberandchill.com">Home</a>', links + ' <a href="https://cyberandchill.com">Main site</a>')
index.write_text(home)
css = OUT / "article.css"
css.write_text(css.read_text() + '\n.related{border-top:1px solid var(--edge);margin-top:46px;padding-top:16px}.related li{margin:10px 0}.related h2{font-size:1.35rem}\n')
urls = ["https://blog.cyberandchill.com/"] + ["https://blog.cyberandchill.com"+p["url"] for p in posts] + ["https://blog.cyberandchill.com"+u for u in hub_urls.values()]
(OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{esc(u)}</loc></url>' for u in urls) + '</urlset>')
print(f"Built {len(posts)} pages, {len(categories)} hubs, changed {replaced} existing article links, added related links. Output: {OUT}")
