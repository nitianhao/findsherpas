from __future__ import annotations

import json
import logging
import re
import sys
import time
from collections import Counter
from typing import Optional
from urllib.parse import quote_plus, urlparse

import anthropic
import requests
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv

from src.models import SearchResult, TestQuery

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Optional proxy support — set PROXY_URL in .env to route all fetches through a proxy.
# Example: PROXY_URL=http://user:pass@proxy.example.com:8080
import os as _os
_PROXY_URL = _os.environ.get("PROXY_URL", "").strip() or None
if _PROXY_URL:
    logger.info("Proxy configured: %s", _PROXY_URL.split("@")[-1] if "@" in _PROXY_URL else _PROXY_URL)

_REQUESTS_PROXIES = {"http": _PROXY_URL, "https": _PROXY_URL} if _PROXY_URL else None
_PW_PROXY = {"server": _PROXY_URL} if _PROXY_URL else None

# LLM calls (validation, extraction, selector generation) require an API key.
# When absent, these functions gracefully skip — the heuristic improvements
# (quality scoring, stealth, persistent context) still work without any API calls.
# When running audits through Claude Code, the LLM steps can be done manually.
_HAS_API_KEY = bool(_os.environ.get("ANTHROPIC_API_KEY", "").strip())

# ---------------------------------------------------------------------------
# Price regex
# ---------------------------------------------------------------------------
_PRICE_RE = re.compile(
    r"(?:"
    r"(?:[A-Z]{0,2}[$€£¥₹₩₪฿₫₴])\s?\d[\d.,]*"
    r"|"
    r"(?:Kč|kč|zł|kr)\s?\d[\d.,]*"
    r"|"
    r"\d[\d.,]*\s?(?:Kč|kč|zł|kr)"
    r"|"
    r"\d[\d.,]*\s?(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|KRW|INR|BRL|SEK|NOK|DKK|PLN|CZK)"
    r")"
)
_PRICE_FALLBACK_RE = re.compile(r"(?:[$€£¥₹]|Kč|zł|kr)\s?\d{1,7}(?:[.,]\d{1,2})?")

# Junk title filters
_JUNK_STARTS = (
    "results for", "showing results", "search results",
    "top trending", "trending deals", "featured deals",
    "popular picks", "recommended for you", "you may also like",
    "sponsored", "advertisement",
    "see all", "view more", "load more", "show more",
    "next page", "previous", "back to top",
    "sign in", "log in", "join now",
    # Dutch / common e-commerce UI strings
    "bekijk vergelijking", "vergelijk", "toon meer", "meer laden",
    "inloggen", "registreren", "mijn account",
    "gratis bezorgd", "gratis verzending", "voor ", "binnen ",
)
_JUNK_EXACT = {
    "free shipping", "new arrivals", "best sellers", "sale", "clearance", "ad", "ads",
}

# Chrome element class/ID patterns
_CHROME_CLASSES = re.compile(
    r"header|banner|hero|promo|nav|footer|sidebar|trending|featured.section|"
    r"advertisement|sponsored|breadcrumb|pagination|toolbar|"
    r"cookie|consent|gdpr|cookiebot|cybot|privacy-modal|cc-window",
    re.I,
)

# Section-header heading text
_SECTION_HEADER_RE = re.compile(
    r"^(top|best|featured|popular|recommended|trending|new|sale|deal|you may|"
    r"related|similar|people also|customers also|sponsored)\b",
    re.I,
)

# Product card class/id/data-attr patterns
_CARD_PATTERN = re.compile(
    r"product|item|result|card|hit|deal|offer|listing|plp-|srp-",
    re.I,
)

# Load-more button text patterns
_LOAD_MORE_RE = re.compile(
    r"show more|load more|view more|see more|see all results",
    re.I,
)

# Product/deal URL path patterns
_PRODUCT_LINK_RE = re.compile(r"/deal|/product|/item|/offer|/dp/|/p/|/listing", re.I)

# ---------------------------------------------------------------------------
# Block detection signals & site-level fetch modes
# ---------------------------------------------------------------------------

_CLOUDFLARE_SIGNALS = (
    "just a moment", "checking your browser",
    "please enable cookies to continue", "ray id",
    "ddos protection by cloudflare",
    "enable javascript and cookies to continue",
)
_IMPERVA_SIGNALS = (
    "incapsula incident", "pardon our interruption", "request unsuccessful",
)


def _classify_response(html: str, status_code: int = 200) -> str:
    """Classify a page response. Returns 'cloudflare', 'imperva', or 'ok'."""
    if not html:
        return "empty"
    sample = html[:5000].lower()
    if any(sig in sample for sig in _CLOUDFLARE_SIGNALS):
        return "cloudflare"
    if any(sig in sample for sig in _IMPERVA_SIGNALS):
        return "imperva"
    return "ok"


def _is_search_redirect(original_url: str, final_url: str, query: str) -> bool:
    """Return True if the server redirected away from the search results page.

    Flags a redirect when BOTH hold:
      1. The URL path changed (ignoring harmless scheme/host normalisation).
      2. The URL-encoded query string is absent from the final URL.
    """
    if not final_url or final_url == original_url:
        return False
    orig = urlparse(original_url)
    final = urlparse(final_url)
    if orig.path == final.path:
        return False  # Only scheme/host changed — harmless normalisation
    encoded = quote_plus(query).lower()
    if encoded in final_url.lower():
        return False  # Query still present — not redirected away from search
    logger.debug("Search redirect detected: %s → %s", original_url, final_url)
    return True


class SiteMode:
    """Fetch strategy for a site, determined once by _probe_site."""
    STATIC = "static"
    PLAYWRIGHT_FIREFOX = "playwright_firefox"
    PLAYWRIGHT_CHROMIUM = "playwright_chromium"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Result validation / junk filter
# ---------------------------------------------------------------------------


def _filter_junk_results(results: list[SearchResult]) -> list[SearchResult]:
    """Remove results that are clearly page chrome, not real products."""
    seen_titles: set[str] = set()
    clean: list[SearchResult] = []

    for r in results:
        title = r.title.strip()
        lower = title.lower()

        if len(title) < 8:
            continue
        if not any(c.isalpha() for c in title):
            continue
        if any(lower.startswith(p) for p in _JUNK_STARTS):
            continue
        if lower in _JUNK_EXACT:
            continue

        title_key = re.sub(r"\s+", " ", lower).strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        clean.append(r)

    for i, r in enumerate(clean, 1):
        r.rank = i

    return clean


# ---------------------------------------------------------------------------
# Price extraction
# ---------------------------------------------------------------------------


def _extract_price(element: Tag) -> Optional[str]:
    for child in element.find_all(True, recursive=True):
        classes = " ".join(child.get("class", [])).lower()
        if any(kw in classes for kw in ("price", "cost", "amount", "money")):
            text = child.get_text(separator=" ", strip=True)
            for pattern in (_PRICE_RE, _PRICE_FALLBACK_RE):
                m = pattern.search(text)
                if m:
                    return m.group(0).strip()

    full_text = element.get_text(separator=" ", strip=True)
    for pattern in (_PRICE_RE, _PRICE_FALLBACK_RE):
        m = pattern.search(full_text)
        if m:
            return m.group(0).strip()

    return None


# ---------------------------------------------------------------------------
# Strategy 0 — Site-specific extraction
# ---------------------------------------------------------------------------


def _try_site_specific(soup: BeautifulSoup, url: str, max_results: int) -> list[SearchResult]:
    """Site-specific extraction for known sites. Returns empty list if no match."""
    host = urlparse(url).netloc.lower()

    if "groupon" in host:
        return _try_groupon(soup, max_results)

    return []


