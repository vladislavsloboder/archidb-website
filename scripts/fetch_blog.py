import html as H, json, os, re, shutil, urllib.request
import markdown

URL = "https://tkfurduojwxrrvfjblkb.supabase.co"
KEY = "sb_publishable_H7Z5jwdHa4mz4OnjsSEKZA_rEM9Kn4c"  # öffentlicher Schlüssel
SITE = "https://archidb.de"
UMAMI_ID = "feec6a83-3346-4469-988c-ce236cd8bc5d"  # Umami Website-ID hier eintragen

TPL = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{t}} – ArchiDB Blog</title><meta name="description" content="{{d}}"><link rel="canonical" href="{{u}}">
<meta property="og:type" content="article"><meta property="og:title" content="{{t}}"><meta property="og:description" content="{{d}}"><meta property="og:url" content="{{u}}"><meta property="og:image" content="https://archidb.de/og-image.jpg">
<script type="application/ld+json">{{ld}}</script>
<style>:root{--bg:#f4f7fb;--fg:#0c1b33;--card:#fff;--mut:#51607a;--acc:#1a6fe0;--line:#dbe3ef}@media(prefers-color-scheme:dark){:root{--bg:#07142b;--fg:#e8eefb;--card:#0e2247;--mut:#9fb0cf;--acc:#4da3ff;--line:#1c355f}}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.8 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}a{color:var(--acc)}
header,footer{background:var(--card);border-bottom:1px solid var(--line);padding:14px 20px}footer{border:0;border-top:1px solid var(--line);color:var(--mut);font-size:14px}
header a{font-weight:800;letter-spacing:.06em;text-decoration:none;color:var(--fg)}header b{color:var(--acc)}
main{max-width:720px;margin:0 auto;padding:36px 20px}h1{font-size:34px;line-height:1.2;margin:0 0 8px}h2{font-size:26px;margin:36px 0 10px}h3{font-size:20px}.meta{color:var(--mut);font-size:14px;margin:0 0 24px}
code{background:var(--card);border:1px solid var(--line);border-radius:5px;padding:1px 6px;font-size:.88em}pre{background:#0b1b36;color:#e6edf7;border-radius:10px;padding:16px;overflow-x:auto}pre code{background:none;border:0;padding:0;color:inherit}
blockquote{margin:0 0 20px;padding:4px 18px;border-left:4px solid var(--acc);background:var(--card);color:var(--mut)}table{border-collapse:collapse;display:block;overflow-x:auto}th,td{border:1px solid var(--line);padding:8px 12px}img{max-width:100%;height:auto;border-radius:10px}</style>{{an}}</head>
<body><header><a href="/">ARCHI<b>DB</b></a> &nbsp;·&nbsp; <a href="/#/blog" style="font-weight:400">Blog</a></header>
<main><h1>{{t}}</h1><p class="meta">{{m}}</p>{{b}}<p><a href="/#/blog">← Alle Artikel</a></p></main>
<footer>© 2026 ArchiDB · <a href="/#/impressum">Impressum</a> · <a href="/#/datenschutz">Datenschutz</a></footer></body></html>"""

q = "select=title,slug,summary,body,author,published_at&published=eq.true&order=published_at.desc"
req = urllib.request.Request(URL + "/rest/v1/posts?" + q, headers={"apikey": KEY})
rows = json.load(urllib.request.urlopen(req))

posts, slugs, urls = [], set(), [SITE + "/"]
os.makedirs("backup", exist_ok=True)
for r in rows:
    slug = re.sub(r"[^a-z0-9-]", "", (r["slug"] or "").lower())
    if not slug:
        continue
    slugs.add(slug)
    body_html = markdown.markdown(r.get("body") or "", extensions=["extra"]).replace('src="blog/', 'src="/blog/')
    day = (r.get("published_at") or "")[:10]
    author = r.get("author") or ""
    summary = r.get("summary") or ""
    posts.append({"title": r["title"], "slug": slug, "date": r.get("published_at") or "", "author": author, "summary": summary, "html": body_html})
    u = f"{SITE}/blog/{slug}/"
    urls.append((u, day))
    ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": r["title"], "description": summary, "inLanguage": "de",
          "datePublished": day, "mainEntityOfPage": u, "author": {"@type": "Person", "name": author or "Vladislav Sloboder"},
          "publisher": {"@type": "Organization", "name": "ArchiDB", "url": SITE + "/"}}
    meta = " · ".join(x for x in [day, author] if x)
    an = f'<script defer src="https://cloud.umami.is/script.js" data-website-id="{UMAMI_ID}"></script>' if UMAMI_ID else ""
    page = TPL.replace("{{an}}", an)
    for k, v in {"{{t}}": H.escape(r["title"]), "{{d}}": H.escape(summary, quote=True), "{{u}}": u, "{{m}}": H.escape(meta), "{{b}}": body_html}.items():
        page = page.replace(k, v)
    page = page.replace("{{ld}}", json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"))
    os.makedirs(f"blog/{slug}", exist_ok=True)
    with open(f"blog/{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    with open(f"backup/{day}-{slug}.md", "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: {r['title']}\ndate: {day}\nauthor: {author}\nsummary: {summary}\n---\n{r.get('body') or ''}\n")

if os.path.isdir("blog"):
    for d in os.listdir("blog"):
        if d != "images" and os.path.isdir("blog/" + d) and d not in slugs:
            shutil.rmtree("blog/" + d)

with open("blog.json", "w", encoding="utf-8") as f:
    json.dump({"posts": posts}, f, ensure_ascii=False, indent=1)
with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for u in urls:
        loc, lm = (u, "") if isinstance(u, str) else u
        f.write(f"<url><loc>{loc}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>\n")
    f.write("</urlset>\n")
print(len(posts), "Artikel geschrieben")
