"""Single source of every number, label and shared selection the client report shows.

Both renderers — the markdown report (`report_generator`) and the HTML report
(`html_renderer`) — read their figures from here, so the .md and the .html of one audit can
never disagree. Rules that apply everywhere:

- **Excluded judgments never count.** A judgment with ``excluded_reason`` set (catalog gap,
  invalid test, unverified fetch) stays in the data for transparency and is listed in the
  "Not scored" appendix, but is left out of every rate, count and KPI (see CONTRACT).
- **No internal numbers reach the client.** Relevance scores are used here only to *select*
  (e.g. which result was the strongest); they are never formatted into client text.
  :func:`sanitize_client_text` strips score talk and workflow markers from legacy evidence.
- **"The store carries X" needs proof** (:func:`proof_of_stock`): a control search for the
  plain term that returned products, or a title from another tested query's results.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from urllib.parse import quote_plus

from src.models import (
    CAPABILITY_CATEGORY_MAP,
    CapabilityGroup,
    CapabilityScore,
    FailureMode,
    QueryJudgment,
    Severity,
)

# ---------------------------------------------------------------------------
# Display vocabulary
# ---------------------------------------------------------------------------

SEVERITY_RANK: dict[str, int] = {
    Severity.PASS.value: 0,
    Severity.MINOR.value: 1,
    Severity.MODERATE.value: 2,
    Severity.CRITICAL.value: 3,
}

SEVERITY_SHORT: dict[str, str] = {
    Severity.CRITICAL.value: "Critical",
    Severity.MODERATE.value: "Moderate",
    Severity.MINOR.value: "Minor",
    Severity.PASS.value: "Pass",
}

# Capability priority wording — identical in the markdown scorecard and the HTML map.
PRIORITY_LABELS: dict[str, str] = {
    Severity.CRITICAL.value: "Focus area",
    Severity.MODERATE.value: "Watch",
    Severity.MINOR.value: "Fine-tune",
    Severity.PASS.value: "Working well",
}

CAPABILITY_NAMES: dict[str, str] = {
    CapabilityGroup.TYPO_TOLERANCE.value: "Typo Tolerance",
    CapabilityGroup.LANGUAGE_UNDERSTANDING.value: "Language Understanding",
    CapabilityGroup.PRODUCT_DISCOVERY.value: "Product Discovery",
    CapabilityGroup.BRAND_MODEL_SEARCH.value: "Brand & Model Search",
    CapabilityGroup.FILTERS_CONSTRAINTS.value: "Filters & Constraints",
    CapabilityGroup.SHOPPING_CONTEXT.value: "Shopping Context",
}

FAILURE_MODE_DISPLAY: dict[str, str] = {
    "PARTIAL_KEYWORD_MATCH": "Partial keyword match",
    "BRAND_BLEED": "Brand bleed",
    "CONSTRAINT_DROPPED": "Constraint dropped",
    "CATEGORY_MAPPING_FAILURE": "Category mapping failure",
    "FACET_NOT_EXTRACTED": "Facet not extracted",
    "NO_FUZZY_MATCHING": "No fuzzy matching",
    "NO_SEMANTIC_UNDERSTANDING": "No semantic understanding",
    "POOR_RANKING": "Poor ranking",
    "DUPLICATE_FLOODING": "Duplicate flooding",
    # Not "Zero results": this mode is also used for junk result pages, and the
    # "returned nothing" count is a separate, broader figure (see ZERO_RESULT_FOOTNOTE).
    "ZERO_RESULTS_OR_GARBAGE": "Nothing usable matched",
    "OTHER": "Other",
}

CATEGORY_DISPLAY: dict[str, str] = {
    "DIRECT_MATCH": "Direct match",
    "BROAD_CATEGORY": "Broad category",
    "SYNONYM": "Synonym",
    "TYPO": "Typo",
    "SPECIAL_CHARACTER": "Special character",
    "MERGED_WORDS": "Merged words",
    "BRAND_SEARCH": "Brand search",
    "SPLIT_WORD": "Split word",
    "NATURAL_LANGUAGE": "Natural language",
    "PRICE_ANCHORED": "Price anchored",
    "NEGATIVE_INTENT": "Negative intent",
    "UNIT_VARIATION": "Unit variation",
    "PLURAL_SINGULAR": "Plural / singular",
    "ABBREVIATION": "Abbreviation",
    "LOCALE_VARIATION": "Locale variation",
    "SKU_MODEL_NUMBER": "SKU / model number",
    "SUBJECTIVE_ATTRIBUTE": "Subjective attribute",
    "OCCASION": "Occasion",
    "SEASONAL_OCCASION": "Seasonal / occasion",
    "MULTI_ATTRIBUTE": "Multi-attribute",
    "STOP_WORD_HEAVY": "Stop-word heavy",
    "PARTIAL_QUERY": "Partial query",
    "LONG_VERBOSE_QUERY": "Long verbose query",
    "SEMANTIC_MEANING": "Semantic meaning",
    "CATEGORY_MAPPING": "Category mapping",
    "FACET_EXTRACTION": "Facet extraction",
    "GIBBERISH": "Gibberish",
}

CATEGORY_TO_CAPABILITY: dict[str, str] = {
    cat.value: cap.value for cap, cats in CAPABILITY_CATEGORY_MAP.items() for cat in cats
}

EXCLUDED_REASON_TEXT: dict[str, str] = {
    "catalog_gap": "The store doesn't appear to stock this — the plain search term returned nothing "
                   "too, so it says nothing about search quality.",
    "invalid_test": "The test query itself turned out to be flawed, so we dropped it.",
    "fetch_unverified": "We couldn't load the results page reliably (blocked, timed out or "
                        "unreadable), so we didn't score it.",
}

# Metric labels shared by both renderers.
FOUND_BUT_WRONG_LABEL = "Products returned, but the wrong ones or in the wrong order"
ZERO_RESULT_LABEL = "Searches that returned nothing usable"
ZERO_RESULT_FOOTNOTE = (
    "Counts every failing search whose results page was empty, whatever the cause. The failure-mode "
    "table explains why each search failed, so its “Nothing usable matched” row is smaller."
)
SAMPLE_NOTE = (
    "The test set is deliberately hard: realistic but demanding phrasings, typos and filters, "
    "not weighted by your traffic. Read the rates as a map of failure patterns, not as a share "
    "of your revenue or of all searches on the site."
)

# A #1 result this weak is off-topic for the shopper. Used to *count*, never displayed.
TOP1_IRRELEVANT_BELOW = 0.40
# The strongest result is only named as "the better match" when it is clearly on-topic.
NAMEABLE_BEST_MIN = 0.60

# Failure modes where the engine retrieved the right kind of product but ordered it badly.
RANKING_MODES = {"POOR_RANKING", "DUPLICATE_FLOODING"}


# ---------------------------------------------------------------------------
# Basic accessors
# ---------------------------------------------------------------------------


def sev(j: QueryJudgment) -> str:
    return getattr(j.severity, "value", j.severity)


def mode(j: QueryJudgment) -> str:
    return getattr(j.failure_mode, "value", j.failure_mode)


def category(j: QueryJudgment) -> str:
    return getattr(j.test_query.category, "value", j.test_query.category)


def is_pass(j: QueryJudgment) -> bool:
    return sev(j) == Severity.PASS.value


def scored(judgments: list[QueryJudgment]) -> list[QueryJudgment]:
    """Judgments that count toward rates (``excluded_reason is None``)."""
    return [j for j in judgments if getattr(j, "excluded_reason", None) is None]


def excluded(judgments: list[QueryJudgment]) -> list[QueryJudgment]:
    return [j for j in judgments if getattr(j, "excluded_reason", None) is not None]


def by_original(j: QueryJudgment):
    return sorted(j.results, key=lambda r: r.original_rank)


def top_result(j: QueryJudgment):
    rs = by_original(j)
    return rs[0] if rs else None


def best_result(j: QueryJudgment):
    """The strongest result in the set (selection only — the score is never shown)."""
    return max(j.results, key=lambda r: r.relevance_score) if j.results else None


def pct(part: float, total: float) -> float:
    return (part / total * 100) if total else 0.0


def fmt_pct(value: float) -> str:
    return f"{value:.0f}%"


def fmt_pos(value: float) -> str:
    """Average positions are always shown with one decimal (#3.6), everywhere."""
    return f"#{value:.1f}"


def md_cell(text) -> str:
    """Make a value safe inside a markdown table cell."""
    return " ".join(str(text if text is not None else "").split()).replace("|", "\\|")


def search_url(template: str, query: str) -> str | None:
    """Reproduction link for one tested query, or None when the template is unusable."""
    t = (template or "").strip()
    if not t.lower().startswith(("http://", "https://")):
        return None
    if "{query}" in t:
        return t.replace("{query}", quote_plus(query))
    if "{}" in t:
        return t.replace("{}", quote_plus(query))
    return None


# ---------------------------------------------------------------------------
# Client-text sanitiser
# ---------------------------------------------------------------------------

# "(€129.95, relevance 0.965)", "(0.617)", "(scores 0.504 and 0.498)"
_SCORE_PAREN = re.compile(r"\s*\((?=[^()]*\d\.\d{2})[^()]*\)")
# "[Override: …]", "[MANUAL VERIFICATION REQUIRED]", "[Severity escalated …]"
_WORKFLOW_BRACKET = re.compile(
    r"\s*\[[^\]]*(?:override|manual verification|escalat|calibrat)[^\]]*\]", re.I
)
_SOFTEN = [
    (re.compile(r"\b(?:highest|best)[- ](?:relevance|scor(?:ing|ed))\b", re.I), "best-matching"),
    (re.compile(r"\bhigher[- ](?:relevance|scor(?:ing|ed))\b", re.I), "better-matching"),
    (re.compile(r"\b(?:lowest|lower|weakest)[- ](?:relevance|scor(?:ing|ed))\b", re.I), "weaker"),
]
# A sentence that still carries internals after the cheap fixes above is dropped whole.
_INTERNAL_SENTENCE = re.compile(
    r"((?<![€£$\d.,])\b[01]\.\d{2,3}\b(?!\s*(?:€|eur|£|\$|kr|sek|dkk|nok|chf|:-|l|ml|cl|dl|kg|g|mm|cm|m|oz)\b)|relevance|\bscor(?:e|es|ed|ing)\b|rerank|voyage|cross-encoder|threshold|"
    r"calibrat|override|materiality|\bLLM\b|claude|sonnet|haiku|anthropic|manual verification|"
    r"escalat|\bstats?\b|top[- ]3 average|\bjudge\b|max_relevance)",
    re.I,
)
_SENTENCE_SPLIT = re.compile(r"(?<!\be\.g\.)(?<!\bi\.e\.)(?<=[.!?])\s+(?=[A-Z0-9\"'“‘(\[#])")


def sanitize_client_text(text: str | None) -> str:
    """Strip numeric relevance talk and workflow markers from evidence a client will read.

    Removes score parentheticals and override/verification markers, softens "highest-relevance"
    wording, then drops any sentence that still mentions scores, thresholds, tooling or
    workflow. Returns "" when nothing client-safe is left — callers then use
    :func:`client_observation`.
    """
    t = " ".join((text or "").split())
    if not t:
        return ""
    t = t.replace("**", "")
    t = _WORKFLOW_BRACKET.sub("", t)
    t = _SCORE_PAREN.sub("", t)
    for pattern, repl in _SOFTEN:
        t = pattern.sub(repl, t)
    kept = [s for s in _SENTENCE_SPLIT.split(t) if s.strip() and not _INTERNAL_SENTENCE.search(s)]
    out = " ".join(kept).strip()
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return out


_MODE_OBSERVATION = {
    "NO_SEMANTIC_UNDERSTANDING": "The search didn't understand what the shopper meant.",
    "CATEGORY_MAPPING_FAILURE": "The search didn't connect this wording to the matching category.",
    "PARTIAL_KEYWORD_MATCH": "Results matched only part of the query.",
    "BRAND_BLEED": "Other brands crowded out the brand the shopper asked for.",
    "CONSTRAINT_DROPPED": "Results ignored a limit the shopper set.",
    "FACET_NOT_EXTRACTED": "An attribute in the query (colour, material, size) wasn't applied.",
    "NO_FUZZY_MATCHING": "The misspelling wasn't recognised.",
    "POOR_RANKING": "Better matches were ranked below weaker ones.",
    "DUPLICATE_FLOODING": "Variants of the same product filled the first results.",
    "ZERO_RESULTS_OR_GARBAGE": "Nothing usable matched the query.",
}


def client_observation(j: QueryJudgment) -> str:
    """Client-safe one-liner for a judgment: sanitised evidence, else a plain data-derived line."""
    text = sanitize_client_text(j.evidence)
    if text:
        return text
    if is_pass(j):
        return "Search handled this well."
    if not j.results:
        return "The search returned no results."
    top = top_result(j)
    return f"The first result was “{top.title}”. {_MODE_OBSERVATION.get(mode(j), '')}".strip()


# ---------------------------------------------------------------------------
# Proof of stock — the only allowed basis for "the store carries X"
# ---------------------------------------------------------------------------

_Q_OPEN = "[\"'“‘]"
_Q_CLOSE = "[\"'”’]"
# Judge evidence states control proof as: searching '<target>' returns products such as '<title>'.
_CONTROL_PROOF_RE = re.compile(
    rf"searching\s+{_Q_OPEN}(?P<term>.+?){_Q_CLOSE}(?=[\s,.;:)])\s+returns?\s+(?:products?\s+)?"
    rf"(?:such\s+as|like|including)\s+{_Q_OPEN}(?P<title>.+?){_Q_CLOSE}(?=[\s,.;:)]|$)",
    re.I,
)

_EXAMPLE_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "with", "some", "any", "me", "my", "i",
    "want", "need", "buy", "find", "looking", "look", "show", "help", "best",
    "nice", "really", "high", "quality", "good", "great", "perfect", "stylish",
    "comfortable", "trendy", "fashionable", "available", "store", "both", "that",
    "would", "work", "casual", "formal", "occasions", "occasion", "where", "can",
    "from", "like", "brands", "brand", "women", "men", "under", "over", "kr", "dkk",
    "size", "pair", "of", "to", "in", "on", "is", "are", "this", "your", "you",
    "clothing", "clothes", "jacket", "jackets", "dress", "dresses", "shoes",
    "shoe", "sneakers", "sneaker", "boots", "boot", "bag", "bags", "handbag",
    "handbags", "sport", "sports", "outfit", "wardrobe", "essentials",
    "til", "og", "en", "et", "med", "jeg", "vil", "have", "kjole", "sko",
    "für", "und", "mit", "ohne", "unter", "der", "die", "das", "för", "och", "utan",
}