def _try_groupon(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract deal cards from Groupon search results."""
    results: list[SearchResult] = []
    seen_titles: set[str] = set()

    # Strategy: find all <a> tags linking to /deals/ paths — these are deal titles
    deal_links = [
        a for a in soup.find_all("a", href=True)
        if re.search(r"/deals?/", a.get("href", ""), re.I)
        and not a.get("href", "").endswith("#")
    ]

    for link in deal_links:
        # --- Title: prefer the <h3> (deal description), fall back to full text ---
        heading = link.find(re.compile(r"^h[1-6]$"))
        if heading:
            title = heading.get_text(separator=" ", strip=True)
        else:
            # Fallback: aria-label or title attribute
            title = (
                link.get("aria-label", "")
                or link.get("title", "")
                or link.get_text(separator=" ", strip=True)
            ).strip()

        if not title or len(title) < 8:
            continue

        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # --- Snippet: first meaningful short descriptor in the card ---
        # Generic approach: scan all inline text elements, skip anything that
        # looks like a price, rating, distance, badge word, or the title itself.
        _noise = re.compile(
            r"^[$€£¥]"           # price starting with currency symbol
            r"|\d+\s*%"          # discount percentage
            r"|\d+\.\d+\s*\("   # rating like "4.8 ("
            r"|\d+\s*(mi|km|m)\b"  # distance
            , re.I,
        )
        _badge_words = frozenset({"popular", "gift", "sponsored", "featured", "new", "sale", "online", "local"})
        snippet: str | None = None
        for el in link.find_all(["span", "p", "small"]):
            txt = el.get_text(strip=True)
            if not txt or len(txt) < 4 or len(txt) > 100:
                continue
            if txt.lower() == title.lower():
                continue
            if _noise.search(txt):
                continue
            if all(w in _badge_words for w in txt.lower().split()):
                continue
            snippet = txt
            break

        # Look for price in the card container (walk up to find it)
        price = None
        card_container = link.parent
        for _ in range(5):
            if card_container is None:
                break
            price = _extract_price(card_container)
            if price:
                break
            card_container = card_container.parent

        href = link.get("href", "")

        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:300],
            price=price,
            snippet=snippet,
            url=href or None,
        ))

        if len(results) >= max_results:
            break

    raw_count = len(results)
    filtered = _filter_junk_results(results)
    logger.debug(
        "Strategy 0 (Groupon site-specific): found %d raw results, %d after filtering",
        raw_count, len(filtered),
    )
    return filtered


# ---------------------------------------------------------------------------
# Strategy 1 — Schema.org JSON-LD
# ---------------------------------------------------------------------------


def _try_schema_org(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []

    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        _collect_products_jsonld(data, results, max_results)
        if len(results) >= max_results:
            break

    for i, r in enumerate(results[:max_results]):
        r.rank = i + 1

    raw = results[:max_results]
    filtered = _filter_junk_results(raw)
    logger.debug(
        "Strategy 1 (Schema.org): found %d raw results, %d after filtering",
        len(raw), len(filtered),
    )
    return filtered


def _collect_products_jsonld(data: object, results: list[SearchResult], max_results: int) -> None:
    if len(results) >= max_results:
        return

    if isinstance(data, dict):
        type_val = data.get("@type", "")
        types = type_val if isinstance(type_val, list) else [type_val]

        if "Product" in types or "Service" in types:
            name = data.get("name", "").strip()
            if name:
                price = None
                offers = data.get("offers", {})
                if isinstance(offers, dict):
                    p = offers.get("price") or offers.get("lowPrice")
                    currency = offers.get("priceCurrency", "")
                    price = (f"{currency} {p}".strip() if currency else str(p)) if p else None
                elif isinstance(offers, list) and offers:
                    p = offers[0].get("price") or offers[0].get("lowPrice")
                    currency = offers[0].get("priceCurrency", "")
                    price = (f"{currency} {p}".strip() if currency else str(p)) if p else None
                if not price and data.get("price"):
                    price = str(data["price"])

                snippet = data.get("description", "")
                snippet = snippet[:300].strip() if isinstance(snippet, str) else None

                results.append(SearchResult(
                    rank=0, title=name, price=price,
                    snippet=snippet or None, url=data.get("url") or data.get("@id"),
                ))

        if "ItemList" in types:
            for item in data.get("itemListElement", []):
                _collect_products_jsonld(item, results, max_results)

        for v in data.values():
            _collect_products_jsonld(v, results, max_results)

    elif isinstance(data, list):
        for item in data:
            _collect_products_jsonld(item, results, max_results)


# ---------------------------------------------------------------------------
# Strategy 2 — Product card patterns (extended)
# ---------------------------------------------------------------------------


def _is_inside_chrome(el: Tag) -> bool:
    for node in [el] + list(el.parents):
        if not isinstance(node, Tag):
            continue
        tag = (node.name or "").lower()
        # Skip root-level tags — body/html are always ancestors and their
        # functional classes (e.g. "js-sticky-header") must not poison all descendants.
        if tag in ("body", "html"):
            continue
        if tag in ("header", "footer", "nav"):
            return True
        # Check each CSS class token individually to prevent substring false positives
        # (e.g. "js-sticky-header" must not match as "header").
        classes = node.get("class", [])
        el_id = node.get("id", "") or ""
        if any(_CHROME_CLASSES.search(cls) for cls in classes):
            return True
        if _CHROME_CLASSES.search(el_id):
            return True
    return False


def _element_matches_card(el: Tag) -> bool:
    """Check if element looks like a product card by class, id, data-attr, or role."""
    # Standard class/id pattern
    classes = " ".join(el.get("class", []))
    if _CARD_PATTERN.search(classes):
        return True
    el_id = el.get("id", "") or ""
    if _CARD_PATTERN.search(el_id):
        return True

    # data-testid attribute
    testid = el.get("data-testid", "") or ""
    if _CARD_PATTERN.search(testid):
        return True

    # Any data-* attribute
    for attr_name, attr_val in el.attrs.items():
        if attr_name.startswith("data-") and isinstance(attr_val, str):
            if _CARD_PATTERN.search(attr_val):
                return True

    # Semantic elements that are commonly used as cards
    if el.name in ("article", "figure"):
        return True

    # role="listitem"
    if el.get("role", "") == "listitem":
        return True

    return False


def _detect_repeated_structure(soup: BeautifulSoup, max_results: int) -> list[Tag]:
    """Find the parent with the most children of the same tag+class pattern.

    Returns candidate card elements from that parent.
    """
    best_group: list[Tag] = []

    for tag_name in ("div", "li", "article", "figure", "section"):
        # Group children by their class signature
        parent_map: dict[int, dict[str, list[Tag]]] = {}

        for el in soup.find_all(tag_name, recursive=True):
            if not isinstance(el, Tag) or not el.parent:
                continue
            if not el.find("a", href=True):
                continue
            text = el.get_text(strip=True)
            if len(text) < 20:
                continue
            if _is_inside_chrome(el):
                continue

            parent_id = id(el.parent)
            # Signature: tag name + first class (if any)
            classes = el.get("class", [])
            sig = f"{tag_name}::{classes[0] if classes else ''}"

            parent_map.setdefault(parent_id, {}).setdefault(sig, []).append(el)

        for sig_map in parent_map.values():
            for group in sig_map.values():
                if len(group) >= 5 and len(group) > len(best_group):
                    best_group = group

    return best_group[:max_results]


def _extract_title_from_card(card: Tag) -> str:
    for child in card.find_all(True, recursive=True):
        classes = " ".join(child.get("class", [])).lower()
        if any(kw in classes for kw in ("title", "name", "heading")):
            text = child.get_text(separator=" ", strip=True)
            if text and len(text) > 2:
                return text[:300]

    # role="heading"
    heading_el = card.find(attrs={"role": "heading"})
    if heading_el:
        text = heading_el.get_text(separator=" ", strip=True)
        if text:
            return text[:300]

    heading = card.find(re.compile(r"^h[1-6]$"))
    if heading:
        text = heading.get_text(separator=" ", strip=True)
        if text:
            return text[:300]

    link = card.find("a")
    if link:
        # Prefer aria-label over text when available
        label = link.get("aria-label", "").strip()
        if label and len(label) > 4:
            return label[:300]
        text = link.get_text(separator=" ", strip=True)
        if text and len(text) > 2:
            return text[:300]

    return ""


def _extract_snippet_from_card(card: Tag) -> Optional[str]:
    for child in card.find_all(True, recursive=True):
        classes = " ".join(child.get("class", [])).lower()
        if any(kw in classes for kw in ("description", "snippet", "subtitle", "detail", "desc")):
            text = child.get_text(separator=" ", strip=True)
            if text and len(text) > 5:
                return text[:300]
    return None


def _extract_url_from_card(card: Tag) -> Optional[str]:
    link = card.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and href != "#":
            return href
    return None


def _try_product_cards(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    seen_titles: set[str] = set()
    cards: list[Tag] = []

    # --- Pass 1: class/id/data-attr/semantic matching ---
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        if el.name in ("span", "label", "b", "i", "em", "strong", "small"):
            continue
        if not _element_matches_card(el):
            continue
        if _is_inside_chrome(el):
            continue

        # Skip chrome-class elements themselves
        classes = " ".join(el.get("class", []))
        el_id = el.get("id", "") or ""
        if _CHROME_CLASSES.search(classes) or _CHROME_CLASSES.search(el_id):
            continue

        # <li> inside a list — only include if the list is inside a result-container
        if el.name == "li":
            parent = el.parent
            if not isinstance(parent, Tag):
                continue
            parent_classes = " ".join(parent.get("class", [])).lower()
            parent_id = (parent.get("id", "") or "").lower()
            if not any(
                kw in parent_classes or kw in parent_id
                for kw in ("result", "search", "list", "grid", "feed", "card")
            ):
                continue

        visible = el.get_text(strip=True)
        if len(visible) < 15:
            continue

        heading = el.find(re.compile(r"^h[1-3]$"))
        if heading and _SECTION_HEADER_RE.match(heading.get_text(strip=True)):
            continue

        cards.append(el)

    # When there are many candidates the list is likely polluted by either:
    #   (a) CSS-module hashed class names (e.g. "BurgerNavigation-module_burgerItem__SZVhF")
    #   (b) Tailwind layout utilities (e.g. "items-center") whose names happen to
    #       contain a keyword like "item".
    # Strategy: find which class names are driving the inflation.  If one class
    # accounts for the majority of matches, strip cards whose ONLY product-keyword
    # class is that dominant one.  If the set is still too large after stripping,
    # discard it entirely (true CSS-module pollution).
    if len(cards) > 200:
        from collections import Counter as _Counter
        match_counts: _Counter[str] = _Counter()
        for c in cards:
            for cls in c.get("class", []):
                if _CARD_PATTERN.search(cls):
                    match_counts[cls] += 1

        if match_counts:
            top_cls, top_count = match_counts.most_common(1)[0]
            dominant_fraction = top_count / len(cards)
            if dominant_fraction > 0.5:
                # Strip cards whose only product-keyword class is the dominant one
                filtered = [
                    c for c in cards
                    if any(
                        _CARD_PATTERN.search(cls) and cls != top_cls
                        for cls in c.get("class", [])
                    )
                ]
                logger.debug(
                    "_try_product_cards: dominant class %r (%d/%d = %.0f%%) stripped; "
                    "%d candidates remaining",
                    top_cls, top_count, len(cards), dominant_fraction * 100, len(filtered),
                )
                cards = filtered

        if len(cards) > 200:
            logger.debug(
                "_try_product_cards: %d raw candidates after stripping — "
                "likely CSS module false positives, clearing",
                len(cards),
            )
            cards = []

    # --- Pass 2: repeated-structure detection (always run, compare quality) ---
    repeated = _detect_repeated_structure(soup, max_results)

    def _card_quality(card_list: list[Tag]) -> float:
        """Fraction of cards that have a link AND (price OR description class)."""
        if not card_list:
            return 0.0
        qualified = 0
        for c in card_list:
            text = c.get_text()
            has_link = bool(c.find("a", href=True))
            has_price = bool(_PRICE_RE.search(text) or _PRICE_FALLBACK_RE.search(text))
            if has_link and has_price:
                qualified += 1
        return qualified / len(card_list)

    # Leaf-dedup pass 1 cards
    card_ids = {id(c) for c in cards}
    leaf_cards: list[Tag] = []
    for card in cards:
        has_matched_descendant = any(
            id(desc) in card_ids
            for desc in card.descendants
            if isinstance(desc, Tag)
        )
        if not has_matched_descendant:
            leaf_cards.append(card)

    # Prefer repeated-structure detection when it yields a meaningfully better
    # quality score, or when pass-1 leaf cards are mostly filter/facet junk.
    q_leaf = _card_quality(leaf_cards)
    q_rep = _card_quality(repeated)
    if repeated and (q_rep > q_leaf + 0.2 or (q_rep > 0 and len(repeated) >= len(leaf_cards))):
        logger.debug(
            "Preferring repeated-structure detection (q=%.2f, %d) over leaf-dedup (q=%.2f, %d)",
            q_rep, len(repeated), q_leaf, len(leaf_cards),
        )
        filtered_cards = repeated
    else:
        filtered_cards = leaf_cards
        if repeated:
            logger.debug(
                "Keeping leaf-dedup (q=%.2f, %d); repeated-structure q=%.2f, %d",
                q_leaf, len(leaf_cards), q_rep, len(repeated),
            )

    # Prefer cards with both link and price/description
    def _card_score(c: Tag) -> int:
        has_link = bool(c.find("a", href=True))
        has_price = bool(_PRICE_RE.search(c.get_text()) or _PRICE_FALLBACK_RE.search(c.get_text()))
        has_desc = any(
            kw in " ".join(child.get("class", [])).lower()
            for child in c.find_all(True, recursive=True)
            for kw in ("desc", "snippet", "subtitle", "detail")
        )
        return (0 if has_link else 2) + (0 if (has_price or has_desc) else 1)

    filtered_cards.sort(key=_card_score)

    for card in filtered_cards:
        title = _extract_title_from_card(card)
        if not title or len(title) < 2:
            continue

        title_lower = re.sub(r"\s+", " ", title.lower()).strip()
        if title_lower in seen_titles:
            continue
        seen_titles.add(title_lower)

        results.append(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=_extract_price(card),
            snippet=_extract_snippet_from_card(card),
            url=_extract_url_from_card(card),
        ))

        if len(results) >= max_results:
            break

    raw_count = len(results)
    filtered = _filter_junk_results(results)
    logger.debug(
        "Strategy 2 (Product cards): found %d raw results, %d after filtering",
        raw_count, len(filtered),
    )
    return filtered


# ---------------------------------------------------------------------------
# Strategy 3 — Generic list fallback
# ---------------------------------------------------------------------------


def _try_generic_list(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    parent_groups: dict[int, list[Tag]] = {}

    for tag_name in ("li", "div", "article", "figure", "section", "tr"):
        for el in soup.find_all(tag_name, recursive=True):
            if not isinstance(el, Tag) or not el.parent:
                continue
            if not el.find("a"):
                continue
            if len(el.get_text(strip=True)) < 10:
                continue
            if _is_inside_chrome(el):
                continue
            parent_groups.setdefault(id(el.parent), []).append(el)

    if not parent_groups:
        return results

    largest_group = max(parent_groups.values(), key=len)
    if len(largest_group) < 2:
        return results

    seen_titles: set[str] = set()

    for el in largest_group:
        link = el.find("a", href=True)
        title, url = "", None

        if link:
            title = link.get_text(separator=" ", strip=True)[:300]
            href = link.get("href", "")
            url = href if href and href != "#" else None

        if not title:
            heading = el.find(re.compile(r"^h[1-6]$"))
            if heading:
                title = heading.get_text(separator=" ", strip=True)[:300]

        if not title or len(title) < 3:
            continue

        title_lower = re.sub(r"\s+", " ", title.lower()).strip()
        if title_lower in seen_titles:
            continue
        seen_titles.add(title_lower)

        results.append(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=_extract_price(el),
            snippet=None,
            url=url,
        ))

        if len(results) >= max_results:
            break

    raw_count = len(results)
    filtered = _filter_junk_results(results)
    logger.debug(
        "Strategy 3 (Generic list): found %d raw results, %d after filtering",
        raw_count, len(filtered),
    )
    return filtered


# ---------------------------------------------------------------------------
# Combined heuristic extraction — run ALL, pick best
# ---------------------------------------------------------------------------


def _score_strategy(results: list[SearchResult]) -> float:
    """Score a strategy's results by quality, not just count.

    Weights: valid URL (3), has price (2), meaningful title (1), not-junk bonus (2).
    This prevents 20 nav links from beating 5 real products.
    """
    if not results:
        return 0.0
    score = 0.0
    for r in results:
        has_url = bool(r.url and not r.url.startswith("#"))
        has_price = r.price is not None
        title_quality = len(r.title) > 20
        # Penalise results that look like junk (even if they passed the filter)
        lower = r.title.lower().strip()
        looks_junky = (
            any(lower.startswith(p) for p in _JUNK_STARTS)
            or lower in _JUNK_EXACT
            or len(r.title) < 10
        )
        score += (
            (3.0 if has_url else 0)
            + (2.0 if has_price else 0)
            + (1.0 if title_quality else 0)
            + (0.0 if looks_junky else 2.0)
        )
    return score


def _extract_results(html: str, max_results: int, url: str = "") -> list[SearchResult]:
    """Run extraction strategies, return the one with the best quality score.

    If a cached SiteExtractionProfile exists (learned from probe), tries it first.
    Falls back to the full 4-strategy sweep if the cache misses.
    """
    global _site_extraction_profile

    # Fast path: try cached LLM-generated selectors first
    if _site_extraction_profile is not None:
        cached_results = _extract_with_cached_selectors(html, _site_extraction_profile, max_results)
        if len(cached_results) >= 3:
            logger.debug(
                "Cached selectors hit: %d results (skipping full strategy sweep)",
                len(cached_results),
            )
            return cached_results
        logger.debug("Cached selectors miss (%d results) — falling back to full sweep", len(cached_results))

    # Full sweep: run all heuristic strategies
    soup = BeautifulSoup(html, "html.parser")

    strategy_results: dict[str, list[SearchResult]] = {}

    strategy_results["site-specific"] = _try_site_specific(soup, url, max_results)
    strategy_results["schema-org"] = _try_schema_org(soup, max_results)
    strategy_results["product-cards"] = _try_product_cards(soup, max_results)
    strategy_results["generic-list"] = _try_generic_list(soup, max_results)

    # Pick the strategy with the highest quality score (not just most results)
    scores = {k: _score_strategy(v) for k, v in strategy_results.items()}
    winner_name = max(scores, key=scores.get)
    winner = strategy_results[winner_name]

    logger.debug(
        "Strategy scores: %s",
        ", ".join(f"{k}:{s:.1f} ({len(strategy_results[k])})" for k, s in scores.items()),
    )
    logger.debug(
        "Strategy winner: %s (score=%.1f, %d results)",
        winner_name, scores[winner_name], len(winner),
    )

    if winner:
        _log_first_titles(winner, winner_name)

    return winner


def _log_first_titles(results: list[SearchResult], strategy: str) -> None:
    titles = [f'"{r.title[:60]}"' for r in results[:3]]
    logger.debug("  %s sample: %s", strategy, " | ".join(titles))


# ---------------------------------------------------------------------------
# JS-rendering detection
# ---------------------------------------------------------------------------


def _needs_js_rendering(html: str, results_count: int) -> bool:
    """Heuristic: True if page is likely JS-rendered and needs Playwright."""
    html_lower = html[:80000].lower()

    # Framework fingerprints — always check these
    for signal in (
        "window.__next_data__", "__nuxt__", "__react_root__",
        'id="__next"', 'id="app"', 'id="root"',
        "window.__remixcontext", "data-reactroot", "ng-app", "react-root",
    ):
        if signal in html_lower:
            return True

    if results_count >= 5:
        return False

    # Strip scripts for body text measurement
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    body = soup.find("body")
    body_text = body.get_text(strip=True) if body else ""

    if len(body_text) < 500:
        return True
    if len(html) > 0 and len(body_text) / len(html) < 0.10:
        return True

    product_links = [
        a for a in soup.find_all("a", href=True)
        if _PRODUCT_LINK_RE.search(a.get("href", ""))
    ]
    if len(product_links) < 5:
        return True

    scripts = soup.find_all("script")
    total_script_len = sum(len(s.string or "") for s in scripts)
    if total_script_len > 5000 and (len(body_text) < 2000 or total_script_len > len(body_text) * 2):
        return True

    return False


# ---------------------------------------------------------------------------
# Playwright fetch with aggressive scroll loop
# ---------------------------------------------------------------------------

_PRODUCT_SELECTORS = (
    "[class*='deal']", "[class*='product']", "[class*='card']",
    "[class*='result']", "[class*='item']", "[class*='offer']", "[class*='listing']",
    "article", "figure[class]",
)


def _apply_stealth(page) -> None:
    """Apply playwright-stealth patches if available, else fall back to basic evasion."""
    try:
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(page)
        logger.debug("Playwright: applied full stealth patches (playwright-stealth v2)")
    except ImportError:
        # Fallback: basic webdriver hide
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        logger.debug("Playwright: playwright-stealth not installed, using basic webdriver hide")


def _dismiss_consent_banners(page) -> None:
    """Dismiss common cookie / GDPR consent banners."""
    _CONSENT_SELECTORS = [
        "button#onetrust-accept-btn-handler",           # OneTrust
        "#accept-all-cookies",                          # generic
        "button[id*='accept-all']",
        "button[id*='accept_all']",
        "button[class*='accept-all']",
        "button[data-testid*='accept']",
        "[aria-label*='Accept all']",
        "[aria-label*='Alle akzeptieren']",
        "button.didomi-components-button--color-green",  # Didomi
        "#CybotCookiebotDialogBodyButtonAccept",         # CookieBot
    ]
    for cs in _CONSENT_SELECTORS:
        try:
            btn = page.query_selector(cs)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(1200)
                logger.debug("Playwright: dismissed cookie banner via '%s'", cs)
                return
        except Exception:
            continue

    # Fallback: text-based button search
    try:
        for btn in page.query_selector_all("button"):
            txt = (btn.inner_text() or "").strip().lower()
            if any(kw in txt for kw in (
                "accept all", "alle akzeptieren", "accepteer alle",
                "accepter tout", "akzeptieren", "accept cookies",
                "povolit vše", "přijmout vše", "souhlasím",
            )):
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1200)
                    logger.debug("Playwright: dismissed consent via text '%s'", txt)
                    return
    except Exception:
        pass


def _scroll_and_load_more(page) -> None:
    """Scroll down and click load-more buttons to reveal all results."""
    # Wait for product selectors
    found_selector = False
    for selector in _PRODUCT_SELECTORS:
        try:
            page.wait_for_selector(selector, timeout=8000)
            found_selector = True
            logger.debug("Playwright: found selector '%s'", selector)
            break
        except Exception:
            continue

    if not found_selector:
        # SPA fallback: wait for networkidle (longer timeout for client-side rendered sites)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        # Poll for DOM to stabilize — SPA sites render products after API calls complete.
        # Wait until the page has a cluster of 5+ sibling elements (product grid signal).
        try:
            page.wait_for_function(
                """() => {
                    const containers = document.querySelectorAll('main, [role="main"], [id*="content"], [class*="content"], [class*="search"], [class*="catalog"], [class*="listing"]');
                    for (const c of containers) {
                        for (const child of c.children) {
                            if (child.children.length >= 5) return true;
                        }
                    }
                    // Fallback: any element with 5+ direct children sharing the same tag
                    const all = document.querySelectorAll('ul, ol, div, section');
                    for (const el of all) {
                        const tags = {};
                        for (const ch of el.children) {
                            tags[ch.tagName] = (tags[ch.tagName] || 0) + 1;
                            if (tags[ch.tagName] >= 5) return true;
                        }
                    }
                    return false;
                }""",
                timeout=15000,
            )
            logger.debug("Playwright: SPA content detected via DOM polling")
        except Exception:
            logger.debug("Playwright: SPA DOM poll timed out — proceeding with current content")

    for _scroll_pass in range(5):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(1500)

    for _load_round in range(3):
        clicked = False
        try:
            buttons = page.query_selector_all("button, a[href]")
            for btn in buttons[:80]:
                try:
                    btn_text = (btn.inner_text() or "").strip()
                    if _LOAD_MORE_RE.search(btn_text):
                        logger.debug("Playwright: clicking '%s'", btn_text)
                        btn.click()
                        page.wait_for_timeout(2000)
                        clicked = True
                        break
                except Exception:
                    continue
        except Exception:
            pass

        if not clicked:
            break

        for _ in range(3):
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(1500)

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)


def _fetch_with_playwright(
    url: str,
    quick_probe: bool = False,
    force_browser: Optional[str] = None,
    reuse_context: Optional[object] = None,
) -> tuple[str, str, str]:
    """Fetch a page using a headless browser.

    Args:
        url: Target URL.
        quick_probe: If True, skip scroll/load-more (just navigate + consent + 2s wait).
        force_browser: 'firefox' or 'chromium' to skip the fallback loop.
        reuse_context: An existing Playwright BrowserContext to reuse.  When provided,
                       skips browser launch entirely — just opens a new page on the
                       existing context.  The caller owns the lifecycle.

    Returns:
        (html, browser_name, final_url) — html is "" if blocked/unavailable.
    """
    # ---- Fast path: reuse an existing persistent context ----
    if reuse_context is not None:
        return _fetch_on_context(reuse_context, url, quick_probe)

    # ---- Normal path: launch browser, try Firefox then Chromium ----
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(
            "Playwright not installed. Install: pip install playwright && playwright install chromium"
        )
        return "", "", ""

    html = ""
    used_browser = ""
    final_url = ""
    try:
        with sync_playwright() as p:
            chromium_opts = {"args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"]}

            if force_browser == "chromium":
                browsers = [(p.chromium, "chromium", chromium_opts)]
            elif force_browser == "firefox":
                browsers = [(p.firefox, "firefox", {})]
            else:
                browsers = [
                    (p.firefox, "firefox", {}),
                    (p.chromium, "chromium", chromium_opts),
                ]

            browser = None
            browser_name = ""
            for browser_type, name, launch_kw in browsers:
                try:
                    browser = browser_type.launch(headless=True, **launch_kw)
                    browser_name = name
                    logger.debug("Playwright: launched %s", name)
                except Exception as e:
                    logger.debug("Playwright: %s unavailable (%s), trying next", name, e)
                    continue

                ctx_kwargs = {
                    "user_agent": _USER_AGENT,
                    "viewport": {"width": 1280, "height": 900},
                }
                if _PW_PROXY:
                    ctx_kwargs["proxy"] = _PW_PROXY
                context = browser.new_context(**ctx_kwargs)
                page = context.new_page()
                _apply_stealth(page)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000)
                    probe_html = page.content()
                    block = _classify_response(probe_html)
                    if block in ("cloudflare", "imperva"):
                        logger.debug("Playwright: %s returned %s block page, trying next browser", name, block)
                        context.close()
                        browser.close()
                        browser = None
                        continue
                except Exception as e:
                    logger.debug("Playwright: %s navigation failed (%s), trying next", name, e)
                    context.close()
                    browser.close()
                    browser = None
                    continue

                break

            if browser is None:
                logger.warning("Playwright: all browsers blocked or unavailable")
                return "", "", ""

            used_browser = browser_name
            _dismiss_consent_banners(page)

            if quick_probe:
                page.wait_for_timeout(2000)
            else:
                _scroll_and_load_more(page)

            html = page.content()
            final_url = page.url
            context.close()
            browser.close()

    except Exception as e:
        logger.warning("Playwright fetch failed for %s: %s", url, e)

    return html, used_browser, final_url


def _fetch_on_context(context, url: str, quick_probe: bool = False) -> tuple[str, str, str]:
    """Fetch a page on an existing BrowserContext (persistent session)."""
    html = ""
    final_url = ""
    try:
        page = context.new_page()
        _apply_stealth(page)
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        probe_html = page.content()
        block = _classify_response(probe_html)
        if block in ("cloudflare", "imperva"):
            logger.debug("Persistent context: %s block detected", block)
            page.close()
            return "", "persistent", ""

        _dismiss_consent_banners(page)

        if quick_probe:
            page.wait_for_timeout(2000)
        else:
            _scroll_and_load_more(page)

        html = page.content()
        final_url = page.url
        page.close()
    except Exception as e:
        logger.warning("Persistent context fetch failed for %s: %s", url, e)

    return html, "persistent", final_url


# ---------------------------------------------------------------------------
# Strategy 4 — LLM extraction (nuclear fallback)
# ---------------------------------------------------------------------------

_STRIP_TAGS_RE = re.compile(r"<(script|style|svg|path|noscript)[^>]*>.*?</\1>", re.I | re.S)
_STRIP_ATTRS_RE = re.compile(r'\s+(?!href=|class=|id=|data-testid=)\w[\w-]*="[^"]*"')
_STRIP_ATTRS_SQ_RE = re.compile(r"\s+(?!href=|class=|id=|data-testid=)\w[\w-]*='[^']*'")


def _clean_html_for_llm(html: str) -> str:
    cleaned = _STRIP_TAGS_RE.sub("", html)
    cleaned = _STRIP_ATTRS_RE.sub("", cleaned)
    cleaned = _STRIP_ATTRS_SQ_RE.sub("", cleaned)
    cleaned = re.sub(r"\n\s*\n+", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _find_main_content(html: str, url: str = "") -> str:
    """Extract the tightest results container available."""
    soup = BeautifulSoup(html, "html.parser")

    # Site-specific: Groupon — find the div with the most /deals/ links
    if "groupon" in url.lower():
        best_el = None
        best_count = 0
        for div in soup.find_all(["div", "main", "section", "ul"]):
            deal_links = div.find_all("a", href=re.compile(r"/deals?/", re.I))
            if len(deal_links) > best_count:
                best_count = len(deal_links)
                best_el = div
        if best_el and best_count >= 3:
            logger.debug("LLM container: Groupon deal list with %d deal links", best_count)
            return str(best_el)

    # Generic: id/class/data-testid containing results/deals/listings keywords
    container_id_re = re.compile(
        r"results?|search.results?|deals?|listings?|product.list|card.list|items?|catalog|feed|grid",
        re.I,
    )
    for tag in ("main", "div", "section", "ul", "ol"):
        for el in soup.find_all(tag):
            el_id = (el.get("id", "") or "").strip()
            el_classes = " ".join(el.get("class", []))
            el_testid = (el.get("data-testid", "") or "").strip()
            if (
                container_id_re.search(el_id)
                or container_id_re.search(el_classes)
                or container_id_re.search(el_testid)
            ):
                if len(str(el)) > 500:
                    logger.debug("LLM container: <%s class='%s' id='%s' data-testid='%s'>", tag, el_classes[:40], el_id, el_testid[:40])
                    return str(el)

    # Fallback: <main>
    main_el = soup.find("main")
    if main_el and len(str(main_el)) > 500:
        return str(main_el)

    return html


def _call_haiku_for_extraction(
    html_chunk: str, query: str, max_results: int, instruction_prefix: str = ""
) -> list[dict]:
    """Make a single Haiku call for HTML extraction. Returns raw list of dicts."""
    if not _HAS_API_KEY:
        logger.debug("LLM extraction skipped: no ANTHROPIC_API_KEY")
        return []
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=3000,
        temperature=0,
        system=(
            "You are a web scraping expert. Your job is to extract product/service/deal "
            "listings from search result page HTML. You are precise and never confuse "
            "page chrome (navigation, banners, buttons, consent dialogs) with actual results."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"{instruction_prefix}"
                f'The search query was: "{query}"\n\n'
                "TASK: Extract up to " + str(max_results) + " product/deal/service listings from "
                "this HTML. Do NOT stop at 3 or 5 — extract ALL listings you can find.\n\n"
                "APPROACH:\n"
                "1. First, identify the REPEATING card-like HTML pattern that contains product listings. "
                "These are usually <article>, <li>, <div>, or <figure> elements that repeat with "
                "similar class names and structure.\n"
                "2. Then extract from EACH card:\n"
                "   - title: the product/deal/service name (from heading, link text, or aria-label)\n"
                "   - price: the displayed price string including currency symbol (null if not visible)\n"
                "   - snippet: a short description if available (null if not)\n"
                "   - url: the href of the main link (null if not found)\n\n"
                "EXCLUSIONS — do NOT extract any of these:\n"
                "- Page headers, section titles ('Results for...', 'Top Trending', 'Recommended')\n"
                "- Navigation links, breadcrumbs, footer links\n"
                "- Cookie/consent banners, sign-in prompts\n"
                "- Filter/facet sidebar items\n"
                "- Promotional banners or sponsored sections\n\n"
                "Respond with ONLY a JSON array of objects. No markdown, no commentary.\n\n"
                f"HTML:\n{html_chunk}"
            ),
        }],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip()[:-3]
        raw = raw.strip()
    return json.loads(raw)


def _extract_with_llm(html: str, query: str, max_results: int = 15, url: str = "") -> list[SearchResult]:
    """Nuclear fallback: ask Claude Haiku to extract results from cleaned HTML."""
    try:
        content_html = _find_main_content(html, url)
        clean = _clean_html_for_llm(content_html)
        truncated = clean[:50000]

        items = _call_haiku_for_extraction(truncated, query, max_results)

        if not isinstance(items, list):
            logger.warning("LLM extraction returned non-array JSON")
            return []

        results = _items_to_results(items, max_results)
        filtered = _filter_junk_results(results)

        # Retry once if we got very few results
        if len(filtered) < 5:
            logger.info(
                "LLM first pass found only %d results, retrying with stronger instruction...",
                len(filtered),
            )
            retry_prefix = (
                f"The previous extraction found only {len(filtered)} results. "
                "Look more carefully at the HTML. Search results are usually rendered as "
                "repeated card-like elements (article, li, figure, div) containing a title link "
                f"and often a price. Extract up to {max_results}.\n\n"
            )
            try:
                retry_items = _call_haiku_for_extraction(truncated, query, max_results, retry_prefix)
                if isinstance(retry_items, list):
                    retry_results = _filter_junk_results(_items_to_results(retry_items, max_results))
                    if len(retry_results) > len(filtered):
                        filtered = retry_results
                        logger.info("LLM retry improved to %d results", len(filtered))
            except Exception as e:
                logger.debug("LLM retry failed: %s", e)

        logger.info("Strategy 4 (LLM): found %d results", len(filtered))
        if filtered:
            _log_first_titles(filtered, "LLM")
        return filtered

    except anthropic.APIError as e:
        logger.warning("LLM extraction API error: %s", e)
        return []
    except (json.JSONDecodeError, IndexError) as e:
        logger.warning("LLM extraction parse error: %s", e)
        return []
    except Exception as e:
        logger.warning("LLM extraction unexpected error: %s", e)
        return []


def _items_to_results(items: list[dict], max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in items[:max_results]:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        results.append(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=item.get("price") or None,
            snippet=item.get("snippet") or None,
            url=item.get("url") or None,
        ))
    return results


# ---------------------------------------------------------------------------
# LLM-generated selector caching — "LLM teaches the scraper"
# ---------------------------------------------------------------------------


class SiteExtractionProfile:
    """Cached extraction selectors learned from the probe query via LLM."""

    def __init__(
        self,
        container_selector: str,
        card_selector: str,
        title_selector: str,
        price_selector: Optional[str] = None,
        url_selector: Optional[str] = None,
    ):
        self.container_selector = container_selector
        self.card_selector = card_selector
        self.title_selector = title_selector
        self.price_selector = price_selector
        self.url_selector = url_selector


def _generate_extraction_profile(
    html: str, results: list[SearchResult], url: str = ""
) -> Optional[SiteExtractionProfile]:
    """Ask Haiku to generate CSS selectors for this site's product cards.

    Sends a trimmed HTML chunk + the titles we found, and asks the LLM to
    identify the repeating card structure.  Runs once per site (on the probe).
    """
    if len(results) < 3:
        return None
    if not _HAS_API_KEY:
        logger.debug("LLM selector generation skipped: no ANTHROPIC_API_KEY")
        return None

    # Find the HTML region around the results for context
    content_html = _find_main_content(html, url)
    clean = _clean_html_for_llm(content_html)
    truncated = clean[:30000]  # smaller chunk — we just need structure

    titles_sample = "\n".join(f"- {r.title[:80]}" for r in results[:8])

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=500,
            temperature=0,
            system=(
                "You are a web scraping expert. Given HTML and a list of product titles found on "
                "the page, identify the CSS selectors for the repeating product card structure."
            ),
            messages=[{
                "role": "user",
                "content": (
                    "I found these product listings on this search results page:\n"
                    f"{titles_sample}\n\n"
                    "Analyze the HTML below and return a JSON object with CSS selectors:\n"
                    "{\n"
                    '  "container_selector": "CSS selector for the parent container holding all cards",\n'
                    '  "card_selector": "CSS selector for each individual product card element",\n'
                    '  "title_selector": "CSS selector for the title element WITHIN a card",\n'
                    '  "price_selector": "CSS selector for the price element WITHIN a card (null if no prices)",\n'
                    '  "url_selector": "CSS selector for the link element WITHIN a card (usually a)"\n'
                    "}\n\n"
                    "Rules:\n"
                    "- Use class-based selectors when possible (more stable than nth-child)\n"
                    "- The card_selector should match ALL product cards, not just one\n"
                    "- Return ONLY the JSON object, no commentary\n\n"
                    f"HTML:\n{truncated}"
                ),
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.rstrip().endswith("```"):
                raw = raw.rstrip()[:-3]
            raw = raw.strip()

        # Extract just the JSON object — LLM sometimes appends commentary
        brace_start = raw.find("{")
        if brace_start == -1:
            logger.warning("LLM selector generation: no JSON object found in response")
            return None
        depth = 0
        brace_end = -1
        for i in range(brace_start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i + 1
                    break
        if brace_end == -1:
            logger.warning("LLM selector generation: unclosed JSON object")
            return None
        raw = raw[brace_start:brace_end]

        data = json.loads(raw)
        profile = SiteExtractionProfile(
            container_selector=data.get("container_selector", ""),
            card_selector=data.get("card_selector", ""),
            title_selector=data.get("title_selector", ""),
            price_selector=data.get("price_selector"),
            url_selector=data.get("url_selector", "a"),
        )

        if not profile.container_selector or not profile.card_selector:
            logger.debug("LLM selector generation: incomplete selectors, skipping cache")
            return None

        logger.info(
            "LLM selector cache: container='%s', card='%s', title='%s'",
            profile.container_selector, profile.card_selector, profile.title_selector,
        )
        return profile

    except Exception as e:
        logger.warning("LLM selector generation failed: %s", e)
        return None


def _extract_with_cached_selectors(
    html: str, profile: SiteExtractionProfile, max_results: int
) -> list[SearchResult]:
    """Fast extraction using LLM-generated selectors from the probe query."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    seen_titles: set[str] = set()

    # Find the container
    container = soup.select_one(profile.container_selector)
    if not container:
        # Try without container — just find cards globally
        cards = soup.select(profile.card_selector)
    else:
        cards = container.select(profile.card_selector)

    if not cards:
        logger.debug("Cached selectors: no cards found with '%s'", profile.card_selector)
        return results

    for card in cards[:max_results * 2]:  # scan extra in case some are junk
        # Extract title
        title = ""
        if profile.title_selector:
            title_el = card.select_one(profile.title_selector)
            if title_el:
                title = title_el.get_text(separator=" ", strip=True)[:300]
        if not title:
            title = _extract_title_from_card(card)
        if not title or len(title) < 3:
            continue

        title_key = re.sub(r"\s+", " ", title.lower()).strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # Extract price
        price = None
        if profile.price_selector:
            price_el = card.select_one(profile.price_selector)
            if price_el:
                text = price_el.get_text(separator=" ", strip=True)
                for pattern in (_PRICE_RE, _PRICE_FALLBACK_RE):
                    m = pattern.search(text)
                    if m:
                        price = m.group(0).strip()
                        break
        if not price:
            price = _extract_price(card)

        # Extract URL
        url = None
        if profile.url_selector:
            link_el = card.select_one(profile.url_selector)
            if link_el:
                href = link_el.get("href", "")
                if href and href != "#":
                    url = href
        if not url:
            url = _extract_url_from_card(card)

        results.append(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=price,
            snippet=_extract_snippet_from_card(card),
            url=url,
        ))

        if len(results) >= max_results:
            break

    filtered = _filter_junk_results(results)
    logger.debug(
        "Cached selectors: found %d raw results, %d after filtering",
        len(results), len(filtered),
    )
    return filtered


