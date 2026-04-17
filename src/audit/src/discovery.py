from __future__ import annotations

import json
import logging
import re
import sys
from urllib.parse import parse_qs, quote_plus, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from src.models import SiteContext, SiteType

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

_GENERIC_NAV_ITEMS = {
    "home", "login", "log in", "sign in", "sign up", "register",
    "cart", "basket", "bag", "checkout", "account", "my account",
    "help", "contact", "contact us", "about", "about us", "faq",
    "privacy", "privacy policy", "terms", "terms of service",
    "cookie", "cookies", "menu", "close", "back", "skip",
    "search", "subscribe", "newsletter", "wishlist", "wish list",
    "returns", "return policy", "shipping", "track order",
}

_SERVICES_KEYWORDS = {
    "book", "booking", "reservation", "reserve", "experience",
    "things to do", "activities", "activity", "spa", "appointment",
    "event", "events", "tickets", "ticket", "tours", "tour",
    "classes", "lessons", "consulting", "service", "services",
    "schedule", "hire", "rental", "rent",
}

_GOODS_KEYWORDS = {
    "add to cart", "buy now", "shipping", "free shipping", "size",
    "color", "colour", "shop by", "add to bag", "in stock",
    "out of stock", "sku", "qty", "quantity",
}


def _resolve_url(base: str, path: str) -> str:
    """Resolve a possibly-relative URL against a base URL."""
    if not path:
        return base
    return urljoin(base, path)


