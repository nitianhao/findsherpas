from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from src.category_selector import CATEGORY_DESCRIPTIONS, RETIRED_CATEGORIES
from src.llm_compat import structured_call
from src.models import QueryCategory, QueryConstraints, SiteContext, SiteType, TestQuery

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Overridable per-run; unset env = unchanged default. See docs/CASE_STUDY_PLAYBOOK.md.
_MODEL = os.environ.get("AUDIT_MODEL_QUERIES", "claude-sonnet-4-6")
MIN_QUERY_COUNT = 60
MAX_QUERY_GENERATION_ATTEMPTS = 3
_MAX_TOKENS = 16000

# Same key discovery writes JSON-LD sku/mpn/gtin codes under (src/discovery.py CATALOG_CODES_KEY).
_CATALOG_CODES_KEY = "catalog_codes"

# ---------------------------------------------------------------------------
# Category groups
# ---------------------------------------------------------------------------

# Built in code from real site data — never by the LLM. An LLM cannot be trusted to copy
# titles verbatim, invent model numbers, or produce gibberish that is reliably gibberish.
DETERMINISTIC_CATEGORIES: frozenset[QueryCategory] = frozenset({
    QueryCategory.DIRECT_MATCH,
    QueryCategory.GIBBERISH,
    QueryCategory.SKU_MODEL_NUMBER,
})
# One base word per perturbation test across these three, or a single hard word gets
# counted as several failures (bächli: 4 base words carried 7 critical findings).
_PERTURBATION_CATEGORIES: frozenset[QueryCategory] = frozenset({
    QueryCategory.TYPO, QueryCategory.SPLIT_WORD, QueryCategory.SPECIAL_CHARACTER,
})
CONSTRAINT_CATEGORIES: frozenset[QueryCategory] = frozenset({
    QueryCategory.PRICE_ANCHORED, QueryCategory.NEGATIVE_INTENT,
    QueryCategory.MULTI_ATTRIBUTE, QueryCategory.FACET_EXTRACTION,
})
GIBBERISH_MAX = 4  # the four-recipe set in CATEGORIES_PLAYBOOK; more adds nothing

# ---------------------------------------------------------------------------
# Per-category counts
# ---------------------------------------------------------------------------

_HIGH = 4
_MEDIUM = 3
_LOW = 2

# Default per-category counts for a top-up run (enforce_min=False, no explicit counts).
# A full run spreads MIN_QUERY_COUNT evenly instead (_build_balanced_query_counts).
QUERY_COUNTS: dict[QueryCategory, int] = {
    # HIGH — most visible failure surface, need repetition to prove a pattern
    QueryCategory.TYPO: _HIGH,
    QueryCategory.SYNONYM: _HIGH,
    QueryCategory.NATURAL_LANGUAGE: _HIGH,
    QueryCategory.OCCASION: _HIGH,
    QueryCategory.SEMANTIC_MEANING: _HIGH,
    QueryCategory.GIBBERISH: GIBBERISH_MAX,
    # MEDIUM — still important, moderate coverage
    QueryCategory.MERGED_WORDS: _MEDIUM,
    QueryCategory.SPLIT_WORD: _MEDIUM,
    QueryCategory.PARTIAL_QUERY: _MEDIUM,
    QueryCategory.MULTI_ATTRIBUTE: _MEDIUM,
    QueryCategory.SUBJECTIVE_ATTRIBUTE: _MEDIUM,
    QueryCategory.CATEGORY_MAPPING: _MEDIUM,
    QueryCategory.FACET_EXTRACTION: _MEDIUM,
    QueryCategory.LONG_VERBOSE_QUERY: _MEDIUM,
    QueryCategory.STOP_WORD_HEAVY: _MEDIUM,
    # LOW — useful but narrower signal, two is enough
    QueryCategory.DIRECT_MATCH: _LOW,
    QueryCategory.BRAND_SEARCH: _LOW,
    QueryCategory.SKU_MODEL_NUMBER: _LOW,
    QueryCategory.SPECIAL_CHARACTER: _LOW,
    QueryCategory.PLURAL_SINGULAR: _LOW,
    QueryCategory.ABBREVIATION: _LOW,
    QueryCategory.LOCALE_VARIATION: _LOW,
    QueryCategory.PRICE_ANCHORED: _LOW,
    QueryCategory.NEGATIVE_INTENT: _LOW,
    QueryCategory.UNIT_VARIATION: _LOW,
    QueryCategory.SEASONAL_OCCASION: _LOW,
}


def _build_balanced_query_counts(
    selected_categories: list[QueryCategory],
    total: int = MIN_QUERY_COUNT,
) -> dict[QueryCategory, int]:
    """Evenly distribute at least ``total`` queries across the selected categories.

    The audit should not overweight one query type while barely sampling another.
    Counts differ by at most one query across the selected category set.
    """
    if not selected_categories:
        return {}

    target_total = max(total, len(selected_categories))
    base = target_total // len(selected_categories)
    remainder = target_total % len(selected_categories)

    return {
        category: base + (1 if index < remainder else 0)
        for index, category in enumerate(selected_categories)
    }


def _calculate_expected_total(
    selected_categories: list[QueryCategory],
    query_counts: dict[QueryCategory, int] | None = None,
) -> int:
    """Sum the expected query count for the given categories."""
    counts = query_counts or QUERY_COUNTS
    return sum(counts.get(cat, _LOW) for cat in selected_categories)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def _norm_key(text: str) -> str:
    """Dedupe/compare key: NFKC, casefolded, whitespace collapsed."""
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


def _tokens(text: str) -> list[str]:
    return _norm_key(text).split()


def _words(text: str) -> list[str]:
    """Alphanumeric words only (punctuation stripped) — for vocabulary building."""
    return re.findall(r"[^\W_]+", _norm_key(text))