# Module-level cache for the extraction profile (set during probe, used for remaining queries)
_site_extraction_profile: Optional[SiteExtractionProfile] = None


# ---------------------------------------------------------------------------
# LLM result validation — lightweight check that extracted items are real products
# ---------------------------------------------------------------------------


def _all_urls_look_like_products(results: list[SearchResult]) -> bool:
    """Fast heuristic: skip LLM validation if every result has a product-like URL."""
    if not results:
        return False
    for r in results:
        if not r.url or r.url.startswith("#"):
            return False
        if not _PRODUCT_LINK_RE.search(r.url):
            return False
    return True


def _validate_results_with_llm(
    results: list[SearchResult], query: str
) -> list[SearchResult]:
    """Ask Haiku which extracted results are real products vs. page chrome.

    Sends only titles + URLs (tiny payload, ~$0.001/call).
    Returns only the validated results, re-indexed 1-based.
    """
    if not results:
        return results
    if not _HAS_API_KEY:
        logger.debug("LLM validation skipped: no ANTHROPIC_API_KEY")
        return results

    # Skip validation when URLs strongly signal real products
    if _all_urls_look_like_products(results):
        logger.debug("Validation skip: all %d URLs match product patterns", len(results))
        return results

    lines = []
    for r in results:
        url_part = r.url[:120] if r.url else "(no URL)"
        lines.append(f"{r.rank}. {r.title[:100]} | {url_part}")
    listing = "\n".join(lines)

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_HAIKU_MODEL,
            max_tokens=300,
            temperature=0,
            system=(
                "You are a web scraping quality checker. "
                "You determine which extracted items are real product/service listings "
                "vs. page chrome (navigation, buttons, banners, cookie consent, headers, footers)."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f'Search query: "{query}"\n\n'
                    f"Extracted results:\n{listing}\n\n"
                    "Return a JSON array of the 1-based indices of items that are REAL "
                    "product/service/deal listings. Exclude navigation links, UI buttons, "
                    "section headers, cookie banners, sign-in prompts, and any other page chrome.\n"
                    "Return ONLY the JSON array, no commentary. Example: [1, 2, 4, 5]"
                ),
            }],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.rstrip().endswith("```"):
                raw = raw.rstrip()[:-3]
            raw = raw.strip()

        valid_indices = set(json.loads(raw))
        validated = [r for r in results if r.rank in valid_indices]

        # Re-index ranks
        for i, r in enumerate(validated, 1):
            r.rank = i

        rejected_count = len(results) - len(validated)
        if rejected_count > 0:
            logger.info(
                "LLM validation: kept %d/%d results for query '%s' (rejected %d as page chrome)",
                len(validated), len(results), query, rejected_count,
            )
        else:
            logger.debug("LLM validation: all %d results validated for '%s'", len(results), query)

        return validated

    except Exception as e:
        logger.warning("LLM validation failed (%s), returning unvalidated results", e)
        return results


