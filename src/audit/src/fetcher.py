from __future__ import annotations

import copy
import gzip
import hashlib
import json
import logging
import os as _os
import re
import sys
import threading
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import anthropic
import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import Comment, Declaration, Doctype, NavigableString, ProcessingInstruction
from dotenv import load_dotenv
from pydantic import BaseModel

from src.llm_compat import LLMResponseError, structured_call
from src.models import FetchOutcome, FetchStatus, SearchResult, TestQuery

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

# Overridable per-run; unset env = unchanged default. See docs/CASE_STUDY_PLAYBOOK.md.
_HAIKU_MODEL = _os.environ.get("AUDIT_MODEL_FETCHER", "claude-haiku-4-5-20251001")

# Optional proxy support — set PROXY_URL in .env to route all fetches through a proxy.
# Example: PROXY_URL=http://user:pass@proxy.example.com:8080
_PROXY_URL = _os.environ.get("PROXY_URL", "").strip() or None
if _PROXY_URL:
    logger.info("Proxy configured: %s", _PROXY_URL.split("@")[-1] if "@" in _PROXY_URL else _PROXY_URL)

_REQUESTS_PROXIES = {"http": _PROXY_URL, "https": _PROXY_URL} if _PROXY_URL else None
_PW_PROXY = {"server": _PROXY_URL} if _PROXY_URL else None

# Sleep hook so tests can run the retry/backoff logic without waiting.
_sleep = time.sleep


def _decode_response(resp) -> str:
    """Decode a requests Response to str, preferring UTF-8 over requests' charset sniffing.

    requests defaults to ISO-8859-1 for text/html without an explicit charset, which
    mangles UTF-8 multibyte sequences (producing artifacts like 'Â kr.'). Force UTF-8
    when the content-type header carries it or when the raw bytes parse cleanly as UTF-8.
    """
    ct = resp.headers.get("content-type", "").lower()
    if "charset=utf-8" in ct or "charset=utf8" in ct:
        return resp.content.decode("utf-8", errors="replace")
    try:
        return resp.content.decode("utf-8")
    except UnicodeDecodeError:
        return resp.text

# LLM calls (validation, extraction, selector generation) require an API key.
# When absent, these functions gracefully skip — the heuristic strategies still work
# without any API calls. Every skip leaves the outcome's strategy/evidence honest.
_HAS_API_KEY = bool(_os.environ.get("ANTHROPIC_API_KEY", "").strip())

# ---------------------------------------------------------------------------
# Price regex
# ---------------------------------------------------------------------------
# A currency must sit directly against its amount. The symbol-after forms refuse a
# symbol that is itself followed by a digit: in "7 £240.00" (review count, then price)
# the old regex matched "7 £" — see the cotswoldoutdoor.com profile.
_CUR_SYM = r"[$€£¥₹₩₪฿₫₴]"
_CUR_WORD = r"(?<![A-Za-z])(?:Kč|kč|zł|kr|CHF|Fr\.)"
_CUR_CODE = r"(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|KRW|INR|BRL|SEK|NOK|DKK|PLN|CZK|HUF|RON)"
_PRICE_RE = re.compile(
    r"(?:"
    rf"(?:[A-Z]{{0,2}}{_CUR_SYM})\s?\d[\d.,]*"              # symbol-before: €14,60 / US$9
    r"|"
    rf"\d[\d.,]*\s?{_CUR_SYM}(?!\s?\d)"                      # symbol-after: 14,60 €
    r"|"
    rf"{_CUR_WORD}\s?\d[\d.,]*"                              # kr 199 / CHF 99.00
    r"|"
    rf"\d[\d.,]*\s?{_CUR_WORD}(?![A-Za-z])(?!\s?\d)"         # 199 kr
    r"|"
    rf"\b{_CUR_CODE}\s?\d[\d.,]*"                            # EUR 12,00
    r"|"
    rf"\d[\d.,]*\s?{_CUR_CODE}\b(?!\s?\d)"                   # 12,00 EUR
    r")"
)
_PRICE_FALLBACK_RE = re.compile(rf"(?:{_CUR_SYM}|{_CUR_WORD})\s?\d{{1,7}}(?:[.,]\d{{1,2}})?")

# Price nodes that are NOT the price a shopper pays: struck-through originals,
# "was"/RRP/UVP, unit prices ("12,40 €/100 ml"), per-month instalments.
_SECONDARY_PRICE_TOKEN_RE = re.compile(
    r"(?:^|[-_])(?:old|was|strike|strikethrough|striked|crossed|line-?through|unit|per|"
    r"before|original|orig|rrp|uvp|msrp|compare|compare-at|reference|base-?price|"
    r"instal?ments?|monthly)(?:[-_]|$)|(?:old|was|strike|unit|list|base|original)Price",
    re.I,
)
_STRUCK_TAGS = ("del", "s", "strike")
_CURRENT_PRICE_TOKEN_RE = re.compile(r"sale|current|final|actual|now|special|reduced|selling|promo|offer", re.I)

# Junk title filters (only applied to UNSCOPED generic strategies — never to a
# dedicated extractor that is already scoped to the real results container).
_JUNK_STARTS = (
    "results for", "showing results", "search results",
    "top trending", "trending deals", "featured deals",
    "popular picks", "recommended for you", "you may also like",
    "see all", "view more", "load more", "show more",
    "next page", "previous", "back to top",
    "sign in", "log in", "join now",
    # Dutch / common e-commerce UI strings
    "bekijk vergelijking", "vergelijk", "toon meer", "meer laden",
    "inloggen", "registreren", "mijn account",
    "gratis bezorgd", "gratis verzending",
)
_JUNK_EXACT = {
    "free shipping", "new arrivals", "best sellers", "sale", "clearance", "ad", "ads",
    "sponsored", "advertisement",
}

# Cookie-banner artefacts are recognised by where they point, never by a title
# word: "cookie" in a title deletes real products (cookie cutters, cookie jars).
_COOKIE_JUNK_URL_RE = re.compile(r"^javascript:|cookie|consent|gdpr|datenschutz|privacy", re.I)
_COOKIE_JUNK_TITLE_RE = re.compile(
    r"^(?:accept|allow|reject|decline|manage|customi[sz]e)\b.{0,30}\bcookies?\b|"
    r"^cookies? (?:settings|policy|preferences|einstellungen|richtlinie|inställningar)\b",
    re.I,
)

# Chrome element class/ID patterns
_CHROME_CLASSES = re.compile(
    r"header|banner|hero|promo|nav|footer|sidebar|trending|featured.section|"
    r"advertisement|breadcrumb|pagination|toolbar|"
    r"cookie|consent|gdpr|cookiebot|cybot|privacy-modal|cc-window",
    re.I,
)

# Section-header heading text
_SECTION_HEADER_RE = re.compile(
    r"^(top|best|featured|popular|recommended|trending|new|sale|deal|you may|"
    r"related|similar|people also|customers also)\b",
    re.I,
)

# Containers that hold recommendation / cross-sell carousels rather than the search
# grid. Matched per class/id/data-testid token on a card's ANCESTORS.
_RECO_CONTAINER_RE = re.compile(
    r"carousel|swiper|splide|slick|glide|recommend|\brecs?\b|upsell|cross-?sell|related|"
    r"also-?(?:bought|viewed|like)|recently-?viewed|last-?seen|trending|bestseller|"
    r"you-?may|personali[sz]ed|minicart|mini-cart|cart-drawer",
    re.I,
)
# Headings that introduce such a carousel, multilingual.
_RECO_HEADING_RE = re.compile(
    r"recommended|you may also like|you might also like|customers (?:also|bought)|others also|"
    r"people also|most popular|popular (?:right now|products|items)|bestsellers?|trending|"
    r"recently viewed|top picks|inspiration for you|"
    r"das könnte (?:dir|ihnen) (?:auch )?gefallen|empfehlungen|empfohlen|beliebte?|andere kunden|"
    r"zuletzt angesehen|du kanske också gillar|populära|rekommenderade|andre kjøpte|anbefal|"
    r"populære|aanbevolen|misschien ook leuk|vous aimerez aussi|recommandé|potrebbe piacerti|"
    r"consigliati|polecane|może ci się spodobać|doporučujeme|mohlo by se vám líbit|suosittel",
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
_PRODUCT_LINK_RE = re.compile(
    r"/deal|/product|/item|/offer|/dp/|/p/|/listing|/produkt|/pd/|/artikel/|-p-\d|/ip/",
    re.I,
)

# Sponsored / paid placement labels as they appear on a tile, multilingual.
_SPONSORED_LABEL_RE = re.compile(
    r"^(?:sponsored|sponsorisé|sponsorizzato|sponsorowane|sponzorováno|patrocinado|"
    r"anzeige|gesponsert|werbung|sponsrad|sponset|annonse|annonce|gesponsord|advertisement|ad)$",
    re.I,
)
_SPONSORED_PREFIX_RE = re.compile(
    r"^(?:sponsored|anzeige|gesponsert|sponsrad|sponset|annonse|annonce|gesponsord|werbung)\b[\s:·|\-–]*",
    re.I,
)
_SPONSORED_ATTR_RE = re.compile(r"(?:^|[-_])(?:sponsored|is-ad|ad-tile|advert|promoted)(?:[-_]|$)", re.I)

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
_BLOCK_TITLE_RE = re.compile(
    r"^\s*(?:just a moment|attention required|access denied|pardon our interruption|"
    r"robot or human|are you a (?:robot|human)|verify(?:ing)? you are (?:a )?human|security check|"
    r"request blocked|you have been blocked|access to this page has been denied|403 forbidden|"
    r"forbidden|zugriff verweigert|one more step|please verify)",
    re.I,
)
# HTTP codes that mean "the WAF/CDN refused us", not "the search found nothing".
_BLOCK_HTTP_CODES = frozenset({400, 401, 403, 405, 407, 429})
# A page with less visible text than this is a challenge/interstitial candidate.
_SMALL_PAGE_TEXT = 2500
_TINY_PAGE_BYTES = 5000


def _visible_text_len(soup: BeautifulSoup) -> int:
    texts, _ = _collect_visible_text(soup)
    return len(" ".join(texts))


def _count_product_links(soup: BeautifulSoup) -> int:
    hrefs = {
        (a.get("href") or "").split("#")[0]
        for a in soup.find_all("a", href=True)
        if _PRODUCT_LINK_RE.search(a.get("href") or "") or "/products/" in (a.get("href") or "")
    }
    return len(hrefs)


def _detect_block(
    html: str,
    status_code: Optional[int] = None,
    final_url: str = "",
    soup: Optional[BeautifulSoup] = None,
    strict: bool = True,
    has_zero_marker: bool = False,
) -> Optional[str]:
    """Return a short block label ("akamai", "datadome", "http_403", …) or None.

    ``strict=False`` uses page signatures only — for the in-browser check made right
    after navigation, when a SPA shell is still tiny and the goto status may belong to
    a challenge that clears a second later. ``strict=True`` (the final verdict) also
    treats WAF status codes and tiny product-less bodies as blocks.
    """
    if not html:
        return "empty"
    lower = html[:60000].lower()
    soup = soup if soup is not None else BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text_len = _visible_text_len(soup)
    small = text_len < _SMALL_PAGE_TEXT
    path = urlparse(final_url or "").path.lower()

    if path.rstrip("/").endswith("/challenge") or 'action="/challenge"' in lower:
        return "shopify_challenge"
    if "errors.edgesuite.net" in lower or (title.lower().startswith("access denied") and "reference #" in lower):
        return "akamai"
    if "captcha-delivery.com" in lower and small:
        return "datadome"
    if small and ("px-captcha" in lower or "press &amp; hold" in lower or "press & hold" in lower):
        return "perimeterx"
    if "_cf_chl_opt" in lower or "cf-browser-verification" in lower:
        return "cloudflare"
    if small and any(sig in lower[:8000] for sig in _CLOUDFLARE_SIGNALS):
        return "cloudflare"
    if small and any(sig in lower[:8000] for sig in _IMPERVA_SIGNALS):
        return "imperva"
    if small and ("awswaf" in lower or "aws-waf-token" in lower):
        return "aws_waf"
    if title and _BLOCK_TITLE_RE.match(title) and small:
        return "challenge"
    if not strict:
        return None
    # A captcha widget on a near-empty page. Not checked in the early in-browser pass:
    # an unrendered SPA shell that merely loads reCAPTCHA for a newsletter form is small too.
    if small and ("g-recaptcha" in lower or "h-captcha" in lower or "hcaptcha.com" in lower
                  or "recaptcha/api" in lower):
        return "captcha"
    if status_code is not None and (status_code in _BLOCK_HTTP_CODES or 500 <= status_code < 600):
        if small or _count_product_links(soup) < 3:
            return f"http_{status_code}"
    if len(html) < _TINY_PAGE_BYTES and not has_zero_marker and _count_product_links(soup) == 0:
        return "tiny_page"
    return None


def _classify_response(html: str, status_code: int = 200) -> str:
    """Classify a page response by signature. Returns 'ok', 'empty' or a block label.

    Kept for callers outside the fetch loop; signature-only (non-strict) so a SPA
    shell that has not rendered yet is not mistaken for a block.
    """
    if not html:
        return "empty"
    return _detect_block(html, status_code, strict=False) or "ok"


# ---------------------------------------------------------------------------
# Redirect detection
# ---------------------------------------------------------------------------

# A path SEGMENT that names a search results page ("/search/", "/de/suche", "/lister.html",
# "/catalogsearch/result"). Segment-based: a PDP slug like "/research-notebook.html" is not one.
_SEARCH_PATH_RE = re.compile(
    r"(?:^|/)(?:search|suche|such|sok|sök|soeg|søg|zoeken|zoek|recherche|ricerca|cerca|buscar|busca|"
    r"szukaj|hledat|vyhledavani|haku|find|query|s|lister|catalogsearch|searchresults?|search-results?)"
    r"(?:/|$|\.html?$|\.aspx?$|\.php$)",
    re.I,
)


def _query_tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text or "").casefold().replace("’", "'")
    return re.findall(r"\w+", text)


def _query_present_in(values: list[str], query: str) -> bool:
    want = set(_query_tokens(query))
    if not want:
        return True
    for value in values:
        if want <= set(_query_tokens(value)):
            return True
    return False


def _url_values(url: str, where: str) -> list[str]:
    parsed = urlparse(url)
    if where == "path":
        return [unquote(parsed.path).replace("+", " ")]
    values: list[str] = []
    for part in (parsed.query, parsed.fragment):
        for vals in parse_qs(part, keep_blank_values=False).values():
            values.extend(vals)
    return values


def _query_location(original_url: str, query: str) -> str:
    """Where the search template puts the query: in the query string or the path."""
    if _query_present_in(_url_values(original_url, "query"), query):
        return "query"
    if _query_present_in(_url_values(original_url, "path"), query):
        return "path"
    return "query"


def _redirect_kind(original_url: str, final_url: str, query: str) -> Optional[str]:
    """Classify where the browser ended up relative to the search URL.

    None       — still on the search page (or only scheme/host/params changed).
    "away"     — the query is gone from the destination (PDP, brand page, …).
    "landing"  — the query survives as a parameter but the path is a category /
                 landing page, not the search page (cotswold `?q=…&sred=1`,
                 bergzeit `?bzsearch=…`, lyko `?fromsearch=…`).

    Tokens are compared after parse_qs + unquote + casefold, so "Arc'teryx",
    "+" vs "%20" and percent-encoded umlauts all compare equal.
    """
    if not final_url or final_url == original_url:
        return None
    orig, final = urlparse(original_url), urlparse(final_url)
    if orig.path.rstrip("/").lower() == final.path.rstrip("/").lower():
        return None
    where = _query_location(original_url, query)
    if not _query_present_in(_url_values(final_url, where), query):
        # /search?q=red+shoes → /search/red-shoes is the same results page, re-routed.
        if _SEARCH_PATH_RE.search(final.path) and _query_present_in(_url_values(final_url, "path"), query):
            return None
        logger.debug("Search redirect (away): %s → %s", original_url, final_url)
        return "away"
    if _SEARCH_PATH_RE.search(final.path):
        return None
    return "landing"


def _is_search_redirect(original_url: str, final_url: str, query: str) -> bool:
    """True if the server redirected away from the search results page (query dropped)."""
    return _redirect_kind(original_url, final_url, query) == "away"


class SiteMode:
    """Fetch strategy for a site, determined once by _probe_site."""
    STATIC = "static"
    PLAYWRIGHT_FIREFOX = "playwright_firefox"
    PLAYWRIGHT_CHROMIUM = "playwright_chromium"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Visible text & page state (no-results markers, hit counts)
# ---------------------------------------------------------------------------

_INVISIBLE_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "head", "iframe", "object"})
_CHROME_TAGS = frozenset({"header", "nav", "footer"})
_CHROME_ROLES = frozenset({"banner", "navigation", "contentinfo", "dialog"})
# Overlays whose text is not the results page: search-as-you-type dropdowns, mini-carts.
_OVERLAY_TOKEN_RE = re.compile(
    r"autocomplete|auto-complete|suggest|typeahead|predictive|minicart|mini-cart|cart-drawer|"
    r"flyout|search-overlay|quick-search|searchbar|search-bar|search-layer",
    re.I,
)


def _is_hidden_tag(tag: Tag) -> bool:
    attrs = tag.attrs or {}
    if "hidden" in attrs:
        return True
    style = (attrs.get("style") or "").replace(" ", "").lower()
    return "display:none" in style or "visibility:hidden" in style


def _is_chrome_container(tag: Tag) -> bool:
    if tag.name in _CHROME_TAGS:
        return True
    attrs = tag.attrs or {}
    if (attrs.get("role") or "").lower() in _CHROME_ROLES:
        return True
    tokens = list(attrs.get("class") or []) + [attrs.get("id") or "", attrs.get("data-testid") or ""]
    return any(t and _OVERLAY_TOKEN_RE.search(t) for t in tokens)


def _collect_visible_text(node) -> tuple[list[str], list[str]]:
    """Walk the DOM once; return (all visible strings, strings outside page chrome).

    Iterative (deep DOMs blow the recursion limit) and non-mutating (the caller keeps
    using the same soup for extraction).
    """
    everything: list[str] = []
    content: list[str] = []
    stack: list[tuple[Tag, bool]] = [(node, False)]
    while stack:
        current, in_chrome = stack.pop()
        children = list(current.children) if hasattr(current, "children") else []
        pending: list[tuple[Tag, bool]] = []
        for child in children:
            if isinstance(child, NavigableString):
                if isinstance(child, (Comment, Declaration, Doctype, ProcessingInstruction)):
                    continue
                s = str(child).strip()
                if s:
                    everything.append(s)
                    if not in_chrome:
                        content.append(s)
            elif isinstance(child, Tag):
                if child.name in _INVISIBLE_TAGS or _is_hidden_tag(child):
                    continue
                pending.append((child, in_chrome or _is_chrome_container(child)))
        # Preserve document order: push children in reverse so the first is popped first.
        for item in reversed(pending):
            stack.append(item)
    return everything, content


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text or "")).strip()


# Explicit "no results" messages, multilingual. Word-bounded: "10 results" must never
# read as "0 results".
_ZERO_COUNT_WORDS = (
    r"results?|treffer|ergebnisse?|träffar|resultater|resultat|resultaten|résultats?|"
    r"risultati|resultados|wyników|výsledků|tulosta|hits|matches|products? found|items? found|"
    r"produkte gefunden|artikel gefunden"
)
_NO_RESULTS_PATTERNS = (
    rf"(?<![\d.,])\b0\s+(?:{_ZERO_COUNT_WORDS})\b",
    r"\bno (?:matching )?(?:results|matches)\b",
    r"\bno (?:products|items) (?:were )?found\b",
    r"\b(?:did not|didn['’]t|does not|doesn['’]t) (?:return|match|find) any (?:results|products|items)",
    r"\b(?:sorry,? )?we (?:couldn['’]t|could not|can['’]t|cannot) find (?:any |anything|results|products|matches|[\"“„'])",
    r"\bnothing (?:matches|matched|found)\b",
    r"\breturned no results\b",
    r"\bzero results\b",
    r"\bkeine (?:passenden |übereinstimmenden )?(?:treffer|ergebnisse|suchergebnisse)\b",
    r"\bkeine (?:passenden )?(?:produkte|artikel) gefunden\b",
    r"\bkein (?:passendes )?(?:ergebnis|produkt) gefunden\b",
    r"\b(?:leider )?nichts gefunden\b",
    r"\binga (?:träffar|resultat|sökresultat)\b",
    r"\binga produkter (?:hittades|matchade)\b",
    r"\bingen (?:resultater|resultat|søgeresultater|søkeresultater|treff|varer fundet|produkter fundet)\b",
    r"\bvi (?:fant|fandt) ingen\b",
    r"\bgeen (?:resultaten|zoekresultaten|producten gevonden)\b",
    r"\baucun (?:résultat|produit (?:ne correspond|trouvé))",
    r"\bpas de résultats?\b",
    r"\bnessun (?:risultato|prodotto trovato)\b",
    r"\bsin resultados\b",
    r"\bno se (?:han )?encontr(?:aron|ado) (?:resultados|productos)",
    r"\bningún resultado\b",
    r"\bnenhum resultado\b",
    r"\bbrak (?:wyników|produktów)\b",
    r"\bnie znaleziono\b",
    r"\bžádné (?:výsledky|produkty)\b",
    r"\bnebyly nalezeny žádné\b",
    r"\bnic (?:nebylo )?nenalezeno\b",
    r"\bei (?:haku)?tuloksia\b",
    r"\bhakusi ei tuottanut\b",
    r"(?:suchergebnis\w*|search results?|results?) (?:für|for)\s*[«»\"'„“”‚‘’]?[^()«»\"„“”]{1,80}[«»\"'„“”‚‘’]?\s*\(0\)",
)
_NO_RESULTS_RE = re.compile("|".join(f"(?:{p})" for p in _NO_RESULTS_PATTERNS), re.I)