def _clean_text(text: str) -> str:
    """Collapse whitespace and strip a string."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_site_name(soup: BeautifulSoup, url: str) -> str:
    """Extract site name from OG tag, <title>, or domain."""
    # og:site_name
    try:
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content", "").strip():
            return og["content"].strip()
    except Exception:
        pass

    # <title> — strip after " - " or " | "
    try:
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            raw = title_tag.string.strip()
            for sep in (" - ", " | ", " — ", " – "):
                if sep in raw:
                    return raw.split(sep)[0].strip()
            return raw
    except Exception:
        pass

    # Fallback: domain
    return urlparse(url).netloc.replace("www.", "")


def _extract_meta_description(soup: BeautifulSoup) -> str:
    """Extract <meta name='description'> content."""
    try:
        tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if tag and tag.get("content", "").strip():
            return tag["content"].strip()
    except Exception:
        logger.warning("Failed to extract meta description")
    return ""


def _extract_nav_categories(soup: BeautifulSoup) -> list[str]:
    """Extract deduplicated link text from <nav> elements."""
    try:
        seen: set[str] = set()
        categories: list[str] = []
        for nav in soup.find_all("nav"):
            for a in nav.find_all("a"):
                text = _clean_text(a.get_text())
                if not text or len(text) > 80:
                    continue
                lower = text.lower()
                if lower in _GENERIC_NAV_ITEMS or lower in seen:
                    continue
                seen.add(lower)
                categories.append(text)
                if len(categories) >= 50:
                    return categories
        return categories
    except Exception:
        logger.warning("Failed to extract nav categories")
        return []


def _extract_brands(soup: BeautifulSoup) -> list[str]:
    """Extract brand names from links, JSON-LD, and brand-related elements."""
    seen_lower: set[str] = set()
    brands: list[str] = []

    def _add(name: str) -> None:
        cleaned = _clean_text(name)
        if not cleaned or len(cleaned) > 100:
            return
        low = cleaned.lower()
        if low not in seen_lower:
            seen_lower.add(low)
            brands.append(cleaned)

    # Brand links
    try:
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "/brand" in href or "/brands" in href:
                text = _clean_text(a.get_text())
                if text:
                    _add(text)
    except Exception:
        logger.warning("Failed to extract brands from links")

    # JSON-LD brand fields
    try:
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue
            _extract_brands_from_jsonld(data, _add)
    except Exception:
        logger.warning("Failed to extract brands from JSON-LD")

    # Elements with brand in class/id
    try:
        for el in soup.find_all(True):
            classes = " ".join(el.get("class", []))
            el_id = el.get("id", "") or ""
            if "brand" in classes.lower() or "brand" in el_id.lower():
                text = _clean_text(el.get_text())
                if text and len(text) < 60:
                    _add(text)
    except Exception:
        logger.warning("Failed to extract brands from class/id elements")

    return brands[:30]


def _extract_brands_from_jsonld(data: object, add_fn: callable) -> None:
    """Recursively pull brand names from JSON-LD structures."""
    if isinstance(data, dict):
        brand = data.get("brand")
        if isinstance(brand, str):
            add_fn(brand)
        elif isinstance(brand, dict):
            name = brand.get("name", "")
            if name:
                add_fn(name)
        for v in data.values():
            _extract_brands_from_jsonld(v, add_fn)
    elif isinstance(data, list):
        for item in data:
            _extract_brands_from_jsonld(item, add_fn)


def _extract_featured_items(soup: BeautifulSoup) -> list[str]:
    """Extract product/service names from JSON-LD and common product card patterns."""
    seen_lower: set[str] = set()
    items: list[str] = []

    def _add(name: str) -> None:
        cleaned = _clean_text(name)
        if not cleaned or len(cleaned) > 200 or len(cleaned) < 3:
            return
        low = cleaned.lower()
        if low not in seen_lower:
            seen_lower.add(low)
            items.append(cleaned)

    # JSON-LD Product entries
    try:
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue
            _extract_products_from_jsonld(data, _add)
    except Exception:
        logger.warning("Failed to extract featured items from JSON-LD")

    # Product card patterns
    _product_pattern = re.compile(
        r"product|item|card|deal|offer", re.I
    )
    try:
        for el in soup.find_all(True, class_=_product_pattern):
            if not isinstance(el, Tag):
                continue
            # Try heading first
            heading = el.find(re.compile(r"^h[1-6]$"))
            if heading:
                _add(heading.get_text())
                continue
            # Try first <a>
            link = el.find("a")
            if link:
                _add(link.get_text())
    except Exception:
        logger.warning("Failed to extract featured items from product cards")

    # Also check data attributes
    try:
        for el in soup.find_all(True, attrs={"data-product-name": True}):
            _add(el["data-product-name"])
        for el in soup.find_all(True, attrs={"data-item-name": True}):
            _add(el["data-item-name"])
    except Exception:
        pass

    return items[:40]


def _extract_products_from_jsonld(data: object, add_fn: callable) -> None:
    """Recursively pull product names from JSON-LD structures."""
    if isinstance(data, dict):
        type_val = data.get("@type", "")
        types = type_val if isinstance(type_val, list) else [type_val]
        if any(t in ("Product", "Service", "Offer") for t in types):
            name = data.get("name", "")
            if name:
                add_fn(name)
        for v in data.values():
            _extract_products_from_jsonld(v, add_fn)
    elif isinstance(data, list):
        for item in data:
            _extract_products_from_jsonld(item, add_fn)


# Ordered by likelihood — checked left-to-right when scanning a URL's params.
_SEARCH_PARAM_NAMES: tuple[str, ...] = (
    "q", "query", "search", "keyword", "k", "term", "s",
    "text", "searchterm", "searchQuery", "sw",
)
_PAGINATION_PARAM_NAMES: frozenset[str] = frozenset(
    {"page", "p", "offset", "start", "from", "pg", "pn", "pagenum"}
)


def _looks_like_search_term(value: str) -> bool:
    """Return True if a URL param value looks like a user-typed search query."""
    if not value or len(value) > 120:
        return False
    if not any(c.isalpha() for c in value):
        return False
    # Reject UUIDs
    if re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        value,
        re.I,
    ):
        return False
    # Reject long hex strings (database IDs)
    if re.match(r"^[0-9a-f]{24,}$", value, re.I):
        return False
    return True


def parse_search_url(url: str) -> tuple[str, str]:
    """Parse a search results page URL and return ``(template, sample_query)``.

    The template has a bare ``{}`` placeholder where the search term goes::

        >>> parse_search_url("https://www.groupon.com/search?query=spa")
        ("https://www.groupon.com/search?query={}", "spa")

    Pagination parameters (``page``, ``offset``, etc.) are stripped from the
    template so the caller can iterate pages independently.

    Args:
        url: A real search results page URL with the query visible in the URL.

    Returns:
        A 2-tuple of ``(template, sample_query)``.

    Raises:
        ValueError: If no search parameter can be identified in the URL.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    def _build_template(search_param: str) -> str:
        parts: list[str] = []
        for name, values in params.items():
            if name.lower() in _PAGINATION_PARAM_NAMES:
                continue
            if name == search_param:
                parts.append(f"{name}={{}}")
            else:
                parts.append(f"{name}={quote_plus(values[0])}")
        qs = "&".join(parts)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return f"{base}?{qs}" if qs else base

    # Pass 1: exact match against known search param names.
    for name in _SEARCH_PARAM_NAMES:
        if name in params:
            value = params[name][0]
            if value:
                return _build_template(name), value

    # Pass 2: case-insensitive match (e.g. "Query", "SEARCH").
    params_lower = {k.lower(): (k, v) for k, v in params.items()}
    for name_lower in _SEARCH_PARAM_NAMES:
        if name_lower in params_lower:
            orig_name, values = params_lower[name_lower]
            value = values[0]
            if value:
                return _build_template(orig_name), value

    # Pass 3: heuristic — any param whose value looks like a typed search query.
    for name, values in params.items():
        value = values[0]
        if _looks_like_search_term(value):
            return _build_template(name), value

    raise ValueError(
        f"Cannot identify a search parameter in URL: {url!r}. "
        "Ensure the URL is a search results page with the query visible in the URL."
    )