def _norm_token(s: str) -> str:
    # Unicode-aware: keeps å/ä/ö/ü/é… (an ASCII-only class shredded non-English words).
    return re.sub(r"[\W_]+", "", (s or "").casefold())


def _query_tokens(q: str) -> list[str]:
    return re.findall(r"[^\W_]+", (q or "").casefold())


def _candidate_phrases(query: str) -> list[str]:
    words = [w for w in _query_tokens(query) if len(w) >= 3 and w not in _EXAMPLE_STOPWORDS]
    phrases = [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)] + words
    out: list[str] = []
    for p in dict.fromkeys(phrases):
        if len(_norm_token(p)) >= 5:
            out.append(p)
    out.sort(key=lambda p: len(_norm_token(p)), reverse=True)
    return out


def control_proof(j: QueryJudgment) -> dict | None:
    """Control-search proof the judge wrote into evidence, if any."""
    m = _CONTROL_PROOF_RE.search(j.evidence or "")
    if not m:
        return None
    return {"working_variant": m.group("term").strip(), "example_title": m.group("title").strip(),
            "source": "control"}


def _cross_query_proof(query: str, judgments: list[QueryJudgment]) -> dict | None:
    """A direct search for the term works elsewhere in the audit (title from another query's
    results). Rejects coincidental generic-word matches via a document-frequency cap."""
    others = [j for j in judgments if j.test_query.query != query and j.results]
    for phrase in _candidate_phrases(query):
        needle = _norm_token(phrase)
        df = sum(1 for j in others if any(needle in _norm_token(r.title) for r in j.results))
        if df == 0 or df > 6:
            continue
        direct = [
            j for j in others
            if needle in _norm_token(j.test_query.query)
            and any(needle in _norm_token(r.title) for r in j.results)
        ]
        if direct:
            direct.sort(key=lambda j: len(j.test_query.query))
            hit = direct[0]
            match = next(r for r in hit.results if needle in _norm_token(r.title))
            return {"working_variant": hit.test_query.query, "example_title": match.title,
                    "source": "cross_query"}
    return None


