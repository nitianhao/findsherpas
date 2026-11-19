import sys, re; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv(override=True)
from src import fetcher
from bs4 import BeautifulSoup

url = "https://www.douglas.de/de/search?q=lippenstift%20rot"
for name in ("_fetch_with_mode","_fetch_playwright","_fetch_static"):
    print(name, "exists:", hasattr(fetcher,name))
print("SiteMode members:", list(fetcher.SiteMode))

html = None
try:
    out = fetcher._fetch_playwright(url)
    html = out[0] if isinstance(out,tuple) else out
except Exception as e:
    print("playwright direct failed:", type(e).__name__, e)

if html:
    print("HTML len:", len(html))
    s = BeautifulSoup(html, "html.parser")
    print(".product-grid   :", len(s.select('.product-grid')))
    print(".product-tile   :", len(s.select('.product-tile')))
    print("a[href*=/p/]    :", len(s.select('a[href*="/p/"]')))
    print("title:", (s.title.string or '')[:80] if s.title else None)
    m = re.search(r'ERGEBNISSE[^<]{0,60}', html, re.I)
    print("heading hit:", m and m.group(0)[:80])
    open('reports/_diag_douglas.html','w',encoding='utf-8').write(html)
    print("saved reports/_diag_douglas.html")
