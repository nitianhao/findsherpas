from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel

from src.llm_compat import structured_call
from src.models import QueryCategory, SiteContext, SiteType, TestQuery
from src.fetcher import _fetch_with_playwright, _decode_response

logger = logging.getLogger(__name__)

# An LLM pass refines the rule-based discovery fields (site_type / brands / categories).
# Overridable so a deeper run (e.g. a case-study audit) can step the tier up without
# forking this module; unset env = the default audit behaves exactly as before.
# See docs/CASE_STUDY_PLAYBOOK.md.
_MODEL = os.environ.get("AUDIT_MODEL_DISCOVERY", "claude-haiku-4-5-20251001")

# Big enough for ~60 nav labels + 40 brands + 40 items echoed back; the old 1500 truncated
# mid-JSON on manufactum / bächli / bergzeit and fell back silently.
_REFINE_MAX_TOKENS = 4000

# Catalog sampling: how many seed searches and how many titles to keep.
_MIN_SEEDS = 5
_MAX_SEEDS = 8
_CATALOG_SAMPLE_SIZE = 150

# provenance key holding JSON-LD sku/mpn/gtin codes (JSON list of {code, kind, title}).
# SiteContext has no dedicated field; query_generator reads this key for SKU_MODEL_NUMBER.
CATALOG_CODES_KEY = "catalog_codes"

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