def proof_of_stock(j: QueryJudgment, judgments: list[QueryJudgment]) -> dict | None:
    """Proof that a failing search should have found products, or None (then make no claim)."""
    return control_proof(j) or _cross_query_proof(j.test_query.query, judgments)


# ---------------------------------------------------------------------------
# Capability scoring + priority (one rule for md scorecard and HTML map)
# ---------------------------------------------------------------------------


def _capability_summary(cap_name: str, severity: str, non_pass: int, total: int) -> str:
    if total == 0:
        return f"No scored searches in {cap_name} (see “Not scored”)."
    if severity == Severity.CRITICAL.value:
        return f"{non_pass} of {total} tested searches show room to improve. A practical place to start for {cap_name}."
    if severity == Severity.MODERATE.value:
        return f"{non_pass} of {total} tested searches showed friction. {cap_name} has a focused opportunity."
    if severity == Severity.MINOR.value:
        return f"{cap_name} mostly works, with smaller refinements in {non_pass} of {total} tested searches."
    return f"All {total} tested searches passed. {cap_name} performs well in this sample."


def build_capability_scores(judgments: list[QueryJudgment]) -> list[CapabilityScore]:
    """Group judgments by capability; severity and summary are computed over SCORED ones only.

    Every judgment (excluded ones too) stays in ``judgments`` so the persisted data is complete.
    Worst severity wins, with an ease-up: CRITICAL drops to MODERATE when more than half the
    capability's scored searches passed.
    """
    grouped: dict[str, list[QueryJudgment]] = defaultdict(list)
    for j in judgments:
        cap = CATEGORY_TO_CAPABILITY.get(category(j))
        if cap:
            grouped[cap].append(j)

    scores: list[CapabilityScore] = []
    for cap, cap_js in grouped.items():
        sc = scored(cap_js)
        total = len(sc)
        worst = max((sev(j) for j in sc), key=lambda s: SEVERITY_RANK.get(s, 0), default=Severity.PASS.value)
        pass_count = sum(1 for j in sc if is_pass(j))
        if worst == Severity.CRITICAL.value and pass_count > total / 2:
            worst = Severity.MODERATE.value
        cap_name = CAPABILITY_NAMES.get(cap, cap)
        scores.append(CapabilityScore(
            capability=CapabilityGroup(cap),
            severity=Severity(worst),
            summary=_capability_summary(cap_name, worst, total - pass_count, total),
            judgments=cap_js,
        ))
    scores.sort(key=lambda cs: capability_sort_key(cs), reverse=True)
    return scores


