from __future__ import annotations

import json
import logging
import re
from collections import Counter

import anthropic
from dotenv import load_dotenv

from src import judge_kb
from src.category_selector import CATEGORY_DESCRIPTIONS
from src.models import (
    FailureMode,
    QueryCategory,
    QueryJudgment,
    ScoredResult,
    Severity,
    TestQuery,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

_SYSTEM_MESSAGE = (
    "You are an expert ecommerce search engine auditor. You analyze search "
    "results to identify exactly what went wrong and provide specific, actionable "
    "fixes. You write for senior business stakeholders who do not understand "
    "search technology — your language must be plain and your evidence must be "
    "concrete."
)

_FAILURE_MODE_DESCRIPTIONS: dict[str, str] = {
    "PARTIAL_KEYWORD_MATCH": (
        "The engine matched one or two words from the query but completely ignored "
        "the rest. Results are related to a word in the query, but not to what the "
        "user actually wanted."
    ),
    "BRAND_BLEED": (
        "The query specified a brand, but results from other brands appeared. The "
        "engine matched on product type and ignored the brand constraint."
    ),
    "CONSTRAINT_DROPPED": (
        "The query included a constraint (price limit, exclusion, size, etc.) that "
        "was silently ignored. Results match the general topic but violate the "
        "constraint."
    ),
    "CATEGORY_MAPPING_FAILURE": (
        "The query used a generic/category term, but the engine only matched it as "
        "a keyword in titles instead of understanding it maps to a product category."
    ),
    "FACET_NOT_EXTRACTED": (
        "A word in the query is actually a filter value (location, color, size, "
        "material) but the engine treated it as a keyword to search in product titles."
    ),
    "NO_FUZZY_MATCHING": (
        "The query contains a typo or misspelling and the engine failed to correct "
        "it or match approximately. Results are either empty or completely unrelated."
    ),
    "NO_SEMANTIC_UNDERSTANDING": (
        "The query describes what the user wants conceptually, but the engine can "
        "only match literal keywords. The right products exist but weren't retrieved "
        "because no keywords overlap."
    ),
    "POOR_RANKING": (
        "Relevant results exist in the result set, but they're buried below "
        "irrelevant ones. The engine retrieved the right products but ordered them "
        "badly."
    ),
    "DUPLICATE_FLOODING": (
        "The same product model occupies several result slots as separate colour/size "
        "variant cards, crowding out distinct products and shrinking the visible "
        "assortment. (Detected automatically from the results.)"
    ),
    "ZERO_RESULTS_OR_GARBAGE": (
        "The engine returned nothing useful at all — either zero results or "
        "completely unrelated items."
    ),
    "OTHER": "None of the above fit. Describe what you observed.",
}

# Map short severity names from LLM to the full enum values
_SEVERITY_MAP: dict[str, Severity] = {
    "CRITICAL": Severity.CRITICAL,
    "MODERATE": Severity.MODERATE,
    "MINOR": Severity.MINOR,
    "PASS": Severity.PASS,
}

# Ordinal severity ranking (higher = worse), for comparing verdicts.
_SEVERITY_RANK: dict[str, int] = {
    Severity.CRITICAL.value: 3,
    Severity.MODERATE.value: 2,
    Severity.MINOR.value: 1,
    Severity.PASS.value: 0,
}

_SEVERITY_EMOJI: dict[str, str] = {
    Severity.CRITICAL.value: "[X]",
    Severity.MODERATE.value: "[!]",
    Severity.MINOR.value: "[~]",
    Severity.PASS.value: "[OK]",
}


# ---------------------------------------------------------------------------
# Deterministic stats
# ---------------------------------------------------------------------------


# Minimum relevance gap between the best available result and the result the
# customer actually saw first for a misordering to count as a real, visible
# failure. When the customer's original #1 is already within this gap of the
# best result, reordering by relevance would not meaningfully change what the
# shopper sees, so a large positional "displacement" is cosmetic rather than a
# CRITICAL ranking failure. This stops generic queries with tightly clustered,
# all-relevant results (e.g. a broad category term where every hit is on-topic)
# from being flagged as severe ranking failures on displacement alone.
MATERIAL_RANK_GAP = 0.20

# Absolute relevance floor below which the customer's FIRST result counts as
# genuinely off-topic / weak. A buried better match is only a CRITICAL ranking
# failure when the customer's original #1 is itself below this floor — i.e. they
# actually saw a poor result first. When the first result is already on-topic
# (>= floor), a higher-scored item further down is reranker-scoring noise (short
# generic queries score on lexical overlap, not shopping quality), so the
# displacement is at most a MODERATE inefficiency, not "customers see irrelevant
# results." Calibrated against product-search rerank scores where < ~0.30 means
# off-topic and 0.30-0.65 spans on-topic-but-modestly-scored category results.
ON_TOPIC_TOP1_FLOOR = 0.30


def _compute_stats(
    results: list[ScoredResult],
) -> tuple[float, float, int]:
    """Compute max_relevance_score, top3_original_average, displacement.

    Returns (max_relevance, top3_avg, displacement).
    """
    if not results:
        return 0.0, 0.0, 15

    max_relevance = max(r.relevance_score for r in results)

    # Top 3 by original_rank
    by_original = sorted(results, key=lambda r: r.original_rank)
    top3 = by_original[:3]
    top3_avg = sum(r.relevance_score for r in top3) / len(top3)

    # Displacement: original_rank of the highest-scoring result minus 1
    best = max(results, key=lambda r: r.relevance_score)
    displacement = best.original_rank - 1

    return max_relevance, top3_avg, displacement


def _top1_seen_relevance(results: list[ScoredResult]) -> float:
    """Relevance of the result shown at the customer's original rank #1."""
    if not results:
        return 0.0
    return min(results, key=lambda r: r.original_rank).relevance_score


# A single product model occupying this many result slots (as separate colour/size
# variant cards) constitutes variant flooding worth flagging. At/above the high
# threshold — or when distinct products fall to/below the unique-ratio floor — the
# wasted assortment is substantial enough to be a MODERATE friction, not just polish.
_FLOOD_MIN_COUNT = 3
_FLOOD_HIGH_COUNT = 5
_FLOOD_UNIQUE_RATIO = 0.40

# Relevance at/below which a result is treated as OFF-CATEGORY (wrong product type for the
# query) — same floor as the "off-topic first result" threshold used for CRITICAL gating.
# Used to distinguish genuine off-category leakage from benign on-category variant flooding.
_OFF_CATEGORY_REL = 0.30

# Colour / material constraint vocabulary. Used to detect single-constraint values in a
# MULTI_ATTRIBUTE / FACET query and check whether they are confirmable from result titles.
_MA_COLOURS = {
    "black", "white", "navy", "blue", "red", "green", "olive", "grey", "gray", "brown",
    "tan", "beige", "khaki", "orange", "yellow", "purple", "pink", "burgundy", "cream",
    "charcoal", "camel", "rust", "teal", "maroon", "gold", "silver",
}
_MA_MATERIALS = {
    "leather", "suede", "wool", "cotton", "linen", "canvas", "denim", "fleece", "cashmere",
    "nylon", "polyester", "silk", "merino", "corduroy", "flannel", "down", "synthetic",
    "ceramic", "stainless", "wood", "wooden", "glass", "rubber",
}


def _unverifiable_constraint_token(query: str, results: list[ScoredResult]) -> str | None:
    """Return a single-constraint colour/material value that CANNOT be confirmed from titles.

    For MULTI_ATTRIBUTE / FACET queries the judge only sees titles, so a colour/material
    constraint is only verifiable when that value (or a conflicting one) appears in a title.
    When the constraint value appears in NO result title, we cannot tell whether the engine
    honoured it (e.g. "black boots" → titles rarely state colour) — that must be routed to a
    human, not silently passed. Returns the first such token, or None when verifiable.
    """
    if not results:
        return None
    q_tokens = set(re.findall(r"[a-z]+", query.lower()))
    cands = (q_tokens & _MA_COLOURS) | (q_tokens & _MA_MATERIALS)
    if not cands:
        return None
    titles = " ".join((r.title or "").lower() for r in results)
    unconfirmed = [t for t in cands if t not in titles]
    return unconfirmed[0] if unconfirmed else None


def _flooding_stats(results: list[ScoredResult]) -> dict | None:
    """Variant-flooding stats: how many slots the most-repeated model occupies.

    Counts by product title — the same model shown as multiple colour/size variant
    cards (distinct URLs, identical title) is what floods the results page.
    """
    titles = [(r.title or "").strip() for r in results if (r.title or "").strip()]
    if not titles:
        return None
    counts = Counter(titles)
    top_title, top_count = counts.most_common(1)[0]
    return {
        "total": len(titles),
        "unique": len(counts),
        "top_title": top_title,
        "top_count": top_count,
    }


def _flooding_severity(stats: dict | None) -> Severity | None:
    """Severity of variant flooding, or None when it is not significant."""
    if not stats or stats["total"] < 4:
        return None
    ratio = stats["unique"] / stats["total"]
    if stats["top_count"] >= _FLOOD_HIGH_COUNT or ratio <= _FLOOD_UNIQUE_RATIO:
        return Severity.MODERATE
    if stats["top_count"] >= _FLOOD_MIN_COUNT:
        return Severity.MINOR
    return None


def _relevance_gap(results: list[ScoredResult]) -> float:
    """Best available relevance minus the relevance the customer saw at their #1."""
    if not results:
        return 0.0
    return max(r.relevance_score for r in results) - _top1_seen_relevance(results)


# Trailing generic product nouns stripped from a BRAND_SEARCH query to isolate the brand.
_BRAND_QUERY_TRAILING_NOUNS = {
    "dress", "dresses", "top", "tops", "coat", "coats", "jacket", "jackets",
    "scarf", "scarves", "bag", "bags", "ceramics", "ceramic", "mug", "mugs",
    "knitwear", "jumper", "jumpers", "socks", "throw", "throws", "shirt", "shirts",
    "blanket", "blankets", "toy", "toys", "candle", "candles", "products", "items",
}


def _stem(t: str) -> str:
    """Light singular/plural stem: drop the plural suffix so plural==singular.

    Strips 'es' only after a sibilant (boxes→box, dishes→dish), otherwise just 's'
    (candles→candle, throws→throw, teachers→teacher) — avoids over-stripping 'candles'→'candl'.
    """
    if len(t) > 4 and t.endswith("es") and t[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return t[:-2]
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def _token_match(a: str, b: str) -> bool:
    """Equal, or singular/plural variants (teacher/teachers, throw/throws, ceramic/ceramics).

    Deliberately NOT prefix-based: prefix matching gave false hits like 'studio'≈'stud'.
    """
    return a == b or _stem(a) == _stem(b)


# Generic words that don't help match a query to a real site category.
_CATEGORY_MATCH_STOPWORDS = {
    "gift", "gifts", "gifting", "ideas", "idea", "shop", "all", "new", "the", "for",
    "and", "of", "to", "a", "an", "by", "your", "our", "best", "sale",
}


def _resembles_site_category(query: str, categories: list[str] | None) -> str | None:
    """Return the site category the query resembles, or None.

    Used to reclassify a zero/empty occasion-or-category query as a
    CATEGORY_MAPPING_FAILURE when the site DOES carry a matching category (the engine
    failed to map the query to its own merchandised category, e.g. "Father's Day gift
    ideas" vs the site's "Father's Day Gifting" category). Matches on shared distinctive
    tokens (length >= 4, excluding generic gift/shop stopwords).
    """
    if not categories:
        return None
    def sig_tokens(s: str) -> set[str]:
        return {
            t for t in re.findall(r"[a-z']+", s.lower())
            if len(t) >= 4 and t not in _CATEGORY_MATCH_STOPWORDS
        }
    q_tokens = sig_tokens(query)
    if not q_tokens:
        return None
    best = None
    best_overlap = 0
    for cat in categories:
        c_tokens = sig_tokens(cat)
        if not c_tokens:
            continue
        overlap = sum(1 for ct in c_tokens if any(_token_match(ct, qt) for qt in q_tokens))
        # Require at least one shared distinctive token, and that it covers most of the
        # category's distinctive tokens (so "Father's Day gift ideas" matches "Father's
        # Day Gifting" but a single incidental word doesn't match a big category).
        if overlap >= 1 and overlap >= min(len(c_tokens), 1) and overlap > best_overlap:
            best, best_overlap = cat, overlap
    return best


# A result set whose BEST result scores below this is uniformly weak, not "near-equal good".
MIN_RELEVANT_TOP = 0.45


def _core_terms_absent(query: str, results: list[ScoredResult]) -> bool:
    """True when none of the query's significant terms appear in any result title.

    Used with a low max-relevance to detect "filler" result sets — the engine returned
    something, but every item is off the query's core product type (e.g. "luxury throws"
    returning beauty gift sets, no throw in any title). Prefix-tolerant (4+ chars) so
    singular/plural and light stems still count as present.
    """
    if not results:
        return False
    q_tokens = [
        t for t in re.findall(r"[a-z']+", query.lower())
        if len(t) >= 4 and t not in _CATEGORY_MATCH_STOPWORDS
    ]
    if not q_tokens:
        return False
    titles = " | ".join((r.title or "").lower() for r in results)
    title_tokens = set(re.findall(r"[a-z']+", titles))
    for qt in q_tokens:
        if any(_token_match(qt, tt) for tt in title_tokens):
            return False  # at least one core term is present in some title
    return True


def _excluded_term(query: str) -> str | None:
    """Extract the term a NEGATIVE_INTENT query wants excluded (after 'not'/'without')."""
    m = re.search(r"\b(?:not|without|no)\s+(.+)$", query.lower())
    if not m:
        return None
    term = m.group(1).strip()
    return term or None


# Category → sub-type product nouns. A CATEGORY-level exclusion ("not jewellery") fails
# detection by literal title substring because products are titled by sub-type ("Bracelet",
# "Necklace"), not by the category word. Map the category to its sub-type nouns so those count
# as violations. Extend as new categories are encountered.
_CATEGORY_SUBTYPES: dict[str, set[str]] = {
    "jewellery": {"bracelet", "earring", "necklace", "pendant", "ring", "brooch", "anklet", "charm", "bangle", "cufflink"},
    "jewelry": {"bracelet", "earring", "necklace", "pendant", "ring", "brooch", "anklet", "charm", "bangle", "cufflink"},
    "knitwear": {"jumper", "sweater", "cardigan", "pullover", "knit"},
    "footwear": {"shoe", "boot", "sneaker", "trainer", "sandal", "slipper", "loafer", "heel"},
}


def _exclusion_violation_fraction(
    query: str,
    results: list[ScoredResult],
    site_categories: list[str] | None = None,
) -> float | None:
    """Fraction of results that VIOLATE the query's exclusion.

    A result violates the exclusion when its title contains the excluded term (substring, so
    'faux leather' violates 'not leather' — still leather-look) OR, for a CATEGORY-level
    exclusion, when its title is a sub-type of that category. Category expansion only applies
    when the excluded term is a known category AND (if site_categories given) the site actually
    carries it — e.g. "not jewellery" on a site with a "Jewellery" category counts titles like
    "Bracelet"/"Necklace"/"Pendant" as violations even though none contain the word "jewellery".
    Returns None if no exclusion term or no results.
    """
    excl = _excluded_term(query)
    if not excl or not results:
        return None
    excl_tokens = [t for t in re.findall(r"[a-z']+", excl) if len(t) >= 3]
    if not excl_tokens:
        return None

    # Build the set of sub-type nouns that count as category-level violations.
    subtype_terms: set[str] = set()
    for tok in excl_tokens:
        subtypes = _CATEGORY_SUBTYPES.get(tok)
        if not subtypes:
            continue
        # Gate on the site actually carrying this category (when categories are known).
        if site_categories:
            cat_tokens = {ct for cat in site_categories for ct in re.findall(r"[a-z']+", cat.lower())}
            if not any(_token_match(tok, ct) for ct in cat_tokens):
                continue
        subtype_terms |= subtypes

    viol = 0
    for r in results:
        t = (r.title or "").lower()
        title_tokens = re.findall(r"[a-z']+", t)
        # Literal substring (catches "faux leather" for "not leather") OR singular/plural stem
        # match (catches "Candle" for excluded "candles").
        if any(et in t for et in excl_tokens) or any(_token_match(et, tt) for et in excl_tokens for tt in title_tokens):
            viol += 1
            continue
        if subtype_terms and any(_token_match(st, tt) for st in subtype_terms for tt in title_tokens):
            viol += 1
    return viol / len(results)


def _query_targets_brand(query: str, brands: list[str] | None) -> bool:
    """True when the query is/contains a known site brand.

    A brand's name often does not appear in product titles, so a brand-targeting query
    can legitimately have low relevance + 'core terms absent' — that is NOT filler. Such
    queries are exempt from the weak-filler guard (verified via the manual brand gate).
    """
    if not brands:
        return False
    q = " ".join(query.lower().split())
    for b in brands:
        bl = " ".join(b.lower().split())
        if not bl:
            continue
        if bl in q or q in bl:
            return True
        # token-level: every significant brand token appears in the query
        b_tokens = [t for t in re.findall(r"[a-z']+", bl) if len(t) >= 3]
        q_tokens = re.findall(r"[a-z']+", q)
        if b_tokens and all(any(_token_match(bt, qt) for qt in q_tokens) for bt in b_tokens):
            return True
    return False


def _brand_search_unverifiable(
    query: str, results: list[ScoredResult], brands: list[str] | None = None
) -> bool:
    """True when a BRAND_SEARCH brand cannot be confirmed from result titles.

    The judge only sees titles, so brand precision is only verifiable when the brand
    name actually appears in product titles (e.g. "Barbour" → every title contains
    "Barbour"). When it does NOT (e.g. "Never Fully Dressed dress" → no title contains
    the brand), the results could be on-brand OR hidden brand-bleed — we cannot tell.
    Such cases must be routed to a human, not auto-passed.

    Brand isolation order:
    1. If a known site brand (from Phase 1 ``brands``) is a substring of the query, that
       IS the brand — check whether it appears in any title. This is the robust path and
       avoids the trailing-noun list missing a product noun (e.g. "Snow Peak cookware":
       "cookware" is not in _BRAND_QUERY_TRAILING_NOUNS, but the known brand "Snow Peak"
       is present in every title → verifiable, NOT a false manual-verification flag).
    2. Fallback (no brands given / no match): strip trailing generic product nouns to
       isolate the brand phrase, then check the query as-is and the trimmed phrase.
    """
    if not results:
        return False  # zero results is a different failure, handled elsewhere
    titles = [(r.title or "").lower() for r in results]

    # Path 1: use the known site brand the query targets.
    if brands:
        q = " ".join(query.lower().split())
        matched = [b for b in brands if b.strip() and " ".join(b.lower().split()) in q]
        # Prefer the longest matching brand (most specific).
        for b in sorted(matched, key=len, reverse=True):
            bl = " ".join(b.lower().split())
            return not any(bl in t for t in titles)

    # Path 2: trailing-noun fallback.
    tokens = query.split()
    candidates = [query]
    trimmed = list(tokens)
    while trimmed and trimmed[-1].lower() in _BRAND_QUERY_TRAILING_NOUNS:
        trimmed = trimmed[:-1]
        if trimmed:
            candidates.append(" ".join(trimmed))
    for cand in candidates:
        c = cand.lower().strip()
        if len(c) < 2:
            continue
        if any(c in t for t in titles):
            return False  # brand phrase present in at least one title → verifiable
    return True


def _displacement_is_cosmetic(results: list[ScoredResult]) -> bool:
    """True when reordering would NOT materially change what the shopper sees.

    The best available result is within ``MATERIAL_RANK_GAP`` of the customer's
    original #1, so every top result is of near-equal relevance — the positional
    "displacement" is cosmetic. A POOR_RANKING failure in this state is at most a
    MINOR polish note, never a MODERATE friction point: the customer searching an
    exact product/brand still got that product/brand first (e.g. "Didriksons
    regnkläder barn" returning all Didriksons kids' rain gear, reordered by tiny
    reranker-score deltas). Distinct from _ranking_materially_broken, which also
    weighs whether the first result is off-topic for CRITICAL eligibility.
    """
    if not results:
        return False
    return _relevance_gap(results) < MATERIAL_RANK_GAP


def _ranking_materially_broken(results: list[ScoredResult]) -> bool:
    """True when a misordering is a real, customer-visible (CRITICAL-eligible) failure.

    Requires BOTH:
    1. The best available result outscores the customer's original #1 by at least
       ``MATERIAL_RANK_GAP`` (reordering would change the top result), AND
    2. The customer's original #1 is itself below ``ON_TOPIC_TOP1_FLOOR`` — i.e.
       they actually saw an off-topic / weak result first.

    If the customer's #1 is already on-topic (>= floor), a higher-scored item buried
    below is reranker-scoring noise on a short/generic query, not a result the
    shopper would perceive as "irrelevant." Such cases are at most MODERATE ranking
    inefficiencies, so this returns False and the CRITICAL cap downstream applies.
    """
    if not results:
        return False
    max_relevance = max(r.relevance_score for r in results)
    top1_seen = _top1_seen_relevance(results)
    gap_material = (max_relevance - top1_seen) >= MATERIAL_RANK_GAP
    first_result_weak = top1_seen < ON_TOPIC_TOP1_FLOOR
    return gap_material and first_result_weak


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_prompt(
    test_query: TestQuery,
    results: list[ScoredResult],
    max_relevance: float,
    top3_avg: float,
    displacement: int,
    kb_section: str = "",
) -> str:
    """Build the user message for the LLM judge.

    ``kb_section`` is an optional block of calibration examples drawn from past audits
    (see ``judge_kb``); it is empty when the knowledge base has no relevant entries.
    """

    cat = QueryCategory(test_query.category)
    cat_desc = CATEGORY_DESCRIPTIONS.get(cat, "")

    top1_seen = _top1_seen_relevance(results)
    relevance_gap = max_relevance - top1_seen
    material_gap = MATERIAL_RANK_GAP
    on_topic_floor = ON_TOPIC_TOP1_FLOOR

    # Original ranking (what the customer saw)
    by_original = sorted(results, key=lambda r: r.original_rank)
    original_lines = []
    for r in by_original:
        parts = [f"#{r.original_rank}", r.title]
        if r.price:
            parts.append(r.price)
        parts.append(f"(relevance: {r.relevance_score:.3f})")
        original_lines.append("  " + " | ".join(parts))

    # Ideal ranking (what they should have seen)
    by_relevance = sorted(results, key=lambda r: r.relevance_score, reverse=True)
    ideal_lines = []
    for i, r in enumerate(by_relevance, 1):
        parts = [f"#{i}", r.title]
        if r.price:
            parts.append(r.price)
        parts.append(f"(relevance: {r.relevance_score:.3f}, was rank #{r.original_rank})")
        ideal_lines.append("  " + " | ".join(parts))

    # Failure mode menu
    fm_lines = []
    for name, desc in _FAILURE_MODE_DESCRIPTIONS.items():
        fm_lines.append(f"  - {name}: {desc}")

    return f"""## Query Under Analysis
- **Query**: "{test_query.query}"
- **Category**: {test_query.category} — {cat_desc}
- **Rationale**: {test_query.rationale}

## What the Customer Saw (original ranking)
{chr(10).join(original_lines) if original_lines else "  (no results)"}

## What the Customer SHOULD Have Seen (ideal ranking by relevance)
{chr(10).join(ideal_lines) if ideal_lines else "  (no results)"}

## Key Stats
- Max relevance score: {max_relevance:.3f}
- Top 3 average relevance: {top3_avg:.3f}
- Displacement of best result: {displacement} positions (best result was at original rank #{displacement + 1})
- Relevance of the result the customer actually saw FIRST (original #1): {top1_seen:.3f}
- Relevance gap (best available − customer's #1): {relevance_gap:.3f}
- Total results: {len(results)}

## Failure Mode Menu
Pick the SINGLE most important failure mode:
{chr(10).join(fm_lines)}

## Severity Criteria
- **CRITICAL**: The customer's FIRST results are genuinely off-topic / irrelevant to the query (wrong product type, wrong brand, wrong category) AND a strong match is buried 7+ positions deep, OR the max relevance score is below 0.25, OR results are completely unrelated to the query. Business impact: customers searching this way see irrelevant results and leave. NOTE: a high reranker gap is NOT sufficient for CRITICAL — if the customer's first result is itself on-topic (relevance >= {on_topic_floor:.2f}), a better-scored item further down is reranker noise, not an irrelevant-results failure. Cap such cases at MODERATE (or MINOR if the first result is near-best).
- **MODERATE**: The best matching result is buried 3+ positions deep AND that result is materially better than what the customer saw first (relevance gap >= {material_gap:.2f}), OR results are partially relevant but miss a key aspect of the query. Business impact: degraded experience, customers may bounce. Do NOT use MODERATE for a buried item that is only marginally better than the customer's #1 (gap < {material_gap:.2f}) — that is a cosmetic reorder among near-equal results; use MINOR.
- **MINOR**: The best matching result is within top 3 but not #1, OR the results are all on-topic and the only issue is a cosmetic reorder among near-equal-relevance items (relevance gap < {material_gap:.2f}, e.g. an exact brand/product query that returned the right brand/product set, just not in the ideal order). Business impact: polish, not a real miss.
- **PASS**: Top 3 results are relevant and well-ordered. Displacement 0-2 and top 3 average above 0.60.
{kb_section}
## Materiality of Displacement — READ CAREFULLY
A CRITICAL ranking failure requires that the customer actually saw OFF-TOPIC results first — not merely lower-scored ones. Two independent reasons a large displacement is NOT critical:
1. **Small gap**: if the **relevance gap (best available − customer's #1)** is small (roughly < {material_gap:.2f}), the customer already saw a near-best result first.
2. **On-topic first result**: if the customer's original #1 is itself on-topic (relevance >= {on_topic_floor:.2f}) — same product type / brand / category as the query intent — then a higher-scored item buried below is reranker-scoring NOISE, not an irrelevant-results failure. Short, generic queries (broad categories, plurals, typos/synonyms of a category, even a brand+category where every hit is that brand) score on lexical token overlap, so the "best" is often an artifact (e.g. a title literally containing the query word). Do NOT call these CRITICAL and do NOT write "customers see irrelevant results" — every result IS relevant. Cap at MODERATE (real ordering inefficiency) or MINOR (first result already near-best).

Reserve CRITICAL ranking failures for cases where the customer's first results are genuinely WRONG (off-topic product type, wrong brand, unrelated category) while a clearly correct match sits buried far below.

## BRAND_SEARCH judging rule
For a BRAND_SEARCH query, the primary test is **brand precision**: every result should be that brand. If all results are the queried brand (no other-brand bleed), the verdict is **PASS**. However, if the result set is dominated by **peripheral/accessory items** while the brand's **signature/flagship products are absent from the top results** (e.g. a "Barbour" search returning pet accessories, umbrellas, and trinkets but no Barbour wax jackets), keep severity **PASS** but explicitly note in the evidence that the flagship products appear buried/absent — a merchandising observation, not a search-relevance defect. Only escalate above PASS if a DIFFERENT brand leaked in (then BRAND_BLEED).

## Dropped-term detection (PARTIAL_KEYWORD_MATCH)
For a multi-word query, check whether the results actually match ALL the significant words — especially the **head/core product noun**. If the engine matched only a SUBSET of the words and dropped a key term (e.g. "winter coat sale" returning winter **socks** — it kept "winter" and dropped "coat"), that is **PARTIAL_KEYWORD_MATCH**, NOT a PASS and NOT merely POOR_RANKING. Severity scales with how much of the page is off-intent: a page dominated by items matching only the secondary word = MODERATE (or CRITICAL if the core term is essentially absent). Do NOT excuse off-intent filler as "catalogue limits" when the dropped term clearly has inventory on the site (cross-check against known categories/other queries).

## Constraint-Violation Detection (CONSTRAINT_DROPPED) — apply these rules literally to the TITLES
You only see result titles and price, so detect a dropped constraint by scanning the titles directly. ONE offending title is enough to flag CONSTRAINT_DROPPED — cite that title as evidence.
- **Colour constraint**: the query names exactly one colour. If ANY result title contains a DIFFERENT colour, the colour constraint was dropped → CONSTRAINT_DROPPED. (e.g. query "navy scarf" → a title containing "Red"/"Green"/etc. = fail.)
- **Exclusion ("… not Y" / "… without Y")**: take the term that appears after "not"/"without". If that excluded term appears in ANY result title, the exclusion was ignored → CONSTRAINT_DROPPED. (e.g. "knitwear not wool" → any title containing "Wool" = fail.)
- **Size / fit / fabric / material / any other single attribute**: the query names one value of the attribute. If ANY result title contains a DIFFERENT value of that same attribute, the constraint was dropped → CONSTRAINT_DROPPED.
- **Price limit** ("under 50"): if any result's price exceeds the limit → CONSTRAINT_DROPPED.
- If the constrained attribute does NOT appear in any title at all, you cannot confirm a violation from titles alone — do not invent one; judge on relevance instead and note the limitation.
- Severity scales with how many results violate: most/all results violating → MODERATE or CRITICAL; one or two among otherwise-correct results → MINOR/MODERATE.

## DIRECT_MATCH judging rule
**Automatic fail:** a DIRECT_MATCH query is an exact product title. If the rank-#1 result's title does NOT contain the exact query text (or there are no results), it is an automatic FAILURE — the shopper named a precise product and did not get it first. (This is also enforced deterministically in code.)

For a DIRECT_MATCH query (an exact product title), the IDEAL outcome is **a single result** — the exact product. It is a PASS ONLY IF the exact product ranks #1 AND every other result is **near-identical**, meaning either: (a) a colour/size variant of that same product, OR (b) a member of the **same named series/collection** — same title pattern AND same product line/brand (e.g. "1960's Space Exploration Sheep Mug" alongside "1970's Hippy Sheep Mug", "1990's Pretty Sheep Mug" — one named Sheep Mug series at the same price).

ANY other result is keyword leakage and makes this a **FAILURE** (PARTIAL_KEYWORD_MATCH), even when the exact product still ranks #1. This explicitly includes:
- A **different brand** — always leakage (e.g. a query for one branded soap returning other brands' washes).
- A **different product line** with a different name, even in the same category (e.g. "Shea Verbena Hands & Body Liquid Soap" → "Palm Wild Hand Wash", "Geranium Hand & Body Wash" are DIFFERENT products → leakage).
- Merely sharing a category ("hand wash", "mug") is NOT near-identical; it must be the same product or same named series.

Severity scales with how much of the set is leakage: a couple of stray items = MINOR/MODERATE; a set dominated by non-matching/different-brand products (even with the exact item at #1) = MODERATE.

## Instructions
- Pick the SINGLE most important failure mode. If the query passed (results are relevant and well-ordered), use severity PASS and set failure_mode to "OTHER" with failure_mode_explanation "No failure detected — results are relevant and well-ordered."
- For **evidence**: cite SPECIFIC results by title and position that demonstrate the problem. Be concrete.
- For **recommended_fix**: be specific to what happened, not generic. Reference the actual results and the actual query. Write this for someone who will hand it to their engineering team.
- If failure_mode is OTHER, you MUST provide failure_mode_explanation.

## Output
Respond with ONLY a JSON object (no markdown fences, no commentary) with these exact keys:
{{
  "failure_mode": "FAILURE_MODE_NAME",
  "failure_mode_explanation": null,
  "severity": "CRITICAL|MODERATE|MINOR|PASS",
  "evidence": "specific results that demonstrate the problem",
  "recommended_fix": "specific fix for what actually happened"
}}"""


# ---------------------------------------------------------------------------
# LLM call + response parsing
# ---------------------------------------------------------------------------


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        text = text[first_nl + 1:] if first_nl != -1 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _call_sonnet(system: str, user: str) -> dict | None:
    """Call Claude Sonnet and return parsed JSON, or None on failure."""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=800,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = response.content[0].text
        cleaned = _strip_fences(raw)
        return json.loads(cleaned)
    except anthropic.APIError as e:
        logger.warning("Sonnet API error: %s", e)
        return None
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.warning("Failed to parse Sonnet response: %s", e)
        return None
    except Exception as e:
        logger.warning("Unexpected error calling Sonnet: %s", e)
        return None


# ---------------------------------------------------------------------------
# Fallback judgment (when LLM fails)
# ---------------------------------------------------------------------------


def _fallback_judgment(
    test_query: TestQuery,
    results: list[ScoredResult],
    max_relevance: float,
    top3_avg: float,
    displacement: int,
) -> QueryJudgment:
    """Produce a stats-only judgment when the LLM call fails."""
    fallback_note = "LLM analysis failed — diagnosis based on relevance scores only."

    if max_relevance < 0.25:
        fm = FailureMode.ZERO_RESULTS_OR_GARBAGE
        sev = Severity.CRITICAL
    elif displacement > 6:
        fm = FailureMode.POOR_RANKING
        # Severity tracks materiality, not raw depth: cosmetic gap -> MINOR,
        # material gap with off-topic #1 -> CRITICAL, else MODERATE.
        if _displacement_is_cosmetic(results):
            sev = Severity.MINOR
        elif _ranking_materially_broken(results):
            sev = Severity.CRITICAL
        else:
            sev = Severity.MODERATE
    elif displacement > 2:
        fm = FailureMode.POOR_RANKING
        sev = Severity.MINOR if _displacement_is_cosmetic(results) else Severity.MODERATE
    else:
        fm = FailureMode.OTHER
        sev = Severity.PASS

    return QueryJudgment(
        test_query=test_query,
        results=results,
        failure_mode=fm,
        failure_mode_explanation=fallback_note if fm == FailureMode.OTHER else None,
        severity=sev,
        evidence=fallback_note,
        recommended_fix=fallback_note,
        displacement=displacement,
        max_relevance_score=max_relevance,
        top3_original_average=top3_avg,
    )


# ---------------------------------------------------------------------------
# Single-query judge
# ---------------------------------------------------------------------------


def _judge_single_query(
    test_query: TestQuery,
    results: list[ScoredResult],
    language: str | None = None,
    site_categories: list[str] | None = None,
    site_brands: list[str] | None = None,
) -> QueryJudgment:
    """Judge a single query's results using deterministic stats + LLM analysis.

    When ``language`` is given, calibration examples from past audits in that language are
    retrieved and injected into the prompt for consistency (see ``judge_kb``).
    """

    max_relevance, top3_avg, displacement = _compute_stats(results)

    kb_section = ""
    if language:
        examples = judge_kb.load_calibration_examples(
            language, str(test_query.category), test_query.query
        )
        kb_section = judge_kb.format_calibration_section(examples)

    prompt = _build_prompt(
        test_query, results, max_relevance, top3_avg, displacement, kb_section
    )
    llm_response = _call_sonnet(_SYSTEM_MESSAGE, prompt)

    if llm_response is None:
        return _fallback_judgment(test_query, results, max_relevance, top3_avg, displacement)

    # Parse failure_mode — "PASS" is not a valid FailureMode; handle silently
    fm_str = llm_response.get("failure_mode", "OTHER")
    if fm_str.upper() == "PASS":
        fm = FailureMode.OTHER
    else:
        try:
            fm = FailureMode(fm_str)
        except ValueError:
            logger.warning("Unknown failure_mode '%s', defaulting to OTHER", fm_str)
            fm = FailureMode.OTHER

    # Parse severity
    sev_str = llm_response.get("severity", "MODERATE")
    sev = _SEVERITY_MAP.get(sev_str.upper(), Severity.MODERATE)

    # Deterministic materiality guard for ranking failures. Severity must track how
    # much the misordering actually costs the shopper, not raw position depth:
    #   * Cosmetic gap (best within MATERIAL_RANK_GAP of the customer's #1): every
    #     top result is near-equal relevance, so a buried higher-scored item is
    #     reranker noise. At most a MINOR polish note — never a MODERATE friction
    #     point (e.g. "Didriksons regnkläder barn" returning all Didriksons kids'
    #     rain gear, reordered by 0.1 score deltas).
    #   * Material gap but the customer's #1 is already on-topic (>= floor): a
    #     genuinely stronger match is buried, but the shopper did not see irrelevant
    #     results — MODERATE, not CRITICAL.
    if fm == FailureMode.POOR_RANKING:
        if _displacement_is_cosmetic(results) and sev in (Severity.CRITICAL, Severity.MODERATE):
            logger.info(
                "Capping POOR_RANKING %s -> MINOR for '%s' (cosmetic displacement, gap %.3f)",
                sev, test_query.query, _relevance_gap(results),
            )
            sev = Severity.MINOR
        elif sev == Severity.CRITICAL and not _ranking_materially_broken(results):
            logger.info(
                "Capping POOR_RANKING CRITICAL -> MODERATE for '%s' (on-topic first result)",
                test_query.query,
            )
            sev = Severity.MODERATE

    # Parse text fields
    evidence = llm_response.get("evidence", "No evidence provided by LLM.")
    recommended_fix = llm_response.get("recommended_fix", "No fix provided by LLM.")
    fm_explanation = llm_response.get("failure_mode_explanation")

    # A MINOR ranking issue is cosmetic — all results are on-topic and the shopper saw a
    # relevant item near the top. Per calibration, do NOT report it as a failure: convert
    # POOR_RANKING/MINOR to a PASS (e.g. a corrected typo or brand+category query whose
    # results are all relevant, just reordered by sub-0.1 score deltas).
    if fm == FailureMode.POOR_RANKING and sev == Severity.MINOR:
        logger.info("POOR_RANKING/MINOR -> PASS for '%s' (cosmetic reorder, all on-topic)", test_query.query)
        fm = FailureMode.OTHER
        sev = Severity.PASS
        fm_explanation = "No failure detected — results are all on-topic; only a cosmetic reorder among near-equal results."

    _cat = test_query.category.value if hasattr(test_query.category, "value") else test_query.category

    # Weak-filler guard. The "near-equal scores → cosmetic/PASS" logic assumes results are
    # relevant. When the BEST result is itself weak (max relevance below MIN_RELEVANT_TOP)
    # AND the query's core terms appear in no result title, the scores are clustered because
    # every item is IRRELEVANT — the engine returned filler of the wrong product type (e.g.
    # "luxury throws" → beauty gift sets, no throw). That is a relevance failure, not a PASS.
    # (BRAND_SEARCH is excluded — handled by its own manual-verification path.)
    if (sev == Severity.PASS and _cat != "BRAND_SEARCH"
            and not _query_targets_brand(test_query.query, site_brands)
            and results and max_relevance < MIN_RELEVANT_TOP
            and _core_terms_absent(test_query.query, results)):
        logger.info("Weak-filler guard: '%s' max_rel=%.3f, core terms absent -> NO_SEMANTIC_UNDERSTANDING", test_query.query, max_relevance)
        fm = FailureMode.NO_SEMANTIC_UNDERSTANDING
        sev = Severity.CRITICAL if max_relevance < 0.25 else Severity.MODERATE
        fm_explanation = None
        evidence = (
            f"All results are weak matches (max relevance {max_relevance:.3f}) and the query's core "
            f"terms appear in no result title — the engine returned filler unrelated to the requested "
            f"product type for '{test_query.query}' rather than the right products. " + (evidence or "")
        )
        recommended_fix = (
            "Detect when no result actually matches the query's core product term and either return "
            "no results (an honest empty state) or map the query to the correct category, instead of "
            "padding the page with unrelated low-relevance products."
        )

    # Variant-flooding override (deterministic). When one product model occupies
    # several result slots as separate colour/size variant cards, that is the real,
    # customer-visible issue — and the relevance-based judge can't see it (duplicates
    # score identical relevance). Make it the headline when it is at least as severe
    # as the current verdict AND the current verdict is only a ranking nuance (or no
    # issue) — never override a worse off-topic / zero-results / category failure.
    flood = _flooding_stats(results)
    flood_sev = _flooding_severity(flood)
    if (
        flood_sev is not None
        and fm in (FailureMode.POOR_RANKING, FailureMode.OTHER)
        and _SEVERITY_RANK.get(flood_sev.value, 0) >= _SEVERITY_RANK.get(sev.value if isinstance(sev, Severity) else sev, 0)
    ):
        title = flood["top_title"]
        title = (title[:40] + "…") if len(title) > 41 else title
        fm = FailureMode.DUPLICATE_FLOODING
        sev = flood_sev
        fm_explanation = None
        evidence = (
            f"Only {flood['unique']} distinct products fill {flood['total']} result slots — "
            f"'{title}' alone appears {flood['top_count']} times as separate colour/size variant "
            f"cards. Repeating one model crowds out other products and shrinks the assortment the "
            f"shopper actually sees."
        )
        recommended_fix = (
            "Collapse colour/size variants of the same product into a single result card (one slot "
            "per model, with variants selectable on the product page) so more distinct products are "
            "visible above the fold."
        )

    # DUPLICATE_FLOODING severity is calibrated by the actual flooding MAGNITUDE (how
    # many slots one model occupies), not by the LLM's guess — the LLM both inflates
    # mid-page flooding to MODERATE AND under-rates top-dominating flooding as MINOR.
    # So make _flooding_severity AUTHORITATIVE for this mode (set, both directions):
    #   - top_count>=5 OR distinct-ratio<=0.40 → MODERATE (flooding reaches the top slots)
    #   - top_count>=3 → MINOR (relevant distinct products lead; repetition is mid/lower page)
    # Examples (Huckberry): "fleece pullover" (top_count 3, ratio 0.80) → MINOR;
    # "beanie" (top_count 5, 10/15 slots, dupes at #1-6) → MODERATE.
    if fm == FailureMode.DUPLICATE_FLOODING:
        det_flood = _flooding_severity(_flooding_stats(results))
        if det_flood is not None:
            sev = det_flood
        else:
            # Flooding is below the significance threshold (the most-repeated model occupies
            # fewer than _FLOOD_MIN_COUNT slots — e.g. just a couple of 2× dupe pairs on
            # "leather jacket"). That is not a real defect: clear the LLM's over-flag to PASS.
            # (If a genuine ranking/relevance problem existed it would carry its own non-flooding
            # verdict; the only thing flagged here was insignificant repetition.)
            fm, sev = FailureMode.OTHER, Severity.PASS
            fm_explanation = None

    # Off-category leakage is NOT duplicate flooding. DUPLICATE_FLOODING is only the right
    # label when the REPEATED items are on-category (relevant) and the sole problem is
    # repetition (e.g. "fleece pullover" → the same pullover 3×). If the flooded product is
    # itself OFF-CATEGORY — low relevance, wrong product type for the query (e.g. "travel bag"
    # → Ripa Ripa swim shorts / sunglasses at ~0.21 repeated down the page) — then the real,
    # more important finding is category/relevance leakage, not the repetition. Reclassify to
    # POOR_RANKING at MODERATE (off-category items diluting a category query degrade the
    # experience even when relevant items lead). On-category flooding (query 9/11/13) is
    # unaffected because its flooded items score above the off-category floor.
    if fm == FailureMode.DUPLICATE_FLOODING:
        _fstats = _flooding_stats(results)
        if _fstats:
            _flooded_rel = max(
                (r.relevance_score for r in results
                 if (r.title or "").strip() == _fstats["top_title"]),
                default=0.0,
            )
            if _flooded_rel < _OFF_CATEGORY_REL:
                fm = FailureMode.POOR_RANKING
                fm_explanation = None
                if _SEVERITY_RANK.get(Severity.MODERATE.value, 0) > _SEVERITY_RANK.get(
                    sev.value if isinstance(sev, Severity) else sev, 0
                ):
                    sev = Severity.MODERATE
                _bad = _fstats["top_title"]
                _bad = (_bad[:40] + "…") if len(_bad) > 41 else _bad
                evidence = (
                    f"Off-category leakage: '{_bad}' (relevance {_flooded_rel:.2f}) is not the "
                    f"product type the query asks for, yet it occupies {_fstats['top_count']} slots. "
                    f"The engine is returning and repeating off-category items rather than filling "
                    f"those slots with relevant products — a relevance/precision failure, not benign "
                    f"variant flooding. " + (evidence or "")
                )
                recommended_fix = (
                    "Apply a minimum-relevance threshold and category/type boosting so off-category "
                    "items (here, swimwear/eyewear for a bag query) are filtered out, freeing slots for "
                    "relevant products. " + (recommended_fix or "")
                )

    # PLURAL_SINGULAR: the capability under test is whether the engine resolves the plural to
    # the right product type. When it does (on-category results) and the ONLY issue left is
    # variant flooding, that capability has PASSED — flooding is incidental noise here and must
    # not drag a plural-resolution test below PASS (e.g. "hoodies" → 15 hoodies, one model 3×).
    # Keep the flooding description as a note in the evidence. (Off-category flooding would have
    # already been reclassified to POOR_RANKING above and won't reach this branch.)
    if _cat == "PLURAL_SINGULAR" and fm == FailureMode.DUPLICATE_FLOODING:
        fm, sev = FailureMode.OTHER, Severity.PASS
        fm_explanation = None
        evidence = (
            "Plural resolved correctly — results are the right product type. (Variant flooding "
            "is present but is a minor merchandising note, not a defect for a plural/singular "
            "resolution test.) " + (evidence or "")
        )

    # Deterministic DIRECT_MATCH guard (hard rule). A DIRECT_MATCH query is an exact
    # product title: the rank-#1 result MUST contain the query string. If there are no
    # results, or the exact query text is not part of the #1 product title, it is an
    # automatic FAIL regardless of what the LLM said — the shopper typed an exact product
    # name and did not get that product first.
    if _cat == "DIRECT_MATCH":
        rank1 = min(results, key=lambda r: r.original_rank) if results else None
        q_norm = " ".join(test_query.query.lower().split())
        title1_norm = " ".join((rank1.title or "").lower().split()) if rank1 else ""
        if rank1 is None:
            fm, sev = FailureMode.ZERO_RESULTS_OR_GARBAGE, Severity.CRITICAL
            fm_explanation = None
            evidence = f"Exact-product query '{test_query.query}' returned no results — the customer cannot find a product they named precisely."
            recommended_fix = "Ensure exact product-title queries return that product. Check indexing/tokenization so an exact title match always resolves."
        elif q_norm not in title1_norm:
            fm = FailureMode.PARTIAL_KEYWORD_MATCH
            # Force at least MODERATE; keep CRITICAL if the LLM already judged it so.
            if sev not in (Severity.CRITICAL, Severity.MODERATE):
                sev = Severity.MODERATE
            fm_explanation = None
            evidence = (
                f"DIRECT_MATCH automatic fail: the exact product query '{test_query.query}' is not "
                f"present in the rank-#1 title ('{rank1.title}'). A shopper searching the exact "
                f"product name did not get that product first."
            )
            recommended_fix = (
                "For exact product-title queries, the matching product must rank #1. Add an exact "
                "title-match boost so a literal product-name query resolves to that product at the top."
            )
        elif all(q_norm in " ".join((r.title or "").lower().split()) for r in results):
            # Exact product is #1 AND every result is that same product (separate
            # catalog IDs or colour/size variants sharing the identical display title).
            # For a DIRECT_MATCH query this is the IDEAL outcome — the shopper named a
            # precise product and got exactly it — NOT duplicate flooding. Force PASS,
            # clearing any earlier variant-flooding/ranking verdict from the LLM or the
            # _flooding override above. (Multiple listings of the SAME product ≠ flooding
            # the page with one model's colour variants while crowding out distinct items.)
            fm, sev = FailureMode.OTHER, Severity.PASS
            fm_explanation = None
            extra = (
                f" the remaining {len(results) - 1} slot(s) show the same product (a separate "
                f"catalog listing/variant of the identical item)" if len(results) > 1 else ""
            )
            evidence = (
                f"Exact-product query '{test_query.query}' returns that exact product at rank #1"
                + (";" + extra + " — the ideal outcome for an exact product-title search." if extra
                   else " — the ideal single-result outcome for an exact product-title search.")
            )
            recommended_fix = ""

    # BRAND_SEARCH verifiability guard. Brand precision is only confirmable when the brand
    # appears in titles; otherwise the judge's PASS is a guess that could mask brand-bleed.
    # Flag such cases for human verification rather than auto-passing.
    if _cat == "BRAND_SEARCH" and _brand_search_unverifiable(test_query.query, results, site_brands):
        logger.info("BRAND_SEARCH '%s' unverifiable from titles — flagging for manual verification", test_query.query)
        evidence = (
            "[MANUAL VERIFICATION REQUIRED] The brand from '" + test_query.query + "' does not appear "
            "in any result title, so brand precision cannot be confirmed from titles alone — the results "
            "may be on-brand or contain hidden brand-bleed. A human must verify the brand of these results. "
            + (evidence or "")
        )
        if fm_explanation is None:
            fm_explanation = "Brand not present in any result title — automated verdict unreliable; manual brand verification required."

    # Title-invisible constraint guard (MULTI_ATTRIBUTE / FACET). The judge sees only titles,
    # so a colour/material constraint can only be confirmed when that value appears in a title.
    # When it appears in NONE of the titles, we cannot tell whether the engine honoured the
    # constraint — the automated PASS is a guess (e.g. "black boots" → boot titles rarely state
    # colour). Flag for manual review rather than silently passing. Skip if already a detected
    # CONSTRAINT_DROPPED violation (a conflicting value WAS visible, so it's verifiably failing).
    if _cat in ("MULTI_ATTRIBUTE", "FACET_EXTRACTION") and fm != FailureMode.CONSTRAINT_DROPPED:
        _unv = _unverifiable_constraint_token(test_query.query, results)
        if _unv:
            logger.info("MULTI_ATTRIBUTE '%s' constraint '%s' not title-visible — flagging for manual verification", test_query.query, _unv)
            evidence = (
                f"[MANUAL VERIFICATION REQUIRED] The '{_unv}' constraint does not appear in any "
                f"result title, so it cannot be confirmed from titles alone — a human must check "
                f"whether the returned products actually match '{_unv}'. " + (evidence or "")
            )
            if fm_explanation is None:
                fm_explanation = f"'{_unv}' constraint not title-visible — automated verdict unverifiable; manual verification required."

    # A CATEGORY_MAPPING test query is by construction a colloquial term for a REAL site
    # category (the generator only builds these against existing categories). So a zero or
    # garbage result IS a category-mapping failure — the engine couldn't bridge the
    # vocabulary gap to its own category (e.g. "bedtime wear" → "Sleep & Loungewear"). This
    # catches the hardest mapping failures, where the query shares NO words with the category
    # name and so deterministic nav-matching below cannot detect it.
    if _cat == "CATEGORY_MAPPING" and fm in (FailureMode.ZERO_RESULTS_OR_GARBAGE, FailureMode.NO_SEMANTIC_UNDERSTANDING):
        logger.info("CATEGORY_MAPPING query '%s' with no usable results -> CATEGORY_MAPPING_FAILURE", test_query.query)
        fm = FailureMode.CATEGORY_MAPPING_FAILURE
        fm_explanation = None

    # Category-mapping reclassification. If a query returned nothing useful (or was judged a
    # zero/semantic failure) but the site DOES carry a category matching the query, the real
    # failure is that the engine can't map the query to its own merchandised category — a
    # CATEGORY_MAPPING_FAILURE, which is sharper and more fixable than NO_SEMANTIC_UNDERSTANDING.
    # EXEMPT SEMANTIC_MEANING and NATURAL_LANGUAGE: both are conceptual/conversational
    # sentences by design — an incidental category word in the sentence ("...keep my food
    # COLD..." spuriously matching "Cold Weather Accessories", which is the opposite intent;
    # "...house feel like a home") must NOT downgrade a genuine semantic-understanding failure
    # into a (often wrong) category-mapping one. These stay NO_SEMANTIC_UNDERSTANDING.
    #
    # ONLY fire on a genuine ZERO result. CATEGORY_MAPPING_FAILURE means "the engine returned
    # NOTHING despite a matching merchandised category" — its evidence literally says "returned
    # no usable results". When the engine DID return items but they are weak/wrong-type filler
    # (the weak-filler guard produced NO_SEMANTIC_UNDERSTANDING with results present, e.g.
    # "jacket not synthetic" → 15 Arc'teryx shirts/shorts at ~0.39), the failure is that the
    # engine didn't UNDERSTAND the query, not that it couldn't reach a category — keep
    # NO_SEMANTIC_UNDERSTANDING. Reclassifying those would both mislabel them and paste a false
    # "no usable results" claim onto a non-empty result set.
    if (not results) and _cat not in ("SEMANTIC_MEANING", "NATURAL_LANGUAGE", "SUBJECTIVE_ATTRIBUTE") and fm in (FailureMode.ZERO_RESULTS_OR_GARBAGE, FailureMode.NO_SEMANTIC_UNDERSTANDING):
        matched_cat = _resembles_site_category(test_query.query, site_categories)
        if matched_cat:
            logger.info("Reclassifying '%s' -> CATEGORY_MAPPING_FAILURE (matches site category '%s')", test_query.query, matched_cat)
            fm = FailureMode.CATEGORY_MAPPING_FAILURE
            fm_explanation = None
            evidence = (
                f"The site has a matching category — '{matched_cat}' — yet the query "
                f"'{test_query.query}' returned no usable results. Search failed to map the query to "
                f"its own merchandised category. " + (evidence or "")
            )
            recommended_fix = (
                f"Map this query/occasion to the existing '{matched_cat}' category: index category "
                f"names and occasion synonyms as searchable terms, or route matching queries to that "
                f"category page. The inventory already exists on-site — search just isn't reaching it."
            )

    # Conversational-zero normalization. For NATURAL_LANGUAGE / SEMANTIC_MEANING queries that
    # returned nothing usable, the root cause is always the engine's inability to understand a
    # conceptual/conversational phrase — so normalize the cluster to NO_SEMANTIC_UNDERSTANDING
    # rather than the literal ZERO_RESULTS_OR_GARBAGE symptom. Keeps the headline finding
    # coherent across the cluster; severity is unchanged (typically CRITICAL).
    if _cat in ("NATURAL_LANGUAGE", "SEMANTIC_MEANING", "SUBJECTIVE_ATTRIBUTE") and fm == FailureMode.ZERO_RESULTS_OR_GARBAGE:
        fm = FailureMode.NO_SEMANTIC_UNDERSTANDING
        fm_explanation = None

    # Deterministic NEGATIVE_INTENT exclusion guard. Count results that VIOLATE the exclusion
    # (contain the excluded term — including faux/imitation, e.g. "Faux Leather" violates "not
    # leather", still being leather-look). Score consistently by how much of the page violates:
    # most/all violating = the engine ignored the negation entirely = CONSTRAINT_DROPPED CRITICAL.
    if _cat == "NEGATIVE_INTENT":
        frac = _exclusion_violation_fraction(test_query.query, results, site_categories)
        if frac is not None and frac >= 0.5:
            excl = _excluded_term(test_query.query)
            new_sev = Severity.CRITICAL if frac >= 0.8 else Severity.MODERATE
            if _SEVERITY_RANK.get(new_sev.value, 0) >= _SEVERITY_RANK.get(sev.value if isinstance(sev, Severity) else sev, 0):
                fm = FailureMode.CONSTRAINT_DROPPED
                sev = new_sev
                fm_explanation = None
                evidence = (
                    f"Exclusion ignored: {round(frac*100)}% of results contain the excluded term "
                    f"'{excl}' (faux/imitation counts — it is still {excl}-look). The engine treated "
                    f"'{test_query.query}' as if the negation were absent. " + (evidence or "")
                )
                recommended_fix = (
                    f"Parse negation ('not'/'without') and filter OUT results matching '{excl}' "
                    f"(including faux/imitation variants), rather than ignoring the exclusion."
                )

    return QueryJudgment(
        test_query=test_query,
        results=results,
        failure_mode=fm,
        failure_mode_explanation=fm_explanation,
        severity=sev,
        evidence=evidence,
        recommended_fix=recommended_fix,
        displacement=displacement,
        max_relevance_score=max_relevance,
        top3_original_average=top3_avg,
    )


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def judge_all_queries(
    queries: list[TestQuery],
    scored_results: dict[str, list[ScoredResult]],
    language: str | None = None,
    provenance: dict | None = None,
    site_categories: list[str] | None = None,
    site_brands: list[str] | None = None,
) -> list[QueryJudgment]:
    """Judge every query's results and produce QueryJudgment objects.

    Processes sequentially. Logs each verdict. Returns list[QueryJudgment].

    When ``language`` is provided, each query is judged with calibration examples from
    past audits in that language injected into the prompt, and the resulting judgements
    are harvested back into the knowledge base. When ``language`` is None the knowledge
    base is bypassed entirely and behavior is identical to before (a safe no-op default).
    """
    judgments: list[QueryJudgment] = []
    total = len(queries)
    severity_counts: Counter[str] = Counter()

    for i, tq in enumerate(queries, 1):
        results = scored_results.get(tq.query, [])
        logger.info("[%d/%d] Judging: '%s' (%d results)", i, total, tq.query, len(results))

        judgment = _judge_single_query(tq, results, language=language, site_categories=site_categories, site_brands=site_brands)
        judgments.append(judgment)

        sev_value = judgment.severity
        if isinstance(sev_value, Severity):
            sev_value = sev_value.value
        emoji = _SEVERITY_EMOJI.get(sev_value, "[ ]")

        # Get the short severity name for logging
        sev_short = "UNKNOWN"
        for short, full in _SEVERITY_MAP.items():
            if full.value == sev_value:
                sev_short = short
                break

        fm_value = judgment.failure_mode
        if isinstance(fm_value, FailureMode):
            fm_value = fm_value.value

        logger.info(
            "%s %s | %s | '%s'",
            emoji, sev_short, fm_value, tq.query,
        )

        severity_counts[sev_short] += 1

    logger.info(
        "Judging complete: %d queries — CRITICAL: %d, MODERATE: %d, MINOR: %d, PASS: %d",
        total,
        severity_counts.get("CRITICAL", 0),
        severity_counts.get("MODERATE", 0),
        severity_counts.get("MINOR", 0),
        severity_counts.get("PASS", 0),
    )

    # Harvest this audit's verdicts into the language KB for future calibration.
    if language:
        judge_kb.harvest(judgments, language, provenance)

    return judgments


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # --- Scenario 1: PASS — exact product name, top results are relevant ---
    pass_query = TestQuery(
        category="DIRECT_MATCH",
        query="Nike Air Max 90",
        rationale="Exact product name lookup — should return the right product at #1",
    )
    pass_results: dict[str, list[ScoredResult]] = {
        "Nike Air Max 90": [
            ScoredResult(rank=1, title="Nike Air Max 90 - White/Black", price="$130.00",
                         snippet="Classic Air Max 90 with visible Air cushioning",
                         url="/p/am90-wb", relevance_score=0.95, original_rank=1),
            ScoredResult(rank=2, title="Nike Air Max 90 Premium - Grey", price="$150.00",
                         snippet="Premium leather Air Max 90",
                         url="/p/am90-grey", relevance_score=0.91, original_rank=2),
            ScoredResult(rank=3, title="Nike Air Max 90 Futura", price="$160.00",
                         snippet="Modern take on the AM90 silhouette",
                         url="/p/am90-futura", relevance_score=0.87, original_rank=3),
            ScoredResult(rank=4, title="Nike Air Max 95 - Black", price="$175.00",
                         snippet="Air Max 95 with gradient side panels",
                         url="/p/am95-blk", relevance_score=0.52, original_rank=4),
        ],
    }

    # --- Scenario 2: CRITICAL — typo with garbage results ---
    critical_query = TestQuery(
        category="TYPO",
        query="nkie air max",
        rationale="Misspelling of 'Nike' — tests fuzzy matching / typo tolerance",
    )
    critical_results: dict[str, list[ScoredResult]] = {
        "nkie air max": [
            ScoredResult(rank=1, title="Air Freshener - Vanilla Scent 3-Pack", price="$8.99",
                         snippet="Keep your car smelling fresh",
                         url="/p/air-fresh", relevance_score=0.08, original_rank=1),
            ScoredResult(rank=2, title="Maximizer Hair Gel 16oz", price="$12.50",
                         snippet="Maximum hold styling gel",
                         url="/p/max-gel", relevance_score=0.05, original_rank=2),
            ScoredResult(rank=3, title="Air Pump for Bicycles", price="$24.99",
                         snippet="Portable floor pump with gauge",
                         url="/p/air-pump", relevance_score=0.06, original_rank=3),
        ],
    }

    # --- Scenario 3: MODERATE — negative intent constraint dropped ---
    moderate_query = TestQuery(
        category="NEGATIVE_INTENT",
        query="running shoes not Nike",
        rationale="Exclusion constraint — Nike results should NOT appear",
    )
    moderate_results: dict[str, list[ScoredResult]] = {
        "running shoes not Nike": [
            ScoredResult(rank=1, title="Nike Pegasus 40 Running Shoe", price="$130.00",
                         snippet="Responsive everyday running shoe",
                         url="/p/peg40", relevance_score=0.35, original_rank=1),
            ScoredResult(rank=2, title="Adidas Ultraboost 22 Running", price="$190.00",
                         snippet="Energy-returning running shoe",
                         url="/p/ub22", relevance_score=0.82, original_rank=2),
            ScoredResult(rank=3, title="Nike Vomero 17", price="$160.00",
                         snippet="Max cushion running shoe",
                         url="/p/vom17", relevance_score=0.30, original_rank=3),
            ScoredResult(rank=4, title="Hoka Clifton 9", price="$145.00",
                         snippet="Lightweight cushioned running shoe",
                         url="/p/clif9", relevance_score=0.80, original_rank=4),
            ScoredResult(rank=5, title="New Balance Fresh Foam 1080v13", price="$160.00",
                         snippet="Plush long-distance running shoe",
                         url="/p/ff1080", relevance_score=0.78, original_rank=5),
        ],
    }

    all_queries = [pass_query, critical_query, moderate_query]
    all_scored = {**pass_results, **critical_results, **moderate_results}

    print("=" * 70)
    print("  LLM Judge — 3 Test Scenarios")
    print("=" * 70)
    print()

    judgments = judge_all_queries(all_queries, all_scored)

    for j in judgments:
        sev_value = j.severity if isinstance(j.severity, str) else j.severity.value
        fm_value = j.failure_mode if isinstance(j.failure_mode, str) else j.failure_mode.value

        sev_short = "UNKNOWN"
        for short, full in _SEVERITY_MAP.items():
            if full.value == sev_value:
                sev_short = short
                break

        print(f"\n{'='*70}")
        print(f"  Query: '{j.test_query.query}'")
        print(f"  Category: {j.test_query.category}")
        print(f"  Severity: {sev_short}")
        print(f"  Failure mode: {fm_value}")
        if j.failure_mode_explanation:
            print(f"  Explanation: {j.failure_mode_explanation}")
        print(f"  Displacement: {j.displacement}")
        print(f"  Max relevance: {j.max_relevance_score:.3f}")
        print(f"  Top 3 avg: {j.top3_original_average:.3f}")
        print(f"  Evidence: {j.evidence}")
        print(f"  Fix: {j.recommended_fix}")
        print(f"{'='*70}")
