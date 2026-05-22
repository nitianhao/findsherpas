"""Step 1b: Re-seed SiteContext for Shop Apotheke.

Pulls featured items from the homepage and multiple broad pharma queries to
eliminate the 'spa' bias from the original seed URL. Forces site_name and
site_type. Regenerates test queries.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

from src.category_selector import select_categories
from src.discovery import (
    _extract_brands,
    _extract_featured_items,
    _extract_meta_description,
    _extract_nav_categories,
    _USER_AGENT,
)
from src.models import SiteContext, SiteType
from src.query_generator import generate_queries

HOMEPAGE = "https://www.shop-apotheke.com/"
SEARCH_TEMPLATE = (
    "https://www.shop-apotheke.com/search.htm?"
    "eventName=search-submit&i=1&q={}&searchChannel=algolia"
)
SEED_QUERIES = [
    "arzneimittel",
    "vitamine",
    "hautpflege",
    "schmerzmittel",
    "nahrungsergänzung",
    "erkältung",
]
OUT = ROOT / "reports" / "www_shop-apotheke_com" / "_rerun"
OUT.mkdir(parents=True, exist_ok=True)


def _fetch_soup(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"},
            timeout=20,
            allow_redirects=True,
        )
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [warn] failed to fetch {url}: {e}")
        return None


def main() -> None:
    merged_featured: list[str] = []
    merged_brands: list[str] = []
    nav_categories: list[str] = []
    meta_desc = ""
    seen_items: set[str] = set()
    seen_brands: set[str] = set()

    print("== Fetching homepage ==")
    hp = _fetch_soup(HOMEPAGE)
    if hp:
        nav_categories = _extract_nav_categories(hp)
        meta_desc = _extract_meta_description(hp)
        for b in _extract_brands(hp):
            if b.lower() not in seen_brands:
                seen_brands.add(b.lower())
                merged_brands.append(b)
        for it in _extract_featured_items(hp):
            if it.lower() not in seen_items:
                seen_items.add(it.lower())
                merged_featured.append(it)
        print(f"  homepage: +{len(merged_featured)} featured, +{len(merged_brands)} brands, {len(nav_categories)} nav")

    print("\n== Fetching broad pharma seed queries ==")
    for q in SEED_QUERIES:
        url = SEARCH_TEMPLATE.format(quote_plus(q))
        soup = _fetch_soup(url)
        if not soup:
            continue
        added_items = added_brands = 0
        for it in _extract_featured_items(soup):
            low = it.lower()
            if low not in seen_items:
                seen_items.add(low)
                merged_featured.append(it)
                added_items += 1
        for b in _extract_brands(soup):
            low = b.lower()
            if low not in seen_brands:
                seen_brands.add(low)
                merged_brands.append(b)
                added_brands += 1
        print(f"  q='{q}': +{added_items} featured, +{added_brands} brands")

    # Clean brands: filter out obvious nav/UI noise, then merge with step1's
    # cleanly-extracted brand list (from search-URL discovery) which had the
    # real pharma/beauty brands (Voltaren, Bepanthol, Eucerin, Redcare, …).
    _BRAND_NOISE_SUBSTR = [
        "newsletter", "gutschein", "rabatt", "hilfe", "faq", "über uns",
        "warenkorb", "suchen", "e-rezept", "anmelden", "registrieren",
        "startseite", "go to page", "schließen", "online-arzt",
        "redpoints", "now! service", "arigato",
    ]
    _BRAND_NAV_EXACT = {
        "arzneimittel", "familie", "beauty & pflege", "sanitätshaus",
        "angebote", "marken", "vitamine & mineralstoffe", "magen & darm",
        "erkältung & grippe", "schmerzen", "kindergesundheit",
        "pflegeprodukte fürs kind", "kinderwunsch", "schwangerschaft",
        "gesichtspflege", "körperpflege", "sonne & schutz",
        "beauty specials", "ernährung", "baby & familie", "sparset",
    }

    def _is_noise_brand(b: str) -> bool:
        low = b.lower().strip()
        if low in _BRAND_NAV_EXACT:
            return True
        return any(s in low for s in _BRAND_NOISE_SUBSTR)

    cleaned_brands = [b for b in merged_brands if not _is_noise_brand(b)]

    # Seed with the vetted pharma/beauty brand list from the April 13 report
    # (clean output from an earlier search-URL discovery pass). Then merge
    # any *additional* cleaned brands found this run.
    _TRUSTED_BRANDS_PATH = (
        ROOT / "reports" / "www_shop-apotheke_com"
        / "www_shop-apotheke_com_20260413_175908_data.json"
    )
    trusted_brands: list[str] = []
    try:
        prior_report = json.loads(_TRUSTED_BRANDS_PATH.read_text(encoding="utf-8"))
        trusted_brands = [
            b for b in prior_report["site_context"].get("brands", [])
            if not _is_noise_brand(b)
        ]
    except Exception as e:
        print(f"  [warn] could not load trusted brands: {e}")

    combined: list[str] = []
    seen_low: set[str] = set()
    for b in trusted_brands + cleaned_brands:
        low = b.lower().strip()
        if low and low not in seen_low:
            seen_low.add(low)
            combined.append(b)
    merged_brands = combined

    # Clean featured items: drop navigation / content / article-title noise.
    _FEATURED_NOISE_SUBSTR = [
        "newsletter", "hilfe & faq", "anmelden", "registrieren",
        "e-rezept-rabatt", "e-rezept", "riesen-auswahl",
        "versandkostenfrei", "folgen sie uns", "deutschland",
        "variante auswählen", "suchergebnisse filtern",
    ]

    def _is_noise_item(it: str) -> bool:
        low = it.lower().strip()
        if len(low) < 5:
            return True
        if any(s in low for s in _FEATURED_NOISE_SUBSTR):
            return True
        # Drop editorial article titles ("Erkältung – Was tun …")
        if any(marker in it for marker in ("–", "—")) and "?" in it:
            return True
        if low.endswith("?"):
            return True
        return False

    merged_featured = [it for it in merged_featured if not _is_noise_item(it)]

    # Cap to reasonable sizes
    merged_featured = merged_featured[:60]
    merged_brands = merged_brands[:40]
    # Nav fallback: if homepage nav was empty, keep prior detection's nav
    if not nav_categories:
        prior = json.loads((OUT / "step1.json").read_text(encoding="utf-8"))
        nav_categories = prior["site_context"].get("nav_categories", [])
        print(f"  [nav] homepage had none — reusing prior nav ({len(nav_categories)})")

    ctx = SiteContext(
        url=HOMEPAGE,
        site_name="Shop Apotheke",
        site_type=SiteType.MARKETPLACE_MIXED,
        nav_categories=nav_categories,
        brands=merged_brands,
        featured_items=merged_featured,
        search_url_template=SEARCH_TEMPLATE,
        raw_meta_description=meta_desc,
    )

    print("\n== Final SiteContext ==")
    print(f"  site_name:     {ctx.site_name}")
    print(f"  site_type:     {ctx.site_type}")
    print(f"  nav:           {len(ctx.nav_categories)}")
    print(f"  brands:        {len(ctx.brands)}")
    print(f"  featured:      {len(ctx.featured_items)}")

    print("\n  Brands:")
    for b in ctx.brands:
        print(f"    - {b}")
    print("\n  Featured (first 40):")
    for f in ctx.featured_items[:40]:
        print(f"    - {f}")

    print("\n== Phase 2: Category Selection ==")
    cats = select_categories(ctx)
    print(f"  selected ({len(cats)}):")
    for c in cats:
        print(f"    - {getattr(c, 'value', c)}")

    print("\n== Phase 3: Query Generation ==")
    queries = generate_queries(ctx, cats)
    print(f"  generated {len(queries)} queries\n")
    current = None
    for tq in queries:
        cat = getattr(tq.category, "value", tq.category)
        if cat != current:
            current = cat
            print(f"\n  [{cat}]")
        print(f'    "{tq.query}"')

    payload = {
        "target_url": HOMEPAGE,
        "site_context": ctx.model_dump(mode="json"),
        "selected_categories": [getattr(c, "value", c) for c in cats],
        "queries": [tq.model_dump(mode="json") for tq in queries],
    }
    (OUT / "step1b.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n  Checkpoint written: {OUT / 'step1b.json'}")


if __name__ == "__main__":
    main()
