import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
from playwright.sync_api import sync_playwright
from src.fetcher import _USER_AGENT, _apply_stealth, _wait_for_cloudflare_clear, _dismiss_consent_banners
url='https://huckberry.com/search?keywords=outdoor'
with sync_playwright() as p:
    b=p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled','--no-sandbox','--disable-dev-shm-usage'])
    ctx=b.new_context(user_agent=_USER_AGENT, viewport={'width':1400,'height':1000}, locale='en-US')
    pg=ctx.new_page(); _apply_stealth(pg)
    pg.goto(url, wait_until='domcontentloaded', timeout=30000)
    _wait_for_cloudflare_clear(pg)
    pg.wait_for_timeout(3000)
    _dismiss_consent_banners(pg)
    # also try clicking common accept buttons
    for sel in ["button:has-text('Accept')","button:has-text('Accept All')","#onetrust-accept-btn-handler","button:has-text('Got it')"]:
        try:
            el=pg.query_selector(sel)
            if el and el.is_visible(): el.click(); pg.wait_for_timeout(800); break
        except Exception: pass
    pg.wait_for_timeout(2500)
    pg.screenshot(path='reports/huckberry_com/huckberry_com_cover.png')
    print('saved cover, title:', pg.title())
    b.close()
