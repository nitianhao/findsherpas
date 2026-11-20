"""Extract literal catalog labels, excluding account/country/footer navigation."""
import re
from urllib.parse import urlparse

UTILITY = re.compile(r'\bexplore\b|nakupovať|nakupovat|blog|práce|hledat|přihl|košík|novink|nyhet|black week|black friday|kontakt|contact|reklam|obchodn|doprava|platba|podmín|podmien|cookies|privacy|terms|shipping|returns|account|login|profil|adressen|bestellungen|übersicht|über |about|magazin|kurse|touren|služby|servis|půjč|pojišt|kalendář|kariér|prodejny|o nás|ke stažení|zákaznick|odstoupen|dárkov|gift|gifting|populärt|bestseller|offers|sale|outlet|continue shopping|featured|last chance|view |shop |up to|%|all jackets|all tops',re.I)


def catalog_categories(soup, url, original):
    host = urlparse(url).netloc.removeprefix('www.')
    collections, menu = [], []
    for a in soup.select('a[href]'):
        href = str(a.get('href',''))
        label = a.get_text(' ',strip=True)
        if not 3 <= len(label) <= 55 or UTILITY.search(label+' '+href):
            continue
        target = urlparse(href)
        if target.netloc and target.netloc.removeprefix('www.') != host:
            continue
        if not target.path or target.path == '/' or href.startswith(('#','mailto:','tel:')):
            continue
        if any(e.name == 'footer' or 'footer' in str(e.get('class','')).lower() for e in a.parents):
            continue
        if '/collections/' in href or '/search?' in href:
            collections.append(label)
        elif any(e.name == 'header' or re.search(r'menu|navigation', str(e.get('class','')),re.I) for e in a.parents):
            menu.append(label)
    return list(dict.fromkeys(collections + menu + [c for c in original if not UTILITY.search(c)]))