def _damerau_levenshtein(a: str, b: str) -> int:
    """Optimal-string-alignment distance (adjacent transpositions count as one edit)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if not la or not lb:
        return la or lb
    prev2: list[int] = []
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[lb]


_STOP_TOKENS = {
    "with", "without", "under", "over", "from", "that", "this", "your", "for", "the", "and",
    "unter", "über", "ohne", "für", "mit", "und", "eine", "einen", "och", "utan", "med", "för",
    "pour", "sans", "avec", "moins", "pas", "uden", "til", "ikke", "voor", "zonder", "onder",
    "something", "need", "want", "looking", "etwas", "suche",
}


# ---------------------------------------------------------------------------
# Grounding: what the site actually shows
# ---------------------------------------------------------------------------


@dataclass
class _Grounding:
    titles: list[str] = field(default_factory=list)       # normalised catalog titles
    known_titles: set[str] = field(default_factory=set)   # norm keys of exact titles
    vocab: set[str] = field(default_factory=set)          # words seen on the site
    brands: list[str] = field(default_factory=list)       # normalised, longest first
    nav: set[str] = field(default_factory=set)
    nav_tokens: set[str] = field(default_factory=set)


def _grounding(site_context: SiteContext) -> _Grounding:
    titles_raw = list(site_context.featured_items or []) + list(site_context.catalog_sample or [])
    g = _Grounding()
    g.titles = [_norm_key(t) for t in titles_raw if t]
    g.known_titles = set(g.titles)
    g.nav = {_norm_key(n) for n in site_context.nav_categories or []}
    g.nav_tokens = {w for n in site_context.nav_categories or [] for w in _words(n)}
    g.brands = sorted({_norm_key(b) for b in site_context.brands or [] if len(_norm_key(b)) >= 2},
                      key=len, reverse=True)
    for text in [*titles_raw, *(site_context.nav_categories or []), *(site_context.brands or [])]:
        g.vocab.update(w for w in _words(text) if len(w) >= 2 and not w.isdigit())
    return g


# ---------------------------------------------------------------------------
# Deterministic categories
# ---------------------------------------------------------------------------

_RESULT_COUNT_RE = re.compile(r"\(\s*\d+\s*\w*\s*\)\s*$")


def _is_brand_category_phrase(title: str, g: _Grounding) -> bool:
    """'Mini Rodini barnkläder', 'Jellycat soft toy': a brand plus a generic type, not a title."""
    key = _norm_key(title)
    for brand in g.brands:
        if key == brand:
            return True
        if key.startswith(brand + " "):
            rest_orig = title.strip()[len(brand):].split() if len(title.strip()) > len(brand) else []
            rest = key[len(brand) + 1:].split()
            if not rest:
                return True
            if all(w in g.nav_tokens for w in rest):
                return True
            no_digits = not any(ch.isdigit() for ch in "".join(rest))
            all_lower = all(tok == tok.lower() for tok in rest_orig)
            return len(rest) <= 2 and no_digits and all_lower
    words = key.split()
    return len(words) <= 3 and all(w in g.nav_tokens for w in words)


def _direct_match_candidates(site_context: SiteContext, g: _Grounding | None = None) -> list[str]:
    """Exact product titles usable as DIRECT_MATCH queries: featured items first, then the
    catalog sample. Nav labels, single words, result-count strings and brand+category
    phrases are excluded."""
    g = g or _grounding(site_context)
    out: list[str] = []
    seen: set[str] = set()
    for raw in [*(site_context.featured_items or []), *(site_context.catalog_sample or [])]:
        title = " ".join(str(raw or "").split())
        key = _norm_key(title)
        if not key or key in seen or key in g.nav:
            continue
        seen.add(key)
        if not (3 <= len(title) <= 120) or len(key.split()) < 2:
            continue
        if re.search(r"[»«“”]", title) or _RESULT_COUNT_RE.search(title):
            continue
        if _is_brand_category_phrase(title, g):
            continue
        out.append(title)
    return out


def _spread(items: list, n: int) -> list:
    """n items spread evenly across the list (avoid taking only the first seed's titles)."""
    if n <= 0 or not items:
        return []
    if n >= len(items):
        return list(items)
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def _build_direct_match(site_context: SiteContext, n: int, seen: set[str], g: _Grounding) -> list[TestQuery]:
    candidates = [c for c in _direct_match_candidates(site_context, g) if _norm_key(c) not in seen]
    featured_keys = {_norm_key(f) for f in site_context.featured_items or []}
    featured = [c for c in candidates if _norm_key(c) in featured_keys]
    sampled = [c for c in candidates if _norm_key(c) not in featured_keys]
    picked = featured[:n] + _spread(sampled, max(0, n - len(featured)))
    return [
        TestQuery(
            category=QueryCategory.DIRECT_MATCH,
            query=title,
            target_term=title,
            rationale="Exact product title copied from the site — the product should come back first.",
        )
        for title in picked[:n]
    ]


def _keyboard_layout(site_context: SiteContext) -> str:
    """qwertz for DE/AT/CH (and CZ/SK/HU), azerty for FR/BE, qwerty elsewhere."""
    parts = re.split(r"[-_]", site_context.locale or "")
    lang = (parts[0] if parts else "").lower()
    region = next((p.upper() for p in parts[1:] if len(p) == 2), "")
    if region in {"DE", "AT", "CH", "LI", "CZ", "SK", "HU"}:
        return "qwertz"
    if region in {"FR", "BE"}:
        return "azerty"
    if region:
        return "qwerty"
    language = (site_context.primary_language or "").lower()
    if lang in {"de", "cs", "sk", "hu"} or language in {"german", "czech", "slovak", "hungarian"}:
        return "qwertz"
    if lang == "fr" or language == "french":
        return "azerty"
    return "qwerty"


_KEYBOARD_ROWS = {"qwerty": "qwertyuiop", "qwertz": "qwertzuiop", "azerty": "azertyuiop"}
# (3) and (4) share no characters: if two inputs with nothing in common return the same
# products, the engine is serving a fallback list rather than matching anything.
_GIBBERISH_LONG = "sfjhdshdssjhdfdsshsdhgsddgshdghshdksghskgdhgshkhkghkskhksdnsidssi"
_GIBBERISH_CONSONANTS = "xkvbnmwrtsdfg"
_GIBBERISH_REPEATED = "zzzqqqjjjyyy"
assert not set(_GIBBERISH_CONSONANTS) & set(_GIBBERISH_REPEATED)


def build_gibberish(site_context: SiteContext, n: int = GIBBERISH_MAX) -> list[TestQuery]:
    """The CATEGORIES_PLAYBOOK recipe: long mash, locale keyboard row, consonant mash,
    repeated-letter mash. Correct behaviour is zero results; target_term is None."""
    layout = _keyboard_layout(site_context)
    recipes = [
        (_GIBBERISH_LONG, "Long keyboard mash (50+ characters) — the right answer is zero results."),
        (_KEYBOARD_ROWS[layout], f"Top keyboard row on a {layout} keyboard — a classic test input; the right answer is zero results."),
        (_GIBBERISH_CONSONANTS, "Consonant mash — the right answer is zero results."),
        (_GIBBERISH_REPEATED, "Repeated-letter mash sharing no letters with the consonant mash — if both return the same products, the engine serves a fallback list."),
    ]
    # With fewer than four, keep the consonant/repeated pair first: it is the sharpest test.
    priority = [2, 3, 0, 1][: max(0, min(n, GIBBERISH_MAX))]
    return [
        TestQuery(category=QueryCategory.GIBBERISH, query=recipes[i][0], rationale=recipes[i][1], target_term=None)
        for i in sorted(priority)
    ]


def _catalog_codes(site_context: SiteContext, explicit: list[dict] | None = None) -> list[dict]:
    if explicit is not None:
        return [c for c in explicit if isinstance(c, dict) and c.get("code")]
    raw = (site_context.provenance or {}).get(_CATALOG_CODES_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [c for c in data if isinstance(c, dict) and c.get("code")] if isinstance(data, list) else []


def _build_sku_queries(site_context: SiteContext, n: int, seen: set[str], codes: list[dict]) -> list[TestQuery]:
    """SKU_MODEL_NUMBER from codes the site itself declares (JSON-LD sku/mpn/gtin) — never invented."""

    def _rank(c: dict) -> tuple:
        code = str(c["code"])
        mixed = any(ch.isalpha() for ch in code) and any(ch.isdigit() for ch in code)
        return (0 if c.get("kind") in ("sku", "mpn") else 1, 0 if mixed else 1)

    out: list[TestQuery] = []
    for c in sorted(codes, key=_rank):
        code = str(c["code"]).strip()
        if not code or _norm_key(code) in seen:
            continue
        title = str(c.get("title") or "").strip()
        kind = str(c.get("kind") or "code").upper()
        out.append(TestQuery(
            category=QueryCategory.SKU_MODEL_NUMBER,
            query=code,
            target_term=title or code,
            rationale=f"{kind} from the site's own product data"
            + (f" for '{title}'" if title else "")
            + " — shoppers paste codes like this into search.",
        ))
        seen.add(_norm_key(code))
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_CURRENCY_WORDS = {
    "EUR": "euro", "GBP": "pounds", "USD": "dollars", "CHF": "Franken / francs", "SEK": "kronor",
    "DKK": "kroner", "NOK": "kroner", "PLN": "złotych", "CZK": "korun", "CAD": "dollars",
    "AUD": "dollars", "JPY": "yen",
}

_SYSTEM_PROMPT = """You are a search-quality engineer generating test queries for an ecommerce site audit. The site data (language, currency, real catalog titles, brands, navigation) and the categories to generate arrive in the user message.

## Hard rules
0. LANGUAGE: write every query in the site's primary customer language. International brand names stay as-is; every other word (product types, attributes, natural phrasing) is in the site language. English only if the site language IS English.
1. GROUNDING: every query must be built from real words in the site data — sampled catalog titles, brands, navigation labels. Never invent a product, brand, model number, size or category. Pair a brand with a product type ONLY when a sampled title shows that brand selling that type ("Mammut Mascara" or "alpibreak Jacke" are invalid when the brand sells neither).
2. target_term (every query): the plainest head term the shopper's intent reduces to, in the site language — "Wanderschuhe" for "Wandersch uhe", "jacket" for "waterproof jacket under 100 pounds", "Salomon" for "Sal&omon". It is searched on its own as a control, so it must be something the sampled catalog shows the site sells.
3. constraints: fill for PRICE_ANCHORED, NEGATIVE_INTENT, MULTI_ATTRIBUTE and FACET_EXTRACTION exactly as described below; null for every other category.
4. ONE perturbation per query. TYPO, SPLIT_WORD and SPECIAL_CHARACTER queries each change exactly one word, and each must use a DIFFERENT base word — never reuse a base word across these three categories (one hard word would otherwise be counted as several failures).
5. VARIETY: spread queries across different product nouns from the catalog sample; no single noun in more than a third of the queries.
6. Every query string is unique and reads like what a shopper types into a search box (lowercase fine, no formal grammar).
7. rationale: one sentence — (a) which site content it is grounded in, (b) what search behaviour it tests. If you cannot name the grounding, do not emit the query.

## Category rules
- TYPO: a drastic but phonetically realistic misspelling of ONE real word — consonant swaps (v→f, s→z), dropped vowels, doubled letters: "Pullofer" (Pullover), "Mamuth" (Mammut), "Zalomoon" (Salomon). 1-3 edits from the real word. The misspelling must not be as close to a DIFFERENT real word ("Wandaschuhe" is as close to "Handschuhe" as to "Wanderschuhe" — invalid) and must not itself be a real word. target_term = the correctly spelled term.
- MERGED_WORDS: two real words typed with NO space: "runningshoes". target_term = the two words with the space ("running shoes").
- SPLIT_WORD: break ONE single word at an arbitrary internal point that is NOT a compound/morpheme seam: "jack et" (jacket), "trous ers" (trousers), "Wanderho sen" (not "Wander hosen"). Both fragments at least 2 letters; neither fragment may be a real word on its own ("s hoes" is invalid: lone letter, and "hoes" is a word). target_term = the unsplit word.
- SPECIAL_CHARACTER: inject exactly ONE special character (*, &, #, $) INSIDE a single real word — never at its start or end, never between two words: "wal*king boots", "Sal&omon". A brand's real apostrophe or hyphen ("Arc'teryx") is not a test. target_term = the clean term.
- SYNONYM: a natural alternative a customer might type for a real category/product term ("sneakers" for "Running Shoes").
- BRAND_SEARCH: ONLY brands from the brands list, alone or with a product type that brand demonstrably sells (see rule 1).
- PARTIAL_QUERY: a truncated real product/brand name ("patag" for Patagonia).
- PLURAL_SINGULAR: the harder direction — the PLURAL, preferring plurals that differ non-trivially from the singular ("scarves", "knives"), not a bare "+s".
- ABBREVIATION: a common abbreviation of a real term on the site.
- LOCALE_VARIATION: a regional spelling or vocabulary variant of a real term (colour/color, trainers/sneakers, Fussball/Fußball). Not a plain query dressed up as a variant.
- CATEGORY_MAPPING: a colloquial term that maps to one of the site's REAL category labels (the target category must exist on the site).
- OCCASION / SEMANTIC_MEANING / NATURAL_LANGUAGE: scenarios grounded in what the site sells; reference real product types.
- SUBJECTIVE_ATTRIBUTE: subjective qualifiers ("cosy", "elegant") on real product types.
- SEASONAL_OCCASION: real product types with a seasonal/event context.
- STOP_WORD_HEAVY: real product/category terms padded with natural stop words.
- LONG_VERBOSE_QUERY: a long, over-specified query about real products/categories.
- UNIT_VARIATION: real products with measurement-format variations ("50ml" vs "50 ml", "size 9" vs "43").
- PRICE_ANCHORED: a real product type plus ONE price limit, the currency written as the WORD shoppers use in the market language, never a symbol: "jacket under 100 pounds", "Jacke unter 100 Franken", "serum under 300 kronor". constraints.price_max (or price_min for "over"/"from") = the number.
- NEGATIVE_INTENT: a real product type plus ONE exclusion after "not"/"without" (in the site language): "knitwear without wool". constraints.exclude = [the excluded term exactly as written in the query].
- MULTI_ATTRIBUTE: a real base product term plus EXACTLY TWO attributes that would appear in a product title (colour, material, gender, volume…), both taken from words seen in sampled titles: "black leather boots". constraints.attributes = the two attribute words exactly as written in the query.
- FACET_EXTRACTION: a real base product term plus EXACTLY ONE filter value (colour, material, size, location): "rucksack 30 l". Sizes and volumes must be realistic for the product type (foundation 30 ml, not 100 ml). constraints.attributes = [that value exactly as written in the query].

Generate exactly the number of queries requested per category."""


def _build_prompt(
    site_context: SiteContext,
    selected_categories: list[QueryCategory],
    query_counts: dict[QueryCategory, int],
    existing_queries: list[str] | None = None,
    rejected: list[tuple[str, str, str]] | None = None,
    used_base_words: set[str] | None = None,
) -> str:
    """Per-call user prompt: site data, categories and counts, prior queries and rejections."""

    nav_list = ", ".join(site_context.nav_categories[:40]) if site_context.nav_categories else "(none detected)"
    brands_list = ", ".join(site_context.brands[:40]) if site_context.brands else "(none detected)"
    titles = list(dict.fromkeys([*(site_context.featured_items or []), *(site_context.catalog_sample or [])]))[:150]
    titles_block = "\n".join(f"  - {t}" for t in titles) if titles else "  (none sampled)"

    categories_block = ""
    for cat in selected_categories:
        count = query_counts.get(cat, _LOW)
        desc = CATEGORY_DESCRIPTIONS.get(cat, "")
        categories_block += f"  - {cat.value} (generate {count} queries): {desc}\n"
    total = _calculate_expected_total(selected_categories, query_counts)

    existing_block = ""
    if existing_queries:
        existing_lines = "\n".join(f"  - {q}" for q in existing_queries)
        existing_block = f"\n## Queries Already Generated\nDo NOT repeat or lightly rephrase any of these:\n{existing_lines}\n"
    if used_base_words:
        existing_block += (
            "\nBase words already used by TYPO / SPLIT_WORD / SPECIAL_CHARACTER (do not reuse): "
            + ", ".join(sorted(used_base_words)) + "\n"
        )
    rejected_block = ""
    if rejected:
        lines = "\n".join(f'  - "{q}" ({c}): {r}' for q, c, r in rejected[:40])
        rejected_block = f"\n## Rejected Last Round\nThese failed validation. Do not resubmit them; fix the stated problem:\n{lines}\n"

    primary_language = getattr(site_context, "primary_language", "English") or "English"
    currency = site_context.currency or ""
    currency_line = (
        f"{currency} — write it as a word, e.g. '{_CURRENCY_WORDS.get(currency, currency)}' (in {primary_language})"
        if currency else "(unknown — use the currency word customers in this market use)"
    )

    return f"""## Site Under Test
- **Site name**: {site_context.site_name or "(unknown)"}
- **URL**: {site_context.url}
- **Site type**: {site_context.site_type}
- **Primary customer language**: {primary_language} (locale {site_context.locale or "unknown"})
- **Currency**: {currency_line}
- **Meta description**: {site_context.raw_meta_description or "(none)"}

## Real Content From This Site
**Navigation categories**: {nav_list}
**Brands carried**: {brands_list}
**Sampled catalog titles ({len(titles)})** — the ground truth for brand×type pairs, attributes and nouns:
{titles_block}

## Categories to Generate ({total} queries total)
{categories_block}{existing_block}{rejected_block}
All queries in **{primary_language}**."""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


class GeneratedConstraints(BaseModel):
    price_max: Optional[float]
    price_min: Optional[float]
    exclude: list[str]
    attributes: list[str]


class GeneratedQuery(BaseModel):
    category: QueryCategory
    query: str
    target_term: str
    rationale: str
    constraints: Optional[GeneratedConstraints]


class GeneratedBatch(BaseModel):
    queries: list[GeneratedQuery]


def _call_llm(system: str, user: str, client=None) -> list[dict]:
    """One structured call (phase="queries"). Returns raw entry dicts; raises on failure."""
    out = structured_call(
        model=_MODEL, system=system, user=user, schema=GeneratedBatch,
        max_tokens=_MAX_TOKENS, phase="queries", temperature=0.7, client=client,
    )
    return _entries(out)


def _entries(parsed) -> list:
    """Raw entries from a parsed batch (model, dict, or anything with ``.queries``)."""
    items = parsed.get("queries") if isinstance(parsed, dict) else getattr(parsed, "queries", parsed)
    out = []
    for item in items or []:
        out.append(item.model_dump(mode="json") if isinstance(item, BaseModel) else item)
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _as_str(value) -> str | None:
    """Coerce an LLM field to a stripped string. Numbers become strings; anything else -> None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        value = str(int(value)) if float(value).is_integer() else str(value)
    if not isinstance(value, str):
        return None
    return " ".join(value.split())


def _str_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [s for s in (_as_str(v) for v in value) if s]


def _as_float(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        m = re.search(r"\d+(?:[.,]\d+)?", str(value))
        return float(m.group(0).replace(",", ".")) if m else None


def _constraints(raw) -> QueryConstraints | None:
    if isinstance(raw, BaseModel):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        return None
    return QueryConstraints(
        price_max=_as_float(raw.get("price_max")),
        price_min=_as_float(raw.get("price_min")),
        exclude=_str_list(raw.get("exclude")),
        attributes=_str_list(raw.get("attributes")),
    )


def _contains(haystack_key: str, needle: str) -> bool:
    n = _norm_key(needle)
    return bool(n) and re.search(rf"(?<![^\W_]){re.escape(n)}(?![^\W_])", haystack_key) is not None


def _changed_word(query: str, target: str) -> tuple[list[str], list[str]]:
    """(target words missing from the query, query words not in the target)."""
    q, t = _tokens(query), _tokens(target)
    return [w for w in t if w not in q], [w for w in q if w not in t]


def _check_typo(query: str, target: str, g: _Grounding) -> tuple[str | None, str | None]:
    missing, extra = _changed_word(query, target)
    if not missing:
        return "query contains target_term unchanged — no misspelling", None
    if len(missing) > 1:
        return "more than one word changed — one perturbation per query", None
    base = missing[0]
    if not extra:
        return f"no misspelled form of '{base}' in the query", None
    typo = min(extra, key=lambda w: _damerau_levenshtein(w, base))
    dist = _damerau_levenshtein(typo, base)
    if not 1 <= dist <= 3:
        return f"'{typo}' is {dist} edits from '{base}' (need 1-3)", base
    if typo in g.vocab:
        return f"'{typo}' is itself a real word on the site", base
    for word in g.vocab:
        if word == base or abs(len(word) - len(typo)) > dist or len(word) < 3:
            continue
        if _damerau_levenshtein(word, base) <= 2:
            continue  # an inflection of the target itself
        if _damerau_levenshtein(typo, word) <= dist:
            return (f"'{typo}' is as close to the real word '{word}' as to '{base}' — "
                    f"the engine may correctly match '{word}'"), base
    return None, base


def _check_split(query: str, target: str, g: _Grounding) -> tuple[str | None, str | None]:
    missing, _extra = _changed_word(query, target)
    if len(missing) != 1:
        return ("target_term must differ from the query by exactly one split word"
                if missing else "query contains target_term unsplit"), None
    base = missing[0]
    q = _tokens(query)
    for i in range(len(q) - 1):
        if q[i] + q[i + 1] == base:
            a, b = q[i], q[i + 1]
            if min(len(a), len(b)) < 2:
                return f"fragment too short ('{a} {b}') — a lone letter is not a split-word test", base
            for frag in (a, b):
                if len(frag) >= 3 and frag in g.vocab:
                    return f"fragment '{frag}' is itself a word on the site — the engine can match it alone", base
            return None, base
    return f"no two adjacent fragments join back to '{base}'", None


def _check_special(query: str, target: str) -> tuple[str | None, str | None]:
    missing, extra = _changed_word(query, target)
    if len(missing) != 1:
        return ("exactly one word must carry the injected character"
                if missing else "query contains target_term unchanged"), None
    base = missing[0]

    def _strip(s: str) -> str:
        return re.sub(r"[\W_]", "", s)

    for tok in extra:
        if tok != base and _strip(tok) == _strip(base):
            injected = len(re.findall(r"[\W_]", tok)) - len(re.findall(r"[\W_]", base))
            if injected != 1:
                return f"'{tok}' injects {injected} characters — inject exactly one", base
            if re.match(r"[\W_]", tok) or re.search(r"[\W_]$", tok):
                return f"the character in '{tok}' must sit inside the word, not at its edge", base
            return None, base
    return f"no word in the query is '{base}' with one injected character", None


def _check_merged(query: str, target: str, g: _Grounding) -> str | None:
    if re.search(r"\s", query.strip()):
        return "merged query must contain no space"
    t = _tokens(target)
    if len(t) < 2:
        return "target_term must be the merged words with their space"
    if _norm_key(query) != "".join(t):
        return "query is not target_term with the space removed"
    if len(g.vocab) >= 50:
        unseen = [w for w in t if w not in g.vocab]
        if unseen:
            return f"merged part(s) {unseen} never appear on the site"
    return None


def _check_brand(query: str, g: _Grounding) -> str | None:
    qk = _norm_key(query)
    found = next((b for b in g.brands if _contains(qk, b)), None)
    if not found:
        if g.brands:
            return "no brand from the site's brand list in the query"
        first = qk.split()[0] if qk else ""
        if sum(1 for t in g.titles if _contains(t, first)) < 2:
            return "no brand list available and the brand is not seen in catalog titles"
        return None
    rest = [w for w in qk.replace(found, " ").split() if len(w) >= 3 and w not in _STOP_TOKENS]
    if rest and len(g.titles) >= 30:
        brand_titles = [t for t in g.titles if _contains(t, found)]
        if brand_titles and not any(w[:5] in t for t in brand_titles for w in rest):
            return (f"'{found}' appears in sampled titles but never with '{' '.join(rest)}' — "
                    "likely a brand/category mismatch")
    return None


def _check_constraints(cat: QueryCategory, query: str, c: QueryConstraints | None, g: _Grounding) -> str | None:
    qk = _norm_key(query)
    if cat == QueryCategory.PRICE_ANCHORED:
        if c is None or (c.price_max is None and c.price_min is None):
            return "constraints.price_max/price_min missing"
        if re.search(r"[€£$¥]", query):
            return "write the currency as a word, not a symbol (a symbol in the URL is a fetch hazard)"
        if not re.search(r"\d", query):
            return "price number missing from the query"
        return None
    if cat == QueryCategory.NEGATIVE_INTENT:
        if c is None or len(c.exclude) != 1:
            return "constraints.exclude must hold exactly one excluded term"
        if not _contains(qk, c.exclude[0]):
            return f"excluded term '{c.exclude[0]}' not in the query"
        return None
    if cat in (QueryCategory.MULTI_ATTRIBUTE, QueryCategory.FACET_EXTRACTION):
        need = 2 if cat == QueryCategory.MULTI_ATTRIBUTE else 1
        if c is None or len(c.attributes) != need:
            return f"constraints.attributes must hold exactly {need} attribute(s)"
        for attr in c.attributes:
            if not _contains(qk, attr):
                return f"attribute '{attr}' not in the query"
            if len(g.titles) >= 30 and not any(_contains(t, attr) for t in g.titles):
                return f"attribute '{attr}' never appears in a sampled title — not title-visible"
        return None
    return None


def _perturbation_base(tq: TestQuery) -> str | None:
    """Base word of an existing TYPO/SPLIT_WORD/SPECIAL_CHARACTER query (best effort)."""
    if QueryCategory(tq.category) not in _PERTURBATION_CATEGORIES or not tq.target_term:
        return None
    missing, _ = _changed_word(tq.query, tq.target_term)
    return missing[0] if len(missing) == 1 else None


@dataclass
class _ScreenState:
    seen: set[str]
    used_bases: set[str]
    capacity: dict[QueryCategory, int]


def _screen_entry(entry, requested: set[QueryCategory], g: _Grounding, state: _ScreenState,
                  site_context: SiteContext | None) -> tuple[TestQuery | None, str | None, str, str]:
    """Validate one raw entry. Returns (query or None, reject reason or None, query text, category)."""
    if isinstance(entry, BaseModel):
        entry = entry.model_dump(mode="json")
    if not isinstance(entry, dict):
        return None, "malformed entry (not an object)", str(entry)[:60], "?"
    raw_cat = entry.get("category")
    cat_name = _as_str(getattr(raw_cat, "value", raw_cat)) or ""
    query = _as_str(entry.get("query")) or ""
    if cat_name not in QueryCategory._value2member_map_:
        return None, f"invalid category '{cat_name}'", query, cat_name
    cat = QueryCategory(cat_name)
    if cat in RETIRED_CATEGORIES:
        return None, "retired category", query, cat_name
    if cat not in requested:
        return None, "category not requested in this round", query, cat_name
    if not query:
        return None, "empty or non-text query", query, cat_name
    key = _norm_key(query)
    if key in state.seen:
        return None, "duplicate query", query, cat_name
    if state.capacity.get(cat, 0) <= 0:
        return None, None, query, cat_name  # over target — silently dropped, not a defect

    if cat == QueryCategory.DIRECT_MATCH:
        if key in g.nav:
            return None, "DIRECT_MATCH query is a navigation category label, not a specific product", query, cat_name
        if key not in g.known_titles:
            return None, "DIRECT_MATCH must be an exact title from the site", query, cat_name

    target = _as_str(entry.get("target_term"))
    if not target and cat != QueryCategory.GIBBERISH:
        return None, "target_term missing", query, cat_name
    constraints = _constraints(entry.get("constraints"))

    reason, base = None, None
    if cat == QueryCategory.TYPO:
        reason, base = _check_typo(query, target, g)
    elif cat == QueryCategory.SPLIT_WORD:
        reason, base = _check_split(query, target, g)
    elif cat == QueryCategory.SPECIAL_CHARACTER:
        reason, base = _check_special(query, target)
    elif cat == QueryCategory.MERGED_WORDS:
        reason = _check_merged(query, target, g)
    elif cat == QueryCategory.BRAND_SEARCH:
        reason = _check_brand(query, g)
    elif cat in CONSTRAINT_CATEGORIES:
        reason = _check_constraints(cat, query, constraints, g)
    if reason is None and base is not None and base in state.used_bases:
        reason = f"base word '{base}' is already used by another typo/split/special-character test"
    if reason:
        return None, reason, query, cat_name

    rationale = _as_str(entry.get("rationale")) or f"Tests {cat_name} behaviour"
    tq = TestQuery(
        category=cat,
        query=query,
        rationale=rationale,
        target_term=target,
        constraints=constraints if cat in CONSTRAINT_CATEGORIES else None,
    )
    state.seen.add(key)
    state.capacity[cat] = state.capacity.get(cat, 0) - 1
    if base:
        state.used_bases.add(base)
    return tq, None, query, cat_name


def _screen_batch(
    raw_queries: list,
    requested: dict[QueryCategory, int],
    site_context: SiteContext | None,
    state: _ScreenState,
    g: _Grounding,
) -> tuple[list[TestQuery], list[tuple[str, str, str]]]:
    """Validate a batch. Returns (accepted, rejected as (query, category, reason))."""
    accepted: list[TestQuery] = []
    rejected: list[tuple[str, str, str]] = []
    for entry in raw_queries or []:
        tq, reason, text, cat_name = _screen_entry(entry, set(requested), g, state, site_context)
        if tq is not None:
            accepted.append(tq)
        elif reason:
            logger.warning("Rejected '%s' (%s): %s", text, cat_name, reason)
            rejected.append((text, cat_name, reason))
    return accepted, rejected


def _validate_queries(
    raw_queries: list,
    selected_categories: list[QueryCategory],
    query_counts: dict[QueryCategory, int],
    site_context: SiteContext | None = None,
) -> list[TestQuery]:
    """Validate and convert raw entries to TestQuery objects (accepted ones only)."""
    ctx = site_context or SiteContext(url="", site_type=SiteType.MARKETPLACE_MIXED)
    capacity = {c: query_counts.get(c, _LOW) for c in selected_categories}
    state = _ScreenState(seen=set(), used_bases=set(), capacity=capacity)
    accepted, _ = _screen_batch(raw_queries, capacity.copy(), ctx, state, _grounding(ctx))
    return accepted


def _missing_query_counts(
    queries: list[TestQuery],
    query_counts: dict[QueryCategory, int],
) -> dict[QueryCategory, int]:
    """Return categories still missing queries after validation/dedupe."""
    counts = Counter(q.category for q in queries)
    missing: dict[QueryCategory, int] = {}
    for category, expected in query_counts.items():
        actual = counts.get(category.value, 0)
        if actual < expected:
            missing[category] = expected - actual
    return missing


def _concentration(queries: list[TestQuery], threshold: float = 0.4) -> tuple[str, float] | None:
    """The noun used by more than ``threshold`` of the free-form queries, if any."""
    skip = {QueryCategory.DIRECT_MATCH.value, QueryCategory.BRAND_SEARCH.value,
            QueryCategory.GIBBERISH.value, QueryCategory.SKU_MODEL_NUMBER.value}
    pool = [q for q in queries if q.category not in skip]
    if len(pool) < 10:
        return None
    counts: Counter = Counter()
    for q in pool:
        words = {w for w in _words(f"{q.query} {q.target_term or ''}") if len(w) >= 4 and not w.isdigit()}
        counts.update(words - _STOP_TOKENS)
    if not counts:
        return None
    noun, n = counts.most_common(1)[0]
    share = n / len(pool)
    return (noun, share) if share > threshold else None


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def _plan(
    site_context: SiteContext,
    selected_categories: list[QueryCategory],
    counts: dict[QueryCategory, int] | None,
    existing: list[TestQuery],
    enforce_min: bool,
    catalog_codes: list[dict] | None,
    seen: set[str],
    g: _Grounding,
) -> tuple[list[TestQuery], dict[QueryCategory, int], list[str]]:
    """Build the deterministic queries and the per-category counts left for the LLM.

    A shortfall in a deterministic category (fewer real titles / codes than requested) is
    reallocated round-robin to the LLM categories when this is a planned run (no explicit
    counts) or ``enforce_min`` is on — so a site with three featured items still gets its
    full query budget instead of failing on "Missing required coverage: DIRECT_MATCH".
    """
    planned = counts is None
    if counts is None:
        if enforce_min:
            total = max(MIN_QUERY_COUNT - len(existing), len(selected_categories))
            counts = _build_balanced_query_counts(selected_categories, total)
        else:
            counts = {c: QUERY_COUNTS.get(c, _LOW) for c in selected_categories}
    order = [*selected_categories, *[c for c in counts if c not in selected_categories]]
    notes: list[str] = []
    deterministic: list[TestQuery] = []
    llm_counts: dict[QueryCategory, int] = {}
    shortfall = 0
    for cat in dict.fromkeys(QueryCategory(c) for c in order):
        n = int(counts.get(cat, 0) or 0)
        if n <= 0:
            continue
        if cat in RETIRED_CATEGORIES:
            notes.append(f"{cat.value}: retired category, not generated")
            continue
        if cat not in DETERMINISTIC_CATEGORIES:
            llm_counts[cat] = n
            continue
        if cat == QueryCategory.DIRECT_MATCH:
            built = _build_direct_match(site_context, n, seen, g)
            why = f"only {len(built)} exact catalog titles available"
        elif cat == QueryCategory.GIBBERISH:
            built = [q for q in build_gibberish(site_context, n) if _norm_key(q.query) not in seen]
            why = f"capped at {GIBBERISH_MAX} (playbook recipe)"
        else:
            built = _build_sku_queries(site_context, n, seen, _catalog_codes(site_context, catalog_codes))
            why = ("no sku/mpn/gtin in the discovery JSON-LD — never invent codes"
                   if not built else f"only {len(built)} real codes found")
        for q in built:
            seen.add(_norm_key(q.query))
        deterministic.extend(built)
        if len(built) < n:
            shortfall += n - len(built)
            notes.append(f"{cat.value}: {len(built)}/{n} ({why})")
            logger.warning("%s: built %d of %d — %s", cat.value, len(built), n, why)

    if shortfall and (planned or enforce_min):
        targets = list(llm_counts)
        if targets:
            for i in range(shortfall):
                llm_counts[targets[i % len(targets)]] += 1
            notes.append(f"reallocated {shortfall} to {', '.join(c.value for c in targets)}")
        else:
            notes.append(f"{shortfall} unfilled: no LLM categories to reallocate to")
    return deterministic, llm_counts, notes


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def generate_queries(
    site_context: SiteContext,
    selected_categories: list[QueryCategory],
    counts: dict[QueryCategory, int] | None = None,
    existing: list[TestQuery] | None = None,
    enforce_min: bool = True,
    *,
    catalog_codes: list[dict] | None = None,
    client=None,
) -> list[TestQuery]:
    """Generate grounded test queries for the selected categories.

    DIRECT_MATCH (real titles), GIBBERISH (playbook recipe) and SKU_MODEL_NUMBER (JSON-LD
    codes) are built in code; every other category comes from one structured LLM call per
    attempt, screened by deterministic validators whose rejections are fed back into the
    next attempt.

    Args:
        counts: exact per-category counts. Default: spread MIN_QUERY_COUNT evenly
            (``enforce_min``) or QUERY_COUNTS per category (top-up).
        existing: queries already kept — never repeated, and their perturbation base words
            are not reused. Use with ``counts`` to top up or regenerate one category.
        enforce_min: require ``len(existing) + len(result) >= MIN_QUERY_COUNT``.
        catalog_codes: override for discovery's sku/mpn/gtin list.

    Returns only the NEW queries, sorted by category. Provenance (model, prompt hash,
    timestamp, notes) is written to ``site_context.provenance['queries_*']``.
    """
    selected_categories = [QueryCategory(c) for c in selected_categories]
    if counts is not None:
        counts = {QueryCategory(k): int(v) for k, v in counts.items()}
    existing = list(existing or [])
    prov = site_context.provenance
    g = _grounding(site_context)
    seen = {_norm_key(q.query) for q in existing}
    used_bases = {b for b in (_perturbation_base(q) for q in existing) if b}

    deterministic, llm_counts, notes = _plan(
        site_context, selected_categories, counts, existing, enforce_min, catalog_codes, seen, g
    )
    expected = len(deterministic) + sum(llm_counts.values())
    logger.info(
        "Generating ~%d queries (%d deterministic) across %d categories for %s",
        expected, len(deterministic), len(selected_categories), site_context.site_name or site_context.url,
    )

    prov["queries_model"] = _MODEL
    prov["queries_system_sha256"] = hashlib.sha256(_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    prov["queries_generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    state = _ScreenState(seen=seen, used_bases=used_bases, capacity=dict(llm_counts))
    generated: list[TestQuery] = []
    rejected: list[tuple[str, str, str]] = []
    attempts = 0
    for attempt in range(1, MAX_QUERY_GENERATION_ATTEMPTS + 1):
        missing = _missing_query_counts(generated, llm_counts)
        if not missing:
            break
        attempts = attempt
        user = _build_prompt(
            site_context,
            list(missing),
            missing,
            existing_queries=[q.query for q in [*existing, *deterministic, *generated]],
            rejected=rejected,
            used_base_words=state.used_bases,
        )
        if attempt == 1:
            prov["queries_prompt_sha256"] = hashlib.sha256(f"{_SYSTEM_PROMPT}\n\n{user}".encode("utf-8")).hexdigest()
        try:
            raw_queries = _call_llm(_SYSTEM_PROMPT, user, client=client)
        except Exception as e:
            logger.error("Query generation LLM call failed on attempt %d/%d: %s: %s",
                         attempt, MAX_QUERY_GENERATION_ATTEMPTS, type(e).__name__, e)
            prov["queries_last_error"] = f"{type(e).__name__}: {e}"[:300]
            continue
        logger.info("LLM returned %d raw query entries on attempt %d/%d",
                    len(raw_queries), attempt, MAX_QUERY_GENERATION_ATTEMPTS)
        accepted, rejected = _screen_batch(raw_queries, missing, site_context, state, g)
        generated.extend(accepted)
        logger.info("Validated %d/%d LLM queries after attempt %d (%d rejected)",
                    len(generated), sum(llm_counts.values()), attempt, len(rejected))

    prov["queries_attempts"] = str(attempts)
    if notes:
        prov["queries_notes"] = "; ".join(notes)[:1000]

    missing = _missing_query_counts(generated, llm_counts)
    result = [*deterministic, *generated]
    if missing:
        missing_desc = ", ".join(f"{cat.value}: {count}" for cat, count in missing.items())
        raise RuntimeError(
            f"Query generation produced {len(result)}/{expected} validated queries. "
            f"Missing required coverage: {missing_desc}"
        )
    if enforce_min and len(existing) + len(result) < MIN_QUERY_COUNT:
        raise RuntimeError(
            f"Query generation produced {len(existing) + len(result)} queries (incl. {len(existing)} existing), "
            f"below the minimum of {MIN_QUERY_COUNT}."
        )

    flagged = _concentration([*existing, *result])
    if flagged:
        noun, share = flagged
        prov["queries_concentration"] = f"'{noun}' in {share:.0%} of queries"
        logger.warning("Term concentration: '%s' appears in %.0f%% of queries — rebalance before fetching",
                       noun, share * 100)

    logger.info("Validated %d queries (expected %d)", len(result), expected)
    cat_order = {QueryCategory(cat).value: i for i, cat in enumerate(selected_categories)}
    result.sort(key=lambda tq: cat_order.get(tq.category, 999))
    return result


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    demo_context = SiteContext(
        url="https://www.kicksworld.com",
        site_name="KicksWorld",
        site_type=SiteType.PHYSICAL_GOODS,
        nav_categories=[
            "Men's Shoes", "Women's Shoes", "Kids' Shoes",
            "Running", "Casual", "Basketball", "Training",
            "Sandals & Slides", "Boots", "Sale", "New Arrivals",
        ],
        brands=[
            "Nike", "Adidas", "New Balance", "Puma", "Reebok",
            "Asics", "Converse", "Vans", "Under Armour", "Hoka",
        ],
        featured_items=[
            "Nike Air Max 90",
            "Adidas Ultraboost 22",
            "New Balance 574 Classic",
            "Nike Dunk Low Retro",
            "Hoka Clifton 9",
            "Converse Chuck Taylor All Star",
            "Puma RS-X",
            "Asics Gel-Kayano 30",
            "Vans Old Skool",
            "Under Armour HOVR Phantom 3",
        ],
        search_url_template="https://www.kicksworld.com/search?q={}",
        raw_meta_description=(
            "KicksWorld — shop the latest sneakers, running shoes, and casual "
            "footwear from Nike, Adidas, New Balance, and more. Free shipping "
            "on orders over $75."
        ),
        locale="en-US",
        currency="USD",
    )

    selected = [
        QueryCategory.DIRECT_MATCH,
        QueryCategory.TYPO,
        QueryCategory.SYNONYM,
        QueryCategory.MERGED_WORDS,
        QueryCategory.SPLIT_WORD,
        QueryCategory.BRAND_SEARCH,
        QueryCategory.PLURAL_SINGULAR,
        QueryCategory.MULTI_ATTRIBUTE,
        QueryCategory.ABBREVIATION,
        QueryCategory.SPECIAL_CHARACTER,
        QueryCategory.PARTIAL_QUERY,
        QueryCategory.GIBBERISH,
    ]

    print(f"Site: {demo_context.site_name} ({demo_context.site_type})")
    print(f"URL:  {demo_context.url}")
    queries = generate_queries(demo_context, selected)

    current_cat = None
    for tq in queries:
        if tq.category != current_cat:
            current_cat = tq.category
            print(f"\n{'='*60}\n  {current_cat}\n{'='*60}")
        print(f"  query:     {tq.query}   (target: {tq.target_term})")
        print(f"  rationale: {tq.rationale}")
        print()

    print(f"Total: {len(queries)} queries generated")
    print(f"Provenance: {demo_context.provenance}")