# Nav labels that make poor catalog-sampling seeds (promotional / editorial / chrome).
_NON_SEED_NAV = {
    "sale", "new", "new in", "new arrivals", "neu", "neuheiten", "nyheter", "nyheder",
    "nouveautés", "nouveau", "novità", "nieuw", "outlet", "angebote", "offers", "deals",
    "erbjudanden", "tilbud", "brands", "marken", "märken", "mærker", "marques", "merken",
    "gift card", "gift cards", "gutschein", "gutscheine", "presentkort", "gavekort",
    "journal", "blog", "inspiration", "magazine", "magazin", "stores", "filialen",
    "butiker", "services", "service", "beratung", "kundenservice", "kundservice",
    "startseite", "all", "shop all", "alle", "alla", "view all", "see all",
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

# Whole-word matching: plain substring counting hit "book" in "facebook", "spa" in "space",
# "rent" in "current".
_SERVICES_PATTERNS = [re.compile(rf"(?<!\w){re.escape(k)}(?!\w)") for k in _SERVICES_KEYWORDS]
_GOODS_PATTERNS = [re.compile(rf"(?<!\w){re.escape(k)}(?!\w)") for k in _GOODS_KEYWORDS]

# A price: currency symbol/code next to a number, either side.
_PRICE_SIGNAL_RE = re.compile(
    r"[$€£¥]\s?\d"
    r"|\d[\d.,]*\s?(?:€|kr\b|zł|Kč|CHF\b|SEK\b|DKK\b|NOK\b|PLN\b|CZK\b)"
    r"|(?<!\w)(?:kr|zł|Kč|CHF|SEK|DKK|NOK)\.?\s?\d",
    re.I,
)


def _strict_llm() -> bool:
    """AUDIT_STRICT_LLM (default on): raise instead of falling back when an LLM step fails."""
    return os.environ.get("AUDIT_STRICT_LLM", "1").strip().lower() not in ("0", "false", "no", "off", "")


def _norm(text: str) -> str:
    """Comparison key: NFKC, casefolded, whitespace collapsed."""
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def _prompt_sha(system: str, user: str) -> str:
    return hashlib.sha256(f"{system}\n\n{user}".encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve_url(base: str, path: str) -> str:
    """Resolve a possibly-relative URL against a base URL."""
    if not path:
        return base
    return urljoin(base, path)


def _clean_text(text: str) -> str:
    """Collapse whitespace and strip a string."""
    return re.sub(r"\s+", " ", text).strip()


def _visible_text(soup: BeautifulSoup) -> str:
    """Page text without <script>/<style> payloads (JSON blobs skew language and keyword counts)."""
    parts = []
    for node in soup.find_all(string=True):
        parent = getattr(node, "parent", None)
        if parent is not None and parent.name in ("script", "style", "noscript", "template"):
            continue
        text = str(node).strip()
        if text:
            parts.append(text)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Language / locale
# ---------------------------------------------------------------------------

# Map of BCP-47 language codes / prefixes to human-readable language names for query generation
_LANG_CODE_MAP: dict[str, str] = {
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "nb": "Norwegian",
    "nn": "Norwegian",
    "fi": "Finnish",
    "de": "German",
    "nl": "Dutch",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "ro": "Romanian",
    "el": "Greek",
    "tr": "Turkish",
    "ru": "Russian",
    "uk": "Ukrainian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "he": "Hebrew",
    "en": "English",
    "is": "Icelandic",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sl": "Slovenian",
    "sr": "Serbian",
}

# Single-language country TLDs → (language, region). Longest suffix first.
_CCTLD_LANG: list[tuple[str, str, str]] = [
    (".co.uk", "en", "GB"), (".com.au", "en", "AU"), (".co.nz", "en", "NZ"),
    (".com.br", "pt", "BR"), (".com.mx", "es", "MX"),
    (".uk", "en", "GB"), (".ie", "en", "IE"), (".au", "en", "AU"), (".nz", "en", "NZ"),
    (".se", "sv", "SE"), (".dk", "da", "DK"), (".no", "nb", "NO"), (".fi", "fi", "FI"),
    (".de", "de", "DE"), (".at", "de", "AT"), (".fr", "fr", "FR"), (".nl", "nl", "NL"),
    (".es", "es", "ES"), (".mx", "es", "MX"), (".it", "it", "IT"), (".pt", "pt", "PT"),
    (".br", "pt", "BR"), (".pl", "pl", "PL"), (".cz", "cs", "CZ"), (".sk", "sk", "SK"),
    (".hu", "hu", "HU"), (".ro", "ro", "RO"), (".ru", "ru", "RU"), (".tr", "tr", "TR"),
    (".jp", "ja", "JP"), (".kr", "ko", "KR"), (".cn", "zh", "CN"),
]

# Multilingual country TLDs → (region, candidate languages, most common first). The page
# text decides between the candidates; the TLD alone never picks one.
_MULTILINGUAL_CCTLD: dict[str, tuple[str, list[str]]] = {
    ".ch": ("CH", ["de", "fr", "it"]),
    ".be": ("BE", ["nl", "fr", "de"]),
    ".ca": ("CA", ["en", "fr"]),
    ".lu": ("LU", ["fr", "de"]),
}

# Function words per language. Only words unique to one list count (computed below), so the
# Nordic languages separate on "och/af/av" etc. rather than on shared letters like ä/ö —
# the old character heuristic read German pages (ä/ö) as Swedish.
_STOPWORDS: dict[str, set[str]] = {
    "en": {"the", "and", "with", "for", "you", "your", "our", "this", "from", "shop", "all", "new"},
    "de": {"und", "der", "die", "das", "mit", "für", "nicht", "ein", "eine", "ist", "auf", "von", "sie", "ihre", "jetzt", "zum", "zur"},
    "fr": {"et", "le", "la", "les", "des", "pour", "avec", "une", "est", "sur", "vous", "nos", "du", "au"},
    "it": {"il", "di", "che", "per", "con", "una", "sono", "gli", "della", "del", "nostri"},
    "es": {"el", "los", "las", "para", "con", "una", "del", "por", "que", "nuestros", "envío"},
    "nl": {"het", "een", "van", "voor", "met", "niet", "en", "zijn", "onze", "je", "bij"},
    "sv": {"och", "att", "för", "med", "inte", "som", "på", "är", "till", "av", "vår", "våra", "alla"},
    "da": {"og", "at", "for", "med", "ikke", "som", "på", "er", "til", "af", "vores", "alle"},
    "nb": {"og", "at", "for", "med", "ikke", "som", "på", "er", "til", "av", "våre", "alle"},
    "pl": {"w", "na", "z", "do", "nie", "się", "jest", "oraz", "dla"},
    "cs": {"v", "na", "s", "do", "je", "se", "pro", "jsou", "nebo"},
    "fi": {"ja", "on", "ei", "että", "kuin", "myös", "tai"},
}
_word_langs: dict[str, set[str]] = {}
for _lang, _words in _STOPWORDS.items():
    for _w in _words:
        _word_langs.setdefault(_w, set()).add(_lang)
_UNIQUE_STOPWORDS: dict[str, str] = {w: next(iter(ls)) for w, ls in _word_langs.items() if len(ls) == 1}


def _parse_lang_tag(tag: str) -> tuple[str, str]:
    """'en-GB' / 'en_gb' / 'sv' -> ('en', 'GB') / ('sv', '')."""
    parts = re.split(r"[-_]", (tag or "").strip())
    code = parts[0].lower() if parts and parts[0] else ""
    region = ""
    for p in parts[1:]:
        if len(p) == 2 and p.isalpha():
            region = p.upper()
            break
    return code, region


def _url_key(url: str) -> str:
    """netloc+path, lowercased, no trailing slash — for comparing canonical/hreflang hrefs."""
    p = urlparse(url)
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/').lower()}"


def _cctld_info(url: str) -> tuple[str, str, list[str]]:
    """Return (language, region, candidates) from the host TLD; candidates set for multilingual TLDs."""
    host = (urlparse(url).hostname or "").lower()
    for suffix, (region, candidates) in _MULTILINGUAL_CCTLD.items():
        if host.endswith(suffix):
            return "", region, candidates
    for suffix, lang, region in _CCTLD_LANG:
        if host.endswith(suffix):
            return lang, region, []
    return "", "", []


def _stopword_scores(text: str) -> Counter:
    scores: Counter = Counter()
    for word in re.findall(r"\w+", (text or "").casefold()[:200_000]):
        lang = _UNIQUE_STOPWORDS.get(word)
        if lang:
            scores[lang] += 1
    return scores


def _detect_language(soup: BeautifulSoup, url: str, text: str | None = None) -> tuple[str, str, str]:
    """Detect the storefront language.

    Returns ``(language_name, bcp47_locale, source)``. Order of trust:

    1. ``<html lang>`` — including ``en``. Sites that genuinely mis-declare are rarer than
       sites the old "skip en" rule broke (an en-GB page with a de-DE alternate read as German).
    2. ``og:locale``.
    3. The hreflang entry whose href IS this page (canonical or current URL). Alternates that
       point elsewhere describe other storefronts, not this one.
    4. A locale-looking first path segment (``/sv-se/``, ``/de/``).
    5. A single-language country TLD. Multilingual TLDs (.ch/.be/.ca/.lu) only narrow the
       candidates; the page's function words pick among them.
    6. Function-word counts over the visible text (needs a clear winner).
    7. English.
    """
    text = text if text is not None else _visible_text(soup)
    tld_lang, tld_region, tld_candidates = _cctld_info(url)

    def _result(code: str, region: str, source: str) -> tuple[str, str, str]:
        if not region and code == tld_lang:
            region = tld_region
        if not region and tld_candidates and code in tld_candidates:
            region = tld_region
        locale = f"{code}-{region}" if region else code
        return _LANG_CODE_MAP.get(code, "English"), locale, source

    og_code, og_region = "", ""
    og = soup.find("meta", property="og:locale")
    if og:
        og_code, og_region = _parse_lang_tag(og.get("content") or "")

    # 1. <html lang>
    html_tag = soup.find("html")
    if html_tag is not None:
        code, region = _parse_lang_tag(html_tag.get("lang") or html_tag.get("xml:lang") or "")
        if code in _LANG_CODE_MAP:
            if not region and og_code == code:
                region = og_region
            return _result(code, region, "html-lang")

    # 2. og:locale
    if og_code in _LANG_CODE_MAP:
        return _result(og_code, og_region, "og-locale")

    # 3. hreflang pointing at this page
    self_keys = {_url_key(url)}
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        self_keys.add(_url_key(urljoin(url, canonical["href"])))
    for link in soup.find_all("link", rel="alternate"):
        hl = (link.get("hreflang") or "").strip()
        href = link.get("href") or ""
        if not hl or hl.lower() == "x-default" or not href:
            continue
        if _url_key(urljoin(url, href)) in self_keys:
            code, region = _parse_lang_tag(hl)
            if code in _LANG_CODE_MAP:
                return _result(code, region, "hreflang-self")

    # 4. First path segment like /sv-se/ or /de/
    segments = [s for s in urlparse(url).path.split("/") if s]
    if segments and re.fullmatch(r"[a-zA-Z]{2}(?:[-_][a-zA-Z]{2})?", segments[0]):
        code, region = _parse_lang_tag(segments[0])
        if code in _LANG_CODE_MAP:
            return _result(code, region, "url-path")

    scores = _stopword_scores(text)

    # 5. Country TLD
    if tld_lang:
        return _result(tld_lang, tld_region, "cctld")
    if tld_candidates:
        best = max(tld_candidates, key=lambda c: (scores.get(c, 0), -tld_candidates.index(c)))
        return _result(best, tld_region, "cctld+text")

    # 6. Function words
    if scores:
        ranked = scores.most_common(2)
        top_lang, top = ranked[0]
        runner = ranked[1][1] if len(ranked) > 1 else 0
        if top >= 8 and top >= 1.5 * runner:
            return _result(top_lang, "", "text")

    return "English", "en", "default"


def _detect_primary_language(soup: BeautifulSoup, url: str) -> str:
    """Backward-compatible wrapper: the human-readable language name only."""
    return _detect_language(soup, url)[0]


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

_CODE_RE = re.compile(r"^[A-Z]{3}$")

# (regex, currency or resolver key). "kr" and "$" depend on the market.
_CURRENCY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"€\s?\d|\d[\d.,]*\s?€|\bEUR\b"), "EUR"),
    (re.compile(r"£\s?\d|\bGBP\b"), "GBP"),
    (re.compile(r"(?<![A-Za-z])zł|\bPLN\b"), "PLN"),
    (re.compile(r"Kč|\bCZK\b"), "CZK"),
    (re.compile(r"\bCHF\b|\bFr\.\s?\d"), "CHF"),
    (re.compile(r"\bSEK\b"), "SEK"),
    (re.compile(r"\bDKK\b"), "DKK"),
    (re.compile(r"\bNOK\b"), "NOK"),
    (re.compile(r"\bUSD\b"), "USD"),
    (re.compile(r"¥\s?\d|\bJPY\b"), "JPY"),
    (re.compile(r"\d[\d.,]*\s?kr\b|(?<![A-Za-z])kr\.?\s?\d", re.I), "KR"),
    (re.compile(r"\$\s?\d"), "DOLLAR"),
]

