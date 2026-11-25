"""Build the static site from tools/site.json and content/*.md.

    pip install markdown
    python tools/build.py          # writes index.html, guides/, sitemap.xml, robots.txt, 404.html

Change the brand, address or kits in tools/site.json, add a guide as content/<slug>.md, and run it again.
"""

import html
import json
import re
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "tools" / "site.json").read_text(encoding="utf-8"))
BASE = CFG["site_url"].rstrip("/")
BRAND = CFG["brand"]
OWNER = CFG["github_owner"]
KITS = {k["slug"]: k for k in CFG["kits"]}


def e(s: str) -> str:
    return html.escape(s, quote=True)


def utm(url: str, campaign: str) -> str:
    return f"{url}?utm_source=site&utm_medium=web&utm_campaign={campaign}"


def page(*, title: str, description: str, path: str, body: str, image: str, jsonld: dict, og_type: str = "website") -> str:
    url = f"{BASE}{path}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/img/{image}.webp">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23128a78'/%3E%3Cpath d='M9 17l5 5 9-11' stroke='white' stroke-width='3.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<link rel="stylesheet" href="/style.css">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="/">{e(BRAND)}</a>
  <nav><a href="/#kits">Kits</a><a href="/#guides">Guides</a><a href="https://github.com/{OWNER}">GitHub</a></nav>
</div></header>
{body}
<footer class="foot"><div class="wrap">
  <p>{e(BRAND)} by {e(CFG["author"])}. Independent starter kits for building with the Claude API. Not affiliated with Anthropic.</p>
  <p>Questions about a kit? Reply to your Gumroad receipt email. We answer within 2 working days.</p>
</div></footer>
</body>
</html>
"""


def kit_card(k: dict, campaign: str) -> str:
    guide = f'<a href="/guides/{k["article"]}/">Read the guide</a> · ' if k.get("article") else ""
    return f"""<article class="card">
  <img src="/img/{k["img"]}.webp" alt="{e(k["name"])} cover" width="1200" height="675" loading="lazy">
  <div class="card-body">
    <h3>{e(k["name"])}</h3>
    <p>{e(k["summary"])}</p>
    <p class="links">{guide}<a href="https://github.com/{k.get("owner", OWNER)}/{k["free_repo"]}">Free version on GitHub</a></p>
    <a class="btn" href="{utm(k["url"], campaign)}">Get the kit · {e(k["price"])}</a>
  </div>
</article>"""


def parse_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines())
    return meta, m.group(2)


def build_guide(slug: str, meta: dict, md: str) -> str:
    k = KITS[meta["kit"]]
    md = md.replace("{{owner}}", k.get("owner", OWNER)).replace("{{kit_url}}", utm(k["url"], slug)).replace("{{kit_price}}", k["price"])
    content = markdown.markdown(md, extensions=["fenced_code", "tables"])
    path = f"/guides/{slug}/"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": meta["title"],
        "description": meta["description"],
        "datePublished": meta["date"],
        "dateModified": meta["date"],
        "author": {"@type": "Person", "name": CFG["author"]},
        "image": f"{BASE}/img/{k['img']}.webp",
        "mainEntityOfPage": f"{BASE}{path}",
    }
    body = f"""<main class="wrap article">
  <p class="crumbs"><a href="/">Home</a> / <a href="/#guides">Guides</a></p>
  <h1>{e(meta["title"])}</h1>
  <p class="meta">{e(CFG["author"])} · {meta["date"]}</p>
  {content}
  <aside class="cta">
    <img src="/img/{k["img"]}.webp" alt="" width="1200" height="675" loading="lazy">
    <div>
      <h2>{e(k["name"])}</h2>
      <p>{e(k["summary"])}</p>
      <a class="btn" href="{utm(k["url"], slug)}">Get the kit · {e(k["price"])}</a>
      <a class="ghost" href="https://github.com/{k.get("owner", OWNER)}/{k["free_repo"]}">Free version on GitHub</a>
    </div>
  </aside>
