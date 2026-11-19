import sys, re; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv(override=True)
from src import fetcher
from bs4 import BeautifulSoup

url = "https://www.douglas.de/de/search?q=lippenstift%20rot"
html, browser, final_url = fetcher._fetch_with_playwright(url, force_browser="chromium")
print("browser:", browser, "| final_url:", final_url, "| html len:", len(html))
s = BeautifulSoup(html, "html.parser")
print(".product-grid :", len(s.select('.product-grid')))
print(".product-tile :", len(s.select('.product-tile')))
print("a[href*=/p/]  :", len(s.select('a[href*="/p/"]')))
print("title         :", (s.title.get_text() if s.title else '')[:90])
m = re.search(r'[0-9\.]+\s*ERGEBNISSE[^<]{0,50}', html, re.I)
print("heading hit   :", m and m.group(0)[:90])
for pat in ("Just a moment","captcha","Access Denied","blockiert","Zugriff"):
    if pat.lower() in html.lower(): print("  !! contains:", pat)
open('reports/_diag_douglas.html','w',encoding='utf-8').write(html)
print("saved reports/_diag_douglas.html")
