"""Small deterministic adapters scoped to observed search grids, never whole-page cards."""
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from src.models import SearchResult


def scoped_products(html, url, limit):
    host = urlparse(url).netloc
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    if 'finisterre.com' in host:
        cards = soup.select('#klevu-search-results a[href*="/products/"]')
        for card in cards:
            title = card.select_one('.ellipsis-2-line')
            if not title:
                continue
            # Direct grid anchor has name and price; no menu carousel anchors.
            price = card.select_one('[class*="text-purpleNavy"]')
            results.append(SearchResult(rank=len(results)+1,title=title.get_text(' ',strip=True),
                url=urljoin(url,card['href']),price=price.get_text(' ',strip=True) if price else None))
    elif 'passenger-clothing.com' in host:
        for card in soup.select('#ProductGridContainer product-card'):
            title = card.select_one('a.product-card__title')
            full = card.select_one('a[aria-label][href*="/products/"]')
            price = card.select_one('.price__regular')
            if title:
                results.append(SearchResult(rank=len(results)+1,
                    title=full.get('aria-label') if full else title.get_text(' ',strip=True),
                    url=urljoin(url,title['href']),price=price.get_text(' ',strip=True) if price else None))
    elif 'watery.dk' in host:
        for card in soup.select('.search-results-grid [data-type="product"]'):
            data = card.select_one('[data-product-name]')
            if data:
                results.append(SearchResult(rank=len(results)+1,title=data['data-product-name'],
                    url=urljoin(url,data.get('data-product-url','')),
                    price=data.get('data-variant-price')))
    elif 'dedoles.sk' in host:
        for card in soup.select('#product-grid .product-card'):
            title = card.select_one('.product-card__heading a')
            price = card.select_one('.price-item--sale') or card.select_one('.price-item--regular')
            if title:
                results.append(SearchResult(rank=len(results)+1,title=title.get_text(' ',strip=True),
                    url=urljoin(url,title['href']),price=price.get_text(' ',strip=True) if price else None))
    elif 'connox.de' in host:
        for card in soup.select('[data-scanner-shadow-evidence] .br-product-card'):
            title = card.select_one('.br-product-card__title')
            brand = card.select_one('.br-product-card__brand')
            link = card.select_one('a.br-product-card__link')
            price = card.select_one('.br-product-card__price-sale')
            if title and link:
                name = ' '.join(e.get_text(' ',strip=True) for e in (brand,title) if e)
                results.append(SearchResult(rank=len(results)+1,title=name,url=link['href'],
                    price=price.get_text(' ',strip=True) if price else None))
    elif 'naturzeit.com' in host or 'rockpoint.cz' in host or 'designtorget.se' in host:
        if 'naturzeit.com' in host:
            cards = soup.select('.cms-listing-row .product-box[data-product-information]')
            title_sel, price_sel = '.product-name', '.product-price'
        elif 'rockpoint.cz' in host:
            cards = soup.select('.c-productlist-squareitem')
            title_sel, price_sel = 'h3.title', '[class*="price"]'
        else:
            cards = soup.select('#product-listings .product-box')
            title_sel, price_sel = '.product-name a', '.price'
        for card in cards:
            title = card.select_one(title_sel)
            link = title if title and title.name == 'a' else card.select_one('a.product-link, a[href]')
            price = card.select_one(price_sel)
            if title and link:
                results.append(SearchResult(rank=len(results)+1,title=title.get_text(' ',strip=True),
                    url=urljoin(url,link.get('href','')),price=price.get_text(' ',strip=True) if price else None))
    seen = set()
    unique = []
    for r in results:
        key = (r.url or '').split('?')[0]
        if key in seen:
            continue
        seen.add(key)
        r.rank = len(unique)+1
        unique.append(r)
    return unique[:limit]


def scoped_count(html, url):
    import re
    soup = BeautifulSoup(html, 'html.parser')
    for noise in soup.select('script,style,header,footer,nav'):
        noise.decompose()
    if 'connox.de' in url:
        count = soup.select_one('[id^="br-search-count-value"]')
        if count and count.get_text(strip=True).isdigit():
            return int(count.get_text(strip=True))
    patterns = {
        'rockpoint.cz': r'Produkty\s*\(([\d\s]+)\)',
        'naturzeit.com': r'(\d+)\s+Produkte? gefunden',
        'watery.dk': r'\b(\d+)\s+produkter\b',
        'designtorget.se': r'matchade\s+(\d+)\s+produkter',
    }
    for host, pattern in patterns.items():
        if host in url:
            found = re.search(pattern,soup.get_text(' ',strip=True),re.I)
            if found:
                return int(found.group(1).replace(' ',''))
    return None


def scoped_brands(html, url):
    soup=BeautifulSoup(html,'html.parser')
    brands={}
    if 'naturzeit.com' in url:
        for card in soup.select('.product-box[data-product-information]'):
            name=card.select_one('a.product-name')
            brand=card.select_one('.product-box-manufacturer-col')
            if name and brand:
                brands[urljoin(url,name['href'])]=brand.get_text(' ',strip=True)
    return brands