# ---------------------------------------------------------------------------
# Probe-first fetch infrastructure
# ---------------------------------------------------------------------------


def _probe_site(
    url: str,
    query: str,
    max_results: int,
) -> tuple[str, list[SearchResult], str, bool]:
    """Probe one URL to determine site-level fetch mode and get first results.

    Strategy (ordered by cost):
      1. Quick static fetch (5s timeout) — catches Cloudflare blocks and cheap wins.
      2. Full Playwright fetch (Firefox → Chromium stealth fallback) — for JS-heavy /
         bot-protected sites.  Block detection is built into _fetch_with_playwright.
      3. LLM extraction fallback on the best HTML retrieved so far.

    Returns:
        (mode, results, html, was_redirected)
        mode: one of SiteMode.{STATIC, PLAYWRIGHT_FIREFOX, PLAYWRIGHT_CHROMIUM, BLOCKED, FAILED}
        was_redirected: True if both static and Playwright landed on a non-search page for
                        this query (caller should retry with a different query).
    """
    # ---- Step 1: Quick static probe (5s) ------------------------------------
    static_html = ""
    static_code = 0
    static_redirected = False
    try:
        resp = requests.get(
            url, headers={"User-Agent": _USER_AGENT},
            timeout=5, allow_redirects=True, proxies=_REQUESTS_PROXIES,
        )
        static_html = resp.text
        static_code = resp.status_code
        static_redirected = _is_search_redirect(url, resp.url, query)
        if static_redirected:
            logger.info("Probe: static redirected to %s for query '%s'", resp.url, query)
        else:
            logger.debug("Probe: static HTTP %d, %d bytes", static_code, len(static_html))
    except requests.RequestException as e:
        logger.debug("Probe: static fetch failed: %s", e)

    # Hard-block detection on static response.
    # Cloudflare on static does NOT mean the site is inaccessible — many sites
    # serve the CF challenge to plain requests but allow Playwright stealth through.
    # Fall through to Playwright; only return BLOCKED if Playwright also fails.
    if static_html and _classify_response(static_html, static_code) == "cloudflare":
        logger.info("Probe: Cloudflare on static fetch → falling through to Playwright")

    # Static accessible, no redirect, and extraction sufficient?
    if not static_redirected and static_code == 200 and len(static_html) > 2000:
        results = _extract_results(static_html, max_results, url=url)
        if len(results) >= 5:
            results = _validate_results_with_llm(results, query)
            logger.info("Probe: static extraction (%d validated results) → STATIC mode", len(results))
            return SiteMode.STATIC, results, static_html, False

    # ---- Step 2: Full Playwright fetch (Firefox → Chromium stealth) ----------
    pw_html, pw_browser, pw_final_url = _fetch_with_playwright(url)

    if not pw_html:
        # Playwright failed — likely hard-blocked.  Try LLM on static HTML as last resort.
        if not static_redirected and static_html and static_code == 200 and len(static_html) > 2000:
            llm_results = _extract_with_llm(static_html, query, max_results, url=url)
            if llm_results:
                logger.info("Probe: static + LLM (%d results) → STATIC mode", len(llm_results))
                return SiteMode.STATIC, llm_results, static_html, False
        logger.info("Probe: all browsers blocked → BLOCKED")
        return SiteMode.BLOCKED, [], "", False

    # Determine mode regardless of redirect (mode is site-level, not query-level)
    mode = SiteMode.PLAYWRIGHT_CHROMIUM if pw_browser == "chromium" else SiteMode.PLAYWRIGHT_FIREFOX

    pw_redirected = _is_search_redirect(url, pw_final_url, query)
    if pw_redirected:
        logger.info(
            "Probe: Playwright also redirected to %s for query '%s' → was_redirected=True",
            pw_final_url, query,
        )
        return mode, [], pw_html, True

    results = _extract_results(pw_html, max_results, url=url)
    results = _validate_results_with_llm(results, query)
    if len(results) < 5:
        llm_results = _extract_with_llm(pw_html, query, max_results, url=url)
        if len(llm_results) > len(results):
            results = llm_results

    was_redirected = static_redirected  # Playwright didn't redirect; static might have
    logger.info(
        "Probe: Playwright/%s (%d validated results) → %s mode%s",
        pw_browser, len(results), mode,
        " [static had redirected]" if static_redirected else "",
    )
    return mode, results, pw_html, was_redirected