def severity_counts(judgments: list[QueryJudgment]) -> dict[str, int]:
    sc = scored(judgments)
    return {
        "critical": sum(1 for j in sc if sev(j) == Severity.CRITICAL.value),
        "moderate": sum(1 for j in sc if sev(j) == Severity.MODERATE.value),
        "minor": sum(1 for j in sc if sev(j) == Severity.MINOR.value),
        "passed": sum(1 for j in sc if is_pass(j)),
        "total": len(sc),
    }


def capability_sort_key(cs: CapabilityScore) -> tuple:
    """Priority order: capability severity first, then critical/moderate/minor counts."""
    c = severity_counts(cs.judgments)
    return (SEVERITY_RANK.get(cs.severity, 0), c["critical"], c["moderate"], c["minor"], -c["passed"])


def capability_rows(judgments: list[QueryJudgment]) -> list[dict]:
    """Capabilities in priority order, with the label and counts both renderers show."""
    rows = []
    for cs in build_capability_scores(judgments):
        c = severity_counts(cs.judgments)
        if not c["total"]:
            continue
        fail_modes = Counter(
            FAILURE_MODE_DISPLAY.get(mode(j), mode(j)) for j in scored(cs.judgments) if not is_pass(j)
        )
        rows.append({
            "capability_key": cs.capability,
            "capability": CAPABILITY_NAMES.get(cs.capability, cs.capability),
            "severity": cs.severity,
            "priority": PRIORITY_LABELS.get(cs.severity, SEVERITY_SHORT.get(cs.severity, "")),
            "summary": cs.summary,
            "top_issue": fail_modes.most_common(1)[0][0] if fail_modes else "",
            **c,
        })
    return rows