def discover_from_search_url(url: str) -> SiteContext:
    """Build a SiteContext from a search results page URL.

    This is the preferred entry point when the caller already has a working
    search URL (e.g. ``https://www.groupon.com/search?query=spa``).  It is more
    reliable than :func:`discover_site` because the URL template is derived
    directly from the provided URL instead of being guessed from a homepage form.

    Args:
        url: A real search results page URL with the query term visible in the URL.

    Returns:
        A fully populated :class:`SiteContext`.

    Raises:
        ValueError: If no search parameter can be identified in ``url``.
        requests.HTTPError: If the page cannot be fetched.
    """
    search_url_template, _sample_query = parse_search_url(url)

    response = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT},
        timeout=15,
        allow_redirects=True,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    html_text = soup.get_text(separator=" ")

    # Use the effective (post-redirect) URL as the canonical base.
    effective_url = response.url

    site_name = _extract_site_name(soup, effective_url)
    raw_meta_description = _extract_meta_description(soup)
    nav_categories = _extract_nav_categories(soup)
    brands = _extract_brands(soup)
    featured_items = _extract_featured_items(soup)
    site_type = _detect_site_type(
        nav_categories, featured_items, raw_meta_description, html_text
    )

    return SiteContext(
        url=effective_url,
        site_name=site_name,
        site_type=site_type,
        nav_categories=nav_categories,
        brands=brands,
        featured_items=featured_items,
        search_url_template=search_url_template,
        raw_meta_description=raw_meta_description,
    )


def _extract_search_url_template(soup: BeautifulSoup, base_url: str) -> str:
    """Find a search form and build a URL template with {} placeholder."""
    _search_input_names = {"q", "query", "search", "keyword", "k", "term", "s"}

    try:
        for form in soup.find_all("form"):
            action = form.get("action", "")
            action_lower = action.lower()

            # Check if form action looks search-related
            action_matches = any(
                kw in action_lower for kw in ("search", "find", "query")
            )

            # Find the search input
            input_name = ""
            for inp in form.find_all("input"):
                name = (inp.get("name") or "").lower()
                inp_type = (inp.get("type") or "").lower()
                if name in _search_input_names or inp_type == "search":
                    input_name = inp.get("name", "")
                    break

            if not input_name and not action_matches:
                continue
            if not input_name:
                # Default guess
                input_name = "q"

            abs_action = _resolve_url(base_url, action) if action else base_url
            # Strip existing query params from action
            parsed = urlparse(abs_action)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return f"{clean_url}?{input_name}={{}}"
    except Exception:
        logger.warning("Failed to extract search URL from forms")

    # Fallback: look for search-related links with query params
    try:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "search" in href.lower() and "=" in href:
                abs_href = _resolve_url(base_url, href)
                parsed = urlparse(abs_href)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                # Try to find which param is the query
                if parsed.query:
                    for param in parsed.query.split("&"):
                        if "=" in param:
                            key = param.split("=")[0].lower()
                            if key in _search_input_names:
                                return f"{clean_url}?{param.split('=')[0]}={{}}"
                return f"{clean_url}?q={{}}"
    except Exception:
        logger.warning("Failed to extract search URL from links")

    return ""