# The page APPLIED a spelling correction and shows results for the corrected query:
# the shopper sees products, so "no results for X" next to it is not a zero.
_AUTO_APPLIED_RE = re.compile(
    r"showing results for|search(?:ed)? instead for|we searched for|results for .{1,60} instead|"
    r"stattdessen|wir zeigen (?:dir|ihnen) (?:ergebnisse|treffer)|ergebnisse für .{1,60} anzeigen|"
    r"visar (?:resultat|träffar) för|viser resultater for|resultaten voor .{1,60} getoond|"
    r"résultats pour .{1,60} affichés|risultati per .{1,60} mostrati",
    re.I,
)
# The page only SUGGESTS a correction ("Did you mean …?"); results may or may not follow.
_SUGGESTION_RE = re.compile(
    r"did you mean|meintest du|meinten sie|menade du|mente du|bedoelde (?:u|je)|"
    r"vous vouliez dire|forse cercavi|intendevi|quisiste decir|czy chodziło ci o|"
    r"měli jste na mysli|tarkoititko",
    re.I,
)

# "Strong" words only ever describe search hits; "weak" ones (items, Artikel, products)
# also appear in product names ("Storage box 12 items"), so they count only in the
# title, the h1 or an element whose id/class/testid says it is a result count.
_STRONG_HIT_WORDS = (
    r"results?|treffer|ergebnisse?|träffar|resultater|resultaten|résultats?|risultati|"
    r"resultados|výsledků|výsledky|wyników|tulosta|hits|suchergebnisse"
)
_WEAK_HIT_WORDS = r"artikel|produkte|produkter|items?|products?|varer|tuotetta|produits|prodotti"
_HIT_WORDS = f"{_STRONG_HIT_WORDS}|{_WEAK_HIT_WORDS}"
_HIT_COUNT_RE = re.compile(
    rf"(?<![\w.,])(\d{{1,3}}(?:[.,   ]\d{{3}})+|\d+)\s*(?:{_HIT_WORDS})\b"
    r"(?!\s*(?:pro|per|je|par|på)\s+(?:seite|page|sida|side|pagina))",
    re.I,
)
_HIT_COUNT_PAREN_RE = re.compile(
    rf"(?:{_HIT_WORDS})\s*\((\d{{1,3}}(?:[.,   ]\d{{3}})+|\d+)\)",
    re.I,
)
_COUNTISH_ATTR_RE = re.compile(r"count|result|hits|total|summary|amount", re.I)
_STRONG_HIT_RE = re.compile(rf"\b(?:{_STRONG_HIT_WORDS})\b", re.I)
_CART_ATTR_RE = re.compile(r"cart|basket|bag|wishlist|warenkorb|varukorg|kurv", re.I)


def _parse_count(raw: str) -> Optional[int]:
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


@dataclass
class HostProfile:
    """Per-host fetch knowledge (see docs/FETCHER_PLAYBOOK.md per-site profiles)."""
    no_results: tuple[str, ...] = ()          # extra no-results regexes (visible text + title)
    generic_markers: bool = True              # False: only this profile's markers count
    zero_title: Optional[str] = None          # regex on <title> that confirms a zero
    hits_regex: Optional[str] = None          # regex with one group = the page's hit count
    pdp_path: Optional[str] = None            # regex: product pages live at this path
    ready_selector: Optional[str] = None      # CSS: the results grid has rendered
    ready_no_results: Optional[str] = None    # JS regex source: no-results state rendered
    ready_timeout_ms: int = 15000


_HOST_PROFILES: dict[str, HostProfile] = {
    "zalando.": HostProfile(
        no_results=(re.escape("Try a different search term or check the spelling."),),
        ready_selector='[data-testid="product-count"]',
        ready_no_results="Try a different search term",
        ready_timeout_ms=20000,
    ),
    # Akamai serves stale SSR headings ("0 Ergebnisse") that are re-rendered client-side,
    # so ONLY the document title confirms a zero on this host (FETCHER_PLAYBOOK douglas.de).
    "douglas.de": HostProfile(
        generic_markers=False,
        zero_title=r"^\s*Keine Ergebnisse gefunden \| DOUGLAS\s*$",
        pdp_path=r"/p/\d+",
    ),
    "manufactum.de": HostProfile(
        no_results=(r"Suchergebnis für »[^«]*«\s*\(0\)",),
        hits_regex=r"Suchergebnis für »[^«]*«\s*\((\d[\d.]*)\)",
    ),
    "bergzeit.de": HostProfile(no_results=(r"ergab leider keine Treffer",)),
    "colourpop.com": HostProfile(
        no_results=(r"\b0 items\b",),
        ready_selector="#product-grid main-product",
        ready_no_results=r"\b0 items\b",
    ),
    "cotswoldoutdoor.com": HostProfile(
        pdp_path=r"^/p/",
        ready_selector='div[data-testid="product-tile-vertical"]',
        ready_no_results=r"\bno results\b|\b0\s+results\b|couldn'?t find",
        ready_timeout_ms=20000,
    ),
    "ahlens.se": HostProfile(
        ready_selector="#product-rain-section",
        ready_no_results=r"inga träffar",
    ),
    "avoca.com": HostProfile(
        ready_selector=".boost-sd__product-item",
        ready_no_results=r"\b0\s+results?\s+found|couldn['’]t find results",
    ),
    "huckberry.com": HostProfile(
        ready_selector="span.ProductTileContent__price, a.ProductTileContent__brand-link",
        ready_no_results=r"couldn['’]?t find|\bno results\b|\b0\s+results\b",
        ready_timeout_ms=20000,
    ),
}


def _host_profile(url: str) -> Optional[HostProfile]:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return None
    for key, profile in _HOST_PROFILES.items():
        if key in host:
            return profile
    return None


@dataclass
class PageState:
    title: str = ""
    no_results_marker: Optional[str] = None   # the matched text, for evidence
    total_hits: Optional[int] = None          # the page's own hit count, when parseable
    hits_strong: bool = False                 # the count used a search-only word ("results")
    max_strong_hits: int = 0                  # largest "N results"-style count anywhere in the headers
    auto_applied: bool = False                # page shows results for a corrected query
    suggestion: bool = False                  # page suggests a correction ("did you mean")


def _main_text(soup: BeautifulSoup, limit: int = 20000) -> str:
    """Visible text outside page chrome: <main> first (the message usually sits there),
    then the rest of the body (some shops render the "no hits" header outside <main>)."""
    body = soup.body or soup
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    parts = []
    if main is not None:
        _, content = _collect_visible_text(main)
        parts.append(_norm_text(" ".join(content))[:limit])
    _, content = _collect_visible_text(body)
    parts.append(_norm_text(" ".join(content))[:limit * 2])
    return " \n ".join(parts)


def _hit_count_candidates(soup: BeautifulSoup) -> list[tuple[str, bool]]:
    """(text, weak_words_allowed) pairs, most authoritative first."""
    out: list[tuple[str, bool]] = []
    if soup.title:
        out.append((soup.title.get_text(" ", strip=True), True))
    for el in soup.find_all(["h1", "h2", "h3"]):
        if el.find_parent(["header", "nav", "footer"]) or _is_hidden_tag(el):
            continue
        text = el.get_text(" ", strip=True)
        if text and len(text) < 200:
            out.append((text, el.name == "h1"))
    for el in soup.find_all(True):
        attrs = el.attrs or {}
        tokens = " ".join(list(attrs.get("class") or []) + [attrs.get("id") or "", attrs.get("data-testid") or ""])
        if not tokens or not _COUNTISH_ATTR_RE.search(tokens) or _CART_ATTR_RE.search(tokens):
            continue
        if el.name in _INVISIBLE_TAGS or el.find_parent(["header", "nav", "footer"]):
            continue
        text = el.get_text(" ", strip=True)
        if text and len(text) < 200:
            out.append((text, True))
    return out


def page_state(html_or_soup, url: str = "", visible_text: Optional[str] = None, query: str = "") -> PageState:
    """Read the page's own account of its result state, for any host.

    - ``no_results_marker``: an explicit no-results message in the visible text or the
      title (multilingual, word-bounded), or a host-profile marker.
    - ``total_hits``: the hit count the page reports in its title / headings / count
      elements ("384 results", "1.234 Artikel", "Products (12)").
    - ``auto_applied`` / ``suggestion``: the page applied / suggested a spelling fix.

    ``visible_text`` (from the browser's innerText) is preferred when given: it honours
    CSS visibility, which a static parse cannot. ``query`` is blanked out before the
    hit-count parse so "pack of 6 items" never reads as 6 hits.
    """
    soup = html_or_soup if isinstance(html_or_soup, BeautifulSoup) else BeautifulSoup(html_or_soup or "", "html.parser")
    profile = _host_profile(url)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = _norm_text(visible_text) if visible_text else _main_text(soup)
    haystack = f"{title} \n {text}"
    state = PageState(title=title)

    marker = None
    if profile and profile.zero_title and re.search(profile.zero_title, title, re.I):
        marker = title
    if marker is None and profile:
        for pat in profile.no_results:
            m = re.search(pat, haystack, re.I)
            if m:
                marker = m.group(0)
                break
    if marker is None and (profile is None or profile.generic_markers):
        m = _NO_RESULTS_RE.search(haystack)
        if m:
            marker = m.group(0)
    state.no_results_marker = marker
    state.auto_applied = bool(_AUTO_APPLIED_RE.search(haystack))
    state.suggestion = bool(_SUGGESTION_RE.search(haystack))

    def _blank_query(text: str) -> str:
        q = (query or "").strip()
        return re.sub(re.escape(q), " ", text, flags=re.I) if len(q) >= 2 else text

    hits, strong, max_strong = None, False, 0
    if profile and profile.hits_regex:
        m = re.search(profile.hits_regex, _blank_query(haystack), re.I)
        if m:
            hits, strong = _parse_count(m.group(1)), True
            max_strong = hits or 0
    if hits is None and (profile is None or profile.generic_markers):
        for cand, weak_ok in _hit_count_candidates(soup):
            cand = _blank_query(cand)
            for rx in (_HIT_COUNT_RE, _HIT_COUNT_PAREN_RE):
                for m in rx.finditer(cand):
                    n = _parse_count(m.group(1))
                    is_strong = bool(_STRONG_HIT_RE.search(m.group(0)))
                    if n is None or (not is_strong and not weak_ok):
                        continue
                    if is_strong:
                        max_strong = max(max_strong, n)
                    if hits is None:
                        hits, strong = n, is_strong
    state.total_hits, state.hits_strong, state.max_strong_hits = hits, strong, max_strong
    if hits == 0 and strong and marker is None:
        state.no_results_marker = "page reports 0 hits"
    return state


# ---------------------------------------------------------------------------
# Result validation / junk filter
# ---------------------------------------------------------------------------


def _filter_junk_results(results: list[SearchResult]) -> list[SearchResult]:
    """Remove results that are clearly page chrome, not real products.

    Only for UNSCOPED strategies (generic sweep, LLM). Ranks are re-numbered because
    a removed nav/chrome item never was a ranked position.
    """
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

        clean.append(r)

    for i, r in enumerate(clean, 1):
        r.rank = i

    return clean


def _is_cookie_junk(r: SearchResult) -> bool:
    return bool(_COOKIE_JUNK_URL_RE.search(r.url or "") or _COOKIE_JUNK_TITLE_RE.search(r.title or ""))


def _detect_sponsored(card: Optional[Tag]) -> bool:
    """True when a tile carries a paid-placement label or attribute."""
    if card is None:
        return False
    for el in [card] + card.find_all(True):
        attrs = el.attrs or {}
        for name, val in attrs.items():
            if name in ("data-sponsored", "data-is-sponsored", "data-ad", "data-promoted") and str(val).lower() not in ("false", "0"):
                return True
            if name in ("class", "data-testid", "data-test", "data-qa"):
                vals = val if isinstance(val, list) else str(val).split()
                if any(_SPONSORED_ATTR_RE.search(v) for v in vals):
                    return True
    for s in card.find_all(string=True):
        if isinstance(s, Comment):
            continue
        if _SPONSORED_LABEL_RE.match(s.strip()):
            return True
    return False


def _strip_sponsored_prefix(r: SearchResult) -> SearchResult:
    m = _SPONSORED_PREFIX_RE.match(r.title or "")
    if m and len(r.title) > m.end() + 3:
        r.title = r.title[m.end():].strip()
        r.sponsored = True
    return r


# ---------------------------------------------------------------------------
# Price extraction
# ---------------------------------------------------------------------------


def _is_secondary_price_node(el: Tag) -> bool:
    if el.name in _STRUCK_TAGS:
        return True
    attrs = el.attrs or {}
    tokens = list(attrs.get("class") or []) + [attrs.get("data-testid") or "", attrs.get("itemprop") or ""]
    style = (attrs.get("style") or "").replace(" ", "").lower()
    if "line-through" in style:
        return True
    return any(t and _SECONDARY_PRICE_TOKEN_RE.search(t) for t in tokens)


def _current_price_text(el: Tag) -> str:
    """Text of ``el`` with struck-through / was / unit-price descendants removed."""
    if not el.find(lambda t: isinstance(t, Tag) and _is_secondary_price_node(t)):
        return el.get_text(separator=" ", strip=True)
    clone = copy.copy(el)
    for bad in clone.find_all(lambda t: isinstance(t, Tag) and _is_secondary_price_node(t)):
        bad.decompose()
    return clone.get_text(separator=" ", strip=True)


def _first_price(text: str) -> Optional[str]:
    for pattern in (_PRICE_RE, _PRICE_FALLBACK_RE):
        m = pattern.search(text or "")
        if m:
            return m.group(0).strip()
    return None


def _inside_secondary(el: Tag, stop: Tag) -> bool:
    node = el
    while node is not None and node is not stop:
        if isinstance(node, Tag) and _is_secondary_price_node(node):
            return True
        node = node.parent
    return False


def _extract_price(element: Tag) -> Optional[str]:
    """The price a shopper pays, from a product card.

    Order: itemprop=price → price-classed nodes that say sale/current/final → any
    price-classed node → the card's text. Struck-through (<del>/<s>), was/RRP/UVP,
    unit-price and instalment nodes are skipped at every step.
    """
    meta = element.find(attrs={"itemprop": "price"})
    if isinstance(meta, Tag) and not _inside_secondary(meta, element):
        content = (meta.get("content") or "").strip()
        if content and re.match(r"^\d[\d.,]*$", content):
            cur = element.find(attrs={"itemprop": "priceCurrency"})
            code = (cur.get("content") or cur.get_text(strip=True)) if isinstance(cur, Tag) else ""
            return f"{code} {content}".strip()
        price = _first_price(_current_price_text(meta))
        if price:
            return price

    current: list[Tag] = []
    plain: list[Tag] = []
    for child in element.find_all(True, recursive=True):
        attrs = child.attrs or {}
        tokens = " ".join(list(attrs.get("class") or []) + [attrs.get("data-testid") or ""]).lower()
        if not any(kw in tokens for kw in ("price", "cost", "amount", "money", "preis", "pris")):
            continue
        if _inside_secondary(child, element):
            continue
        (current if _CURRENT_PRICE_TOKEN_RE.search(tokens) else plain).append(child)
    for child in current + plain:
        price = _first_price(_current_price_text(child))
        if price:
            return price

    return _first_price(_current_price_text(element))


# ---------------------------------------------------------------------------
# Strategy 0 — Site-specific extraction
# ---------------------------------------------------------------------------


# Hosts that server-render the product grid but hydrate prices client-side.
# For these the probe must not short-circuit to STATIC mode (prices would be
# missing) — always fetch via Playwright so prices load.
_CLIENT_RENDERED_PRICE_HOSTS = ("bergzeit.de", "lyko.com")


# Hosts that must be fetched with Chromium, not Firefox. cotswoldoutdoor.com
# issues a client-side `?...&sred=1` redirect from /lister.html to a curated
# category page for many keyword queries; Firefox aborts that redirect with a
# "Network Protocol Error" (capturing a ~6KB stub → 0 results), while Chromium
# follows it cleanly and renders the full product grid. Forcing Chromium makes
# the probe settle on PLAYWRIGHT_CHROMIUM so every query uses it.
_PREFER_CHROMIUM_HOSTS = ("cotswoldoutdoor.com",)