# ---------------------------------------------------------------------------
# Root causes — one mechanism presented once, with its N affected searches
# ---------------------------------------------------------------------------

_FILTER_FAMILY = {"PRICE_ANCHORED": "price", "NEGATIVE_INTENT": "exclusion"}

_MECHANISM_LABELS: dict[tuple[str, str], str] = {
    ("CONSTRAINT_DROPPED", "price"): "Price limits in the query are ignored",
    ("CONSTRAINT_DROPPED", "exclusion"): "Exclusions such as “not” or “without” are ignored",
    ("FACET_NOT_EXTRACTED", "price"): "Price phrases aren't read as a filter",
    ("FACET_NOT_EXTRACTED", "exclusion"): "Exclusions such as “not” or “without” are ignored",
}
_MECHANISM_BY_MODE: dict[str, str] = {
    "CONSTRAINT_DROPPED": "Stated limits (colour, material, size) are dropped",
    "FACET_NOT_EXTRACTED": "Attributes in the query aren't applied as filters",
    "NO_SEMANTIC_UNDERSTANDING": "Everyday phrasing isn't understood",
    "CATEGORY_MAPPING_FAILURE": "Common terms aren't mapped to your categories",
    "NO_FUZZY_MATCHING": "Misspellings aren't corrected",
    "PARTIAL_KEYWORD_MATCH": "One word in the query outweighs the rest",
    "BRAND_BLEED": "Brand requests return other brands",
    "POOR_RANKING": "Right products found, but ranked below weaker ones",
    "DUPLICATE_FLOODING": "Variants of one product crowd out the rest",
    "ZERO_RESULTS_OR_GARBAGE": "The wording finds nothing usable",
    "OTHER": "Other search gaps",
}


def _family(j: QueryJudgment) -> str:
    cat = category(j)
    cap = CATEGORY_TO_CAPABILITY.get(cat, "")
    if cap == CapabilityGroup.FILTERS_CONSTRAINTS.value:
        return _FILTER_FAMILY.get(cat, "attribute")
    return cap


def mechanism_label(j: QueryJudgment) -> str:
    m = mode(j)
    return _MECHANISM_LABELS.get((m, _family(j))) or _MECHANISM_BY_MODE.get(m, "Other search gaps")


def root_causes(judgments: list[QueryJudgment]) -> list[dict]:
    """Failing scored searches grouped by (failure mode, category family), biggest first."""
    groups: dict[tuple[str, str], list[QueryJudgment]] = defaultdict(list)
    for j in scored(judgments):
        if not is_pass(j):
            groups[(mode(j), _family(j))].append(j)
    out = []
    for (m, fam), js in groups.items():
        js.sort(key=lambda j: -SEVERITY_RANK.get(sev(j), 0))
        out.append({
            "failure_mode": m,
            "family": fam,
            "mechanism": mechanism_label(js[0]),
            "count": len(js),
            "critical": sum(1 for j in js if sev(j) == Severity.CRITICAL.value),
            "queries": [j.test_query.query for j in js],
        })
    # Merge groups that resolve to the same mechanism label (e.g. two modes, one cause).
    merged: dict[str, dict] = {}
    for g in out:
        m = merged.get(g["mechanism"])
        if m is None:
            merged[g["mechanism"]] = g
        else:
            m["count"] += g["count"]
            m["critical"] += g["critical"]
            m["queries"] += g["queries"]
    rows = list(merged.values())
    rows.sort(key=lambda g: (g["critical"], g["count"]), reverse=True)
    return rows


# Why zero-result searches failed, in plain words — derived from data, not hard-coded.
_ZERO_CAUSE = {
    "NO_SEMANTIC_UNDERSTANDING": "everyday phrasing wasn't understood",
    "CATEGORY_MAPPING_FAILURE": "common terms weren't mapped to the right category",
    "NO_FUZZY_MATCHING": "a misspelling wasn't corrected",
    "CONSTRAINT_DROPPED": "a limit or exclusion in the query wasn't handled",
    "FACET_NOT_EXTRACTED": "a limit or exclusion in the query wasn't handled",
    "PARTIAL_KEYWORD_MATCH": "one word in the query outweighed the rest",
    "BRAND_BLEED": "a brand name wasn't recognised",
    "ZERO_RESULTS_OR_GARBAGE": "the wording matched nothing in the index",
}