_KR_BY_REGION = {"SE": "SEK", "DK": "DKK", "NO": "NOK", "IS": "ISK"}
_KR_BY_LANG = {"sv": "SEK", "da": "DKK", "nb": "NOK", "nn": "NOK", "no": "NOK", "is": "ISK"}
_DOLLAR_BY_REGION = {"US": "USD", "CA": "CAD", "AU": "AUD", "NZ": "NZD", "MX": "MXN", "SG": "SGD", "HK": "HKD"}


def _jsonld_blocks(soup: BeautifulSoup) -> list:
    blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            blocks.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue
    return blocks


def _collect_key(data: object, key: str, out: list) -> None:
    if isinstance(data, dict):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
        for v in data.values():
            _collect_key(v, key, out)
    elif isinstance(data, list):
        for item in data:
            _collect_key(item, key, out)


def _currency_from_text(text: str, locale: str) -> str:
    """Most frequent currency signalled in price-like text; '' when unknown."""
    code, region = _parse_lang_tag(locale)
    counts: Counter = Counter()
    for pattern, cur in _CURRENCY_PATTERNS:
        n = len(pattern.findall(text or ""))
        if not n:
            continue
        if cur == "KR":
            cur = _KR_BY_REGION.get(region) or _KR_BY_LANG.get(code, "")
        elif cur == "DOLLAR":
            cur = _DOLLAR_BY_REGION.get(region, "USD")
        if cur:
            counts[cur] += n
    return counts.most_common(1)[0][0] if counts else ""


def _detect_currency(soup: BeautifulSoup, text: str, locale: str) -> tuple[str, str]:
    """Return ``(ISO-4217 code, source)``: JSON-LD priceCurrency, price meta tags, then price text."""
    found: list[str] = []
    for block in _jsonld_blocks(soup):
        _collect_key(block, "priceCurrency", found)
    found = [c.upper() for c in found if _CODE_RE.match(c.upper())]
    if found:
        return Counter(found).most_common(1)[0][0], "jsonld"
    for attrs in ({"itemprop": "priceCurrency"}, {"property": "product:price:currency"},
                  {"property": "og:price:currency"}):
        tag = soup.find(attrs=attrs)
        if tag is not None:
            val = (tag.get("content") or tag.get_text() or "").strip().upper()
            if _CODE_RE.match(val):
                return val, "meta"
    cur = _currency_from_text(text, locale)
    return (cur, "price-text") if cur else ("", "unknown")


# Second-level labels that are not the brand (e.g. example.co.uk, brand.com.au).
_PUBLIC_SECOND_LEVELS = {"co", "com", "org", "net", "ac", "gov", "edu"}

# Title segment separators, ordered longest-first so multi-char dashes win.
_TITLE_SEPARATORS = (" — ", " – ", " - ", " | ", " · ")


def _domain_brand(url: str) -> str:
    """Derive a brand name from the domain (e.g. www.miinto.dk -> 'Miinto')."""
    netloc = urlparse(url).netloc.split(":")[0]
    labels = [p for p in netloc.split(".") if p and p.lower() != "www"]
    if not labels:
        return ""
    if len(labels) >= 3 and labels[-2].lower() in _PUBLIC_SECOND_LEVELS:
        sld = labels[-3]
    elif len(labels) >= 2:
        sld = labels[-2]
    else:
        sld = labels[0]
    return sld.capitalize()