def _fetch_with_mode(
    url: str,
    query: str,
    max_results: int,
    mode: str,
    reuse_context: Optional[object] = None,
) -> tuple[list[SearchResult], bool]:
    """Fetch and extract results for *one* URL using the mode determined by _probe_site.

    Skips the probe overhead — applies the already-proven fetch strategy directly.
    When reuse_context is provided, Playwright modes use the persistent session.

    Returns:
        (results, was_redirected) — was_redirected=True means the server sent us to a
        non-search page for this query; caller should skip and try a different query.
    """
    if mode in (SiteMode.BLOCKED, SiteMode.FAILED):
        return [], False

    html = ""
    final_url = url

    if mode == SiteMode.STATIC:
        try:
            resp = requests.get(
                url, headers={"User-Agent": _USER_AGENT},
                timeout=15, allow_redirects=True, proxies=_REQUESTS_PROXIES,
            )
            resp.raise_for_status()
            html = resp.text
            final_url = resp.url
        except requests.RequestException as e:
            logger.warning("Static fetch failed for %s: %s", url, e)
            return [], False

    elif reuse_context is not None:
        # Persistent session — use shared context regardless of browser type
        html, _, final_url = _fetch_with_playwright(url, reuse_context=reuse_context)

    elif mode == SiteMode.PLAYWRIGHT_CHROMIUM:
        html, _, final_url = _fetch_with_playwright(url, force_browser="chromium")

    else:  # PLAYWRIGHT_FIREFOX (default)
        html, _, final_url = _fetch_with_playwright(url)

    if not html:
        return [], False

    if _is_search_redirect(url, final_url, query):
        logger.info("Query '%s' redirected to %s — skipping", query, final_url)
        return [], True

    results = _extract_results(html, max_results, url=url)
    results = _validate_results_with_llm(results, query)
    if len(results) < 5:
        llm_results = _extract_with_llm(html, query, max_results, url=url)
        if len(llm_results) > len(results):
            results = llm_results

    return results, False


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def fetch_all_results(
    search_url_template: str,
    queries: list[TestQuery],
    max_results: int = 15,
) -> dict[str, list[SearchResult]]:
    """Fetch search result pages for every query and extract structured data.

    Uses a probe-first strategy:
      1. Probe the first query to determine site-level fetch mode (static / playwright /
         blocked) using the cheapest successful approach.
      2. If the site is blocked, skip all remaining queries immediately (fast-fail).
      3. Apply the proven mode to all remaining queries without re-probing.

    This cuts wall-clock time dramatically for blocked sites (Cloudflare saves
    ~30s × N queries vs the old per-query approach) and avoids redundant Playwright
    launches for sites where static HTML already works.
    """
    # Reset per-site state from any previous run
    global _site_extraction_profile
    _site_extraction_profile = None

    if not search_url_template or "{}" not in search_url_template:
        logger.error("Invalid search_url_template '%s' — must contain '{}'", search_url_template)
        return {q.query: [] for q in queries}
    if not queries:
        return {}

    all_results: dict[str, list[SearchResult]] = {}
    total = len(queries)
    empty_count = thin_count = 0

    # ---- Phase 1: Probe — find first non-redirecting query, establish site mode ----
    # Walk through queries until one gives a real search results page.
    site_mode = SiteMode.FAILED
    remaining_queries: list[TestQuery] = list(queries)
    probe_position = 0  # tracks which slot in the output dict each probe query occupies

    while remaining_queries:
        probe_tq = remaining_queries.pop(0)
        probe_position += 1
        probe_url = search_url_template.replace("{}", quote_plus(probe_tq.query))
        logger.info("[probe %d/%d] Probing with query: '%s'", probe_position, total, probe_tq.query)

        site_mode, probe_results, probe_html, was_redirected = _probe_site(
            probe_url, probe_tq.query, max_results
        )
        all_results[probe_tq.query] = probe_results

        if was_redirected:
            logger.info(
                "Probe query '%s' redirected — trying next query", probe_tq.query
            )
            empty_count += 1
            thin_count += 1
            if site_mode in (SiteMode.BLOCKED, SiteMode.FAILED):
                break  # blocked AND redirected — nothing to try
            continue  # try next query as probe

        logger.info(
            "[%d/%d] '%s' → %d results (mode: %s)",
            probe_position, total, probe_tq.query, len(probe_results), site_mode,
        )

        # Learn extraction selectors from the probe's HTML + results
        if probe_results and probe_html and len(probe_results) >= 3:
            _site_extraction_profile = _generate_extraction_profile(
                probe_html, probe_results, url=probe_url
            )

        if not probe_results:
            empty_count += 1
        if len(probe_results) < 5:
            thin_count += 1
        break  # probe succeeded (non-redirected)

    # Fast-fail: skip everything if site is inaccessible
    if site_mode in (SiteMode.BLOCKED, SiteMode.FAILED):
        logger.info(
            "Site probe returned %s — skipping %d remaining queries",
            site_mode, len(remaining_queries),
        )
        for tq in remaining_queries:
            all_results[tq.query] = []
            empty_count += 1
            thin_count += 1
        _log_summary(total, 0, 0, empty_count, site_mode)
        return all_results

    # ---- Phase 2: Apply proven mode to remaining queries --------------------
    # For Playwright modes, create a persistent browser context so cookies and
    # session state carry over across all queries (improves bot-protection bypass).
    pw_count = llm_count = 0
    persistent_pw = None   # Playwright sync_playwright context manager
    persistent_browser = None
    persistent_context = None
    is_pw_mode = site_mode in (SiteMode.PLAYWRIGHT_FIREFOX, SiteMode.PLAYWRIGHT_CHROMIUM)

    if is_pw_mode and remaining_queries:
        try:
            from playwright.sync_api import sync_playwright
            persistent_pw = sync_playwright().start()
            chromium_opts = {"args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"]}
            if site_mode == SiteMode.PLAYWRIGHT_CHROMIUM:
                persistent_browser = persistent_pw.chromium.launch(headless=True, **chromium_opts)
            else:
                persistent_browser = persistent_pw.firefox.launch(headless=True)
            pctx_kwargs = {
                "user_agent": _USER_AGENT,
                "viewport": {"width": 1280, "height": 900},
            }
            if _PW_PROXY:
                pctx_kwargs["proxy"] = _PW_PROXY
            persistent_context = persistent_browser.new_context(**pctx_kwargs)
            logger.info("Created persistent browser context for %d remaining queries", len(remaining_queries))
        except Exception as e:
            logger.warning("Failed to create persistent context: %s — falling back to per-query browsers", e)
            persistent_context = None

    # LLM-primary promotion: if heuristic extraction keeps failing, switch to
    # direct LLM extraction for remaining queries.
    use_llm_primary = False
    consecutive_thin = 0  # track consecutive queries with < 3 results

    if remaining_queries:
        time.sleep(1.5)

    try:
        for i, tq in enumerate(remaining_queries, probe_position + 1):
            query_str = tq.query
            url = search_url_template.replace("{}", quote_plus(query_str))

            if use_llm_primary:
                # LLM-primary mode: fetch HTML then go straight to LLM extraction
                logger.info("[%d/%d] Fetching '%s' (LLM-primary mode)", i, total, query_str)
                html = ""
                if site_mode == SiteMode.STATIC:
                    try:
                        resp = requests.get(
                            url, headers={"User-Agent": _USER_AGENT},
                            timeout=15, allow_redirects=True, proxies=_REQUESTS_PROXIES,
                        )
                        html = resp.text
                    except requests.RequestException:
                        pass
                elif persistent_context is not None:
                    html, _, _ = _fetch_on_context(persistent_context, url)
                else:
                    html, _, _ = _fetch_with_playwright(url)

                if html:
                    results = _extract_with_llm(html, query_str, max_results, url=url)
                else:
                    results = []
                was_redirected = False
                llm_count += 1
            else:
                logger.info("[%d/%d] Fetching '%s' (mode: %s)", i, total, query_str, site_mode)
                try:
                    results, was_redirected = _fetch_with_mode(
                        url, query_str, max_results, site_mode,
                        reuse_context=persistent_context,
                    )
                except Exception as e:
                    logger.warning("Unexpected error fetching '%s': %s", query_str, e)
                    results, was_redirected = [], False

            if was_redirected:
                logger.info("[%d/%d] '%s' redirected — skipping", i, total, query_str)
                all_results[query_str] = []
                empty_count += 1
                thin_count += 1
            else:
                all_results[query_str] = results
                if is_pw_mode:
                    pw_count += 1
                if not results:
                    empty_count += 1
                if len(results) < 5:
                    thin_count += 1
                logger.info("[%d/%d] '%s' → %d results", i, total, query_str, len(results))

                # Track consecutive thin results for LLM-primary promotion
                if not use_llm_primary:
                    if len(results) < 3:
                        consecutive_thin += 1
                        if consecutive_thin >= 2:
                            use_llm_primary = True
                            logger.info(
                                "Promoting to LLM-primary extraction: %d consecutive queries "
                                "with < 3 results after heuristic+validation",
                                consecutive_thin,
                            )
                    else:
                        consecutive_thin = 0

            if i < total:
                time.sleep(1.5)
    finally:
        # Clean up persistent browser resources
        if persistent_context is not None:
            try:
                persistent_context.close()
            except Exception:
                pass
        if persistent_browser is not None:
            try:
                persistent_browser.close()
            except Exception:
                pass
        if persistent_pw is not None:
            try:
                persistent_pw.stop()
            except Exception:
                pass

    _log_summary(total, pw_count, llm_count, empty_count, site_mode)

    thin_pct = thin_count / total * 100 if total else 0
    if thin_pct > 50:
        print(
            f"\nWARNING: {thin_pct:.0f}% of queries returned fewer than 5 results. "
            f"Site mode was '{site_mode}'. "
            "Consider checking the page HTML manually or adjusting extraction strategies.\n"
        )

    return all_results


def _log_summary(total: int, pw_count: int, llm_count: int, empty_count: int, mode: str) -> None:
    logger.info(
        "Fetch complete: %d queries, mode=%s, %d Playwright, %d LLM, %d empty",
        total, mode, pw_count, llm_count, empty_count,
    )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    template = sys.argv[1] if len(sys.argv) > 1 else "https://www.groupon.com/search?query={}"

    demo_queries = [
        TestQuery(category="DIRECT_MATCH", query="spa deals", rationale="Test real deal extraction"),
        TestQuery(category="BROAD_CATEGORY", query="restaurants", rationale="Broad category test"),
    ]

    print(f"Search template: {template}")
    print(f"Queries: {[q.query for q in demo_queries]}\n")

    results = fetch_all_results(template, demo_queries, max_results=15)

    for query_str, result_list in results.items():
        print(f"\n{'='*60}")
        print(f"  Query: '{query_str}' — {len(result_list)} results")
        print(f"{'='*60}")
        for r in result_list:
            print(f"  #{r.rank} {r.title[:80]}")
            if r.price:
                print(f"       price:   {r.price}")
            if r.snippet:
                print(f"       snippet: {r.snippet[:80]}")
            if r.url:
                print(f"       url:     {r.url[:80]}")
            print()