</main>"""
    return page(title=meta["title"], description=meta["description"], path=path, body=body,
                image=k["img"], jsonld=jsonld, og_type="article")


def build_index(guides: list[tuple[str, dict]]) -> str:
    b = CFG["bundle"]
    cards = "\n".join(kit_card(k, "home") for k in CFG["kits"])
    guide_items = "\n".join(
        f'<li><a href="/guides/{slug}/">{e(m["title"])}</a><span>{e(m["description"])}</span></li>' for slug, m in guides
    )
    title = f"{BRAND}: Claude AI starter kits with one-command AWS deploy"
    description = ("Production-ready starter kits for building with Claude: AI phone receptionist, Airbnb guest concierge, "
                   "MCP server, invoice extraction, PDF chatbot, lead research and support agents. Full source code, free lite versions.")
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": title,
        "itemListElement": [
            {"@type": "ListItem", "position": i, "item": {
                "@type": "Product", "name": k["name"], "description": k["summary"], "image": f"{BASE}/img/{k['img']}.webp",
                "offers": {"@type": "Offer", "price": k["price"].lstrip("$"), "priceCurrency": "USD", "url": k["url"]}}}
            for i, k in enumerate(CFG["kits"], start=1)
        ],
    }
    body = f"""<main>
<section class="hero"><div class="wrap">
  <p class="eyebrow">Starter kits for the Claude API</p>
  <h1>{e(CFG["tagline"])}</h1>
  <p class="lead">Each kit is a complete app with full source code: Python and FastAPI, Next.js, tests, Docker, HTTPS, and a one-command AWS deploy. Use them for your own business or sell the result to clients. Every kit has a free lite version on GitHub, so you can try the idea first.</p>
  <p><a class="btn" href="#kits">See the kits</a> <a class="ghost" href="#guides">Read the free guides</a></p>
</div></section>

<section id="kits" class="wrap">
  <h2>Kits</h2>
  <div class="grid">
{cards}
  </div>
  <div class="bundle">
    <img src="/img/{b["img"]}.webp" alt="Bundle cover" width="1200" height="675" loading="lazy">
    <div>
      <h3>{e(b["name"])} · {e(b["price"])}</h3>
      <p>Document Chatbot, Lead Research, Support Agent, MCP Server and DocSift together, for less than the price of three.</p>
      <a class="btn" href="{utm(b["url"], "home-bundle")}">Get the bundle · {e(b["price"])}</a>
    </div>
  </div>
</section>

<section id="guides" class="wrap">
  <h2>Free guides</h2>
  <ul class="guides">
{guide_items}
  </ul>
</section>

<section class="wrap faq">
  <h2>Questions</h2>
  <h3>What do I get?</h3>
  <p>A zip with the full source code, tests, deploy scripts, guides and a cost sheet. One-time payment, no subscription.</p>
  <h3>What do I need?</h3>
  <p>Basic Python, a Claude API key, and Docker to run it locally. For AWS, the AWS CLI signed in to your account. Running costs are listed in each kit, usually a few cents per conversation or document.</p>
  <h3>Can I use it for client work?</h3>
  <p>Yes. Build and sell solutions for your clients with it. You may not resell the kit itself as a template.</p>
  <h3>Refunds?</h3>
  <p>30-day money-back guarantee through Gumroad. If something doesn't work, reply to your receipt and we'll help first.</p>
</section>
</main>"""
    return page(title=title, description=description, path="/", body=body, image=b["img"], jsonld=jsonld)


def main() -> None:
    guides = []
    for md_path in sorted((ROOT / "content").glob("*.md")):
        meta, md = parse_md(md_path)
        slug = md_path.stem
        out = ROOT / "guides" / slug / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build_guide(slug, meta, md), encoding="utf-8")
        guides.append((slug, meta))
    order = {k["article"]: i for i, k in enumerate(CFG["kits"]) if k.get("article")}
    guides.sort(key=lambda g: order.get(g[0], 99))
    (ROOT / "index.html").write_text(build_index(guides), encoding="utf-8")

    today = date.today().isoformat()
    urls = [f"{BASE}/"] + [f"{BASE}/guides/{s}/" for s, _ in guides]
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    (ROOT / "404.html").write_text(page(
        title=f"Page not found · {BRAND}", description="Page not found.", path="/404.html", image=CFG["bundle"]["img"],
        jsonld={"@context": "https://schema.org", "@type": "WebPage"},
        body='<main class="wrap article"><h1>Page not found</h1><p><a href="/">Go to the home page</a></p></main>'),
        encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(guides)} guides + index for {BASE}")


if __name__ == "__main__":
    main()