def _extract_site_name(soup: BeautifulSoup, url: str) -> str:
    """Extract the brand/site name, strongly preferring the brand over a category.

    Priority: og:site_name (if not a nav category) -> domain-derived brand ->
    last <title> segment (if not a nav category) -> bare domain. The domain is
    preferred over <title> parsing because page titles often lead with a category
    (e.g. a Danish marketplace search page titled 'Tøj | Miinto'), which previously
    leaked the category into the brand slot.
    """
    nav_categories = {c.strip().lower() for c in _extract_nav_categories(soup)}

    def _is_categoryish(name: str) -> bool:
        return name.strip().lower() in nav_categories

    # 1. og:site_name — most reliable when present and not a category label
    try:
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content", "").strip():
            cand = og["content"].strip()
            if not _is_categoryish(cand):
                return cand
    except Exception:
        pass

    # 2. Domain-derived brand — deterministic, correct for the vast majority of sites
    domain_brand = _domain_brand(url)
    if domain_brand:
        return domain_brand

    # 3. <title> — take the LAST segment (brand usually trails), if not a category
    try:
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            raw = title_tag.string.strip()
            cand = raw
            for sep in _TITLE_SEPARATORS:
                if sep in raw:
                    cand = raw.split(sep)[-1].strip()
                    break
            if cand and not _is_categoryish(cand):
                return cand
    except Exception:
        pass

    # 4. Fallback: bare domain
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


_CODE_KEYS = ("sku", "mpn", "gtin13", "gtin12", "gtin14", "gtin8", "gtin")


def _extract_products_from_jsonld(
    data: object,
    add_fn: callable,
    code_fn: Optional[Callable[[str, str, str], None]] = None,
) -> None:
    """Recursively pull product names (and, via ``code_fn``, sku/mpn/gtin codes) from JSON-LD.

    ``code_fn(code, kind, title)`` receives every identifier found on a Product/Offer node, so
    SKU_MODEL_NUMBER queries can use codes the site actually prints instead of invented ones.
    """
    if isinstance(data, dict):
        type_val = data.get("@type", "")
        types = type_val if isinstance(type_val, list) else [type_val]
        if any(t in ("Product", "ProductGroup", "Service", "Offer") for t in types):
            name = data.get("name", "")
            if isinstance(name, str) and name:
                add_fn(name)
            if code_fn is not None:
                for key in _CODE_KEYS:
                    val = data.get(key)
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        val = str(int(val))
                    if isinstance(val, str) and val.strip():
                        code_fn(val.strip(), key, name if isinstance(name, str) else "")
        for v in data.values():
            _extract_products_from_jsonld(v, add_fn, code_fn)
    elif isinstance(data, list):
        for item in data:
            _extract_products_from_jsonld(item, add_fn, code_fn)


def _extract_jsonld_catalog(soup: BeautifulSoup) -> tuple[list[str], list[dict]]:
    """Product titles and identifier codes declared in the page's JSON-LD."""
    titles: list[str] = []
    seen_titles: set[str] = set()
    codes: list[dict] = []
    seen_codes: set[str] = set()

    def _add_title(name: str) -> None:
        cleaned = _clean_text(name)
        if 3 <= len(cleaned) <= 200 and _norm(cleaned) not in seen_titles:
            seen_titles.add(_norm(cleaned))
            titles.append(cleaned)

    def _add_code(code: str, kind: str, title: str) -> None:
        if not (3 <= len(code) <= 40) or code.casefold() in seen_codes:
            return
        seen_codes.add(code.casefold())
        codes.append({"code": code, "kind": kind, "title": _clean_text(title or "")})

    for block in _jsonld_blocks(soup):
        _extract_products_from_jsonld(block, _add_title, _add_code)
    return titles, codes


# ---------------------------------------------------------------------------
# Search URL parsing
# ---------------------------------------------------------------------------