def zero_result_causes(judgments: list[QueryJudgment], limit: int = 3) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for j in scored(judgments):
        if not is_pass(j) and not j.results:
            counts[_ZERO_CAUSE.get(mode(j), "the search found no match")] += 1
    return counts.most_common(limit)


# ---------------------------------------------------------------------------
# "Most severe example" — one picker for both renderers
# ---------------------------------------------------------------------------

_HIGH_INTENT_CATEGORIES = {
    "PRICE_ANCHORED", "MULTI_ATTRIBUTE", "SKU_MODEL_NUMBER", "BRAND_SEARCH",
    "TYPO", "SPLIT_WORD", "PLURAL_SINGULAR", "DIRECT_MATCH",
}
_MATCHED_CATEGORY_RE = re.compile(r"matching category[^'\"“‘]*['\"“‘]([^'\"”’]+)['\"”’]")


def _excluded_term_simple(query: str) -> str | None:
    """The term a 'X not Y' / 'X without Y' query asks to exclude."""
    m = re.search(r"\b(?:not|without|no|ohne|utan|uden|uten|sans|zonder)\s+(.+)$", query.casefold())
    return m.group(1).strip() if m else None


def pick_worst_example(judgments: list[QueryJudgment], nav_categories: list[str] | None = None) -> str:
    """One ready-made sentence describing the most damning, TRUE failure ("" if none).

    Scored, non-PASS judgments only. A "you carry it" claim needs proof: a control search /
    another query's results (:func:`proof_of_stock`), or a judged category match that is a real
    navigation category of the site. Otherwise the sentence states only the dead end.
    """
    sc = scored(judgments)
    nav = {c.casefold().strip() for c in (nav_categories or [])}
    candidates: list[tuple[float, float, str]] = []
    for j in sc:
        if is_pass(j):
            continue
        q = j.test_query.query
        if not q:
            continue
        m = mode(j)

        if not j.results:
            proof = proof_of_stock(j, sc)
            cat = None
            if m == FailureMode.CATEGORY_MAPPING_FAILURE.value:
                hit = _MATCHED_CATEGORY_RE.search(j.evidence or "")
                cat = hit.group(1) if hit and hit.group(1).casefold().strip() in nav else None
            if cat:
                candidates.append((1, len(q), (
                    f'A customer searching "{q}" gets a blank page — even though you have a '
                    f'"{cat}" category for exactly this.'
                )))
            elif proof:
                candidates.append((1.2, len(q), (
                    f'A customer searching "{q}" gets a blank page — yet searching '
                    f'"{proof["working_variant"]}" shows products such as "{proof["example_title"]}".'
                )))
            else:
                high = category(j) in _HIGH_INTENT_CATEGORIES
                candidates.append((2 if high else 3, len(q),
                                   f'A customer searching "{q}" gets a blank page — no results at all.'))
            continue

        if m == FailureMode.CONSTRAINT_DROPPED.value:
            excl = _excluded_term_simple(q)
            if excl:
                n = len(j.results)
                candidates.append((1.5, float(-n), (
                    f'A customer searching "{q}" is still shown {n} results that include '
                    f'"{excl}" — the exact thing they asked to leave out.'
                )))
                continue

        top = top_result(j)
        best = best_result(j)
        if sev(j) == Severity.CRITICAL.value and top.relevance_score < TOP1_IRRELEVANT_BELOW:
            candidates.append((4, top.relevance_score, (
                f'A customer searching "{q}" sees "{top.title}" at the #1 spot — not what they asked for.'
            )))
        elif j.displacement > 2 and best.relevance_score >= NAMEABLE_BEST_MIN:
            pos = j.displacement + 1
            candidates.append((5, float(-pos), (
                f'A customer searching "{q}" has to scroll to position {pos} to reach the '
                f'best-matching product — below {j.displacement} weaker results.'
            )))

    if not candidates:
        return ""
    candidates.sort(key=lambda c: (c[0], c[1]))
    return candidates[0][2]


# ---------------------------------------------------------------------------
# What's working — computed from data, or omitted
# ---------------------------------------------------------------------------