def _detect_site_type(
    nav_categories: list[str],
    featured_items: list[str],
    meta_description: str,
    html_text: str,
) -> SiteType:
    """Heuristically classify a site as physical goods, services, or mixed."""
    combined_nav = " ".join(nav_categories).lower()
    combined_items = " ".join(featured_items).lower()
    meta_lower = meta_description.lower()
    text_sample = html_text[:50_000].lower()

    all_text = f"{combined_nav} {combined_items} {meta_lower} {text_sample}"

    service_hits = sum(1 for kw in _SERVICES_KEYWORDS if kw in all_text)
    goods_hits = sum(1 for kw in _GOODS_KEYWORDS if kw in all_text)

    # Price patterns (currency symbols followed by numbers)
    price_count = len(re.findall(r"[$€£¥]\s?\d", text_sample))
    goods_hits += min(price_count, 5)  # Cap contribution

    if service_hits >= 3 and goods_hits <= 1:
        return SiteType.SERVICES_EXPERIENCES
    if goods_hits >= 3 and service_hits <= 1:
        return SiteType.PHYSICAL_GOODS
    if goods_hits >= 3 and service_hits >= 3:
        return SiteType.MARKETPLACE_MIXED
    if goods_hits > service_hits:
        return SiteType.PHYSICAL_GOODS
    if service_hits > goods_hits:
        return SiteType.SERVICES_EXPERIENCES
    return SiteType.MARKETPLACE_MIXED


def discover_site(url: str) -> SiteContext:
    """Fetch a site's homepage and extract structured context deterministically."""
    response = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT},
        timeout=15,
        allow_redirects=True,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    html_text = soup.get_text(separator=" ")

    site_name = _extract_site_name(soup, url)
    raw_meta_description = _extract_meta_description(soup)
    nav_categories = _extract_nav_categories(soup)
    brands = _extract_brands(soup)
    featured_items = _extract_featured_items(soup)
    search_url_template = _extract_search_url_template(soup, url)
    site_type = _detect_site_type(
        nav_categories, featured_items, raw_meta_description, html_text
    )

    return SiteContext(
        url=url,
        site_name=site_name,
        site_type=site_type,
        nav_categories=nav_categories,
        brands=brands,
        featured_items=featured_items,
        search_url_template=search_url_template,
        raw_meta_description=raw_meta_description,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    target = sys.argv[1] if len(sys.argv) > 1 else "https://www.amazon.com"
    ctx = discover_site(target)
    print(f"url:                  {ctx.url}")
    print(f"site_name:            {ctx.site_name}")
    print(f"site_type:            {ctx.site_type}")
    print(f"raw_meta_description: {ctx.raw_meta_description[:120]}...")
    print(f"search_url_template:  {ctx.search_url_template}")
    print(f"nav_categories ({len(ctx.nav_categories)}):")
    for c in ctx.nav_categories[:15]:
        print(f"  - {c}")
    if len(ctx.nav_categories) > 15:
        print(f"  ... and {len(ctx.nav_categories) - 15} more")
    print(f"brands ({len(ctx.brands)}):")
    for b in ctx.brands[:10]:
        print(f"  - {b}")
    if len(ctx.brands) > 10:
        print(f"  ... and {len(ctx.brands) - 10} more")
    print(f"featured_items ({len(ctx.featured_items)}):")
    for item in ctx.featured_items[:10]:
        print(f"  - {item}")
    if len(ctx.featured_items) > 10:
        print(f"  ... and {len(ctx.featured_items) - 10} more")