# Ordered by likelihood — checked left-to-right when scanning a URL's params.
_SEARCH_PARAM_NAMES: tuple[str, ...] = (
    "q", "query", "search", "keyword", "k", "term", "s",
    "text", "searchterm", "searchQuery", "sw",
)
_PAGINATION_PARAM_NAMES: frozenset[str] = frozenset(
    {"page", "p", "offset", "start", "from", "pg", "pn", "pagenum"}
)
# Never the search term, even when the value looks like words (pass 3 guessing).
_NON_SEARCH_PARAM_NAMES: frozenset[str] = frozenset(
    {"lang", "language", "locale", "sort", "sortby", "sort_by", "order", "orderby", "currency",
     "page", "country", "region", "ref", "view", "layout", "gclid", "fbclid", "msclkid"}
)
# Tracking params dropped from the template entirely.
_TRACKING_PARAM_RE = re.compile(r"^(utm_.*|gclid|fbclid|msclkid|_ga|mc_cid|mc_eid)$", re.I)
# Path-based search: /search/<term>, /s/<term>, /suche/<term>, ...
_PATH_SEARCH_SEGMENTS: frozenset[str] = frozenset(
    {"search", "s", "suche", "sok", "sök", "soeg", "søg", "recherche", "buscar", "busca",
     "zoeken", "szukaj", "hledat", "hledani", "cerca", "ricerca", "haku", "sog"}
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

    Pagination parameters (``page``, ``offset``, etc.) and tracking parameters (``utm_*``,
    ``gclid``…) are stripped from the template. A known search parameter is accepted even
    with an empty value (``?utm_source=news&q=`` → ``q``, sample ``""``). ``lang``, ``sort``,
    ``currency`` and similar are never guessed as the search term. Path-based search
    (``/search/<term>``) is supported.

    Raises:
        ValueError: If no search parameter can be identified in the URL.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    def _build_template(search_param: str) -> str:
        parts: list[str] = []
        for name, values in params.items():
            if name.lower() in _PAGINATION_PARAM_NAMES or _TRACKING_PARAM_RE.match(name):
                continue
            if name == search_param:
                parts.append(f"{name}={{}}")
            else:
                parts.append(f"{name}={quote_plus(values[0])}")
        qs = "&".join(parts)
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return f"{base}?{qs}" if qs else base

    params_lower = {k.lower(): k for k in params}

    # Pass 1: known search param names with a value (exact, then case-insensitive).
    for name in _SEARCH_PARAM_NAMES:
        orig = name if name in params else params_lower.get(name.lower())
        if orig and params[orig][0]:
            return _build_template(orig), params[orig][0]

    # Pass 2: known names with an empty value (a search page reached with a blank box).
    for name in _SEARCH_PARAM_NAMES:
        orig = name if name in params else params_lower.get(name.lower())
        if orig:
            return _build_template(orig), ""

    # Pass 3: heuristic — any non-excluded param whose value looks like a typed query.
    for name, values in params.items():
        low = name.lower()
        if (low in _NON_SEARCH_PARAM_NAMES or low in _PAGINATION_PARAM_NAMES
                or _TRACKING_PARAM_RE.match(name)):
            continue
        if _looks_like_search_term(values[0]):
            return _build_template(name), values[0]

    # Pass 4: path-based search — /search/<term>
    segments = parsed.path.split("/")
    for i, seg in enumerate(segments[:-1]):
        if seg.lower() in _PATH_SEARCH_SEGMENTS and segments[i + 1]:
            from urllib.parse import unquote_plus

            term = unquote_plus(segments[i + 1])
            if not _looks_like_search_term(term):
                continue
            new_path = "/".join(segments[: i + 1] + ["{}"] + segments[i + 2:])
            kept = [f"{n}={quote_plus(v[0])}" for n, v in params.items()
                    if n.lower() not in _PAGINATION_PARAM_NAMES and not _TRACKING_PARAM_RE.match(n)]
            base = f"{parsed.scheme}://{parsed.netloc}{new_path}"
            return (f"{base}?{'&'.join(kept)}" if kept else base), term

    raise ValueError(
        f"Cannot identify a search parameter in URL: {url!r}. "
        "Ensure the URL is a search results page with the query visible in the URL."
    )


# ---------------------------------------------------------------------------
# Page fetching
# ---------------------------------------------------------------------------

# Strong bot-wall markers: checked anywhere near the top of the page.
_CHALLENGE_STRONG = (
    "just a moment", "checking your browser", "cf-chl", "/cdn-cgi/challenge-platform",
    "ddos protection by cloudflare", "enable javascript and cookies to continue",
    "incapsula incident", "_incapsula_resource", "pardon our interruption",
    "px-captcha", "verify you are human", "attention required",
)
# Weak markers: also present on normal pages (newsletter reCAPTCHA, DataDome tags), so they
# only count when the page has almost no visible text.
_CHALLENGE_WEAK = ("captcha", "access denied", "datadome", "are you a robot", "ray id", "request unsuccessful")
_NEAR_EMPTY_CHARS = 200


def _page_problem(html: str) -> str | None:
    """Why a statically fetched page is unusable for discovery (None = fine)."""
    if not html or not html.strip():
        return "empty response"
    sample = html[:20_000].lower()
    for marker in _CHALLENGE_STRONG:
        if marker in sample:
            return f"bot challenge ({marker!r})"
    text_len = len(_visible_text(BeautifulSoup(html, "html.parser")))
    if text_len < 600:
        for marker in _CHALLENGE_WEAK:
            if marker in sample:
                return f"bot challenge ({marker!r})"
    if text_len < _NEAR_EMPTY_CHARS:
        return f"near-empty page ({text_len} chars of text)"
    return None


def _fetch_html(url: str) -> tuple[str, str]:
    """Fetch ``url`` statically; fall back to Playwright on any request error, a bot
    challenge, or a near-empty (JS-rendered) page. Returns ``(html, final_url)``.

    Raises the original request error (or RuntimeError) when Playwright also gets nothing.
    """
    error: Exception | None = None
    static_html = ""
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=15, allow_redirects=True)
        response.raise_for_status()
        static_html = _decode_response(response)
        problem = _page_problem(static_html)
        if problem is None:
            return static_html, response.url
        reason = problem
    except requests.RequestException as e:
        error = e
        reason = f"{type(e).__name__}: {e}"

    logger.warning("Static discovery fetch unusable for %s (%s); trying Playwright", url, reason)
    pw_html, _browser, final_url = _fetch_with_playwright(url, quick_probe=True)
    if pw_html:
        problem = _page_problem(pw_html)
        if problem:
            logger.warning("Playwright page for %s still looks wrong: %s", url, problem)
        return pw_html, final_url or url
    if error is not None:
        raise error
    raise RuntimeError(f"Could not fetch a usable page for {url}: {reason}")


# ---------------------------------------------------------------------------
# Catalog sampling
# ---------------------------------------------------------------------------

# fetch_fn(queries, search_url_template) -> {query: [title | SearchResult-like]}
SeedFetchFn = Callable[[list[str], str], dict]


def _default_seed_fetch(queries: list[str], search_url_template: str) -> dict:
    """Run seed searches through the fetcher's public API.

    Prefers ``fetch_all_outcomes`` (only trusted outcomes are used — a bot wall or an
    unverified empty page is not catalog evidence) and falls back to ``fetch_all_results``.
    """
    from src import fetcher

    fetch_outcomes = getattr(fetcher, "fetch_all_outcomes", None)
    if fetch_outcomes is not None:
        # light: one attempt per seed, no LLM extraction — sampling must stay cheap and fast.
        outcomes = fetch_outcomes(queries=queries, search_url_template=search_url_template,
                                  max_results=20, light=True)
        out: dict = {}
        for q, outcome in (outcomes or {}).items():
            if getattr(outcome, "trusted", True):
                out[q] = list(getattr(outcome, "results", []) or [])
            else:
                logger.info("Seed search '%s' not trusted (%s); skipped", q, getattr(outcome, "status", "?"))
        return out
    legacy = fetcher.fetch_all_results(
        search_url_template,
        [TestQuery(category=QueryCategory.CATEGORY_MAPPING, query=q, rationale="catalog sample seed") for q in queries],
        max_results=20,
    )
    return dict(legacy or {})