def whats_working_items(judgments: list[QueryJudgment]) -> list[dict]:
    """[{label, text}] strengths. Every statement is checked against the data; [] when none hold.

    Primary: query categories where every scored test passed (≥2 tests). Fallback statements
    are each verified: results returned for most searches, near misses (best result at #2–#3),
    misspellings recognised (TYPO tests that passed or whose right products were retrieved).
    """
    sc = scored(judgments)
    by_cat: dict[str, list[QueryJudgment]] = defaultdict(list)
    for j in sc:
        by_cat[category(j)].append(j)

    strong = []
    for cat, js in by_cat.items():
        if len(js) >= 2 and all(is_pass(j) for j in js):
            strong.append((len(js), cat, js))
    strong.sort(key=lambda t: (-t[0], t[1]))
    if strong:
        return [
            {"label": CATEGORY_DISPLAY.get(cat, cat),
             "text": f"({n}/{n} passed) — e.g. “{js[0].test_query.query}”"}
            for n, cat, js in strong
        ]

    items: list[dict] = []
    n = len(sc)
    with_results = [j for j in sc if j.results]
    if n and len(with_results) / n >= 0.8:
        items.append({
            "label": "Search returns products",
            "text": f"for {len(with_results)} of {n} tested searches — dead ends are the exception.",
        })
    near = [j for j in sc if not is_pass(j) and j.results and 1 <= j.displacement <= 2]
    if near:
        ex = ", ".join(f"“{j.test_query.query}”" for j in near[:3])
        word = "search" if len(near) == 1 else "searches"
        items.append({
            "label": "Close to correct",
            "text": f"on {len(near)} {word} ({ex}): the best match was at #2 or #3, just not at #1.",
        })
    typos = by_cat.get("TYPO", [])
    recognised = [j for j in typos if is_pass(j) or (j.results and mode(j) in RANKING_MODES)]
    if typos and recognised and len(recognised) / len(typos) >= 0.5:
        items.append({
            "label": "Misspellings are often recognised",
            "text": f"— {len(recognised)} of {len(typos)} typo searches still reached the right products.",
        })
    return items


# ---------------------------------------------------------------------------
# Aggregate stats
# ---------------------------------------------------------------------------


def compute_stats(judgments: list[QueryJudgment], nav_categories: list[str] | None = None) -> dict:
    """Every KPI in the report, over SCORED judgments only. Raw numbers; format with fmt_*."""
    sc = scored(judgments)
    ex = excluded(judgments)
    n = len(sc)
    counts = severity_counts(sc)
    with_results = [j for j in sc if j.results]
    nres = len(with_results)
    failing = [j for j in sc if not is_pass(j)]

    zero_fail = [j for j in failing if not j.results]
    found_but_wrong = [j for j in failing if j.results]
    top1_bad = [j for j in found_but_wrong if top_result(j).relevance_score < TOP1_IRRELEVANT_BELOW]

    # A junk page (nothing relevant anywhere) has no "best match" position to celebrate: its
    # top item sitting at #1 must not count as a relevant result in the top 3.
    relevant_sets = [j for j in with_results if j.max_relevance_score >= TOP1_IRRELEVANT_BELOW]
    top3_hit = sum(1 for j in relevant_sets if j.displacement <= 2)
    top3_miss = nres - top3_hit
    avg_best = (sum(j.displacement + 1 for j in relevant_sets) / len(relevant_sets)) if relevant_sets else 0.0

    # Worst zero-result example: only one with proof may carry a "you carry it" claim.
    zero_critical = [j for j in zero_fail if sev(j) == Severity.CRITICAL.value]
    worst_zero, worst_zero_proof = None, None
    for j in zero_critical:
        proof = proof_of_stock(j, sc)
        if proof:
            worst_zero, worst_zero_proof = j, proof
            break
    if worst_zero is None and zero_critical:
        worst_zero = zero_critical[0]

    weak_top1 = [j for j in top1_bad]
    worst_rank = max(weak_top1, key=lambda j: j.displacement) if weak_top1 else None

    mode_counts = Counter(mode(j) for j in failing)
    return {
        "total_tested": len(judgments),
        "total_queries": n,
        "excluded_count": len(ex),
        "excluded_by_reason": dict(Counter(j.excluded_reason for j in ex)),
        "critical_count": counts["critical"],
        "moderate_count": counts["moderate"],
        "minor_count": counts["minor"],
        "pass_count": counts["passed"],
        "friction_count": counts["moderate"] + counts["minor"],
        "pct_critical": pct(counts["critical"], n),
        "zero_result_count": len(zero_fail),
        "pct_zero_result": pct(len(zero_fail), n),
        "empty_page_count": sum(1 for j in sc if not j.results),
        "found_but_wrong_count": len(found_but_wrong),
        "pct_found_but_wrong": pct(len(found_but_wrong), n),
        "with_results_count": nres,
        "avg_best_position": avg_best,
        "pct_top3_irrelevant": pct(top3_miss, nres),
        "pct_top3_relevant_all": pct(top3_hit, n),
        "pct_top1_irrelevant": pct(len(top1_bad), nres),
        "no_relevant_first_count": len(zero_fail) + len(top1_bad),
        "pct_no_relevant_first": pct(len(zero_fail) + len(top1_bad), n),
        "failure_mode_counts": [
            {"mode": m, "label": FAILURE_MODE_DISPLAY.get(m, m), "count": c} for m, c in mode_counts.most_common()
        ],
        "zero_result_causes": zero_result_causes(sc),
        "num_categories": len({category(j) for j in sc}),
        "worst_zero_query": worst_zero.test_query.query if worst_zero else "",
        "worst_zero_proof": worst_zero_proof,
        "worst_example_query": worst_rank.test_query.query if worst_rank else "",
        "worst_example_displacement": worst_rank.displacement if worst_rank else 0,
        "worst_example": pick_worst_example(sc, nav_categories),
    }


