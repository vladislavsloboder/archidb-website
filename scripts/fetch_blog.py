import json, os, urllib.request
import markdown

URL = "https://tkfurduojwxrrvfjblkb.supabase.co"
KEY = "sb_publishable_H7Z5jwdHa4mz4OnjsSEKZA_rEM9Kn4c"  # öffentlicher Schlüssel, darf im Repo stehen

q = "select=title,slug,summary,body,author,published_at&published=eq.true&order=published_at.desc"
req = urllib.request.Request(URL + "/rest/v1/posts?" + q, headers={"apikey": KEY})
rows = json.load(urllib.request.urlopen(req))

posts = []
os.makedirs("backup", exist_ok=True)
for r in rows:
    posts.append({
        "title": r["title"], "slug": r["slug"], "date": r.get("published_at") or "",
        "author": r.get("author") or "", "summary": r.get("summary") or "",
        "html": markdown.markdown(r.get("body") or "", extensions=["extra"]),
    })
    day = (r.get("published_at") or "")[:10]
    with open(f"backup/{day}-{r['slug']}.md", "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: {r['title']}\ndate: {day}\nauthor: {r.get('author') or ''}\nsummary: {r.get('summary') or ''}\n---\n{r.get('body') or ''}\n")

with open("blog.json", "w", encoding="utf-8") as f:
    json.dump({"posts": posts}, f, ensure_ascii=False, indent=1)
print(len(posts), "Artikel geschrieben")