def _seed_terms(nav_categories: list[str], brands: list[str], seed_query: str = "") -> list[str]:
    """5-8 seed searches from the top nav departments (brands top up a thin nav)."""
    seeds: list[str] = []
    seen = {_norm(seed_query)} if seed_query else set()

    def _ok(label: str) -> bool:
        low = _norm(label)
        if not low or low in seen or low in _NON_SEED_NAV or low in _GENERIC_NAV_ITEMS:
            return False
        if len(low) > 40 or len(low.split()) > 4 or any(ch.isdigit() for ch in low):
            return False
        return any(ch.isalpha() for ch in low)

    for label in nav_categories:
        if len(seeds) >= _MAX_SEEDS:
            break
        if _ok(label):
            seen.add(_norm(label))
            seeds.append(_clean_text(label))
    for brand in brands:
        if len(seeds) >= _MIN_SEEDS:
            break
        if _ok(brand):
            seen.add(_norm(brand))
            seeds.append(_clean_text(brand))
    return seeds


def _merge_titles(sources: list[list[str]], limit: int) -> list[str]:
    """Round-robin merge with NFKC/casefold dedupe, so no single source (e.g. the seed
    query's own results page) dominates the sample."""
    out: list[str] = []
    seen: set[str] = set()
    queues = [list(s) for s in sources if s]
    while queues and len(out) < limit:
        nxt = []
        for q in queues:
            while q:
                title = _clean_text(str(q.pop(0)))
                key = _norm(title)
                if 3 <= len(title) <= 200 and key not in seen:
                    seen.add(key)
                    out.append(title)
                    break
            if q:
                nxt.append(q)
            if len(out) >= limit:
                break
        queues = nxt
    return out


def build_catalog_sample(
    *,
    search_url_template: str,
    nav_categories: list[str],
    brands: list[str],
    page_titles: list[str],
    homepage_titles: list[str] | None = None,
    seed_query: str = "",
    fetch_fn: SeedFetchFn | None = None,
    limit: int = _CATALOG_SAMPLE_SIZE,
) -> tuple[list[str], list[str], str]:
    """Collect ~150 real product titles from the homepage plus 5-8 seed searches.

    Seed results come back through ``fetch_fn`` (default: the fetcher's public API; tests
    stub it). Returns ``(titles, prices, provenance_note)``.
    """
    seeds = _seed_terms(nav_categories, brands, seed_query) if search_url_template else []
    per_seed: list[list[str]] = []
    prices: list[str] = []
    note_bits = []
    if seeds:
        try:
            results = (fetch_fn or _default_seed_fetch)(seeds, search_url_template) or {}
        except Exception as e:  # sampling is best-effort; the gap is recorded, not hidden
            logger.warning("Catalog sampling seed searches failed: %s", e)
            results = {}
            note_bits.append(f"seed searches failed: {type(e).__name__}: {e}")
        hit = 0
        for seed in seeds:
            titles = []
            for item in results.get(seed, []) or []:
                title = item if isinstance(item, str) else getattr(item, "title", "")
                if title:
                    titles.append(title)
                price = None if isinstance(item, str) else getattr(item, "price", None)
                if price:
                    prices.append(str(price))
            if titles:
                hit += 1
            per_seed.append(titles)
        note_bits.insert(0, f"{hit}/{len(seeds)} seed searches returned titles ({', '.join(seeds)})")
    else:
        note_bits.append("no usable seed terms")
    sources = [homepage_titles or [], *per_seed, page_titles]
    titles = _merge_titles(sources, limit)
    note = f"{len(titles)} titles; " + "; ".join(note_bits)
    return titles, prices, note


# ---------------------------------------------------------------------------
# Site-type heuristic
# ---------------------------------------------------------------------------


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

    service_hits = sum(1 for p in _SERVICES_PATTERNS if p.search(all_text))
    goods_hits = sum(1 for p in _GOODS_PATTERNS if p.search(all_text))

    # Price patterns (currency symbol/code next to a number)
    price_count = len(_PRICE_SIGNAL_RE.findall(text_sample))
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


# ---------------------------------------------------------------------------
# LLM refinement
# ---------------------------------------------------------------------------


class RefinedProfile(BaseModel):
    """Structured output of the refinement pass. Evidence first, verdict after."""

    site_type_evidence: str
    site_type: SiteType
    brands: list[str]
    nav_categories: list[str]
    featured_items: list[str]


_REFINE_SYSTEM = """You clean up the auto-detected profile of an ecommerce/services website for a search-quality audit. The rule-based scraper is noisy: it mixes brand names into navigation, fills "featured items" with nav/legal links, and misclassifies the site type.

Return a corrected profile.

Rules:
- site_type_evidence: one or two sentences naming the concrete signals (departments, prices, booking language) behind your site_type.
- site_type: PHYSICAL_GOODS = sells its own catalog of physical products. MARKETPLACE_MIXED = broad multi-department retailer and/or carries many third-party brands. SERVICES_EXPERIENCES = the core offering is bookings/appointments/experiences/tickets. A goods retailer that ALSO runs cafés, visitor sites, or "experiences" is still a goods retailer — do NOT classify it as SERVICES_EXPERIENCES for that reason.
- brands: proper-noun product labels sold on the site (third-party brands and the site's own house brand). Pull these OUT of the navigation list. Empty list if none are identifiable.
- nav_categories: real product departments/categories only. Remove brand names (they go in brands), and remove generic chrome ("Shop All", "Go to ...") and filter values (sizes, colours). "New In" is fine if it's a real department.
- featured_items: specific PRODUCT titles only, copied exactly as written. Drop nav links, legal/footer links (Privacy Policy, Terms, Cookie Policy), result-count strings and account/cart items. Empty list if no real products are identifiable.
- Copy names exactly as they appear in the data. Do not invent, translate or complete anything: every brand, category and item you return must appear in the data you were given."""