def formatted_stats(stats: dict) -> dict[str, str]:
    """The exact strings both renderers print for the headline figures."""
    return {
        "pct_critical": fmt_pct(stats["pct_critical"]),
        "pct_zero_result": fmt_pct(stats["pct_zero_result"]),
        "pct_found_but_wrong": fmt_pct(stats["pct_found_but_wrong"]),
        "pct_no_relevant_first": fmt_pct(stats["pct_no_relevant_first"]),
        "pct_top3_irrelevant": fmt_pct(stats["pct_top3_irrelevant"]),
        "pct_top3_relevant_all": fmt_pct(stats["pct_top3_relevant_all"]),
        "pct_top1_irrelevant": fmt_pct(stats["pct_top1_irrelevant"]),
        "avg_best_position": fmt_pos(stats["avg_best_position"]),
        "critical_of_total": f"{stats['critical_count']} of {stats['total_queries']}",
        "zero_of_total": f"{stats['zero_result_count']} of {stats['total_queries']}",
        "found_wrong_of_total": f"{stats['found_but_wrong_count']} of {stats['total_queries']}",
    }


def position_context(avg_best: float) -> str:
    """Wording for the average best position that stays true for any value."""
    if avg_best <= 1.5:
        return "usually at or near the top"
    if avg_best <= 3:
        return "within the first three results most shoppers look at"
    return "past the first three results most shoppers look at"


def scope_line(stats: dict, audit_date: str, locale: str) -> str:
    parts = [f"{stats['total_tested']} searches tested"]
    if stats["excluded_count"]:
        parts[0] += f" ({stats['total_queries']} scored)"
    if audit_date:
        parts.append(audit_date)
    if locale:
        parts.append(locale)
    parts.append("desktop")
    return " · ".join(parts)


# ---------------------------------------------------------------------------
# Shared result-list selections
# ---------------------------------------------------------------------------

_BETTER_MATCH_MODES = {"POOR_RANKING", "PARTIAL_KEYWORD_MATCH", "DUPLICATE_FLOODING", "BRAND_BLEED"}


def show_better_matches(j: QueryJudgment) -> bool:
    """Whether a "Should have seen" list is honest for this judgment: results exist, a clearly
    on-topic product sat below #1, and the failure is about ordering, not the wrong products."""
    if not j.results or j.displacement <= 0 or mode(j) not in _BETTER_MATCH_MODES:
        return False
    best = best_result(j)
    return best is not None and best.relevance_score >= NAMEABLE_BEST_MIN


def better_matches(j: QueryJudgment, k: int = 3) -> list:
    """Top-k results by strength (selection only), for the "Should have seen" list."""
    if not show_better_matches(j):
        return []
    return sorted(j.results, key=lambda r: r.relevance_score, reverse=True)[:k]


# ---------------------------------------------------------------------------
# Benchmarks — our own targets plus an optional, labelled peer benchmark
# ---------------------------------------------------------------------------

BENCHMARK_NOTE = (
    "Targets are the levels Find Sherpas aims for in client work, not published industry "
    "averages."
)


def benchmark_rows(stats: dict, peer_benchmark: dict | None = None) -> list[dict]:
    """Rows for the comparison table. ``peer_benchmark`` (optional) =
    {"label": str, "sample_size": int, "values": {stat_key: float}} — rendered only when given."""
    peer_vals = (peer_benchmark or {}).get("values") or {}

    def peer(key: str, fmt) -> str | None:
        v = peer_vals.get(key)
        return fmt(float(v)) if v is not None else None

    dead = stats["pct_no_relevant_first"]
    top3 = stats["pct_top3_relevant_all"]
    avg = stats["avg_best_position"]
    top1 = stats["pct_top1_irrelevant"]
    return [
        {"metric": "Searches where the shopper wasn't shown a relevant result first (all searches)",
         "your_score": fmt_pct(dead), "target": "under 10%", "peer": peer("pct_no_relevant_first", fmt_pct),
         "score_class": "below" if dead > 10 else "meets"},
        {"metric": "Relevant result in the top 3 (all searches)",
         "your_score": fmt_pct(top3), "target": "80% or more", "peer": peer("pct_top3_relevant_all", fmt_pct),
         "score_class": "below" if top3 < 80 else "meets"},
        {"metric": "Average best result position (searches that returned products)",
         "your_score": fmt_pos(avg), "target": "#1–2", "peer": peer("avg_best_position", fmt_pos),
         "score_class": "below" if avg > 2 else "meets"},
        {"metric": "Irrelevant #1 result (searches that returned products)",
         "your_score": fmt_pct(top1), "target": "under 10%", "peer": peer("pct_top1_irrelevant", fmt_pct),
         "score_class": "below" if top1 > 10 else "meets"},
    ]


def peer_label(peer_benchmark: dict | None) -> str:
    if not peer_benchmark:
        return ""
    label = peer_benchmark.get("label") or "Peer sites"
    n = peer_benchmark.get("sample_size")
    return f"{label} (n={n})" if n else label