def _prefers_chromium(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(h in host for h in _PREFER_CHROMIUM_HOSTS)


# Hosts with a hand-tuned extractor in _try_site_specific. For these the dispatcher
# never falls back to generic strategies (they would scrape recommendation chrome as
# results). An EMPTY extraction is NOT proof of zero results by itself: it becomes
# ZERO_CONFIRMED only when page_state() sees a no-results marker, otherwise
# ZERO_UNVERIFIED — a render lapse or a bot wall looks exactly like an empty grid.
_DEDICATED_EXTRACTOR_HOSTS = ("groupon", "lyko.com", "ahlens.se", "bergzeit.de", "avoca.com", "huckberry.com", "manufactum.de", "imerco.dk", "baechli-bergsport.ch", "cotswoldoutdoor.com", "zalando.", "douglas.de", "colourpop.com")


# Hosts known to send a query that uniquely matches one product straight to that
# product's detail page (PDP). Every redirect on EVERY host is now extracted on the
# destination (_analyse_page → _extract_pdp / the listing extractors), so this list
# only lets the probe settle on STATIC mode from such a PDP hit. A PDP redirect is a
# GOOD search behaviour (see JUDGE_PLAYBOOK.md for how DIRECT_MATCH scores it).
_PDP_REDIRECT_HOSTS = ("baechli-bergsport.ch", "cotswoldoutdoor.com", "douglas.de")


def _needs_pdp_redirect_extraction(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(h in host for h in _PDP_REDIRECT_HOSTS)


# Authoritative-no-results destination paths, by host substring. A redirect
# landing here is a GENUINE zero, not a category/brand listing — even though
# the page renders a "you might also like" recommendation carousel using the
# identical product-tile markup as the real results grid. Caught when the
# generic category-redirect fallback (added for the Arc'teryx brand-page case)
# scraped this carousel as 10 fake "waterproof jacket under £100" results, none
# of which were jackets or under £100 — same failure class as the
# ahlens.se/manufactum.de/bergzeit.de "phantom recommendations on a no-hits
# page" trap (see General silent-failure patterns). Must be checked BEFORE
# falling back to `_try_site_specific` on a redirect destination.
_NO_RESULTS_PATH_MARKERS = {
    "cotswoldoutdoor.com": "/lister/no-results",
}


def _is_authoritative_no_results(final_url: str) -> bool:
    try:
        host = urlparse(final_url).netloc.lower()
        path = urlparse(final_url).path.lower()
    except Exception:
        return False
    for h, marker in _NO_RESULTS_PATH_MARKERS.items():
        if h in host and marker in path:
            return True
    return False


# ---------------------------------------------------------------------------
# JSON-LD helpers (shared by the PDP detector and Strategy 1)
# ---------------------------------------------------------------------------

_LD_PRODUCT_TYPES = {"Product", "Service", "IndividualProduct", "ProductModel", "Vehicle", "Book"}
# Keys whose values describe *other* things than the listing itself: variants, related
# products, offers, reviews. Recursing into them turned one product into five results.
_LD_SKIP_KEYS = {
    "offers", "isRelatedTo", "isSimilarTo", "hasVariant", "isVariantOf", "itemOffered",
    "review", "reviews", "aggregateRating", "brand", "manufacturer", "isAccessoryOrSparePartFor",
    "isConsumableFor", "model", "subjectOf", "potentialAction", "breadcrumb", "publisher",
    "author", "image", "logo", "address", "seller", "includesObject", "workExample", "audience",
}


def _ld_types(node: dict) -> set[str]:
    raw = node.get("@type")
    vals = raw if isinstance(raw, list) else [raw]
    out = set()
    for v in vals:
        if isinstance(v, str) and v:
            out.add(v.rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    return out


def _ld_str(value) -> str:
    if isinstance(value, str):
        return unescape(value).strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, dict):
        return _ld_str(value.get("@value") or value.get("name") or "")
    if isinstance(value, list) and value:
        return _ld_str(value[0])
    return ""


def _jsonld_blocks(soup: BeautifulSoup) -> list:
    blocks = []
    for script in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        raw = script.string if script.string is not None else script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            blocks.append(json.loads(raw.strip()))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return blocks


def _ld_price(node: dict) -> Optional[str]:
    offers = node.get("offers")
    candidates = offers if isinstance(offers, list) else [offers]
    for off in candidates:
        if not isinstance(off, dict):
            continue
        p = off.get("price")
        if p in (None, ""):
            p = off.get("lowPrice")
        if p in (None, "") and isinstance(off.get("priceSpecification"), dict):
            p = off["priceSpecification"].get("price")
        if p in (None, ""):
            continue
        currency = _ld_str(off.get("priceCurrency"))
        return f"{currency} {_ld_str(p)}".strip()
    if node.get("price") not in (None, ""):
        return _ld_str(node.get("price"))
    return None


def _ld_top_level_products(blocks: list) -> tuple[list[dict], bool]:
    """Product nodes reachable without passing through an ItemList; plus 'has ItemList'."""
    products: list[dict] = []
    has_list = False

    def walk(node, depth=0):
        nonlocal has_list
        if depth > 6:
            return
        if isinstance(node, list):
            for n in node:
                walk(n, depth + 1)
            return
        if not isinstance(node, dict):
            return
        types = _ld_types(node)
        if types & _LD_PRODUCT_TYPES:
            products.append(node)
            return
        if "ItemList" in types or "OfferCatalog" in types:
            has_list = True
            return
        for key in ("@graph", "mainEntity", "mainEntityOfPage"):
            if key in node:
                walk(node[key], depth + 1)

    for b in blocks:
        walk(b)
    return products, has_list


# ---------------------------------------------------------------------------
# PDP (product detail page) detection — a search that lands on ONE product
# ---------------------------------------------------------------------------


def _extract_pdp(soup: BeautifulSoup, final_url: str) -> Optional[SearchResult]:
    """Return the single product a search redirected to, or None if this is not a PDP.

    A page counts as a PDP only on positive evidence: og:type=product, a
    product:price:amount meta, exactly one top-level JSON-LD Product with no ItemList,
    or the host's own PDP path rule. A brand/category landing page has an <h1> too —
    without that evidence its heading must never become a fake one-product result
    (cotswoldoutdoor.com: "Arc'teryx" → /brands/arcteryx.html is a listing).
    """
    try:
        path = urlparse(final_url).path
    except Exception:
        path = ""
    profile = _host_profile(final_url)
    if profile and profile.pdp_path and not re.search(profile.pdp_path, path):
        return None

    og_type = soup.find("meta", attrs={"property": "og:type"})
    og_product = bool(og_type and "product" in (og_type.get("content") or "").lower())
    amount_tag = soup.find("meta", attrs={"property": re.compile(r"^(?:product|og):price:amount$")})
    ld_products, has_list = _ld_top_level_products(_jsonld_blocks(soup))
    path_rule = bool(profile and profile.pdp_path and re.search(profile.pdp_path, path))
    if not (path_rule or og_product or amount_tag or (len(ld_products) == 1 and not has_list)):
        return None

    ld = ld_products[0] if len(ld_products) == 1 else None
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)
    if not title and ld:
        title = _ld_str(ld.get("name"))
    if not title:
        og_title = soup.find("meta", attrs={"property": "og:title"})
        title = re.split(r"\s+[|–-]\s+", (og_title.get("content") or "").strip())[0] if og_title else ""
    if not title:
        return None

    price = None
    if amount_tag and amount_tag.get("content"):
        currency_tag = soup.find("meta", attrs={"property": re.compile(r"^(?:product|og):price:currency$")})
        currency = (currency_tag.get("content") or "").strip() if currency_tag else ""
        price = f"{currency} {amount_tag['content'].strip()}".strip()
    if not price and ld:
        price = _ld_price(ld)
    if not price:
        price_el = soup.select_one('[data-testid="product_price-actual-price"]') \
            or soup.select_one('[data-testid="product_price-previous-price"]')
        if price_el:
            price = price_el.get_text(" ", strip=True) or None
    if not price:
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc:
            price = _first_price(og_desc.get("content") or "")

    link = ""
    canon = soup.find("link", attrs={"rel": "canonical"})
    if canon and canon.get("href"):
        link = canon["href"].strip()
    if not link:
        og_url = soup.find("meta", attrs={"property": "og:url"})
        link = (og_url.get("content") or "").strip() if og_url else ""
    return SearchResult(rank=1, title=title[:200], url=link or final_url, price=price)


def _try_extract_pdp_as_result(html: str, final_url: str) -> list[SearchResult]:
    """Legacy wrapper: [the PDP's single product] or []."""
    pdp = _extract_pdp(BeautifulSoup(html, "html.parser"), final_url)
    return [pdp] if pdp else []


# Hosts that serve a Cloudflare "Just a moment..." JS challenge to headless
# browsers but let a *headed* (non-headless) Chromium session through. For these
# we launch headed, force Chromium (Firefox isn't reliably installed and the
# challenge is Chromium-friendly), and wait for the challenge to clear before
# classifying the response as blocked.
# zalando.* (every market): no challenge page, but headless Chromium gets a 403 / soft "Not Found"
# with zero products (and is flaky — sometimes classified as blocked outright). Headed
# Chromium returns the normal page reliably: ~806KB, 84 product articles.
_HEADED_CHROMIUM_HOSTS = ("huckberry.com", "zalando.", "douglas.de", "colourpop.com")


def _has_dedicated_extractor(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(h in host for h in _DEDICATED_EXTRACTOR_HOSTS)


def _needs_headed_chromium(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(h in host for h in _HEADED_CHROMIUM_HOSTS)


def _try_site_specific(soup: BeautifulSoup, url: str, max_results: int) -> list[SearchResult]:
    """Site-specific extraction for known sites. Returns empty list if no match."""
    host = urlparse(url).netloc.lower()

    if "colourpop.com" in host:
        return _try_colourpop(soup, max_results)

    if "groupon" in host:
        return _try_groupon(soup, max_results)

    if "lyko.com" in host:
        return _try_lyko(soup, max_results)

    if "ahlens.se" in host:
        return _try_ahlens(soup, max_results)

    if "bergzeit.de" in host:
        return _try_bergzeit(soup, max_results)

    if "avoca.com" in host:
        return _try_avoca(soup, max_results)

    if "huckberry.com" in host:
        return _try_huckberry(soup, max_results)

    if "manufactum.de" in host:
        return _try_manufactum(soup, max_results)

    if "baechli-bergsport.ch" in host:
        return _try_baechli(soup, max_results)

    if "imerco.dk" in host:
        return _try_imerco(soup, max_results)

    if "cotswoldoutdoor.com" in host:
        return _try_cotswoldoutdoor(soup, max_results)

    if "zalando." in host:
        return _try_zalando(soup, max_results)

    if "douglas.de" in host:
        return _try_douglas(soup, max_results)

    return []


def _try_colourpop(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Read ColourPop's visible search grid, excluding hidden recommendations."""
    results: list[SearchResult] = []
    seen: set[str] = set()
    for card in soup.select("#product-grid main-product"):
        link = card.select_one('h2 a[href*="/products/"]')
        if not link:
            continue
        title = link.get_text(" ", strip=True)
        href = (link.get("href") or "").strip()
        if not title or not href:
            continue
        key = href.split("?", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        price_match = re.search(r"Regular price\s*(\$[\d,.]+)", card.get_text(" ", strip=True))
        price = price_match.group(1) if price_match else None
        url = f"https://colourpop.com{href}" if href.startswith("/") else href
        results.append(SearchResult(rank=len(results) + 1, title=title[:120], price=price, url=url,
                                    sponsored=_detect_sponsored(card)))
        if len(results) >= max_results:
            break
    return results



# Zalando's authoritative no-results marker. This exact sentence appears ONLY on a
# genuine zero-results page and nowhere else on the site, which makes it the single
# reliable signal — see _try_zalando for why structure/count checks are not.
_ZALANDO_NO_RESULTS_MARKER = "Try a different search term or check the spelling."

# Card chrome that precedes the brand/name lines inside a Zalando <article>.
_ZALANDO_PRICE_LINE = re.compile(r"^\u20ac\s?[\d.,]+$")
_ZALANDO_ORIGINAL_PRICE_LABEL = re.compile(
    r"^(reference price|originally|last lowest price|rrp)\b", re.I
)
# Zalando PDPs carry no product:price meta; the price sits in og:description
# ("... - brown for \u20ac13.59 (01/09/2026). Free shipping ...").
_ZALANDO_PDP_PRICE = re.compile(r"for\s*\u20ac\s*([\d.,]+)")



def _try_douglas(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Douglas (douglas.de) search results.

    Structure (verified live 2026-09-14):
      .product-grid  >  .product-tile  >  .product-tile__details-container

    Two traps this guards against:

    1. **SEO footer links.** A naive ``a[href*="/p/"]`` sweep over the page finds
       ~72 links on a typical search page, but only ~52 are real product tiles —
       the remaining ~20 live in ``.seo-footer__column`` and are category/SEO
       links, not results. Scoping to ``.product-grid`` excludes them.

    2. **Hashed CSS-module class names.** Douglas ships hashed classes
       (``_9b02884cbd4bdbe2``) for the inner brand/name/price nodes, so there is
       no stable ``.product-tile__brand``/``__name``/``__price`` to select. The
       stable surface is the tile's own text: its FIRST line is the full
       accessible product title (e.g. "Lippenstift fuer Unisex DIOR Rouge Dior
       Velvet 999 - 999"), and the price line carries UVP, selling price and a
       parenthesised unit price.

    NOTE (critical, see FETCHER_PLAYBOOK / DISCOVERY_PLAYBOOK): Douglas has **no
    no-results page**. A nonsense query still renders a populated
    ``.product-grid`` of unrelated fallback products under a confident heading
    ("99 ERGEBNISSE FUER „QWERTZUIOP“"). So a non-empty return from this
    function is NOT evidence that the query matched anything. Relevance scoring,
    not result count, is the signal on this host.
    """
    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    grids = soup.select(".product-grid")
    tiles = []
    for g in grids:
        tiles.extend(g.select(".product-tile"))
    if not tiles:
        # Search can redirect to a category/brand listing that still uses tiles
        # but not the .product-grid wrapper. Fall back to tiles anywhere EXCEPT
        # the SEO footer.
        tiles = [
            tl for tl in soup.select(".product-tile")
            if not tl.find_parent(class_=re.compile(r"seo-footer", re.I))
        ]

    for tile in tiles:
        if len(results) >= max_results:
            break

        link = tile.find("a", href=re.compile(r"/p/"))
        if link is None:
            continue
        href = (link.get("href") or "").split("?")[0].strip()
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)
        url_full = f"https://www.douglas.de{href}" if href.startswith("/") else href

        raw = tile.get_text(separator="\n", strip=True)

        # Title: hashed CSS-module classes mean there is no stable
        # .product-tile__name selector, and the visible title lives in a
        # visually-hidden leaf <span>. Pick it structurally: the first
        # childless descendant whose text is substantial, not a number, and
        # carries no price. Do NOT hardcode the hashed class — it changes on
        # every deploy. (See FETCHER_PLAYBOOK douglas.de profile.)
        title = ""
        for el in tile.find_all(True):
            if el.find(True) is not None:
                continue
            s = " ".join((el.get_text() or "").split())
            if len(s) > 15 and not s[:1].isdigit() and "\u20ac" not in s:
                title = s[:180]
                break
        if not title:
            lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
            if not lines:
                continue
            title = lines[0]

        # Price: drop the parenthesised unit price ("(11.140,00 EUR / 1 kg)"),
        # then take the LAST remaining amount — with a UVP present the order is
        # [UVP, selling price]; without one there is a single amount.
        price = None
        price_text = re.sub(r"\([^)]*\)", " ", raw)
        amounts = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}\s*€", price_text)
        if amounts:
            price = amounts[-1].replace("\xa0", " ").strip()

        results.append(
            SearchResult(
                rank=len(results) + 1,
                title=title,
                price=price,
                url=url_full,
                sponsored=_detect_sponsored(tile),
            )
        )

    return results


def _try_zalando(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Zalando (zalando.ie / zalando.co.uk) search results.

    THE TRAP this exists to prevent: Zalando's no-results page renders NO search
    results but pads itself with two recommendation carousels ("Recommended for
    you" / "Most popular - Our customers bought"). Those carousel cards are real
    products with real prices and real PDP URLs, sitting in the SAME <article>
    elements inside the SAME `ul[role="list"]` structure as genuine results — so
    neither the tag, the container, nor the result count can tell them apart. A
    gibberish control query returned 15 confident phantom results (baggy jeans),
    and a real conversational query returned 4 phantom trainers when its true
    answer was zero. The phantom set also ROTATES between runs, so it cannot be
    caught by eyeballing counts either.

    The only dependable discriminator is the sentence Zalando prints on a genuine
    no-hits page and nowhere else, so that string gates the whole extractor (it is
    also the host profile's no-results marker → ZERO_CONFIRMED). The grid itself is
    read only from the `product-count` header down to the first carousel heading.
    The host is in _DEDICATED_EXTRACTOR_HOSTS, so the generic/LLM fallbacks never run.

    Card text is line-structured with no data-testid hooks (class names are hashed
    per build and must NOT be used), e.g.:

        Bestseller / Top rated / heart_outlined      <- badges (variable)
        adidas Performance                           <- brand
        GALAXY 8 M - Road running shoes - core black <- name
        From
        \u20ac49.95                                      <- current price
        Reference price: / \u20ac55.00 / up to / -9%      <- original price (ignored)

    Rather than blacklisting badge words (an open-ended set), brand+name are taken
    as the last two non-empty lines BEFORE the first price line - the same
    "lines before price" approach used by _try_ahlens. Title = "brand name" so
    BRAND_SEARCH / DIRECT_MATCH queries that include the brand can match, matching
    the _try_imerco / _try_manufactum / _try_huckberry convention.

    No generic junk filter is applied: once scoped to a confirmed results container
    its title-length heuristic only risks dropping legitimately short real names
    (the baechli-bergsport.ch lesson).
    """
    page_text = soup.get_text(" ", strip=True)
    if _ZALANDO_NO_RESULTS_MARKER in page_text:
        logger.info("Zalando: authoritative no-results marker present -> 0 results")
        return []

    # PDP short-circuit. An exact article code (e.g. "PI954K02Z-O11") redirects
    # straight to that product's detail page - correct, desirable search behaviour
    # (judge: PDP-redirect on an exact-identifier query = PASS). _analyse_page now
    # catches this first (token-based _redirect_kind + _extract_pdp); this stays as a
    # second guard. Before, the article code embedded in the destination slug
    # (".../...-pi954k02z-o11.html") hid the redirect, so extraction would
    # otherwise run against the PDP and return its "similar products" carousels as
    # search results - measured: 52 <article> elements, 15 phantom results, on a
    # page with no search grid at all. Detect the PDP by its og:type and return the
    # ONE product it represents.
    og_type = soup.find("meta", attrs={"property": "og:type"})
    if og_type and "product" in (og_type.get("content") or "").lower():
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else ""
        if not title:
            og_title = soup.find("meta", attrs={"property": "og:title"})
            title = (og_title.get("content") or "").split(" - Zalando")[0] if og_title else ""
        if not title:
            return []

        price = None
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc:
            m = _ZALANDO_PDP_PRICE.search(og_desc.get("content") or "")
            if m:
                price = f"\u20ac{m.group(1)}"

        link = ""
        canon = soup.find("link", attrs={"rel": "canonical"})
        if canon and canon.get("href"):
            link = canon["href"].strip()
        if not link:
            og_url = soup.find("meta", attrs={"property": "og:url"})
            if og_url and og_url.get("content"):
                link = og_url["content"].strip()

        logger.info("Zalando: PDP redirect detected -> 1 result (%s)", title[:60])
        return [SearchResult(rank=1, title=title[:200], url=link, price=price)]

    results: list[SearchResult] = []
    seen: set[str] = set()

    # Scope: the real grid follows the "N items" count header. Recommendation
    # carousels come after it under their own headings ("Recommended for you",
    # "Most popular - Our customers bought"), so collect <article>s in document order
    # from the count header and stop at the first carousel heading. No count header
    # means this is not a results grid we can trust -> [] (ZERO_UNVERIFIED upstream,
    # unless the no-results marker is present).
    count_el = soup.select_one('[data-testid="product-count"]')
    if count_el is None:
        logger.info("Zalando: no product-count header -> not a trusted results grid")
        return []
    cards: list[Tag] = []
    for el in count_el.find_all_next(["article", "h2", "h3", "h4"]):
        if el.name != "article":
            if _RECO_HEADING_RE.search(el.get_text(" ", strip=True)):
                break
            continue
        cards.append(el)

    for card in cards:
        link = None
        for a in card.select("a[href]"):
            href = (a.get("href") or "").strip()
            if ".html" in href:
                link = href
                break
        if not link:
            continue
        key = link.split("?")[0].split("#")[0]
        if key in seen:
            continue

        lines = [ln.strip() for ln in card.get_text("\n").split("\n")]
        lines = [ln for ln in lines if ln]

        price = None
        price_idx = None
        for i, ln in enumerate(lines):
            if _ZALANDO_PRICE_LINE.match(ln):
                price, price_idx = ln, i
                break

        # brand + name = last two meaningful lines before the price block
        head = lines[:price_idx] if price_idx is not None else lines
        head = [
            ln for ln in head
            if ln.lower() not in ("from", "heart_outlined", "up to")
            and not _ZALANDO_ORIGINAL_PRICE_LABEL.match(ln)
            and not ln.startswith("-")
        ]
        if len(head) >= 2:
            brand, name = head[-2], head[-1]
        elif head:
            brand, name = "", head[-1]
        else:
            continue
        if not name:
            continue
        title = name if (brand and name.lower().startswith(brand.lower())) else f"{brand} {name}".strip()

        seen.add(key)
        results.append(
            SearchResult(rank=len(results) + 1, title=title[:200], url=link, price=price,
                         sponsored=_detect_sponsored(card))
        )
        if len(results) >= max_results:
            break

    return results


def _try_huckberry(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Huckberry (huckberry.com) search results.

    Huckberry is React-rendered behind a Cloudflare "Just a moment..." JS
    challenge that only clears for a *headed* Chromium session (see
    `_HEADED_CHROMIUM_HOSTS`). Once rendered, each product tile has a content
    block with a brand link `a.ProductTileContent__brand-link`, a product name
    anchor pointing at `/store/<brand>/category/p/<id>-<slug>`, and a price in
    `span.ProductTileContent__price`. Products appear in multiple tiles (e.g. a
    featured row + the main grid), so we dedupe by the numeric product id.

    Scoping to these content blocks is authoritative: a genuine no-results page
    ("We couldn't find …") renders ZERO brand links / price spans, so returning
    `[]` correctly signals a search miss. The host is in
    `_DEDICATED_EXTRACTOR_HOSTS` so an empty result short-circuits the
    generic/LLM fallbacks (phantom-result guard).
    """
    prod_href_re = re.compile(r"/store/.+/p/(\d+)-")
    price_re = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")

    results: list[SearchResult] = []
    seen_ids: set[str] = set()

    for brand_link in soup.select("a.ProductTileContent__brand-link"):
        # Climb to the tile container that holds this product's price.
        cont = brand_link
        for _ in range(6):
            cont = cont.parent
            if cont is None:
                break
            if cont.select_one("span.ProductTileContent__price"):
                break
        if cont is None:
            continue

        prod = cont.find("a", href=prod_href_re)
        if not prod:
            continue
        href = (prod.get("href") or "").split("?")[0].split("#")[0].strip()
        m = prod_href_re.search(href)
        if not m:
            continue
        pid = m.group(1)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        brand = brand_link.get_text(" ", strip=True)
        name = prod.get_text(" ", strip=True)
        if not name:
            continue
        # Title = brand + product name, unless the name already leads with the brand.
        title = name if name.lower().startswith(brand.lower()) else f"{brand} {name}".strip()

        price = None
        price_el = cont.select_one("span.ProductTileContent__price")
        if price_el:
            pm = price_re.search(price_el.get_text(" ", strip=True))
            if pm:
                price = pm.group(0).replace(" ", "")
        if price is None:
            price = _extract_price(cont)

        url_full = f"https://huckberry.com{href}" if href.startswith("/") else href
        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:120],
            url=url_full,
            price=price,
            sponsored=_detect_sponsored(cont),
        ))
        if len(results) >= max_results:
            break

    # Scoped to real tiles: no generic junk filter (it drops short real names).
    logger.debug("Strategy 0 (Huckberry site-specific): found %d results", len(results))
    return results


def _try_ahlens(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Åhléns (ahlens.se) search results.

    The real search grid lives in <section id="product-rain-section"> (inside the
    "tab-products" tabpanel). Recommendation/cross-sell carousels — notably the
    mini-cart "Du kanske också gillar" panel, which is full of unrelated skönhet
    products — live OUTSIDE this section. Scoping extraction to the section is what
    stops the fetcher from silently returning the cart drawer's beauty recommendations
    instead of the actual search matches.

    Each card (`div.group/product-card`) renders its text as brand / name / price,
    with sale cards prepending a "-NN%" badge and adding "Rea" + a "Lägsta pris 30
    dagar" original-price line. Title = brand + name; price = the current price.
    """
    section = soup.select_one("#product-rain-section") or soup.select_one("#tab-products")
    if section is None:
        return []

    results: list[SearchResult] = []
    seen: set[str] = set()
    badge_re = re.compile(r"^-?\d+\s*%$")
    # Lines that are card chrome, not part of the product name: sale labels,
    # stock-status badges ("Endast i varuhus" = in-store only), and the variant
    # swatch block ("Produkten finns i färgerna:" + colour names follow).
    label_re = re.compile(
        r"^(rea|lägsta pris|ord\.?\s*pris|nyhet|fler färger|finns i färgerna"
        r"|produkten finns|endast (i varuhus|online)|finns i varuhus|köp online"
        r"|slutsåld|fåtal kvar)",
        re.I,
    )
    price_line_re = re.compile(r"\d[\d\s .,]*\s*kr", re.I)

    def _is_price_line(ln: str) -> bool:
        return bool(price_line_re.search(ln) or _PRICE_RE.search(ln))

    for card in section.find_all(class_="group/product-card"):
        link = card.find("a", href=re.compile(r"/produkter/"))
        if not link:
            continue
        href = (link.get("href") or "").split("#")[0].strip()
        if not href or href in seen:
            continue
        seen.add(href)

        lines = [ln.strip() for ln in card.get_text("\n", strip=True).split("\n") if ln.strip()]

        # Title = brand + product name: the lines BEFORE the first price line.
        # Everything after the price (variant swatches, "Lägsta pris", the
        # struck-through original price) is excluded by construction. Leading
        # badges ("-40%", "Endast i varuhus", "Rea") are then stripped.
        price_idx = next((i for i, ln in enumerate(lines) if _is_price_line(ln)), len(lines))
        title_lines = [
            ln for ln in lines[:price_idx]
            if not badge_re.match(ln) and not label_re.match(ln)
        ]
        title = " ".join(title_lines).strip()
        if not title or len(title) < 4:
            continue

        # Price: the first price-bearing line is the current (sale) price; the
        # "Lägsta pris 30 dagar" original-price line is skipped via label_re.
        # Normalise the Swedish non-breaking-space thousands separator ("1 000 kr")
        # which the generic price regex would otherwise truncate to "000 kr".
        price = None
        for ln in lines:
            if label_re.match(ln):
                continue
            m = re.search(r"\d[\d\s .,]*\s*kr", ln)
            if m:
                price = re.sub(r"[\s ]+", " ", m.group(0)).strip()
                break
        if price is None:
            price = _extract_price(card)
        url_full = f"https://www.ahlens.se{href}" if href.startswith("/") else href

        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:120],
            url=url_full,
            price=price,
            sponsored=_detect_sponsored(card),
        ))
        if len(results) >= max_results:
            break

    # Scoped to #product-rain-section: no generic junk filter.
    logger.debug("Strategy 0 (Åhléns site-specific): found %d results", len(results))
    return results


def _try_avoca(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Avoca (avoca.com) search results.

    Avoca is Shopify with the **Boost AI Search & Discovery** widget. The search
    grid renders client-side as `div.boost-sd__product-item` cards, each with a
    `.boost-sd__product-title`, a `.boost-sd__product-price` line (e.g. "Regular
    price €59.99 €59.99", or a sale price under `--sale`), and a product link
    `a.boost-sd__product-link` → `/products/<handle>`.

    Scoping to `boost-sd__product-item` is authoritative: a genuine no-results
    page ("0 results found for …") renders ZERO such items, so returning `[]` here
    correctly signals a search miss instead of falling through to recommendation
    carousels. The host is registered in `_DEDICATED_EXTRACTOR_HOSTS` so an empty
    result never falls through to the generic/LLM fallbacks (phantom-result guard).
    """
    items = soup.select("div.boost-sd__product-item")
    if not items:
        return []

    results: list[SearchResult] = []
    seen: set[str] = set()
    euro_re = re.compile(r"€\s?\d[\d.,]*")

    for card in items:
        link = card.select_one("a.boost-sd__product-link[href*='/products/']") \
            or card.select_one("a[href*='/products/']")
        if not link:
            continue
        href = (link.get("href") or "").split("?")[0].split("#")[0].strip()
        if not href or href in seen:
            continue
        seen.add(href)

        title_el = card.select_one(".boost-sd__product-title")
        title = title_el.get_text(" ", strip=True) if title_el else ""
        if not title or len(title) < 3:
            continue

        price = None
        price_el = card.select_one(".boost-sd__product-price--sale") \
            or card.select_one(".boost-sd__product-price")
        if price_el:
            m = euro_re.search(price_el.get_text(" ", strip=True))
            if m:
                price = m.group(0).replace(" ", "")
        if price is None:
            price = _extract_price(card)

        url_full = f"https://avoca.com{href}" if href.startswith("/") else href
        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:120],
            url=url_full,
            price=price,
            sponsored=_detect_sponsored(card),
        ))
        if len(results) >= max_results:
            break

    # Scoped to Boost product items: no generic junk filter.
    logger.debug("Strategy 0 (Avoca site-specific): found %d results", len(results))
    return results


def _try_baechli(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Bächli Bergsport (baechli-bergsport.ch) search results.

    Server-rendered (Rent-a-Shop platform) — works fully on a static fetch.
    Results grid: `<div class="grid multiline products"><article>...</article></div>`.
    Each card: `<p>Brand</p><h3><a href="...">Name</a></h3><span>CHF <span>99.00</span></span>`.

    THE TRAP (caught at 4a): the generic price extractor looks for a class
    containing "price"/"cost"/"amount"/"money", but the price span here has NO
    class — it's a bare `<span>CHF <span>99.00</span></span>`. The generic
    extractor falls through to its fallback price regex which doesn't recognize
    "CHF", so every result silently loses its price. Parse "CHF" + amount
    directly off the card text instead.

    A SEPARATE, more serious trap: an exact-title query that uniquely matches
    one product redirects straight to that product's detail page (no grid at
    all) — handled upstream by `_extract_pdp` /
    `_PDP_REDIRECT_HOSTS`, not here.

    Title = product name only (brand lives in a separate `<p>` sibling, not
    needed for DIRECT_MATCH/BRAND_SEARCH since brand is also a standalone query).
    """
    chf_re = re.compile(r"CHF\s*([\d.,]+)")
    results: list[SearchResult] = []
    seen: set[str] = set()

    for article in soup.select("div.grid.products article"):
        name_el = article.select_one("h3 a")
        if not name_el:
            continue
        href = (name_el.get("href") or "").split("#")[0].strip()
        if not href or href in seen:
            continue
        seen.add(href)

        title = name_el.get_text(" ", strip=True)
        if not title:
            continue

        price = None
        m = chf_re.search(article.get_text(" ", strip=True))
        if m:
            price = f"CHF {m.group(1)}"

        url_full = f"https://www.baechli-bergsport.ch{href}" if href.startswith("/") else href
        results.append(SearchResult(rank=len(results) + 1, title=title[:120], url=url_full, price=price,
                                    sponsored=_detect_sponsored(article)))
        if len(results) >= max_results:
            break

    # Do NOT run the generic _filter_junk_results here: its `len(title) < 8`
    # heuristic (meant to drop nav/chrome junk on unscoped strategies) silently
    # dropped genuine short product names on this site (e.g. "Talon 6", 7 chars),
    # producing a false ranking gap. This extractor is already scoped to the real
    # results container, so every <h3><a> here is a genuine product — no filter needed.
    logger.debug("Strategy 0 (Bächli site-specific): found %d results", len(results))
    return results


def _try_cotswoldoutdoor(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Cotswold Outdoor (cotswoldoutdoor.com) search/listing pages.

    THE TRAP (caught at 4a): the generic price extractor's fallback regex matches
    the FIRST digit-then-currency-symbol pattern in the card's full text, but each
    card also renders a star-rating review COUNT (e.g. "0", "7", "15") immediately
    before the price block. On cards with a low review count the regex matches
    "7 £" (count + symbol) instead of "£240.00" (the real price), silently
    corrupting price data on a meaningful fraction of results.

    Cotswold uses stable `data-testid` hooks (works on both the search/lister grid
    and on a brand/category landing page, which share the same tile markup):
      - card:  `div[data-testid="product-tile-vertical"]`
      - link:  first `a[href*="/p/"]` inside the card
      - title: `div[class*="product-tile__title"]` (brand `<strong>` + name span)
      - price: `span[data-testid="product-tile-vertical-price-actual-price"]`
               (current/sale price); falls back to
               `span[data-testid="product-tile-vertical-price-previous-price"]`
               (RRP) if no actual-price span is present.

    Scoping to the data-testid price spans sidesteps the review-count collision
    entirely — no full-text regex is needed.
    """
    results: list[SearchResult] = []
    seen: set[str] = set()

    for card in soup.select('div[data-testid="product-tile-vertical"]'):
        link = card.select_one('a[href*="/p/"]')
        if not link:
            continue
        href = (link.get("href") or "").split("#")[0].strip()
        if not href or href in seen:
            continue
        seen.add(href)

        title_el = card.select_one('div[class*="product-tile__title"]')
        title = title_el.get_text(" ", strip=True) if title_el else link.get("href", "")
        if not title:
            continue

        price = None
        price_el = card.select_one('span[data-testid="product-tile-vertical-price-actual-price"]')
        if not price_el:
            price_el = card.select_one('span[data-testid="product-tile-vertical-price-previous-price"]')
        if price_el:
            price = price_el.get_text(" ", strip=True)

        url_full = f"https://www.cotswoldoutdoor.com{href}" if href.startswith("/") else href
        results.append(SearchResult(rank=len(results) + 1, title=title[:120], url=url_full, price=price,
                                    sponsored=_detect_sponsored(card)))
        if len(results) >= max_results:
            break

    logger.debug("Strategy 0 (Cotswold Outdoor site-specific): found %d results", len(results))
    return results


def _try_manufactum(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Manufactum (manufactum.de) search results.

    THE TRAP (caught at 4a): on a genuine no-results query Manufactum's search
    header reads "Suchergebnis für »…« (0)" but the page is padded with a large
    grid of fallback/recommendation products (oak furniture, shoes, …). The
    generic strategy scrapes those phantoms and masks the search failure. So the
    header count is authoritative: (0) → `[]` (the host profile's no-results marker
    makes that ZERO_CONFIRMED); (N) → at most N tiles, since anything past N is
    padding; header missing / unparseable → `[]`, which surfaces as ZERO_UNVERIFIED.
    Never scrape "all tiles" without a parsed count.

    Manufactum exposes STABLE `data-test-*` hooks (the CSS module class names are
    hashed and change per build, so we must NOT key off them):
      - card:    `div[data-test-sell-product-tile="true"]`
      - link:    `a[data-test-sell-product-link="true"]` → `/<slug>-a<id>/`
      - name:    `span[data-test-sell-product-name="true"]` (self-contained title,
                 brand usually embedded — no brand prefix needed)
      - price:   `span[data-test-stelar-price-price="true"]` (e.g. "39,90 €")

    Registered in `_DEDICATED_EXTRACTOR_HOSTS` so `[]` never falls through to the
    generic/LLM fallbacks.
    """
    # Header count → authoritative (phantom-result guard).
    header = soup.find("h1")
    m = re.search(r"\((\d[\d.]*)\)\s*$", header.get_text(" ", strip=True)) if header else None
    if not m:
        logger.info("Strategy 0 (Manufactum site-specific): results header unparseable -> not trusting tiles")
        return []
    header_count = _parse_count(m.group(1)) or 0
    if header_count == 0:
        logger.debug("Strategy 0 (Manufactum site-specific): header reports (0) -> empty")
        return []
    max_results = min(max_results, header_count)

    results: list[SearchResult] = []
    seen: set[str] = set()

    for tile in soup.select('div[data-test-sell-product-tile="true"]'):
        link = tile.select_one('a[data-test-sell-product-link="true"]') \
            or tile.select_one('a[href*="-a"]')
        name_el = tile.select_one('span[data-test-sell-product-name="true"]')
        if not link or not name_el:
            continue
        href = (link.get("href") or "").split("?")[0].split("#")[0].strip()
        if not href or href in seen:
            continue
        seen.add(href)

        name = name_el.get_text(" ", strip=True)
        if not name or len(name) < 3:
            continue
        # Title = brand + name (unless the name already leads with the brand), same
        # convention as _try_ahlens/_try_huckberry. The manufacturer lives in a
        # separate span, NOT the title — without it, BRAND_SEARCH queries (e.g.
        # "Armedangels") score as false misses because the brand never appears in
        # the title. Composing brand+name keeps DIRECT_MATCH valid too (the judge
        # does a containment check; exact product names stay a substring).
        brand_el = tile.select_one('span[data-test-sell-product-manufacturer="true"]')
        brand = brand_el.get_text(" ", strip=True) if brand_el else ""
        if brand and not name.lower().startswith(brand.lower()):
            title = f"{brand} {name}"
        else:
            title = name

        price = None
        price_el = tile.select_one('span[data-test-stelar-price-price="true"]')
        if price_el:
            price = price_el.get_text(" ", strip=True) or None
        if price is None:
            price = _extract_price(tile)

        url_full = f"https://www.manufactum.de{href}" if href.startswith("/") else href
        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:120],
            url=url_full,
            price=price,
            sponsored=_detect_sponsored(tile),
        ))
        if len(results) >= max_results:
            break

    # Scoped to data-test tiles: no generic junk filter.
    logger.debug("Strategy 0 (Manufactum site-specific): found %d results", len(results))
    return results


def _try_imerco(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Imerco (imerco.dk) search results.

    Imerco is a Next.js client-rendered site; the search grid renders into product
    cards with CSS-module class names whose suffixes are hashed per build, so we key
    off the STABLE class-name prefixes via substring match:
      - card:   div[class*="ProductHit_wrapper"]
      - link:   a[class*="ProductHit_card"] -> /<slug>?id=<id> (relative)
      - brand:  span[class*="NewProductCard_brand"]
      - name:   span[class*="NewProductCard_name"]
      - price:  span[class*="ProductPrices_emphasized"] (first = displayed price;
                member + non-member prices each render as an emphasized span)

    Title = brand + name (e.g. "Eva Trio Stainless Steel Gryde") so BRAND_SEARCH and
    DIRECT_MATCH queries (which include the brand) match; same convention as
    _try_manufactum/_try_ahlens.

    No-results page renders ZERO ProductHit cards and no recommendation carousel
    using that class (header "0 resultater"), so scoping to the card class is
    naturally authoritative — registered in _DEDICATED_EXTRACTOR_HOSTS.
    """
    results: list[SearchResult] = []
    seen: set[str] = set()

    for card in soup.select('div[class*="ProductHit_wrapper"]'):
        link = card.select_one('a[class*="ProductHit_card"]') \
            or card.select_one('a[href*="?id="]')
        if not link:
            continue
        href = (link.get("href") or "").strip()
        if not href:
            continue
        key = href.split("#")[0]
        if key in seen:
            continue
        seen.add(key)

        brand_el = card.select_one('[class*="NewProductCard_brand"]')
        name_el = card.select_one('[class*="NewProductCard_name"]')
        brand = brand_el.get_text(" ", strip=True) if brand_el else ""
        name = name_el.get_text(" ", strip=True) if name_el else ""
        if not name:
            continue
        if brand and not name.lower().startswith(brand.lower()):
            title = f"{brand} {name}"
        else:
            title = name

        price = None
        price_el = card.select_one('[class*="ProductPrices_emphasized"]')
        if price_el:
            val = price_el.get_text(" ", strip=True)
            if val:
                price = f"{val} kr"
        if price is None:
            price = _extract_price(card)

        url_full = f"https://www.imerco.dk{href}" if href.startswith("/") else href
        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:120],
            url=url_full,
            price=price,
            sponsored=_detect_sponsored(card),
        ))
        if len(results) >= max_results:
            break

    # Scoped to ProductHit cards: no generic junk filter.
    logger.debug("Strategy 0 (Imerco site-specific): found %d results", len(results))
    return results


def _try_bergzeit(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Bergzeit search results.

    Bergzeit product anchors use the URL pattern `/p/<slug>/<id>/`. Each product
    appears multiple times (image link, title link, per-size variant links), so we
    deduplicate by the numeric product id. The link text carries
    "<brand> | <category>\\n<product name>\\n<price>".
    """
    results: list[SearchResult] = []
    seen_ids: set[str] = set()

    id_re = re.compile(r"^/p/[^/]+/(\d+)/")

    # Scope to the actual search-results grid. Product cards carry the class
    # `products-list__product-box`; promo/recommendation `/p/` links (e.g. the
    # footer voucher teaser) live outside it and must NOT be treated as results.
    product_links = soup.find_all("a", class_=re.compile(r"products-list__product-box"))
    if not product_links:
        # Fallback: anchors inside the results wrapper, excluding footer teasers.
        # Never the whole page: on a "Deine Suche ergab leider keine Treffer" page the
        # only /p/ anchors are the recommendation carousel (12 phantom results once).
        wrapper = soup.select_one(
            ".products-list-page__products-list-wrapper, .products-list-page__main, .products-list"
        )
        if wrapper is None:
            return []
        product_links = [
            a for a in wrapper.find_all("a", href=True)
            if id_re.match(a.get("href", ""))
            and not a.find_parent(class_=re.compile(r"footer-teaser"))
            and not _is_inside_reco(a)
        ]

    for link in product_links:
        if not id_re.match((link.get("href") or "")):
            continue
        href = (link.get("href") or "").split("#")[0].strip()
        m = id_re.match(href)
        if not m:
            continue
        pid = m.group(1)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        url_full = f"https://www.bergzeit.de{href}" if href.startswith("/") else href

        # Title: link text is "<brand> | <category>\n<product name>\n<price>".
        # Drop a leading "Größen" size-picker label and the trailing price line.
        raw = link.get_text(separator="\n", strip=True)
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        lines = [ln for ln in lines if ln.lower() != "größen"]
        # Price: search the whole card container, not just the anchor — on many
        # cards the price node sits as a sibling of the product-box link.
        card = link.find_parent(class_=re.compile(r"products-list__element")) or link.parent or link
        price = _extract_price(card) or _extract_price(link)
        # Build title from brand/name lines, excluding any line that is just a price
        title_lines = [
            ln for ln in lines
            if not _PRICE_RE.search(ln) and not _PRICE_FALLBACK_RE.search(ln)
        ]
        title = " ".join(title_lines).strip()
        # Strip sale-card noise that trails the product name: discount badges,
        # availability hints, and size runs (alpha "XXS XS S M L", numeric
        # "38 39 40", or pipe/decimal "41 | 42 | 42.5").
        title = re.sub(r"\+?\s*verf[üu]gbar in vielen Gr[öo][ßs]en", "", title, flags=re.I)
        title = re.sub(r"\bDu sparst\s*(?:bis\s*)?\d+\s*%", "", title, flags=re.I)
        title = re.sub(
            r"\b(?:XXS|XS|S|M|L|XL|XXL|XXXL|3XL|4XL)\b(?:\s*\|?\s*(?:XXS|XS|S|M|L|XL|XXL|XXXL|3XL|4XL)\b)+",
            "",
            title,
        )
        # Trailing numeric/pipe size run (2+ size tokens, optional decimals).
        title = re.sub(r"(?:\b\d{1,3}(?:[.,]\d)?\b\s*\|?\s*){2,}$", "", title)
        title = re.sub(r"\s*\|\s*", " | ", title)
        title = re.sub(r"\s{2,}", " ", title).strip(" |+")

        if not title or len(title) < 4:
            continue

        results.append(SearchResult(
            rank=len(results) + 1,
            title=title[:120],
            url=url_full,
            price=price,
            sponsored=_detect_sponsored(card),
        ))
        if len(results) >= max_results:
            break

    return results


def _try_lyko(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract product cards from Lyko search results.

    Lyko uses a stable class `link-product-page` on product anchor tags.
    Each product appears twice (image link + price link) — we deduplicate by URL.
    """
    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    def _card_text(a) -> str:
        """Text of the anchor's product-card container (climbs up to 2 levels for a kr price)."""
        node = a.find_parent()
        if node is None:
            return a.get_text(separator=" ", strip=True)
        t = node.get_text(separator=" ", strip=True)
        if " kr" not in t.lower():
            gp = node.find_parent()
            if gp is not None:
                t = gp.get_text(separator=" ", strip=True)
        return t

    product_links = soup.find_all("a", class_=re.compile(r"link-product-page", re.I))
    # Fallback: a search query can REDIRECT to a category page (e.g. "herrparfym"
    # -> /sv/parfym/herrparfym), where products use a hashed class (not
    # link-product-page) and deeper /sv/.../... URLs. The reliable discriminator
    # between a real product card and a category-filter chip is that the product
    # card's parent contains a "kr" price; chips do not.
    if not product_links:
        product_links = [
            a for a in soup.find_all("a", href=True)
            if a.get("href", "").startswith("/sv/")
            and len([s for s in a.get("href", "").split("?")[0].split("/") if s]) >= 3
            and " kr" in _card_text(a).lower()
        ]

    for link in product_links:
        href = (link.get("href") or "").split("?")[0].strip()
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        url_full = f"https://lyko.com{href}" if href.startswith("/") else href

        # Title: prefer the anchor's own text (clean on search pages); fall back to
        # the card text on category pages where the anchor wraps only the image.
        raw = link.get_text(separator=" ", strip=True)
        if len(raw.strip()) < 8:
            raw = _card_text(link)
        sponsored = bool(re.search(r"\bSponsrad\b", raw + " " + _card_text(link), re.I))
        # Remove promo badges: "Combo Deal 20%", "Se villkor på produktsidan", "Reapris X kr", "Utan kampanj X kr"
        text = re.sub(r"Combo Deal\s*\d+%", "", raw, flags=re.I)
        # Leading promo/badge labels that prefix the product name in the card.
        text = re.sub(r"\b(WOW-pris|G[åa]va p[åa] k[öo]pet|Sponsrad|Nyhet|Rek\.?\s*pris|Rekommenderat\s*pris)\b", "", text, flags=re.I)
        text = re.sub(r"Se villkor p[åa] produktsidan", "", text, flags=re.I)
        text = re.sub(r"Reapris\s*[\d\s,.]+kr", "", text, flags=re.I)
        text = re.sub(r"Utan kampanj\s*[\d\s,.]+kr", "", text, flags=re.I)
        text = re.sub(r"Utan paketpris[:\s]*[\d\s,.]+kr", "", text, flags=re.I)
        text = re.sub(r"Kampanj\s*\d+%", "", text, flags=re.I)
        text = re.sub(r"[\d][\d\s,.]*\s*kr", "", text)
        text = re.sub(r"\bK[ÖO]P\b", "", text, flags=re.I)
        text = re.sub(r"\s{2,}", " ", text).strip()

        # Must look like a real product name (brand + name, at least 8 chars, not a nav link)
        if not text or len(text) < 8:
            continue
        # Skip obvious non-product strings
        if any(skip in text.lower() for skip in ("se profilsida", "kontakta", "mina sidor", "kundservice", "villkor")):
            continue

        # Price: the displayed price is NOT inside the anchor — it lives in the
        # parent product-card container (a classless <span>, hydrated by JS).
        # Read the card text and pick the CURRENT price:
        #   - "Reapris N kr" (Combo Deal campaign price) wins if present;
        #   - otherwise the first standalone "N kr" after stripping the
        #     original-price lines ("Rek. pris N kr" / "Rekommenderat pris N kr"
        #     / "Utan kampanj N kr").
        price = None
        card_text = _card_text(link)
        reapris_m = re.search(r"Reapris\s*(\d[\d\s,.]*\s*kr)", card_text, flags=re.I)
        if reapris_m:
            price = reapris_m.group(1).strip()
        else:
            stripped = re.sub(
                r"(Rek\.?\s*pris|Rekommenderat\s*pris|Utan\s*kampanj)\s*\d[\d\s,.]*\s*kr",
                "", card_text, flags=re.I,
            )
            price_m = re.search(r"(\d[\d\s,.]*\s*kr)", stripped)
            if price_m:
                price = re.sub(r"\s+", " ", price_m.group(1)).strip()

        results.append(SearchResult(
            rank=len(results) + 1,
            title=text[:120],
            url=url_full,
            price=price,
            sponsored=sponsored,
        ))
        if len(results) >= max_results:
            break

    return results


def _try_groupon(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    """Extract deal cards from Groupon search results."""
    results: list[SearchResult] = []

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
    """Products described in JSON-LD, in the page's own order (ItemList.position first).

    Structured data is clean product data, so the generic junk filter (title length,
    junk words) is not applied: it would drop short real names like "Talon 6".
    """
    results: list[SearchResult] = []
    seen: set[str] = set()
    for data in _jsonld_blocks(soup):
        _collect_products_jsonld(data, results, max_results, seen)
        if len(results) >= max_results:
            break

    results = results[:max_results]
    for i, r in enumerate(results, 1):
        r.rank = i
    logger.debug("Strategy 1 (Schema.org): found %d results", len(results))
    return results


def _ld_result(node: dict) -> Optional[SearchResult]:
    name = _ld_str(node.get("name"))
    if not name:
        return None
    snippet = _ld_str(node.get("description"))[:300] or None
    url = _ld_str(node.get("url")) or _ld_str(node.get("@id")) or None
    return SearchResult(rank=0, title=name[:300], price=_ld_price(node), snippet=snippet, url=url)


def _ld_add(result: Optional[SearchResult], results: list[SearchResult], seen: set[str]) -> None:
    if result is None:
        return
    key = (result.url or result.title).split("#")[0].casefold()
    if key in seen:
        return
    seen.add(key)
    results.append(result)


def _collect_products_jsonld(
    data: object,
    results: list[SearchResult],
    max_results: int,
    seen: Optional[set[str]] = None,
    _depth: int = 0,
) -> None:
    """Collect Product nodes. ItemLists are walked once, sorted by ListItem.position;
    a Product's own children (variants, related products, offers) are never collected."""
    seen = seen if seen is not None else set()
    if len(results) >= max_results or _depth > 12:
        return

    if isinstance(data, list):
        for item in data:
            _collect_products_jsonld(item, results, max_results, seen, _depth + 1)
        return
    if not isinstance(data, dict):
        return

    types = _ld_types(data)
    if types & _LD_PRODUCT_TYPES:
        _ld_add(_ld_result(data), results, seen)
        return

    if "ItemList" in types or "OfferCatalog" in types:
        elems = data.get("itemListElement") or []
        if isinstance(elems, dict):
            elems = [elems]
        if not isinstance(elems, list):
            return

        def _pos(el) -> float:
            if isinstance(el, dict):
                try:
                    return float(el.get("position"))
                except (TypeError, ValueError):
                    pass
            return float("inf")

        for el in sorted(elems, key=_pos):  # stable: unpositioned keep DOM order
            if len(results) >= max_results:
                return
            if not isinstance(el, dict):
                continue
            el_types = _ld_types(el)
            if "ListItem" in el_types:
                item = el.get("item")
                if isinstance(item, dict) and (_ld_types(item) & _LD_PRODUCT_TYPES or item.get("name")):
                    _ld_add(_ld_result(item), results, seen)
                elif isinstance(item, dict) and _ld_types(item):
                    _collect_products_jsonld(item, results, max_results, seen, _depth + 1)
                elif el.get("name") and (el.get("url") or isinstance(item, str)):
                    _ld_add(SearchResult(rank=0, title=_ld_str(el.get("name"))[:300],
                                         url=_ld_str(el.get("url")) or _ld_str(item) or None), results, seen)
            else:
                _collect_products_jsonld(el, results, max_results, seen, _depth + 1)
        return

    for key, value in data.items():
        if key in _LD_SKIP_KEYS or (key.startswith("@") and key != "@graph"):
            continue
        if isinstance(value, (dict, list)):
            _collect_products_jsonld(value, results, max_results, seen, _depth + 1)


# ---------------------------------------------------------------------------
# Strategy 2 — Product card patterns (extended)
# ---------------------------------------------------------------------------


_CONTENT_OVERRIDE_RE = re.compile(
    r"product|result|search|catalog|listing|grid|card|item|hit|deal|offer",
    re.I,
)


def _is_inside_chrome(el: Tag) -> bool:
    for node in [el] + list(el.parents):
        if not isinstance(node, Tag):
            continue
        tag = (node.name or "").lower()
        # Skip root-level tags and custom elements (hyphenated tag names like
        # app-root, cx-storefront) — they are app framework containers whose
        # classes often contain chrome keywords as camelCase substrings.
        if tag in ("body", "html") or "-" in tag:
            continue
        if tag in ("header", "footer", "nav"):
            return True
        # Check each CSS class token individually to prevent substring false positives
        # (e.g. "js-sticky-header" must not match as "header").
        # Exception: if the same token also contains a product/content keyword
        # (e.g. "product-grid-sidebar"), it is NOT chrome.
        classes = node.get("class", [])
        el_id = node.get("id", "") or ""
        for cls in classes:
            if _CHROME_CLASSES.search(cls) and not _CONTENT_OVERRIDE_RE.search(cls):
                return True
        if _CHROME_CLASSES.search(el_id) and not _CONTENT_OVERRIDE_RE.search(el_id):
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


def _attr_tokens(node: Tag) -> list[str]:
    # Class / id / testid only: an aria-label is a sentence ("Results related to boots").
    attrs = node.attrs or {}
    return list(attrs.get("class") or []) + [attrs.get("id") or "", attrs.get("data-testid") or ""]


def _is_inside_reco(el: Tag) -> bool:
    """True if ``el`` sits inside a recommendation / carousel / mini-cart container."""
    for node in [el] + list(el.parents):
        if not isinstance(node, Tag) or node.name in ("body", "html", "[document]"):
            continue
        if any(t and _RECO_CONTAINER_RE.search(t) for t in _attr_tokens(node)):
            return True
    return False


def _preceding_heading_is_reco(el: Tag) -> bool:
    """True if the nearest heading above ``el`` (ignoring header/nav/footer menus)
    introduces a recommendation carousel."""
    for heading in el.find_all_previous(re.compile(r"^h[1-4]$"), limit=8):
        if heading.find_parent(["header", "nav", "footer"]):
            continue
        return bool(_RECO_HEADING_RE.search(heading.get_text(" ", strip=True)))
    return False


def _doc_order(soup: BeautifulSoup) -> dict[int, int]:
    return {id(el): i for i, el in enumerate(soup.find_all(True))}


def _group_quality(group: list[Tag]) -> float:
    """Mean per-card quality: has a link (1) and a price (1), out of 2."""
    if not group:
        return 0.0
    total = 0.0
    for c in group:
        text = c.get_text(" ")
        total += (1.0 if c.find("a", href=True) else 0.0) + (
            1.0 if (_PRICE_RE.search(text) or _PRICE_FALLBACK_RE.search(text)) else 0.0)
    return total / (2 * len(group))


def _detect_repeated_structure(soup: BeautifulSoup, max_results: int) -> list[Tag]:
    """Find the repeated card group that is the search grid; return its cards in DOM order.

    1. Group candidate cards by (parent, tag+first-class signature).
    2. Merge same-signature groups whose parents are siblings with the same signature —
       a grid split around editorial blocks (douglas.de: 8 + 4 + 12 + 28 tiles in four
       .product-grid blocks) is ONE result list, and its real rank 1 is in the first block.
    3. Score each group by mean quality × min(n, k); recommendation carousels (by
       container class or the heading that introduces them) are heavily discounted.
    4. Among groups scoring within 80% of the best, take the one nearest the top of
       <main> — never simply the largest (a 15-tile carousel beat a 4-tile grid).
    """
    order = _doc_order(soup)
    k = max(1, max_results)
    groups: dict[tuple[int, str], list[Tag]] = {}
    parents: dict[tuple[int, str], Tag] = {}

    for tag_name in ("div", "li", "article", "figure", "section"):
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
            classes = el.get("class", [])
            sig = f"{tag_name}::{classes[0] if classes else ''}"
            key = (id(el.parent), sig)
            groups.setdefault(key, []).append(el)
            parents[key] = el.parent

    def _sig(node: Tag) -> str:
        classes = node.get("class", []) if isinstance(node, Tag) else []
        return f"{getattr(node, 'name', '')}::{classes[0] if classes else ''}"

    merged: dict[tuple, list[Tag]] = {}
    for key, group in groups.items():
        parent = parents[key]
        grand = parent.parent
        if grand is not None and not _is_inside_reco(group[0]):
            mkey = ("merge", id(grand), _sig(parent), key[1])
        else:
            mkey = ("single",) + key
        merged.setdefault(mkey, []).extend(group)

    main = soup.find("main") or soup.find(attrs={"role": "main"})
    scored: list[tuple[float, int, list[Tag]]] = []
    for group in merged.values():
        if len(group) < 3:
            continue
        group.sort(key=lambda t: order.get(id(t), 0))
        # Drop cards nested inside other cards of the same group (keep the outer one).
        ids = {id(g) for g in group}
        group = [g for g in group if not any(id(p) in ids for p in g.parents)]
        if len(group) < 3:
            continue
        score = _group_quality(group) * min(len(group), k)
        if _is_inside_reco(group[0]) or _preceding_heading_is_reco(group[0]):
            score *= 0.25
        if main is not None and main not in group[0].parents:
            score *= 0.7
        scored.append((score, order.get(id(group[0]), 0), group))

    if not scored:
        return []
    best = max(s for s, _, _ in scored)
    if best <= 0:
        return []
    near = [item for item in scored if item[0] >= 0.8 * best]
    chosen = min(near, key=lambda item: item[1])[2]
    # Return 3× the requested count so downstream deduplication (color variants,
    # price-identical items) has enough buffer to still reach max_results.
    return chosen[: max_results * 3]


_HOVER_CONTAINER_RE = re.compile(
    # Match visibility/display-state class tokens, NOT CSS animation suffixes like
    # "hover-underline" or "hover-effect".  Require the pattern to appear as a
    # standalone suffix after a "--" BEM modifier or as a standalone class token.
    r"isvisible-false|is-hidden|is-invisible|fresnel-greaterThan|"
    r"visually-hidden|sr-only|offscreen|display--none|"
    r"(?:^|[\s_-])hover-content(?:$|[\s_-])|"  # hover-content as a word
    r"(?:^|[\s_-])on-hover(?:$|[\s_-])|"       # on-hover as a word
    r"--hover-show\b|--hover-visible\b|--is-hidden\b|--is-invisible\b",
    re.I,
)


def _is_hover_or_hidden(el: Tag) -> bool:
    """True if this element (or an ancestor) is a hover/hidden container."""
    for node in [el] + list(el.parents):
        if not isinstance(node, Tag):
            continue
        attrs = getattr(node, "attrs", None)
        if not attrs:
            continue
        classes = " ".join(attrs.get("class", []) or []).lower()
        testid = (attrs.get("data-testid", "") or "").lower()
        if _HOVER_CONTAINER_RE.search(classes):
            return True
        if re.search(r"hover-content|hover-show|hover-overlay", testid):
            return True
    return False


_BADGE_ATTR_RE = re.compile(r"flag|badge|tag|sticker|promo|label|sponsored", re.I)
_NAME_ATTR_RE = re.compile(r"(?:^|-)(?:product-?name|item-?name|name|title)(?:-|$)", re.I)


def _is_badge_element(el: Tag) -> bool:
    """True if this element looks like a product badge/tag (Neu, Sale, Sponsored…)."""
    attrs = getattr(el, "attrs", None) or {}
    # data-*-flag / data-*-badge / etc.
    for attr_name in attrs:
        if attr_name.startswith("data-") and _BADGE_ATTR_RE.search(attr_name):
            return True
    # data-nc="badge…" (used by some component libraries)
    data_nc = (attrs.get("data-nc", "") or "").lower()
    if "badge" in data_nc:
        return True
    # Check parent too — if parent has data-nc="badge…", this child is a badge
    parent = el.parent
    if isinstance(parent, Tag):
        parent_attrs = getattr(parent, "attrs", None) or {}
        parent_nc = (parent_attrs.get("data-nc", "") or "").lower()
        if "badge" in parent_nc:
            return True
    # class-based badge detection
    classes = " ".join(attrs.get("class", []) or []).lower()
    if _BADGE_ATTR_RE.search(classes):
        return True
    return False


_DATA_PROPS_TITLE_KEYS = (
    "brandLine1", "brandLine2", "brandLine3",
    "articleDescription", "title", "name", "productName", "articleName",
)


def _extract_title_from_card(card: Tag) -> str:
    # -1. Card IS a heading element — return its text directly.
    if card.name and re.match(r"^h[1-6]$", card.name):
        text = card.get_text(separator=" ", strip=True)
        if text:
            return text[:300]

    # 0. data-props / data-product JSON: many React sites embed full product data
    #    as a JSON string on the card or a direct descendant.
    for el in [card] + card.find_all(True, recursive=True):
        for attr_name in ("data-props", "data-product", "data-item", "data-product-data"):
            props_str = el.get(attr_name, "") or ""
            if not props_str:
                continue
            try:
                props = json.loads(props_str)
                if not isinstance(props, dict):
                    continue
                parts = [
                    props[k].strip()
                    for k in _DATA_PROPS_TITLE_KEYS
                    if isinstance(props.get(k), str) and props[k].strip()
                ]
                if parts:
                    return " ".join(parts)[:300]
            except (json.JSONDecodeError, TypeError):
                pass

    # 1. Any data-* attribute NAME containing "name" or "title" as a word token
    #    (covers data-testid="product-X-name", data-test-sell-product-name, etc.)
    for child in card.find_all(True, recursive=True):
        if _is_hover_or_hidden(child) or _is_badge_element(child):
            continue
        attrs = getattr(child, "attrs", None) or {}
        for attr_name in attrs:
            if attr_name.startswith("data-") and _NAME_ATTR_RE.search(attr_name):
                text = child.get_text(separator=" ", strip=True)
                if text and len(text) > 2:
                    return text[:300]

    # 2. class containing "title", "name", or "heading" — skip hover/badge containers
    for child in card.find_all(True, recursive=True):
        if _is_hover_or_hidden(child) or _is_badge_element(child):
            continue
        classes = " ".join(child.get("class", [])).lower()
        if any(kw in classes for kw in ("title", "name", "heading")):
            text = child.get_text(separator=" ", strip=True)
            if text and len(text) > 2:
                return text[:300]

    # 3. role="heading"
    heading_el = card.find(attrs={"role": "heading"})
    if heading_el and not _is_hover_or_hidden(heading_el):
        text = heading_el.get_text(separator=" ", strip=True)
        if text:
            return text[:300]

    # 4. <h1>–<h6>
    heading = card.find(re.compile(r"^h[1-6]$"))
    if heading and not _is_hover_or_hidden(heading):
        text = heading.get_text(separator=" ", strip=True)
        if text:
            return text[:300]

    # 5. Link text fallback — strip hover/hidden and badge subtrees before reading.
    #    Skip generic UI aria-labels that don't describe the product.
    _GENERIC_ARIA_LABELS = re.compile(
        r"^(view product|add to (cart|bag|basket|wishlist)|like product|"
        r"remove|delete|close|open|toggle|expand|collapse|share|save|buy|purchase)$",
        re.I,
    )
    link = card.find("a")
    if link:
        label = link.get("aria-label", "").strip()
        if label and len(label) > 4 and not _GENERIC_ARIA_LABELS.match(label):
            return label[:300]
        link_copy = copy.copy(link)
        for node in link_copy.find_all(True):
            if isinstance(node, Tag) and (_is_hover_or_hidden(node) or _is_badge_element(node)):
                node.decompose()
        text = link_copy.get_text(separator=" ", strip=True)
        if text and len(text) > 2:
            return text[:300]

    # 6. Accumulate leaf text nodes that look like a product name, stopping at prices.
    #    Handles sites with fully hashed CSS-in-JS class names (e.g. styled-components)
    #    where none of the class-based heuristics above can fire.
    _UI_JUNK_RE = re.compile(
        r"^(like|add to|view|remove|close|open|toggle|share|save|buy|"
        r"purchase|wishlist|cart|basket|bag|compare|quick view|more info|"
        r"sponsored|anzeige|gesponsert|sponsrad|annonse|annonce|"
        r"sold out|out of stock|unavailable|new|sale|–?\d+\s*%|"
        r"\+\d+\s*(mehr|more|colors?|colours?|variants?|options?)|"  # "+3 mehr", "+2 colors"
        r"ab\s+[\d,.])",  # "ab 4,99 €" (German "from price")
        re.I,
    )
    name_parts: list[str] = []
    for child in card.find_all(True, recursive=True):
        if _is_hover_or_hidden(child) or _is_badge_element(child):
            continue
        if child.find(True):  # skip non-leaf elements (would duplicate text)
            continue
        text = child.get_text(separator=" ", strip=True)
        if not text:
            continue
        # Stop accumulating once we hit a price
        if _PRICE_RE.search(text) or _PRICE_FALLBACK_RE.search(text):
            break
        if len(text) < 3 or len(text) > 150:
            continue
        if _UI_JUNK_RE.match(text):
            continue
        if re.match(r"^[\s​\d%.,/()\-]+$", text):
            continue
        name_parts.append(text)
        # Stop after collecting a reasonable product name (brand + product line)
        if len(name_parts) >= 3 or sum(len(p) for p in name_parts) >= 80:
            break
    if name_parts:
        return " ".join(name_parts)[:300]

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
    # Check if the card itself is inside an <a> (e.g. heading leaf inside a link wrapper)
    parent = card.parent
    if isinstance(parent, Tag) and parent.name == "a":
        href = parent.get("href", "")
        if href and href != "#":
            return href
    link = card.find("a", href=True)
    if link:
        href = link.get("href", "")
        if href and href != "#":
            return href
    return None


def _try_product_cards(soup: BeautifulSoup, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
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

        if _is_inside_reco(el):
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
        match_counts: Counter[str] = Counter()
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

    # Keep DOM order — it IS the ranking the shopper sees. (Sorting by a link/price
    # "card score" here once moved price-less real results below priced chrome.)
    for card in filtered_cards:
        title = _extract_title_from_card(card)
        if not title or len(title) < 2:
            continue

        results.append(_strip_sponsored_prefix(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=_extract_price(card),
            snippet=_extract_snippet_from_card(card),
            url=_extract_url_from_card(card),
            sponsored=_detect_sponsored(card),
        )))

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
            if _is_inside_chrome(el) or _is_inside_reco(el):
                continue
            parent_groups.setdefault(id(el.parent), []).append(el)

    if not parent_groups:
        return results

    largest_group = max(parent_groups.values(), key=len)
    if len(largest_group) < 2:
        return results

    for el in largest_group:
        # Use smart title extraction (strips hover/hidden containers) rather than
        # raw link.get_text() which picks up size labels and other hover-only text.
        title = _extract_title_from_card(el)
        url = _extract_url_from_card(el)

        if not title:
            link = el.find("a", href=True)
            if link:
                href = link.get("href", "")
                url = url or (href if href and href != "#" else None)

        if not title or len(title) < 3:
            continue

        results.append(_strip_sponsored_prefix(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=_extract_price(el),
            snippet=None,
            url=url,
            sponsored=_detect_sponsored(el),
        )))

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


def _result_quality(r: SearchResult) -> float:
    """0..1 quality of one extracted result: URL (3), price (2), real title (1), not junk (2)."""
    has_url = bool(r.url and not r.url.startswith("#"))
    has_price = r.price is not None
    title_quality = len(r.title) > 20
    lower = r.title.lower().strip()
    looks_junky = (
        any(lower.startswith(p) for p in _JUNK_STARTS)
        or lower in _JUNK_EXACT
        or len(r.title) < 10
    )
    return ((3.0 if has_url else 0) + (2.0 if has_price else 0)
            + (1.0 if title_quality else 0) + (0.0 if looks_junky else 2.0)) / 8.0


def _score_strategy(results: list[SearchResult], k: int = 15) -> float:
    """Mean result quality × min(n, k).

    Summing per-result points let a 15-item recommendation carousel beat a 4-item real
    grid on volume alone; the mean keeps 20 nav links from beating 5 real products and
    the min(n, k) cap stops volume past k from counting at all.
    """
    if not results:
        return 0.0
    mean = sum(_result_quality(r) for r in results) / len(results)
    return mean * min(len(results), max(1, k))


def _first_position(results: list[SearchResult], html: str) -> int:
    """Where the strategy's first result sits in the page (proxy for DOM order)."""
    for r in results[:3]:
        for needle in (r.url, (r.url or "").replace("&", "&amp;"), r.title):
            if needle:
                pos = html.find(needle)
                if pos >= 0:
                    return pos
    return len(html) + 1


_GENERIC_STRATEGIES = ("schema-org", "product-cards", "generic-list", "cached-selectors")


def _extract_page(
    soup: BeautifulSoup,
    html: str,
    url: str,
    max_results: int,
    query: str = "",
    allow_llm: bool = True,
    client=None,
) -> tuple[list[SearchResult], str]:
    """Extraction only (no status logic). Returns (results, strategy name).

    Callers must have ruled out a no-results marker first (see _analyse_page): on a
    no-results page every strategy below happily scrapes the recommendation carousel.
    """
    global _site_extraction_profile

    # Highest priority: a purpose-built site-specific extractor. When it matches a
    # known host its hand-tuned output must win over generic cached selectors.
    site_results = _try_site_specific(soup, url, max_results)
    if site_results:
        logger.debug("Site-specific extractor matched: %d results", len(site_results))
        return site_results, "site-specific"

    # Dedicated hosts never fall through to generic strategies: on a no-results or
    # half-rendered page those scrape recommendation chrome. Empty here becomes
    # ZERO_CONFIRMED or ZERO_UNVERIFIED in _analyse_page, never phantom results.
    if _has_dedicated_extractor(url):
        logger.debug("Dedicated extractor returned 0 for known host — no generic fallback")
        return [], "site-specific"

    if _site_extraction_profile is not None:
        cached_results = _extract_with_cached_selectors(soup, _site_extraction_profile, max_results)
        if len(cached_results) >= 3:
            logger.debug("Cached selectors hit: %d results (skipping full strategy sweep)", len(cached_results))
            return cached_results, "cached-selectors"
        logger.debug("Cached selectors miss (%d results) — falling back to full sweep", len(cached_results))

    strategy_results: dict[str, list[SearchResult]] = {
        "schema-org": _try_schema_org(soup, max_results),
        "product-cards": _try_product_cards(soup, max_results),
        "generic-list": _try_generic_list(soup, max_results),
    }
    for name in strategy_results:
        strategy_results[name] = [r for r in strategy_results[name] if not _is_cookie_junk(r)]

    scores = {name: _score_strategy(res, max_results) for name, res in strategy_results.items()}
    best = max(scores.values())
    winner_name = "none"
    winner: list[SearchResult] = []
    if best > 0:
        # Among strategies within 80% of the best score, take the one whose results
        # start highest on the page.
        near = [name for name, sc in scores.items() if sc >= 0.8 * best]
        winner_name = min(near, key=lambda n: _first_position(strategy_results[n], html))
        winner = strategy_results[winner_name]
    logger.debug(
        "Strategy scores: %s → %s",
        ", ".join(f"{k}:{sc:.1f} ({len(strategy_results[k])})" for k, sc in scores.items()),
        winner_name,
    )

    if allow_llm and winner:
        winner = _validate_results_with_llm(winner, query, client=client)
    if allow_llm and len(winner) < 5:
        llm_results = _extract_with_llm(html, query, max_results, url=url, client=client)
        if len(llm_results) > len(winner):
            winner, winner_name = llm_results, "llm"

    if winner:
        _log_first_titles(winner, winner_name)
    return winner, winner_name


def _extract_results(html: str, max_results: int, url: str = "") -> list[SearchResult]:
    """Legacy entry point: extracted results for one page ([] on a no-results page).

    New code should use _analyse_page, which also returns WHY the list is empty.
    """
    outcome = _analyse_page(html=html, url=url, final_url=url, query="", max_results=max_results)
    return outcome.results


def _log_first_titles(results: list[SearchResult], strategy: str) -> None:
    titles = [f'"{r.title[:60]}"' for r in results[:3]]
    logger.debug("  %s sample: %s", strategy, " | ".join(titles))


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
        "button.cc-btn.cc-allow",                        # CookieConsent.js (Sportamore et al.)
        "button.cc-btn-decision.cc-allow",               # CookieConsent.js variant
        ".cc-compliance .cc-allow",                      # CookieConsent.js generic
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
                # Swedish
                "acceptera", "godkänn", "godkann", "fortsätt", "tillåt alla",
                "tillat alla", "acceptera alla",
                # Norwegian / Danish
                "godta alle", "accepter alle",
            )):
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1200)
                    logger.debug("Playwright: dismissed consent via text '%s'", txt)
                    return
    except Exception:
        pass

    # JS eval fallback — directly clicks any visible consent/allow button by class or text.
    # Catches CookieConsent.js (.cc-allow), custom banners, and others that don't respond
    # to Playwright's query_selector due to timing or shadow DOM issues.
    try:
        clicked = page.evaluate("""() => {
            function isVisible(el) {
                const r = el.getBoundingClientRect();
                const s = window.getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
            }
            function removeBannerContainer(el) {
                const containers = ['.cc-window', '.cc-overlay', '#cookieconsent', '[class*="cookie-banner"]',
                                    '[class*="consent-banner"]', '[id*="cookie"]'];
                for (const sel of containers) {
                    const c = document.querySelector(sel);
                    if (c) { c.remove(); }
                }
            }
            const classSelectors = [
                'button.cc-allow', 'button.cc-btn-decision', '.cc-compliance button',
                '.cc-window button.cc-btn', '[class*="accept"][class*="btn"]',
                '[class*="consent"] button[class*="accept"]',
            ];
            for (const sel of classSelectors) {
                const el = document.querySelector(sel);
                if (el && isVisible(el)) { el.click(); removeBannerContainer(el); return sel; }
            }
            const acceptWords = [
                'accept all', 'acceptera', 'fortsätt', 'godkänn', 'tillåt',
                'accepter', 'akzeptieren', 'accepteer', 'povolit', 'souhlasím',
                'godta', 'allow all', 'allow cookies',
            ];
            for (const btn of document.querySelectorAll('button')) {
                const txt = (btn.innerText || '').trim().toLowerCase();
                if (acceptWords.some(w => txt.includes(w)) && isVisible(btn)) {
                    btn.click(); removeBannerContainer(btn); return 'text:' + txt.slice(0, 40);
                }
            }
            return null;
        }""")
        if clicked:
            page.wait_for_timeout(1200)
            logger.debug("Playwright: JS-eval dismissed consent via '%s'", clicked)
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
            # First pass: JS click on load-more buttons by CSS class pattern.
            # JS click bypasses Playwright's viewport/visibility checks, which fail
            # when a sticky header/footer pushes the button outside the viewport rect.
            # Capture current tile count, then JS-click the load-more button.
            pre_count = page.evaluate("""() => {
                return document.querySelectorAll(
                    'section[class*="tile"], li[class*="product"], li[class*="item"], ' +
                    'div[class*="product-tile"], div[class*="product_tile"], ' +
                    'article'
                ).length;
            }""") or 0
            js_clicked = page.evaluate("""() => {
                const selectors = [
                    '[class*="load-more"]', '[class*="load_more"]',
                    '[class*="loadmore"]', '[class*="show-more"]',
                    '[class*="show_more"]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) { el.click(); return el.textContent.trim().slice(0, 40); }
                }
                return null;
            }""")
            if js_clicked:
                logger.debug("Playwright: JS-clicked load-more '%s' (pre-count=%d)", js_clicked, pre_count)
                # Wait until DOM tile count grows beyond pre-click count, or 7s elapses.
                if pre_count > 0:
                    try:
                        page.wait_for_function(
                            f"""() => {{
                                return document.querySelectorAll(
                                    'section[class*="tile"], li[class*="product"], li[class*="item"], ' +
                                    'div[class*="product-tile"], div[class*="product_tile"], article'
                                ).length > {pre_count};
                            }}""",
                            timeout=7000,
                        )
                    except Exception:
                        page.wait_for_timeout(4000)
                else:
                    page.wait_for_timeout(4000)
                clicked = True
            else:
                # Second pass: text-based search with JS click fallback
                buttons = page.query_selector_all("button, a[href]")
                for btn in buttons[:80]:
                    try:
                        btn_text = (btn.inner_text() or "").strip()
                        if _LOAD_MORE_RE.search(btn_text):
                            logger.debug("Playwright: JS-clicking '%s'", btn_text)
                            page.evaluate("(el) => el.click()", btn)
                            try:
                                page.wait_for_load_state("networkidle", timeout=6000)
                            except Exception:
                                page.wait_for_timeout(3000)
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


def _hydrate_lazy_prices(page, url: str) -> None:
    """Host-scoped lazy-load trigger for sites that hydrate prices on scroll.

    Bergzeit renders product titles/links immediately but only hydrates the
    price node (`.product-box-content__price`) once a card scrolls into view.
    A single jump to the bottom misses mid-page cards, so step through the page
    incrementally, then wait briefly for the price nodes to populate. No-op for
    other hosts so the shared fetch path is unaffected.
    """
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return
    if "bergzeit.de" not in host:
        return

    try:
        height = page.evaluate("document.body.scrollHeight") or 0
        step = 700
        pos = 0
        while pos < height:
            page.evaluate(f"window.scrollTo(0, {pos})")
            page.wait_for_timeout(250)
            pos += step
            height = page.evaluate("document.body.scrollHeight") or height
        page.evaluate("window.scrollTo(0, 0)")
        # Give the price nodes a moment to finish hydrating.
        try:
            page.wait_for_function(
                "document.querySelectorAll('.product-box-content__price').length > 0",
                timeout=4000,
            )
        except Exception:
            pass
        page.wait_for_timeout(800)
    except Exception:
        pass


# Readiness: wait until EITHER the host's results grid OR its no-results state has
# rendered. Client-rendered grids (Boost, Zalando, Åhléns, Cotswold's post-redirect
# hydration) are empty for seconds after domcontentloaded; capturing then reads a
# real page as zero. Returns 'grid' | 'no_results' | 'timeout' (never fails open:
# a timeout is recorded and turns an empty capture into TIMEOUT, not a zero).
_READY_JS = """([sel, rx]) => {
    if (sel && document.querySelector(sel)) return 'grid';
    if (rx) {
        const t = (document.title || '') + ' ' + (document.body ? document.body.innerText : '');
        if (new RegExp(rx, 'i').test(t)) return 'no_results';
    }
    return false;
}"""


def _wait_for_host_ready(page, url: str) -> Optional[str]:
    profile = _host_profile(url)
    if not profile or not (profile.ready_selector or profile.ready_no_results):
        return None
    try:
        handle = page.wait_for_function(
            _READY_JS,
            arg=[profile.ready_selector or "", profile.ready_no_results or ""],
            timeout=profile.ready_timeout_ms,
        )
        state = handle.json_value() or "timeout"
    except Exception:
        logger.debug("Readiness wait timed out for %s — recording timeout", url)
        state = "timeout"
    page.wait_for_timeout(800)
    return state


def _wait_for_cloudflare_clear(page, timeout_ms: int = 30000) -> bool:
    """Wait for a Cloudflare "Just a moment..." JS challenge to auto-clear.

    Headed Chromium passes Cloudflare's managed challenge on its own after a few
    seconds; this polls the page title/marker until the real content replaces the
    interstitial. Returns True if cleared, False if it timed out still on the
    challenge. Used for `_HEADED_CHROMIUM_HOSTS` before block-classifying the
    response (otherwise the still-rendering challenge looks like a hard block).
    """
    try:
        page.wait_for_function(
            """() => {
                const t = (document.title || '');
                if (/just a moment/i.test(t)) return false;
                const b = document.body ? document.body.innerText : '';
                return !/just a moment|checking your browser|verifying you are human/i.test(b);
            }""",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        logger.debug("Cloudflare challenge did not clear within %dms", timeout_ms)
        return False


# Visible text as the browser renders it (honours CSS display:none, which a static
# parse cannot), outside header/nav/footer/dialogs. Mutates the DOM, so it runs
# after the HTML and the screenshot have been captured.
_VISIBLE_TEXT_JS = """() => {
    const drop = 'header, nav, footer, [role=banner], [role=navigation], [role=contentinfo], [role=dialog]';
    for (const el of document.querySelectorAll(drop)) el.remove();
    const main = document.querySelector('main, [role=main]');
    const head = main ? (main.innerText || '').slice(0, 20000) : '';
    const body = document.body ? (document.body.innerText || '').slice(0, 40000) : '';
    return head + '\n' + body;
}"""


@dataclass
class PageFetch:
    """One HTTP/browser fetch of a search URL, before any extraction."""
    html: str = ""
    final_url: str = ""
    http_status: Optional[int] = None
    browser: str = ""
    error: Optional[str] = None
    timed_out: bool = False
    ready: Optional[str] = None            # grid | no_results | timeout | None (no host wait)
    visible_text: Optional[str] = None     # browser innerText of the main content
    block: Optional[str] = None            # signature block seen in the browser loop
    screenshot: Optional[str] = None
    search_api: list = field(default_factory=list)   # [(vendor, url, body)] captured responses


def _static_fetch(url: str, timeout: float = 15) -> PageFetch:
    try:
        resp = requests.get(
            url, headers={"User-Agent": _USER_AGENT},
            timeout=timeout, allow_redirects=True, proxies=_REQUESTS_PROXIES,
        )
    except requests.Timeout as e:
        return PageFetch(final_url=url, error=f"timeout: {e}", timed_out=True, browser="static")
    except requests.RequestException as e:
        return PageFetch(final_url=url, error=str(e)[:300], browser="static")
    return PageFetch(html=_decode_response(resp), final_url=resp.url, http_status=resp.status_code, browser="static")


def _playwright_fetch(
    url: str,
    quick_probe: bool = False,
    force_browser: Optional[str] = None,
    screenshot_path: Optional[str] = None,
) -> PageFetch:
    """Fetch a page in a real browser. Never raises; failures are recorded on PageFetch.

    Browser order: headed Chromium for `_HEADED_CHROMIUM_HOSTS`, Chromium for
    `_PREFER_CHROMIUM_HOSTS` / force_browser="chromium", else Firefox then Chromium.
    A browser that lands on a bot-wall signature is skipped; if all do, the last
    block page is returned (so the caller reports BLOCKED, not an empty zero).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(
            "Playwright not installed. Install: pip install playwright && playwright install chromium"
        )
        return PageFetch(final_url=url, error="playwright not installed")

    out = PageFetch(final_url=url)
    try:
        with sync_playwright() as p:
            chromium_opts = {"args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"]}
            if "colourpop.com" in urlparse(url).netloc.lower():
                chromium_opts["channel"] = "chrome"

            # Some hosts (Cloudflare "Just a moment...") only let a *headed*
            # Chromium session through. Force headed Chromium for those.
            headed_host = _needs_headed_chromium(url)
            launch_headless = not headed_host

            if headed_host or _prefers_chromium(url) or force_browser == "chromium":
                browsers = [(p.chromium, "chromium", chromium_opts)]
            elif force_browser == "firefox":
                browsers = [(p.firefox, "firefox", {})]
            else:
                browsers = [
                    (p.firefox, "firefox", {}),
                    (p.chromium, "chromium", chromium_opts),
                ]

            browser = context = page = None
            captured: list = []
            for browser_type, name, launch_kw in browsers:
                try:
                    browser = browser_type.launch(headless=launch_headless, **launch_kw)
                    logger.debug("Playwright: launched %s (headless=%s)", name, launch_headless)
                except Exception as e:
                    logger.debug("Playwright: %s unavailable (%s), trying next", name, e)
                    browser = None
                    out.error = f"{name} unavailable: {e}"[:300]
                    continue

                ctx_kwargs = {"user_agent": _USER_AGENT, "viewport": {"width": 1280, "height": 900}}
                if _PW_PROXY:
                    ctx_kwargs["proxy"] = _PW_PROXY
                context = browser.new_context(**ctx_kwargs)
                page = context.new_page()
                _apply_stealth(page)
                captured = []
                page.on("response", lambda resp, _c=captured: _capture_search_api(resp, _c))

                try:
                    goto_resp = page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    out.http_status = goto_resp.status if goto_resp is not None else None
                    page.wait_for_timeout(3000)
                    # For headed Cloudflare hosts, give the JS challenge time to
                    # auto-clear before deciding it's a block.
                    if headed_host:
                        _wait_for_cloudflare_clear(page)
                    probe_html = page.content()
                    block = _detect_block(probe_html, out.http_status, page.url, strict=False)
                    if block:
                        logger.debug("Playwright: %s returned %s block page, trying next browser", name, block)
                        out.html, out.final_url, out.block, out.browser = probe_html, page.url, block, name
                        context.close()
                        browser.close()
                        browser = None
                        continue
                except Exception as e:
                    logger.debug("Playwright: %s navigation failed (%s), trying next", name, e)
                    out.error = f"{name} navigation failed: {e}"[:300]
                    out.timed_out = "timeout" in str(e).lower()
                    context.close()
                    browser.close()
                    browser = None
                    continue
                break

            if browser is None:
                if out.block:
                    logger.warning("Playwright: every browser hit a block page (%s)", out.block)
                else:
                    logger.warning("Playwright: all browsers unavailable or failed for %s", url)
                return out

            out.browser = name
            out.block = None
            out.error = None
            out.timed_out = False
            _dismiss_consent_banners(page)
            out.ready = _wait_for_host_ready(page, url)

            if quick_probe:
                page.wait_for_timeout(2000)
            else:
                _scroll_and_load_more(page)
                _hydrate_lazy_prices(page, url)

            out.html = page.content()
            out.final_url = page.url
            if screenshot_path:
                try:
                    # Top of the page = what the shopper sees first (the scroll loop left
                    # us at the bottom). Viewport only: full-page PNGs run to megabytes.
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(300)
                    page.screenshot(path=screenshot_path, full_page=False)
                    out.screenshot = screenshot_path
                except Exception as e:
                    logger.debug("Screenshot failed: %s", e)
            out.search_api = _read_captured_search_api(captured)
            try:
                out.visible_text = page.evaluate(_VISIBLE_TEXT_JS)
            except Exception:
                out.visible_text = None
            context.close()
            browser.close()

    except Exception as e:
        logger.warning("Playwright fetch failed for %s: %s", url, e)
        out.error = str(e)[:300]
        out.timed_out = out.timed_out or "timeout" in str(e).lower()

    return out


def _fetch_with_playwright(
    url: str,
    quick_probe: bool = False,
    force_browser: Optional[str] = None,
) -> tuple[str, str, str]:
    """Legacy wrapper: (html, browser_name, final_url); html is "" if blocked/unavailable."""
    pf = _playwright_fetch(url, quick_probe=quick_probe, force_browser=force_browser)
    if pf.block or not pf.html:
        return "", "", ""
    return pf.html, pf.browser, pf.final_url


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


def _best_product_container(soup: BeautifulSoup, url: str = "") -> Optional[Tag]:
    """The tightest container holding most of the page's distinct product links.

    Picking the first div whose class matched items?/grid grabbed Tailwind's
    `items-center` in the site header. Density of product links is what identifies
    the results grid.
    """
    link_re = re.compile(r"/deals?/", re.I) if "groupon" in (url or "").lower() else None
    hrefs_by_el: dict[int, set[str]] = {}
    el_by_id: dict[int, Tag] = {}
    depth_by_id: dict[int, int] = {}
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").split("#")[0]
        if not href:
            continue
        if link_re is not None:
            if not link_re.search(href):
                continue
        elif not (_PRODUCT_LINK_RE.search(href) or "/products/" in href):
            continue
        if _is_inside_chrome(a):
            continue
        ancestors = [anc for anc in a.parents if isinstance(anc, Tag) and anc.name not in ("html", "[document]", "body")]
        for depth_from_leaf, anc in enumerate(ancestors):
            if anc.name not in ("main", "div", "section", "ul", "ol"):
                continue
            hrefs_by_el.setdefault(id(anc), set()).add(href)
            el_by_id[id(anc)] = anc
            depth_by_id[id(anc)] = len(ancestors) - depth_from_leaf
    if not hrefs_by_el:
        return None
    best = max(len(v) for v in hrefs_by_el.values())
    if best < 3:
        return None
    candidates = [i for i, v in hrefs_by_el.items() if len(v) >= 0.8 * best]
    chosen = max(candidates, key=lambda i: depth_by_id[i])
    return el_by_id[chosen]


def _find_main_content(html: str, url: str = "") -> str:
    """Extract the tightest results container available (for LLM prompts)."""
    soup = BeautifulSoup(html, "html.parser")
    container = _best_product_container(soup, url)
    if container is not None and len(str(container)) > 500:
        logger.debug("LLM container: <%s class='%s'>", container.name, " ".join(container.get("class", []))[:40])
        return str(container)
    main_el = soup.find("main")
    if main_el and len(str(main_el)) > 500:
        return str(main_el)
    return html


class _LLMExtractedItem(BaseModel):
    title: str
    price: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None


class _LLMExtraction(BaseModel):
    items: list[_LLMExtractedItem]


_EXTRACTION_SYSTEM = (
    "You are a web scraping expert. You extract product/service/deal listings from search "
    "result page HTML, in the order they appear in the HTML. You are precise and never confuse "
    "page chrome (navigation, banners, buttons, consent dialogs) with actual results.\n\n"
    "APPROACH:\n"
    "1. Identify the REPEATING card-like HTML pattern that contains the listings — usually "
    "<article>, <li>, <div> or <figure> elements that repeat with similar class names.\n"
    "2. From EACH card take: title (product name exactly as written in the HTML), price "
    "(displayed current price including currency, null if none), snippet (short description "
    "or null), url (the main link's href exactly as written, null if none).\n\n"
    "RULES:\n"
    "- Copy titles and hrefs verbatim from the HTML. Never invent, translate or complete them.\n"
    "- Keep the page order. Do not judge relevance: include every listing in the results grid.\n"
    "- Exclude page headers, section titles, navigation, breadcrumbs, footer links, cookie/"
    "consent banners, sign-in prompts, filter/facet items and promotional banners.\n"
    "- If the page shows a no-results message, return an empty list — a recommendation "
    "carousel on a no-results page is not a result list."
)


def _llm_enabled(client) -> bool:
    return client is not None or _HAS_API_KEY


def _call_haiku_for_extraction(
    html_chunk: str, max_results: int, instruction_prefix: str = "", client=None,
) -> list[dict]:
    """One structured Haiku call for HTML extraction. Returns a list of plain dicts.

    The search query is deliberately NOT sent: knowing it invites the model to keep
    only on-topic items, which makes a bad search engine look good.
    """
    if not _llm_enabled(client):
        logger.debug("LLM extraction skipped: no ANTHROPIC_API_KEY")
        return []
    parsed = structured_call(
        model=_HAIKU_MODEL,
        system=_EXTRACTION_SYSTEM,
        user=f"{instruction_prefix}Extract up to {max_results} listings.\n\nHTML:\n{html_chunk}",
        schema=_LLMExtraction,
        max_tokens=4000,
        phase="fetcher",
        temperature=0,
        client=client,
    )
    return [item.model_dump() for item in parsed.items]


def _norm_for_grounding(text: str) -> str:
    text = unicodedata.normalize("NFKC", unescape(text or "")).casefold()
    return re.sub(r"[\W_]+", " ", text).strip()


def _ground_llm_results(results: list[SearchResult], html: str, page_text_norm: str) -> list[SearchResult]:
    """Drop LLM items that are not on the page: title not in the visible text, or a URL
    that does not occur in the HTML. An LLM may only report what a shopper would see."""
    html_l = html.lower()
    grounded: list[SearchResult] = []
    for r in results:
        title_norm = _norm_for_grounding(r.title)
        if not title_norm or title_norm not in page_text_norm:
            logger.info("LLM grounding: dropped %r (title not on page)", r.title[:60])
            continue
        if r.url:
            u = r.url.strip().lower()
            path = urlparse(u).path or u
            if not any(n and n in html_l for n in (u, u.replace("&", "&amp;"), path if len(path) > 3 else "")):
                logger.info("LLM grounding: dropped %r (url not in HTML)", r.title[:60])
                continue
        grounded.append(r)
    for i, r in enumerate(grounded, 1):
        r.rank = i
    return grounded


def _extract_with_llm(
    html: str, query: str = "", max_results: int = 15, url: str = "", client=None,
) -> list[SearchResult]:
    """Last-resort fallback: ask Haiku to extract results from the cleaned results container.

    Every item is grounded against the page before it is accepted (see
    _ground_llm_results); the query is used for logging only.
    """
    if not _llm_enabled(client):
        return []
    try:
        content_html = _find_main_content(html, url)
        truncated = _clean_html_for_llm(content_html)[:50000]
        soup = BeautifulSoup(html, "html.parser")
        texts, _ = _collect_visible_text(soup)
        page_text_norm = _norm_for_grounding(" ".join(texts))

        def _run(prefix: str = "") -> list[SearchResult]:
            items = _call_haiku_for_extraction(truncated, max_results, prefix, client=client)
            results = _filter_junk_results(_items_to_results(items, max_results))
            return _ground_llm_results(results, html, page_text_norm)

        filtered = _run()
        if len(filtered) < 5:
            logger.info("LLM first pass found only %d grounded results, retrying once", len(filtered))
            retry_prefix = (
                f"A previous extraction found only {len(filtered)} listings. Look more carefully: "
                "search results are usually repeated card-like elements containing a title link "
                "and often a price.\n\n"
            )
            try:
                retry = _run(retry_prefix)
                if len(retry) > len(filtered):
                    filtered = retry
            except (LLMResponseError, anthropic.APIError) as e:
                logger.debug("LLM retry failed: %s", e)

        logger.info("Strategy 4 (LLM) for '%s': %d grounded results", query, len(filtered))
        if filtered:
            _log_first_titles(filtered, "LLM")
        return filtered

    except (LLMResponseError, anthropic.APIError) as e:
        logger.warning("LLM extraction failed: %s", e)
        return []
    except Exception as e:
        logger.warning("LLM extraction unexpected error: %s", e)
        return []


def _items_to_results(items: list[dict], max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in items[:max_results]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        results.append(_strip_sponsored_prefix(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=item.get("price") or None,
            snippet=item.get("snippet") or None,
            url=item.get("url") or None,
        )))
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


class _LLMSelectorProfile(BaseModel):
    container_selector: str
    card_selector: str
    title_selector: str
    price_selector: Optional[str] = None
    url_selector: Optional[str] = None


_SELECTOR_SYSTEM = (
    "You are a web scraping expert. Given HTML and a list of product titles found on the page, "
    "identify the CSS selectors for the repeating product card structure.\n"
    "Rules:\n"
    "- container_selector: the parent container holding all result cards.\n"
    "- card_selector: matches EVERY individual result card, not just one.\n"
    "- title_selector / price_selector / url_selector: relative to a card (price null if no prices; "
    "url usually 'a').\n"
    "- Prefer class-based selectors over nth-child. Never select recommendation carousels."
)


def _generate_extraction_profile(
    html: str, results: list[SearchResult], url: str = "", client=None,
) -> Optional[SiteExtractionProfile]:
    """Ask Haiku for CSS selectors of this site's product cards. Runs once per site."""
    if len(results) < 3:
        return None
    if not _llm_enabled(client):
        logger.debug("LLM selector generation skipped: no ANTHROPIC_API_KEY")
        return None

    truncated = _clean_html_for_llm(_find_main_content(html, url))[:30000]
    titles_sample = "\n".join(f"- {r.title[:80]}" for r in results[:8])
    try:
        data = structured_call(
            model=_HAIKU_MODEL,
            system=_SELECTOR_SYSTEM,
            user=f"Product listings found on this page:\n{titles_sample}\n\nHTML:\n{truncated}",
            schema=_LLMSelectorProfile,
            max_tokens=600,
            phase="fetcher",
            temperature=0,
            client=client,
        )
    except Exception as e:
        logger.warning("LLM selector generation failed: %s", e)
        return None
    if not data.container_selector or not data.card_selector:
        logger.debug("LLM selector generation: incomplete selectors, skipping cache")
        return None
    logger.info(
        "LLM selector cache: container='%s', card='%s', title='%s'",
        data.container_selector, data.card_selector, data.title_selector,
    )
    return SiteExtractionProfile(
        container_selector=data.container_selector,
        card_selector=data.card_selector,
        title_selector=data.title_selector,
        price_selector=data.price_selector,
        url_selector=data.url_selector or "a",
    )


def _extract_with_cached_selectors(
    soup_or_html, profile: SiteExtractionProfile, max_results: int
) -> list[SearchResult]:
    """Fast extraction using LLM-generated selectors from the probe query."""
    soup = soup_or_html if isinstance(soup_or_html, BeautifulSoup) else BeautifulSoup(soup_or_html, "html.parser")
    results: list[SearchResult] = []

    try:
        container = soup.select_one(profile.container_selector)
        cards = container.select(profile.card_selector) if container else soup.select(profile.card_selector)
    except Exception as e:  # invalid CSS from the model
        logger.debug("Cached selectors invalid (%s)", e)
        return results

    if not cards:
        logger.debug("Cached selectors: no cards found with '%s'", profile.card_selector)
        return results

    for card in cards[:max_results * 2]:  # scan extra in case some are junk
        if _is_inside_reco(card):
            continue
        title = ""
        if profile.title_selector:
            try:
                title_el = card.select_one(profile.title_selector)
            except Exception:
                title_el = None
            if title_el:
                title = title_el.get_text(separator=" ", strip=True)[:300]
        if not title:
            title = _extract_title_from_card(card)
        if not title or len(title) < 3:
            continue

        price = None
        if profile.price_selector:
            try:
                price_el = card.select_one(profile.price_selector)
            except Exception:
                price_el = None
            if price_el and not _is_secondary_price_node(price_el):
                price = _first_price(_current_price_text(price_el))
        if not price:
            price = _extract_price(card)

        url = None
        if profile.url_selector:
            try:
                link_el = card.select_one(profile.url_selector)
            except Exception:
                link_el = None
            if link_el:
                href = link_el.get("href", "")
                if href and href != "#":
                    url = href
        if not url:
            url = _extract_url_from_card(card)

        results.append(_strip_sponsored_prefix(SearchResult(
            rank=len(results) + 1,
            title=title,
            price=price,
            snippet=_extract_snippet_from_card(card),
            url=url,
            sponsored=_detect_sponsored(card),
        )))

        if len(results) >= max_results:
            break

    filtered = _filter_junk_results(results)
    logger.debug("Cached selectors: found %d raw results, %d after filtering", len(results), len(filtered))
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
        if not (_PRODUCT_LINK_RE.search(r.url) or "/products/" in r.url):
            return False
    return True


class _LLMValidation(BaseModel):
    product_indices: list[int]


_VALIDATION_SYSTEM = (
    "You are a web scraping quality checker. You receive items extracted from an online shop's "
    "search results page and decide which are REAL product/service/deal listings and which are "
    "page chrome: navigation links, UI buttons, section headers, cookie banners, sign-in prompts, "
    "headers, footers.\n"
    "- Judge only 'is this a listing', never whether it is relevant to anything.\n"
    "- If the same title appears several times keep ALL occurrences (colour/size variants).\n"
    "Return the 1-based indices of the real listings."
)


def _validate_results_with_llm(
    results: list[SearchResult], query: str = "", client=None,
) -> list[SearchResult]:
    """Ask Haiku which extracted results are real products vs. page chrome.

    Sends only titles + URLs. The query is NOT sent: with it, the model drops
    off-topic real results, which makes a bad search engine look good.
    Returns only the validated results, re-indexed 1-based.
    """
    if not results:
        return results
    if not _llm_enabled(client):
        logger.debug("LLM validation skipped: no ANTHROPIC_API_KEY")
        return results
    if _all_urls_look_like_products(results):
        logger.debug("Validation skip: all %d URLs match product patterns", len(results))
        return results

    listing = "\n".join(
        f"{r.rank}. {r.title[:100]} | {r.url[:120] if r.url else '(no URL)'}" for r in results
    )
    try:
        parsed = structured_call(
            model=_HAIKU_MODEL,
            system=_VALIDATION_SYSTEM,
            user=f"Extracted items:\n{listing}",
            schema=_LLMValidation,
            max_tokens=400,
            phase="fetcher",
            temperature=0,
            client=client,
        )
    except Exception as e:
        logger.warning("LLM validation failed (%s), returning unvalidated results", e)
        return results

    valid = set(parsed.product_indices)
    validated = [r for r in results if r.rank in valid]
    for i, r in enumerate(validated, 1):
        r.rank = i
    if len(validated) < len(results):
        logger.info(
            "LLM validation: kept %d/%d results for '%s' (rejected %d as page chrome)",
            len(validated), len(results), query, len(results) - len(validated),
        )
    return validated


# ---------------------------------------------------------------------------
# Search-engine API capture (Playwright network interception)
# ---------------------------------------------------------------------------
# Many shops render results from a hosted search engine's JSON API. Capturing that
# response gives an independent hit count and ordering to cross-check the DOM read.

_SEARCH_API_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("algolia", re.compile(r"(?:algolia\.net|algolianet\.com)/1/indexes/", re.I)),
    ("klevu", re.compile(r"ksearchnet\.com|klevu\.com/cs/", re.I)),
    ("constructor", re.compile(r"cnstrc\.com/(?:search|browse)/", re.I)),
    ("bloomreach", re.compile(r"dxpapi\.com|brsrvr\.com", re.I)),
    ("doofinder", re.compile(r"doofinder\.com/.*search", re.I)),
    ("searchspring", re.compile(r"searchspring\.io/api/search", re.I)),
    ("boost", re.compile(r"mybcapps\.com/bc-sf-filter/search|boostcommerce\.net/.*search", re.I)),
    ("nosto", re.compile(r"search\.nosto\.com|api\.nosto\.com/v1/graphql", re.I)),
)
_MAX_CAPTURED_API = 12


def _search_api_vendor(url: str) -> Optional[str]:
    for vendor, rx in _SEARCH_API_PATTERNS:
        if rx.search(url or ""):
            return vendor
    return None


def _capture_search_api(resp, sink: list) -> None:
    """page.on('response') handler: remember matching responses; bodies are read later
    (reading a body inside the event callback can dead-lock the sync API)."""
    try:
        vendor = _search_api_vendor(resp.url)
        if vendor and len(sink) < _MAX_CAPTURED_API:
            sink.append((vendor, resp))
    except Exception:
        pass


def _read_captured_search_api(captured: list) -> list[tuple[str, str, str]]:
    out = []
    for vendor, resp in captured:
        try:
            body = resp.text()
        except Exception:
            continue
        if body and len(body) < 5_000_000:
            out.append((vendor, resp.url, body))
    return out


@dataclass
class SearchApiResult:
    vendor: str
    query: Optional[str]
    total: Optional[int]
    titles: list[str] = field(default_factory=list)


def _url_param(url: str, *names: str) -> Optional[str]:
    params = parse_qs(urlparse(url).query)
    for n in names:
        if params.get(n):
            return params[n][0]
    return None


def _int_or_none(v) -> Optional[int]:
    try:
        return int(v) if v is not None and not isinstance(v, bool) else None
    except (TypeError, ValueError):
        return None


def _hit_titles(hits, *keys: str) -> list[str]:
    titles = []
    for h in hits or []:
        if not isinstance(h, dict):
            continue
        for k in keys:
            v = h.get(k)
            if isinstance(v, dict):  # Algolia localised fields {"en": "..."}
                v = next((x for x in v.values() if isinstance(x, str)), None)
            if isinstance(v, str) and v.strip():
                titles.append(v.strip())
                break
    return titles


def _parse_algolia(data, url: str) -> list[SearchApiResult]:
    blocks = data.get("results") if isinstance(data.get("results"), list) else [data]
    out = []
    for b in blocks:
        if not isinstance(b, dict) or "nbHits" not in b:
            continue
        out.append(SearchApiResult("algolia", b.get("query"), _int_or_none(b.get("nbHits")),
                                   _hit_titles(b.get("hits"), "name", "title", "product_name")))
    return out


def _parse_klevu(data, url: str) -> list[SearchApiResult]:
    out = []
    for b in data.get("queryResults") or []:
        if not isinstance(b, dict):
            continue
        meta = b.get("meta") or {}
        if b.get("id") not in (None, "productSearch") and "product" not in str(b.get("id")).lower():
            continue
        out.append(SearchApiResult("klevu", meta.get("searchedTerm"), _int_or_none(meta.get("totalResultsFound")),
                                   _hit_titles(b.get("records"), "name", "title")))
    if not out and isinstance(data.get("meta"), dict):
        meta = data["meta"]
        out.append(SearchApiResult("klevu", meta.get("searchedTerm") or _url_param(url, "term", "q"),
                                   _int_or_none(meta.get("totalResultsFound")),
                                   _hit_titles(data.get("result"), "name", "title")))
    return out


def _parse_constructor(data, url: str) -> list[SearchApiResult]:
    resp = data.get("response") or {}
    if "total_num_results" not in resp:
        return []
    req = data.get("request") or {}
    return [SearchApiResult("constructor", req.get("term") or _url_param(url, "term", "q"),
                            _int_or_none(resp.get("total_num_results")),
                            _hit_titles(resp.get("results"), "value", "name"))]


def _parse_bloomreach(data, url: str) -> list[SearchApiResult]:
    resp = data.get("response") or {}
    if "numFound" not in resp:
        return []
    return [SearchApiResult("bloomreach", _url_param(url, "q"), _int_or_none(resp.get("numFound")),
                            _hit_titles(resp.get("docs"), "title", "name"))]


def _parse_doofinder(data, url: str) -> list[SearchApiResult]:
    if "total" not in data or "results" not in data:
        return []
    return [SearchApiResult("doofinder", data.get("query") or _url_param(url, "query", "q"),
                            _int_or_none(data.get("total")), _hit_titles(data.get("results"), "title", "name"))]


def _parse_searchspring(data, url: str) -> list[SearchApiResult]:
    pag = data.get("pagination") or {}
    if "totalResults" not in pag:
        return []
    q = data.get("query")
    q = q.get("original") or q.get("matchType") if isinstance(q, dict) else q
    return [SearchApiResult("searchspring", (q if isinstance(q, str) else None) or _url_param(url, "q"),
                            _int_or_none(pag.get("totalResults")), _hit_titles(data.get("results"), "name", "title"))]


def _parse_boost(data, url: str) -> list[SearchApiResult]:
    if "total_product" not in data:
        return []
    return [SearchApiResult("boost", _url_param(url, "q"), _int_or_none(data.get("total_product")),
                            _hit_titles(data.get("products"), "title", "name"))]


def _parse_nosto(data, url: str) -> list[SearchApiResult]:
    search = ((data.get("data") or {}).get("search")) if isinstance(data.get("data"), dict) else None
    if not isinstance(search, dict) or not isinstance(search.get("products"), dict):
        return []
    products = search["products"]
    return [SearchApiResult("nosto", search.get("query"), _int_or_none(products.get("total")),
                            _hit_titles(products.get("hits"), "name", "title"))]


_SEARCH_API_PARSERS: dict[str, Callable] = {
    "algolia": _parse_algolia, "klevu": _parse_klevu, "constructor": _parse_constructor,
    "bloomreach": _parse_bloomreach, "doofinder": _parse_doofinder, "searchspring": _parse_searchspring,
    "boost": _parse_boost, "nosto": _parse_nosto,
}


def parse_search_api_payload(vendor: str, url: str, body: str) -> list[SearchApiResult]:
    """Parse one captured search-engine response. Never raises."""
    parser = _SEARCH_API_PARSERS.get(vendor)
    if parser is None:
        return []
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    try:
        return parser(data, url)
    except Exception as e:  # unexpected payload shape
        logger.debug("search API parse failed (%s): %s", vendor, e)
        return []


def _search_api_summary(captured: list, query: str) -> Optional[SearchApiResult]:
    """The captured search-API answer for THIS query (autocomplete / recommendation
    calls on the same page carry other queries and are ignored)."""
    parsed: list[SearchApiResult] = []
    for vendor, url, body in captured or []:
        parsed.extend(parse_search_api_payload(vendor, url, body))
    want = _query_tokens(query)
    for r in parsed:
        if r.query is not None and _query_tokens(r.query) == want and r.total is not None:
            return r
    return None


# ---------------------------------------------------------------------------
# Page analysis — one page → FetchOutcome (status + results), no network
# ---------------------------------------------------------------------------


def _outcome(query: str, status: FetchStatus, **kw) -> FetchOutcome:
    return FetchOutcome(query=query, status=status, **kw)


def _analyse_page(
    *,
    html: str,
    url: str,
    final_url: str,
    query: str,
    max_results: int,
    http_status: Optional[int] = None,
    visible_text: Optional[str] = None,
    ready: Optional[str] = None,
    search_api: Optional[list] = None,
    allow_llm: bool = True,
    client=None,
) -> FetchOutcome:
    """Decide what one fetched page says about the search, and extract its results.

    Order matters — each step guards the next:
      1. known no-results destination path                       → ZERO_CONFIRMED
      2. bot wall / WAF status / tiny product-less page        → BLOCKED
      3. redirected onto a single product page                   → REDIRECT, 1 result
      4. explicit no-results marker on the page                  → ZERO_CONFIRMED, []
         (even if a carousel is present: those are phantoms; skip all extraction)
      5. extract (dedicated extractor, or cached/generic/LLM)    → OK / PARTIAL / REDIRECT
      6. nothing extracted, no marker                            → ZERO_UNVERIFIED (TIMEOUT
         when the readiness wait timed out). Never an authoritative empty list.
    """
    final_url = final_url or url
    base = dict(final_url=final_url, http_status=http_status)
    if not html:
        return _outcome(query, FetchStatus.ERROR, evidence="empty response", **base)

    soup = BeautifulSoup(html, "html.parser")
    state = page_state(soup, final_url, visible_text, query=query)
    base["page_title"] = state.title[:200] or None

    if _is_authoritative_no_results(final_url):
        return _outcome(query, FetchStatus.ZERO_CONFIRMED, total_hits=0, strategy="path-marker",
                        evidence=f"search redirected to the no-results page {urlparse(final_url).path}", **base)

    block = _detect_block(html, http_status, final_url, soup=soup, strict=True,
                          has_zero_marker=bool(state.no_results_marker))
    if block:
        return _outcome(query, FetchStatus.BLOCKED, evidence=f"bot wall / refused ({block})", **base)

    api = _search_api_summary(search_api or [], query) if query else None

    kind = _redirect_kind(url, final_url, query) if query else None
    if kind:
        pdp = _extract_pdp(soup, final_url)
        if pdp is not None:
            return _outcome(query, FetchStatus.REDIRECT, results=[pdp], total_hits=1, strategy="pdp",
                            evidence=f"search went straight to a product page ({final_url})", **base)

    note = ""
    if state.no_results_marker:
        if state.auto_applied:
            note = (f"page says '{state.no_results_marker}' but shows results for a corrected query; "
                    "kept those results")
        elif state.max_strong_hits:
            return _outcome(query, FetchStatus.ZERO_UNVERIFIED, total_hits=state.total_hits, strategy="marker",
                            evidence=(f"page shows a no-results message ('{state.no_results_marker}') and a "
                                      f"hit count ({state.max_strong_hits}) — ambiguous, verify by hand"), **base)
        else:
            return _outcome(query, FetchStatus.ZERO_CONFIRMED, total_hits=0, strategy="marker",
                            evidence=f"page says: '{state.no_results_marker}'", **base)

    results, strategy = _extract_page(soup, html, final_url, max_results * 2, query, allow_llm, client)

    hits = state.total_hits
    hits_from_api = False
    if hits is None and api is not None:
        hits, hits_from_api = api.total, True
    notes = [note] if note else []
    if hits and state.hits_strong and not hits_from_api and 0 < hits < len(results):
        notes.append(f"page reports {hits} hits; dropped {len(results) - hits} extra tiles (recommendation padding)")
        results = results[:hits]
    results = results[:max_results]
    for i, r in enumerate(results, 1):
        r.rank = i
    if api is not None:
        notes.append(f"{api.vendor} search API reports {api.total} hits")
        if results and api.titles and _norm_for_grounding(api.titles[0])[:40] not in _norm_for_grounding(results[0].title):
            notes.append(f"API top hit '{api.titles[0][:60]}' differs from page rank 1")

    if results and api is not None and api.total == 0 and not state.auto_applied and not kind:
        # The engine's own API answered "0 hits"; whatever tiles the page shows are a
        # recommendation / bestseller fallback, not search results.
        return _outcome(query, FetchStatus.ZERO_CONFIRMED, total_hits=0, strategy="search-api",
                        evidence=(f"{api.vendor} search API returned 0 hits; ignored {len(results)} "
                                  f"recommendation tiles on the page"), **base)

    if results:
        if kind:
            status = FetchStatus.REDIRECT
            notes.insert(0, f"search redirected to {final_url}")
        elif hits and len(results) < min(hits, max_results):
            status = FetchStatus.PARTIAL
            notes.insert(0, f"page reports {hits} hits, extracted {len(results)}")
        else:
            status = FetchStatus.OK
        return _outcome(query, status, results=results, total_hits=hits, strategy=strategy,
                        evidence="; ".join(notes), **base)

    if api is not None and api.total == 0:
        return _outcome(query, FetchStatus.ZERO_CONFIRMED, total_hits=0, strategy="search-api",
                        evidence=f"{api.vendor} search API returned 0 hits for this query", **base)
    if ready == "timeout":
        return _outcome(query, FetchStatus.TIMEOUT, total_hits=hits, strategy=strategy,
                        evidence="results grid and no-results message both failed to render in time", **base)
    if hits:
        why = f"page reports {hits} hits but no product tiles could be read"
    elif kind:
        why = f"redirected to {final_url}; no products found there and no no-results message"
    elif "douglas.de" in urlparse(final_url).netloc.lower():
        why = ("no product tiles and no 'Keine Ergebnisse gefunden' title — Douglas blocks automated "
               "browsers (Akamai), so this is not a confirmed zero")
    else:
        why = "no products extracted and no no-results message on the page"
    return _outcome(query, FetchStatus.ZERO_UNVERIFIED, total_hits=hits, strategy=strategy, evidence=why, **base)


def _outcome_from_page(
    pf: PageFetch, url: str, query: str, max_results: int, allow_llm: bool = True, client=None,
) -> FetchOutcome:
    base = dict(final_url=pf.final_url or url, http_status=pf.http_status)
    if pf.block:
        return _outcome(query, FetchStatus.BLOCKED, evidence=f"bot wall in every browser ({pf.block})", **base)
    if not pf.html:
        if pf.timed_out:
            return _outcome(query, FetchStatus.TIMEOUT, evidence=pf.error or "timed out", **base)
        if pf.http_status is not None and (pf.http_status in _BLOCK_HTTP_CODES or pf.http_status >= 500):
            return _outcome(query, FetchStatus.BLOCKED, evidence=f"HTTP {pf.http_status}", **base)
        return _outcome(query, FetchStatus.ERROR, evidence=pf.error or "empty response", **base)
    return _analyse_page(
        html=pf.html, url=url, final_url=pf.final_url or url, query=query, max_results=max_results,
        http_status=pf.http_status, visible_text=pf.visible_text, ready=pf.ready,
        search_api=pf.search_api, allow_llm=allow_llm and not _LIGHT_MODE, client=client,
    )


# ---------------------------------------------------------------------------
# Evidence capture
# ---------------------------------------------------------------------------


def _query_slug(query: str) -> str:
    base = unicodedata.normalize("NFKD", query or "").encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower()[:60] or "query"
    return f"{base}-{hashlib.sha1((query or '').encode('utf-8')).hexdigest()[:8]}"


def _evidence_paths(evidence_dir: Optional[str], query: str, attempt: int) -> tuple[Optional[str], Optional[str]]:
    if not evidence_dir:
        return None, None
    d = Path(evidence_dir)
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.warning("Evidence dir unavailable (%s): %s", evidence_dir, e)
        return None, None
    stem = f"{_query_slug(query)}_a{attempt}"
    return str(d / f"{stem}.html.gz"), str(d / f"{stem}.png")


def _attach_evidence(outcome: FetchOutcome, html: str, html_path: Optional[str], screenshot: Optional[str]) -> None:
    saved = []
    if html_path and html:
        try:
            with gzip.open(html_path, "wt", encoding="utf-8") as fh:
                fh.write(html)
            saved.append(html_path)
        except OSError as e:
            logger.debug("Evidence HTML not saved: %s", e)
    if screenshot and Path(screenshot).exists():
        saved.append(screenshot)
    if saved:
        outcome.evidence = (f"{outcome.evidence} " if outcome.evidence else "") + f"[evidence: {', '.join(saved)}]"


# ---------------------------------------------------------------------------
# Probe-first fetch infrastructure
# ---------------------------------------------------------------------------

# Per-attempt wall-clock cap. The worker thread cannot be killed: a hung Playwright
# fetch keeps running as a daemon thread until the process exits (deferred: a
# subprocess-per-fetch model would fix it, see FETCHER_PLAYBOOK).
_PER_ATTEMPT_TIMEOUT_S = 300
_PROBE_TIMEOUT_S = 600
_MAX_ATTEMPTS = 3            # zero_unverified / timeout / error / thin results
_ZERO_CONFIRM_ATTEMPTS = 2   # a confirmed zero is re-checked once (backend flakiness)
_RETRY_BACKOFF_S = (2.0, 5.0, 10.0)
_MAX_PROBES = 3
_MAX_CONSECUTIVE_BLOCKS = 3   # consecutive BLOCKED / TIMEOUT / ERROR outcomes before giving up
_FAILURE_STATUSES = frozenset({FetchStatus.BLOCKED.value, FetchStatus.TIMEOUT.value, FetchStatus.ERROR.value})

# Light mode (catalog sampling): one attempt per page, no LLM extraction/validation, no
# profile learning. Set only for the duration of one fetch_all_outcomes(light=True) call.
_LIGHT_MODE = False
_THIN_RESULTS = 3
_BETWEEN_QUERIES_S = 1.5

_STATUS_RANK = {
    FetchStatus.OK.value: 6, FetchStatus.REDIRECT.value: 6, FetchStatus.PARTIAL.value: 6,
    FetchStatus.ZERO_CONFIRMED.value: 5, FetchStatus.ZERO_UNVERIFIED.value: 4,
    FetchStatus.TIMEOUT.value: 3, FetchStatus.BLOCKED.value: 2, FetchStatus.ERROR.value: 1,
}


def _status_value(o: FetchOutcome) -> str:
    return o.status.value if isinstance(o.status, FetchStatus) else str(o.status)


def _outcome_rank(o: FetchOutcome) -> tuple:
    return (_STATUS_RANK.get(_status_value(o), 0), len(o.results))


def _needs_retry(o: FetchOutcome, attempts: int) -> bool:
    if _LIGHT_MODE:
        return False
    st = _status_value(o)
    if st == FetchStatus.BLOCKED.value:
        return False  # hammering a WAF escalates the block (douglas.de profile)
    if st == FetchStatus.ZERO_CONFIRMED.value:
        return attempts < _ZERO_CONFIRM_ATTEMPTS
    if st in (FetchStatus.ZERO_UNVERIFIED.value, FetchStatus.TIMEOUT.value, FetchStatus.ERROR.value):
        return attempts < _MAX_ATTEMPTS
    if len(o.results) < _THIN_RESULTS:
        if o.total_hits is not None and o.total_hits <= len(o.results):
            return False
        if o.strategy == "pdp":
            return False
        return attempts < _MAX_ATTEMPTS
    return False


def _run_with_timeout(timeout_s: float, fn, *args, **kwargs) -> tuple[str, object]:
    """Run fn in a daemon thread. Returns ('ok', value) | ('timeout', None) | ('error', exc)."""
    box: dict = {}

    def _target() -> None:
        try:
            box["value"] = fn(*args, **kwargs)
        except Exception as exc:  # recorded as ERROR by the caller
            box["error"] = exc

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        return "timeout", None
    if "error" in box:
        return "error", box["error"]
    return "ok", box.get("value")


def _fetch_once(
    url: str, query: str, max_results: int, mode: str,
    evidence_dir: Optional[str] = None, attempt: int = 1, client=None,
) -> tuple[FetchOutcome, str]:
    """One fetch of one query with the site's proven mode. Never raises for page problems."""
    if mode in (SiteMode.BLOCKED, SiteMode.FAILED):
        status = FetchStatus.BLOCKED if mode == SiteMode.BLOCKED else FetchStatus.ERROR
        return _outcome(query, status, attempts=0, evidence=f"not fetched (site mode {mode})"), ""
    html_path, shot = _evidence_paths(evidence_dir, query, attempt)
    if mode == SiteMode.STATIC:
        pf = _static_fetch(url, timeout=15)
    elif mode == SiteMode.PLAYWRIGHT_CHROMIUM:
        pf = _playwright_fetch(url, force_browser="chromium", screenshot_path=shot)
    else:  # PLAYWRIGHT_FIREFOX: Firefox first, Chromium fallback
        pf = _playwright_fetch(url, screenshot_path=shot)
    outcome = _outcome_from_page(pf, url, query, max_results, client=client)
    _attach_evidence(outcome, pf.html, html_path, pf.screenshot)
    return outcome, pf.html


def _fetch_with_retries(
    url: str, query: str, max_results: int, mode: str,
    evidence_dir: Optional[str] = None, client=None,
    first: Optional[tuple[FetchOutcome, str]] = None,
) -> tuple[FetchOutcome, str]:
    """Fetch, re-fetching zero / thin / timeout / error results with backoff.

    A zero is accepted as ZERO_CONFIRMED only when a no-results marker was seen (and is
    re-checked once — manufactum.de and bergzeit.de both flip between a no-hits page
    and real results for the same URL). The best attempt wins; ``attempts`` records
    how many fetches were made.
    """
    attempts: list[tuple[FetchOutcome, str]] = [first] if first else []
    while True:
        if attempts:
            best = max(attempts, key=lambda a: _outcome_rank(a[0]))[0]
            if not _needs_retry(best, len(attempts)):
                break
            delay = _RETRY_BACKOFF_S[min(len(attempts) - 1, len(_RETRY_BACKOFF_S) - 1)]
            logger.info("'%s' → %s (%d results); retrying in %.0fs (attempt %d)",
                        query, _status_value(best), len(best.results), delay, len(attempts) + 1)
            _sleep(delay)
        n = len(attempts) + 1
        kind, value = _run_with_timeout(
            _PER_ATTEMPT_TIMEOUT_S, _fetch_once, url, query, max_results, mode, evidence_dir, n, client,
        )
        if kind == "ok":
            attempts.append(value)
        elif kind == "timeout":
            logger.warning("Query '%s' attempt %d timed out after %ds", query, n, _PER_ATTEMPT_TIMEOUT_S)
            attempts.append((_outcome(query, FetchStatus.TIMEOUT, final_url=url,
                                      evidence=f"fetch exceeded {_PER_ATTEMPT_TIMEOUT_S}s"), ""))
        else:
            logger.warning("Unexpected error fetching '%s': %s", query, value)
            attempts.append((_outcome(query, FetchStatus.ERROR, final_url=url,
                                      evidence=f"{type(value).__name__}: {value}"[:300]), ""))

    best_outcome, best_html = max(attempts, key=lambda a: _outcome_rank(a[0]))
    best_outcome.attempts = len(attempts)
    seen = [_status_value(a[0]) for a in attempts]
    if len(set(seen)) > 1:
        best_outcome.evidence = (f"{best_outcome.evidence}; " if best_outcome.evidence else "") + \
            f"attempts: {', '.join(seen)}"
    return best_outcome, best_html


def _probe_outcome(
    url: str, query: str, max_results: int, evidence_dir: Optional[str] = None, client=None,
) -> tuple[str, FetchOutcome, str]:
    """Probe one URL to choose the site-level fetch mode; returns (mode, outcome, html).

    Strategy (ordered by cost):
      1. Quick static fetch (5s). Good enough (k results, prices server-rendered) → STATIC.
      2. Full Playwright fetch (Firefox → Chromium stealth fallback).
      3. Static is kept when Playwright is not better (count and price coverage).
    mode is BLOCKED when every transport hit a bot wall, FAILED when nothing loaded.
    """
    html_path, shot = _evidence_paths(evidence_dir, query, 1)
    host = urlparse(url).netloc.lower()
    client_priced_host = any(h in host for h in _CLIENT_RENDERED_PRICE_HOSTS)

    static = _static_fetch(url, timeout=5)
    static_out = _outcome_from_page(static, url, query, max_results, allow_llm=False)
    logger.debug("Probe: static %s (%d results)", _status_value(static_out), len(static_out.results))

    def _static_final() -> tuple[str, FetchOutcome, str]:
        final = _outcome_from_page(static, url, query, max_results, client=client)
        _attach_evidence(final, static.html, html_path, None)
        return SiteMode.STATIC, final, static.html

    if (_status_value(static_out) == FetchStatus.REDIRECT.value and static_out.strategy == "pdp"
            and _needs_pdp_redirect_extraction(url)):
        logger.info("Probe: static redirect was a unique-match PDP → STATIC mode")
        return _static_final()
    if static_out.trusted and len(static_out.results) >= max_results and not client_priced_host:
        logger.info("Probe: static extraction (%d results) → STATIC mode", len(static_out.results))
        return _static_final()

    pw = _playwright_fetch(url, screenshot_path=shot)
    if not pw.html:
        if static_out.trusted and static_out.results:
            logger.info("Probe: Playwright unavailable — keeping static (%d results)", len(static_out.results))
            return _static_final()
        if _status_value(static_out) == FetchStatus.BLOCKED.value:
            _attach_evidence(static_out, static.html, html_path, None)
            return SiteMode.BLOCKED, static_out, static.html
        failed = _outcome_from_page(pw, url, query, max_results)
        logger.info("Probe: no page from any transport → FAILED (%s)", failed.evidence)
        return SiteMode.FAILED, failed, ""

    pw_out = _outcome_from_page(pw, url, query, max_results, client=client)
    _attach_evidence(pw_out, pw.html, html_path, pw.screenshot)
    if _status_value(pw_out) == FetchStatus.BLOCKED.value:
        if static_out.trusted and static_out.results:
            return _static_final()
        logger.info("Probe: all browsers blocked → BLOCKED (%s)", pw_out.evidence)
        return SiteMode.BLOCKED, pw_out, pw.html

    mode = SiteMode.PLAYWRIGHT_CHROMIUM if pw.browser == "chromium" else SiteMode.PLAYWRIGHT_FIREFOX
    # Static is kept when Playwright is not better. Count is not the only signal: some
    # sites render prices client-side, so equal counts with better price coverage win.
    if static_out.trusted and len(static_out.results) >= 5 and len(pw_out.results) <= len(static_out.results):
        static_final = _outcome_from_page(static, url, query, max_results, client=client)
        pw_priced = sum(1 for r in pw_out.results if r.price)
        static_priced = sum(1 for r in static_final.results if r.price)
        if len(static_final.results) >= len(pw_out.results) and static_priced >= pw_priced:
            logger.info("Probe: Playwright/%s (%d) not better than static (%d) → STATIC mode",
                        pw.browser, len(pw_out.results), len(static_final.results))
            _attach_evidence(static_final, static.html, html_path, None)
            return SiteMode.STATIC, static_final, static.html
    logger.info("Probe: Playwright/%s → %s (%s, %d results)", pw.browser, mode,
                _status_value(pw_out), len(pw_out.results))
    return mode, pw_out, pw.html


def _probe_site(url: str, query: str, max_results: int) -> tuple[str, list[SearchResult], str, bool]:
    """Legacy wrapper: (mode, results, html, was_redirected=False)."""
    mode, outcome, html = _probe_outcome(url, query, max_results)
    return mode, outcome.results, html, False


def _fetch_with_mode(
    url: str,
    query: str,
    max_results: int,
    mode: str,
    reuse_context: Optional[object] = None,
) -> tuple[list[SearchResult], bool]:
    """Legacy wrapper for per-query runner scripts: (results, was_redirected=False).

    Redirects are now always extracted on the destination, so there is nothing to
    skip. Use _fetch_outcome_with_mode to learn WHY a list is empty.
    """
    outcome, _ = _fetch_once(url, query, max_results, mode)
    return outcome.results, False


def _fetch_outcome_with_mode(url: str, query: str, max_results: int, mode: str,
                             evidence_dir: Optional[str] = None) -> FetchOutcome:
    """One query, proven mode, with the standard retry policy."""
    outcome, _ = _fetch_with_retries(url, query, max_results, mode, evidence_dir)
    return outcome


# ---------------------------------------------------------------------------
# Main public functions
# ---------------------------------------------------------------------------


def _query_str(q) -> str:
    return q.query if isinstance(q, TestQuery) else str(q)


def _search_url(template: str, query: str) -> str:
    return template.replace("{}", quote_plus(query))


_profile_attempted = False


def _maybe_learn_profile(outcome: FetchOutcome, html: str, url: str, client=None) -> None:
    """Learn cached selectors once per site from the first good generic extraction."""
    global _site_extraction_profile, _profile_attempted
    if _LIGHT_MODE or _profile_attempted or _site_extraction_profile is not None or not html:
        return
    if _has_dedicated_extractor(url) or _status_value(outcome) != FetchStatus.OK.value:
        return
    if outcome.strategy not in ("schema-org", "product-cards", "generic-list") or len(outcome.results) < 3:
        return
    _profile_attempted = True
    _site_extraction_profile = _generate_extraction_profile(html, outcome.results, url=url, client=client)


def fetch_all_outcomes(
    queries: list,
    search_url_template: str,
    max_results: int = 15,
    evidence_dir: Optional[str] = None,
    on_outcome: Optional[Callable[[FetchOutcome], None]] = None,
    client=None,
    light: bool = False,
) -> dict[str, FetchOutcome]:
    """See :func:`_fetch_all_outcomes`. ``light=True`` = one attempt, no LLM (catalog sampling)."""
    global _LIGHT_MODE
    previous, _LIGHT_MODE = _LIGHT_MODE, light
    try:
        return _fetch_all_outcomes(queries, search_url_template, max_results, evidence_dir, on_outcome, client)
    finally:
        _LIGHT_MODE = previous


def _fetch_all_outcomes(
    queries: list,
    search_url_template: str,
    max_results: int = 15,
    evidence_dir: Optional[str] = None,
    on_outcome: Optional[Callable[[FetchOutcome], None]] = None,
    client=None,
) -> dict[str, FetchOutcome]:
    """Fetch every query's search page; return {query: FetchOutcome}, in input order.

    Every outcome carries a FetchStatus — an empty ``results`` list is only evidence of
    zero results when status is ZERO_CONFIRMED. ``queries`` may be strings or TestQuery.

    Probe-first: the first query establishes the site-level fetch mode (static /
    Playwright / blocked) with the cheapest transport that works; the rest reuse it.
    A blocked or unreachable site fails fast (every remaining query gets BLOCKED /
    TIMEOUT / ERROR with attempts=0, never an empty "zero"). ``on_outcome`` is called
    after each query (checkpointing). ``evidence_dir`` saves gzipped HTML (and, with
    Playwright, a viewport screenshot) per attempt; the paths are noted in evidence.
    """
    global _site_extraction_profile, _profile_attempted
    _site_extraction_profile = None
    _profile_attempted = False

    qlist = list(dict.fromkeys(_query_str(q) for q in queries))
    outcomes: dict[str, FetchOutcome] = {}

    def _emit(o: FetchOutcome) -> None:
        outcomes[o.query] = o
        logger.info("'%s' → %s, %d results%s", o.query, _status_value(o), len(o.results),
                    f" ({o.evidence[:120]})" if o.evidence else "")
        if on_outcome is not None:
            try:
                on_outcome(o)
            except Exception as e:  # a checkpoint failure must not lose the fetch
                logger.warning("on_outcome callback failed for '%s': %s", o.query, e)

    if not search_url_template or "{}" not in search_url_template:
        logger.error("Invalid search_url_template '%s' — must contain '{}'", search_url_template)
        for q in qlist:
            _emit(_outcome(q, FetchStatus.ERROR, attempts=0, evidence="invalid search URL template"))
        return {q: outcomes[q] for q in qlist}
    if not qlist:
        return {}

    total = len(qlist)
    remaining = list(qlist)
    site_mode = SiteMode.FAILED
    last_failure: Optional[FetchOutcome] = None
    probes = 0

    # ---- Phase 1: probe until a transport works ----------------------------
    while remaining and probes < _MAX_PROBES and site_mode == SiteMode.FAILED:
        q = remaining.pop(0)
        probes += 1
        url = _search_url(search_url_template, q)
        logger.info("[probe %d/%d] Probing with query: '%s'", probes, total, q)
        kind, value = _run_with_timeout(_PROBE_TIMEOUT_S, _probe_outcome, url, q, max_results, evidence_dir, client)
        if kind == "timeout":
            print(f"\nTIMEOUT: probing '{q}' exceeded {_PROBE_TIMEOUT_S}s — trying the next query as probe.\n")
            last_failure = _outcome(q, FetchStatus.TIMEOUT, final_url=url,
                                    evidence=f"site probe exceeded {_PROBE_TIMEOUT_S}s")
            _emit(last_failure)
            continue
        if kind == "error":
            last_failure = _outcome(q, FetchStatus.ERROR, final_url=url,
                                    evidence=f"probe failed: {type(value).__name__}: {value}"[:300])
            _emit(last_failure)
            continue
        probe_mode, outcome, html = value
        if probe_mode == SiteMode.FAILED:
            last_failure = outcome
            _emit(outcome)
            continue
        site_mode = probe_mode
        if site_mode != SiteMode.BLOCKED and _needs_retry(outcome, 1):
            outcome, html = _fetch_with_retries(url, q, max_results, site_mode, evidence_dir, client,
                                                first=(outcome, html))
        _emit(outcome)
        if site_mode == SiteMode.BLOCKED:
            last_failure = outcome
        else:
            _maybe_learn_profile(outcome, html, url, client)

    if site_mode in (SiteMode.BLOCKED, SiteMode.FAILED):
        status = FetchStatus.BLOCKED if site_mode == SiteMode.BLOCKED else (
            FetchStatus(_status_value(last_failure)) if last_failure is not None else FetchStatus.ERROR)
        reason = last_failure.evidence if last_failure is not None else site_mode
        logger.info("Site probe → %s — skipping %d remaining queries", site_mode, len(remaining))
        for q in remaining:
            _emit(_outcome(q, status, attempts=0, final_url=_search_url(search_url_template, q),
                           evidence=f"not fetched: site probe failed ({reason})"[:300]))
        _log_summary(outcomes, site_mode)
        return {q: outcomes[q] for q in qlist}

    # ---- Phase 2: proven mode for the rest ----------------------------------
    consecutive_blocks = 0
    last_status = FetchStatus.BLOCKED.value
    for i, q in enumerate(remaining, probes + 1):
        url = _search_url(search_url_template, q)
        if consecutive_blocks >= _MAX_CONSECUTIVE_BLOCKS:
            _emit(_outcome(q, FetchStatus(last_status), attempts=0, final_url=url,
                           evidence=f"not fetched: {consecutive_blocks} queries in a row ended {last_status}"))
            continue
        _sleep(_BETWEEN_QUERIES_S)
        logger.info("[%d/%d] Fetching '%s' (mode: %s)", i, total, q, site_mode)
        outcome, html = _fetch_with_retries(url, q, max_results, site_mode, evidence_dir, client)
        _emit(outcome)
        _maybe_learn_profile(outcome, html, url, client)
        last_status = _status_value(outcome)
        consecutive_blocks = consecutive_blocks + 1 if last_status in _FAILURE_STATUSES else 0

    _log_summary(outcomes, site_mode)
    return {q: outcomes[q] for q in qlist}


def fetch_all_results(
    search_url_template: str,
    queries: list,
    max_results: int = 15,
) -> dict[str, list[SearchResult]]:
    """Legacy wrapper: {query: results}. An empty list here can mean blocked, timeout or
    unverified — new code should call fetch_all_outcomes and read the status."""
    outcomes = fetch_all_outcomes(queries, search_url_template, max_results=max_results)
    return {q: o.results for q, o in outcomes.items()}


def _log_summary(outcomes: dict[str, FetchOutcome], mode: str) -> None:
    counts = Counter(_status_value(o) for o in outcomes.values())
    logger.info("Fetch complete: %d queries, mode=%s, statuses=%s", len(outcomes), mode, dict(counts))
    untrusted = sum(1 for o in outcomes.values() if not o.trusted)
    if outcomes and untrusted / len(outcomes) > 0.25:
        print(
            f"\nWARNING: {untrusted}/{len(outcomes)} queries were not observed reliably "
            f"({dict(counts)}). Site mode was '{mode}'. Check the evidence before judging.\n"
        )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    template = sys.argv[1] if len(sys.argv) > 1 else "https://www.groupon.com/search?query={}"
    demo_queries = ["spa deals", "restaurants"]

    print(f"Search template: {template}")
    print(f"Queries: {demo_queries}\n")

    for query_str, outcome in fetch_all_outcomes(demo_queries, template, max_results=15).items():
        print(f"\n{'='*60}")
        print(f"  Query: '{query_str}' — {outcome.status}, {len(outcome.results)} results")
        print(f"  {outcome.evidence}")
        print(f"{'='*60}")
        for r in outcome.results:
            print(f"  #{r.rank} {r.title[:80]}{'  [sponsored]' if r.sponsored else ''}")
            if r.price:
                print(f"       price:   {r.price}")
            if r.url:
                print(f"       url:     {r.url[:80]}")