def _refine_user_prompt(
    *, site_name: str, meta_description: str, nav_categories: list[str], brands: list[str],
    featured_items: list[str], html_text: str, heuristic_site_type: SiteType,
) -> str:
    nav_block = ", ".join(nav_categories[:60]) or "(none)"
    brands_block = ", ".join(brands[:40]) or "(none)"
    items_block = " | ".join(featured_items[:40]) or "(none)"
    text_sample = re.sub(r"\s+", " ", html_text)[:6000]
    return f"""## What the scraper found
- Site name: {site_name or "(unknown)"}
- Meta description: {meta_description or "(none)"}
- Heuristic site_type (often wrong): {heuristic_site_type.value}
- Navigation categories: {nav_block}
- Brands: {brands_block}
- Featured items (separated by " | "): {items_block}

## Page text sample
{text_sample}"""


def _keep_grounded(values: list[str], pools: list[list[str]], page_text: str) -> tuple[list[str], list[str]]:
    """Keep values that appear in one of the input lists or in the page text. Returns (kept, dropped)."""
    pool_keys = {_norm(v) for pool in pools for v in pool}
    text_key = _norm(page_text)
    kept, dropped, seen = [], [], set()
    for v in values or []:
        if not isinstance(v, str) or not v.strip():
            continue
        key = _norm(v)
        if key in seen:
            continue
        seen.add(key)
        if key in pool_keys or (len(key) >= 2 and key in text_key):
            kept.append(_clean_text(v))
        else:
            dropped.append(v)
    return kept, dropped


def _refine_with_llm(
    *,
    site_name: str,
    meta_description: str,
    nav_categories: list[str],
    brands: list[str],
    featured_items: list[str],
    html_text: str,
    heuristic_site_type: SiteType,
    provenance: dict[str, str] | None = None,
    client=None,
) -> dict | None:
    """Use an LLM to correct the rule-based discovery fields.

    The substring-count heuristic (:func:`_detect_site_type`) over-weights experiential
    nouns and can't see purchase signals, so goods retailers with lifestyle/café framing get
    misclassified as SERVICES_EXPERIENCES. The rule-based extractors also leave brand names
    mixed into ``nav_categories`` and pack ``featured_items`` with nav/legal junk. This pass
    re-derives ``site_type``, splits brands out of nav, and keeps only real products.

    Every returned brand / nav label / item must appear in the scraped lists or the page
    text; anything else is dropped as a hallucination.

    Returns ``{site_type, brands, nav_categories, featured_items}`` or ``None`` on failure.
    A failure is never silent: ``provenance['refine']`` becomes ``'fallback: <error>'``, and
    with ``AUDIT_STRICT_LLM`` on (the default) the error is raised instead.
    """
    prov = provenance if provenance is not None else {}
    user = _refine_user_prompt(
        site_name=site_name, meta_description=meta_description, nav_categories=nav_categories,
        brands=brands, featured_items=featured_items, html_text=html_text,
        heuristic_site_type=heuristic_site_type,
    )
    prov["discovery_model"] = _MODEL
    prov["discovery_prompt_sha256"] = _prompt_sha(_REFINE_SYSTEM, user)
    prov["discovery_generated_at"] = _now_iso()
    try:
        out = structured_call(
            model=_MODEL, system=_REFINE_SYSTEM, user=user, schema=RefinedProfile,
            max_tokens=_REFINE_MAX_TOKENS, phase="discovery", temperature=0, client=client,
        )
    except Exception as e:  # API error, refusal, truncation, schema failure — recorded below
        prov["refine"] = f"fallback: {type(e).__name__}: {e}"[:500]
        logger.error("Discovery refinement FAILED — using heuristic fields: %s", prov["refine"])
        if _strict_llm():
            raise
        return None

    pools = [nav_categories, brands, featured_items]
    new_brands, drop_b = _keep_grounded(out.brands, pools, html_text)
    new_nav, drop_n = _keep_grounded(out.nav_categories, pools, html_text)
    new_items, drop_i = _keep_grounded(out.featured_items, pools, html_text)
    dropped = [f"{label}: {', '.join(vals[:8])}" for label, vals in
               (("brands", drop_b), ("nav", drop_n), ("items", drop_i)) if vals]
    prov["refine"] = "llm"
    if dropped:
        prov["refine_dropped"] = "; ".join(dropped)[:500]
        logger.warning("Refinement returned values not in the page; dropped %s", prov["refine_dropped"])
    site_type = out.site_type if isinstance(out.site_type, SiteType) else SiteType(out.site_type)
    return {
        "site_type": site_type.value,
        "site_type_evidence": out.site_type_evidence,
        "brands": new_brands,
        "nav_categories": new_nav,
        "featured_items": new_items,
    }


# ---------------------------------------------------------------------------
# Shared context builder
# ---------------------------------------------------------------------------


def _homepage_url(url: str) -> str:
    """Storefront root, keeping a locale path prefix (lyko.com/sv/sok → lyko.com/sv/)."""
    p = urlparse(url)
    segments = [s for s in p.path.split("/") if s]
    prefix = ""
    if segments and re.fullmatch(r"[a-zA-Z]{2}(?:[-_][a-zA-Z]{2})?", segments[0]) and len(segments) > 1:
        prefix = segments[0] + "/"
    return f"{p.scheme}://{p.netloc}/{prefix}"


