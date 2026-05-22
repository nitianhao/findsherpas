"""Rescue-fetch suspected scraper-miss queries for underarmour.cz and patch phase 4 checkpoint."""
import json
import sys
from pathlib import Path
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
sys.path.insert(0, str(AUDIT_ROOT))
from playwright.sync_api import sync_playwright

QUERIES = ["mik ina", "mik"]
BASE = "https://www.underarmour.cz/search?q={}"

EXTRACT_JS = r"""
() => {
  const links = Array.from(document.querySelectorAll('a'));
  const products = [];
  const seen = new Set();
  for (const a of links) {
    const href = a.getAttribute('href') || '';
    if (!/^\/(damsk|pansk|divci|klucic|detsk|unisex)[eaá]?-/i.test(href)) continue;
    if (seen.has(href)) continue;
    let title = a.getAttribute('aria-label') || a.getAttribute('title') || '';
    if (!title || title.length < 12) {
      let p = a.closest('article, li, div');
      for (let i = 0; i < 6 && p; i++) {
        const h = p.querySelector('h1,h2,h3,h4,[class*="title" i], [class*="name" i]');
        if (h && h.innerText && h.innerText.trim().length > 12) { title = h.innerText.trim(); break; }
        p = p.parentElement;
      }
    }
    if (title && title.length > 12) {
      seen.add(href);
      products.push({ href, title: title.slice(0, 150) });
    }
    if (products.length >= 15) break;
  }
  return products;
}
"""

def rescue():
    results = {}
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        ctx = browser.new_context(locale="cs-CZ")
        page = ctx.new_page()
        for q in QUERIES:
            url = BASE.format(quote(q))
            print(f"-> {q}: {url}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(9000)
                try:
                    page.locator("button:has-text('Povolit vše'), button:has-text('Accept')").first.click(timeout=2000)
                    page.wait_for_timeout(1000)
                except Exception:
                    pass
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1500)
                products = page.evaluate(EXTRACT_JS)
            except Exception as e:
                print(f"   error: {e}")
                products = []
            items = []
            for i, pr in enumerate(products[:15], 1):
                href = pr["href"]
                if href.startswith("/"):
                    href = "https://www.underarmour.cz" + href
                items.append({
                    "rank": i,
                    "title": pr["title"],
                    "price": None,
                    "snippet": None,
                    "url": href,
                })
            results[q] = items
            print(f"   got {len(items)}")
        browser.close()
    return results

if __name__ == "__main__":
    rescued = rescue()
    cp = PROJECT_ROOT / "reports" / "_checkpoint_phase4.json"
    data = json.loads(cp.read_text())
    for q, items in rescued.items():
        data[q] = items
    cp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print("\n=== SUMMARY ===")
    for q, items in rescued.items():
        print(f"  {q}: {len(items)}")