def _build_site_context(
    *,
    html: str,
    url: str,
    search_url_template: str,
    seed_query: str = "",
    homepage_html: str | None = None,
    refine: bool = True,
    sample: bool = True,
    fetch_fn: SeedFetchFn | None = None,
    homepage_fetch: Callable[[str], tuple[str, str]] | None = None,
    llm_client=None,
) -> SiteContext:
    """Extract → LLM refine → language/currency → catalog sample. Used by both entry points."""
    provenance: dict[str, str] = {}
    soup = BeautifulSoup(html, "html.parser")
    html_text = _visible_text(soup)

    site_name = _extract_site_name(soup, url)
    raw_meta_description = _extract_meta_description(soup)
    nav_categories = _extract_nav_categories(soup)
    brands = _extract_brands(soup)
    featured_items = _extract_featured_items(soup)
    jsonld_titles, codes = _extract_jsonld_catalog(soup)
    site_type = _detect_site_type(nav_categories, featured_items, raw_meta_description, html_text)

    if refine:
        refined = _refine_with_llm(
            site_name=site_name,
            meta_description=raw_meta_description,
            nav_categories=nav_categories,
            brands=brands,
            featured_items=featured_items,
            html_text=html_text,
            heuristic_site_type=site_type,
            provenance=provenance,
            client=llm_client,
        )
        if refined:
            site_type = SiteType(refined["site_type"])
            if refined.get("brands"):
                brands = refined["brands"]
            if refined.get("nav_categories"):
                nav_categories = refined["nav_categories"]
            # featured_items may legitimately become empty (junk removed) — accept the list as-is.
            featured_items = refined["featured_items"]
            logger.info("LLM refined discovery: site_type=%s, %d brands", site_type.value, len(brands))
    else:
        provenance["refine"] = "skipped"

    primary_language, locale, lang_source = _detect_language(soup, url, html_text)
    provenance["language"] = lang_source
    logger.info("Detected primary language: %s (%s, from %s)", primary_language, locale, lang_source)

    # Catalog sample: real titles that ground query generation beyond the seed page.
    page_titles = _merge_titles([jsonld_titles, featured_items], _CATALOG_SAMPLE_SIZE)
    prices: list[str] = []
    if sample and search_url_template and "{}" in search_url_template:
        homepage_titles: list[str] = []
        if homepage_html is None:
            home_url = _homepage_url(url)
            try:
                homepage_html, _ = (homepage_fetch or _fetch_html)(home_url)
            except Exception as e:
                logger.warning("Homepage fetch for catalog sampling failed: %s", e)
                provenance["catalog_homepage"] = f"failed: {type(e).__name__}: {e}"[:300]
                homepage_html = ""
        if homepage_html:
            home_soup = BeautifulSoup(homepage_html, "html.parser")
            home_jsonld, home_codes = _extract_jsonld_catalog(home_soup)
            homepage_titles = _merge_titles([home_jsonld, _extract_featured_items(home_soup)], 60)
            codes.extend(c for c in home_codes if c["code"].casefold() not in {x["code"].casefold() for x in codes})
        catalog_sample, prices, note = build_catalog_sample(
            search_url_template=search_url_template,
            nav_categories=nav_categories,
            brands=brands,
            page_titles=page_titles,
            homepage_titles=homepage_titles,
            seed_query=seed_query,
            fetch_fn=fetch_fn,
        )
        provenance["catalog_sample"] = note
    else:
        catalog_sample = page_titles
        provenance["catalog_sample"] = f"skipped; {len(catalog_sample)} titles from the discovery page only"

    currency, cur_source = _detect_currency(soup, html_text, locale)
    if not currency and prices:
        currency = _currency_from_text(" ".join(prices), locale)
        cur_source = "sampled-prices" if currency else cur_source
    provenance["currency"] = cur_source

    if codes:
        provenance[CATALOG_CODES_KEY] = json.dumps(codes[:30], ensure_ascii=False)

    return SiteContext(
        url=url,
        site_name=site_name,
        site_type=site_type,
        nav_categories=nav_categories,
        brands=brands,
        featured_items=featured_items,
        search_url_template=search_url_template,
        raw_meta_description=raw_meta_description,
        primary_language=primary_language,
        locale=locale,
        currency=currency,
        catalog_sample=catalog_sample,
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def discover_from_search_url(
    url: str,
    *,
    refine: bool = True,
    sample_catalog: bool = True,
    fetch_fn: SeedFetchFn | None = None,
) -> SiteContext:
    """Build a SiteContext from a search results page URL.

    This is the preferred entry point when the caller already has a working
    search URL (e.g. ``https://www.groupon.com/search?query=spa``).  It is more
    reliable than :func:`discover_site` because the URL template is derived
    directly from the provided URL instead of being guessed from a homepage form.

    Args:
        url: A real search results page URL with the query term visible in the URL.
        refine: Run the LLM refinement pass (default True).
        sample_catalog: Fetch the homepage and 5-8 seed searches to build
            ``catalog_sample`` (default True; pass False for a fast run).
        fetch_fn: Override for the seed-search fetch (tests stub this).

    Raises:
        ValueError: If no search parameter can be identified in ``url``.
        requests.RequestException / RuntimeError: If the page cannot be fetched at all.
    """
    search_url_template, sample_query = parse_search_url(url)
    html, effective_url = _fetch_html(url)
    return _build_site_context(
        html=html,
        url=effective_url,
        search_url_template=search_url_template,
        seed_query=sample_query,
        refine=refine,
        sample=sample_catalog,
        fetch_fn=fetch_fn,
    )


def discover_site(
    url: str,
    *,
    refine: bool = True,
    sample_catalog: bool = True,
    fetch_fn: SeedFetchFn | None = None,
) -> SiteContext:
    """Fetch a site's homepage and build the same context as :func:`discover_from_search_url`
    (refinement and catalog sampling included), guessing the search template from a form."""
    html, effective_url = _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    search_url_template = _extract_search_url_template(soup, effective_url)
    return _build_site_context(
        html=html,
        url=effective_url,
        search_url_template=search_url_template,
        homepage_html=html,
        refine=refine,
        sample=sample_catalog,
        fetch_fn=fetch_fn,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    target = sys.argv[1] if len(sys.argv) > 1 else "https://www.amazon.com"
    ctx = discover_site(target)
    print(f"url:                  {ctx.url}")
    print(f"site_name:            {ctx.site_name}")
    print(f"site_type:            {ctx.site_type}")
    print(f"language / locale:    {ctx.primary_language} / {ctx.locale}  currency: {ctx.currency}")
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
    print(f"catalog_sample: {len(ctx.catalog_sample)} titles")
    print(f"provenance: {json.dumps(ctx.provenance, ensure_ascii=False, indent=2)}")
