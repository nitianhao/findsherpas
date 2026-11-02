"""Render an AuditReport into a branded HTML file using the Jinja2 template."""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import mimetypes
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from src.advanced_diagnostics import build_advanced_diagnostics_sections
from src.models import (
    AuditReport,
    QueryJudgment,
    Severity,
)
from src.report_generator import audit_date_text, report_content, roadmap_reach_text
from src.report_stats import (
    BENCHMARK_NOTE,
    CAPABILITY_NAMES as _CAPABILITY_NAMES,
    CATEGORY_DISPLAY as _CATEGORY_DISPLAY,
    EXCLUDED_REASON_TEXT,
    FAILURE_MODE_DISPLAY as _FAILURE_MODE_DISPLAY,
    FOUND_BUT_WRONG_LABEL,
    SAMPLE_NOTE,
    SEVERITY_RANK as _SEVERITY_RANK,
    SEVERITY_SHORT as _SEVERITY_SHORT,
    ZERO_RESULT_FOOTNOTE,
    ZERO_RESULT_LABEL,
    benchmark_rows,
    better_matches,
    build_capability_scores,
    by_original,
    capability_rows,
    client_observation,
    compute_stats,
    whats_working_items,
    excluded,
    formatted_stats,
    peer_label,
    root_causes,
    sanitize_client_text,
    scope_line,
    scored,
    search_url,
)

logger = logging.getLogger(__name__)

# Rendered HTML must stay under GitHub's 1 MB contents-API limit, with headroom.
HTML_SIZE_BUDGET = 900_000
# Cover screenshot re-encode: wide enough for a sharp cover, small enough for the budget.
_COVER_MAX_WIDTH = 1400
_COVER_QUALITY = 80
_COVER_MAX_BYTES = 350_000

# ISO-639-1 codes for the language of queries/titles (the report prose itself is English).
_LANG_CODES = {
    "english": "en", "german": "de", "swedish": "sv", "danish": "da", "norwegian": "no",
    "finnish": "fi", "french": "fr", "dutch": "nl", "italian": "it", "spanish": "es",
    "polish": "pl", "czech": "cs", "slovak": "sk", "portuguese": "pt", "hungarian": "hu",
    "romanian": "ro", "greek": "el", "turkish": "tr", "arabic": "ar", "hebrew": "he",
    "japanese": "ja", "chinese": "zh", "korean": "ko", "lithuanian": "lt", "latvian": "lv",
    "estonian": "et", "croatian": "hr", "slovenian": "sl", "bulgarian": "bg", "ukrainian": "uk",
}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_DIR = _PROJECT_ROOT / "templates"
_ASSETS_DIR = _PROJECT_ROOT / "assets"


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

def _severity_class(severity_value: str) -> str:
    """Map a Severity enum .value to a CSS class name."""
    short = _SEVERITY_SHORT.get(severity_value, "")
    return short.lower()  # "critical", "moderate", "minor", "pass"


def _severity_short(severity_value: str) -> str:
    return _SEVERITY_SHORT.get(severity_value, severity_value)


# ---------------------------------------------------------------------------
# Data builders
# ---------------------------------------------------------------------------

def _build_stats(report: AuditReport, judgments: list[QueryJudgment]) -> dict:
    """The shared stats (src.report_stats) plus the exact strings the template prints."""
    raw = compute_stats(judgments, report.site_context.nav_categories)
    return {**raw, "fmt": formatted_stats(raw)}


_TITLE_STOPWORDS = {
    "and", "or", "the", "with", "for", "in", "on", "by", "to", "of",
    "not", "without", "under", "over", "best", "sellers", "active",
    "inch", "inches",
}

_TITLE_GENERIC_PRODUCT_TERMS = {
    "shoe", "shoes", "sneaker", "sneakers", "short", "shorts", "shirt", "shirts",
    "pant", "pants", "chino", "chinos", "dress", "dresses", "jacket", "jackets",
    "boot", "boots", "bag", "bags", "backpack", "backpacks", "deal", "deals",
    "restaurant", "restaurants", "spa", "massage", "fitness", "class", "classes",
}


def _join_title_themes(themes: list[str]) -> str:
    if len(themes) == 1:
        return themes[0]
    if len(themes) == 2:
        return f"{themes[0]} and {themes[1]}"
    return f"{', '.join(themes[:-1])}, and {themes[-1]}"


def _build_title_themes(judgments: list[QueryJudgment]) -> list[str]:
    """Create a compact, client-specific title from the actual failing query patterns."""
    failing = [
        j for j in judgments
        if j.severity in {Severity.CRITICAL.value, Severity.MODERATE.value}
    ]
    failing.sort(key=lambda j: (_SEVERITY_RANK.get(j.severity, 0), j.displacement), reverse=True)

    themes: list[str] = []

    def add(theme: str) -> None:
        if theme and theme not in themes and len(themes) < 3:
            themes.append(theme)

    for j in failing:
        query = j.test_query.query.strip()
        if j.failure_mode == "CATEGORY_MAPPING_FAILURE" and len(query.split()) <= 3:
            add(query.lower())
            break

    if any(
        j.failure_mode in {"BRAND_BLEED", "NO_FUZZY_MATCHING"}
        or j.test_query.category == "BRAND_SEARCH"
        for j in failing
    ):
        add("brand")

    product_tokens: Counter[str] = Counter()
    for j in failing:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", j.test_query.query.lower()):
            if token in _TITLE_STOPWORDS or len(token) < 4:
                continue
            if token in _TITLE_GENERIC_PRODUCT_TERMS:
                product_tokens[token] += 1

    for token, _count in product_tokens.most_common():
        add(token)
        if len(themes) >= 3:
            break

    if len(themes) < 3 and any(j.failure_mode == "NO_SEMANTIC_UNDERSTANDING" for j in failing):
        add("shopping context")

    if len(themes) < 3 and any(
        j.failure_mode in {"CONSTRAINT_DROPPED", "FACET_NOT_EXTRACTED", "BRAND_BLEED"}
        for j in failing
    ):
        add("attribute filters")

    if not themes and any(j.failure_mode == "POOR_RANKING" for j in failing):
        add("ranking")

    return themes


def _build_report_title(site_name: str, stats: dict) -> str:
    if stats["critical_count"] > 0:
        return (
            f"{stats['total_queries']} {site_name} Searches. "
            f"{stats['critical_count']} That Fail the Shopper."
        )
    if stats["friction_count"] > 0:
        return (
            f"{stats['total_queries']} {site_name} Searches. "
            f"{stats['friction_count']} Friction Points."
        )
    return f"How {site_name} search holds up under real customer queries"


def _build_report_subtitle(site_name: str) -> str:
    return (
        f"An independent audit of how {site_name} search handles product names, "
        "brands, filters, and shopper intent."
    )


def _build_short_version(site_name: str, stats: dict, roadmap_items: list[dict]) -> dict:
    n, crit, friction = stats["total_queries"], stats["critical_count"], stats["friction_count"]
    if crit:
        risk = (
            f"This report focuses on the {crit} {'search' if crit == 1 else 'searches'} where a shopper "
            "likely hits a dead end: no usable result, an off-topic first result, a dropped constraint, "
            "or the right product buried too far down."
        )
    elif friction:
        risk = (
            f"No tested search failed outright. This report focuses on the {friction} "
            f"{'search' if friction == 1 else 'searches'} where the shopper still has to work too hard."
        )
    else:
        risk = "Every scored search returned a relevant result first."
    return {
        "intro": (
            f"We tested {n} realistic customer searches against {site_name}'s search, live on site. The "
            "audit checks whether shoppers see a relevant top result, not just whether the search returns "
            "something."
        ),
        "risk": risk,
        "fix": _build_short_version_fix(roadmap_items),
    }


def _build_short_version_fix(roadmap_items: list[dict]) -> str:
    """The headline 'first fix to ship' line: the top roadmap item's TITLE only ("" if none)."""
    if roadmap_items:
        title = " ".join((roadmap_items[0].get("title") or "").split()).rstrip(".")
        if title:
            return f"The first fix to ship: {title}."
    return ""


def _coverage_class(critical: int, moderate: int, minor: int) -> str:
    if critical:
        return "hm-gap"
    if moderate:
        return "hm-mixed"
    if minor:
        return "hm-developing"
    return "hm-good"


_CATEGORY_EXPLANATIONS: dict[str, str] = {
    "DIRECT_MATCH": "Can customers find an exact product when they already know the name?",
    "BROAD_CATEGORY": "Does search understand high-level shopping terms and collection-style queries?",
    "CATEGORY_MAPPING": "Can colloquial customer language map to the site's actual merchandising categories?",
    "TYPO": "Does search recover when brand or product terms are misspelled?",
    "PARTIAL_QUERY": "Do incomplete typed-ahead queries surface plausible products before the full term is entered?",
    "SYNONYM": "Does search connect customer vocabulary to the store's preferred product wording?",
    "NATURAL_LANGUAGE": "Can longer, conversational needs be translated into product intent?",
    "BRAND_SEARCH": "Are brand requests recognized and protected from unrelated results?",
    "FACET_EXTRACTION": "Are structured attributes like material, size, or product feature extracted from text?",
    "NEGATIVE_INTENT": "Can the engine respect exclusions such as 'not', 'without', or 'no'?",
    "PRICE_ANCHORED": "Can price constraints be recognized and used as a ranking or filtering signal?",
    "MULTI_ATTRIBUTE": "Can search keep multiple requirements active at the same time?",
    "PLURAL_SINGULAR": "Does search normalize simple wording variants such as singular and plural terms?",
    "SUBJECTIVE_ATTRIBUTE": "Can descriptive shopping language like premium, casual, or comfortable be mapped sensibly?",
    "SEASONAL_OCCASION": "Can seasonal or occasion-based needs map to relevant categories and products?",
}


_CATEGORY_REMEDIES: dict[str, str] = {
    "DIRECT_MATCH": "Protect exact product-title matches and verify they are not outranked by broader keyword matches.",
    "BROAD_CATEGORY": "Map common retail terms to collections, category pages, and merchandising rules.",
    "CATEGORY_MAPPING": "Create a synonym layer between customer phrases and internal taxonomy labels.",
    "TYPO": "Add fuzzy matching for high-value brands, product names, and common category terms.",
    "PARTIAL_QUERY": "Tune prefix matching and autocomplete-backed retrieval for short or incomplete terms.",
    "SYNONYM": "Expand synonym dictionaries and semantic embeddings for the product language customers actually use.",
    "NATURAL_LANGUAGE": "Extract intent phrases from longer queries before ranking products.",
    "BRAND_SEARCH": "Detect brand entities and boost or filter to products from the requested brand.",
    "FACET_EXTRACTION": "Parse attributes into structured facets, then enforce them in ranking or filtering.",
    "NEGATIVE_INTENT": "Add exclusion handling so banned terms reduce or remove matching products.",
    "PRICE_ANCHORED": "Parse numeric price limits and connect them to product price metadata.",
    "MULTI_ATTRIBUTE": "Score each constraint independently so one matched term does not drown out the rest.",
    "PLURAL_SINGULAR": "Normalize singular, plural, and close inflection variants before retrieval.",
    "SUBJECTIVE_ATTRIBUTE": "Connect subjective descriptors to curated tags, product copy, and merchandising attributes.",
    "SEASONAL_OCCASION": "Add occasion and season tags, then use them as ranking signals for broad needs.",
}


_CATEGORY_SIGNAL_LABELS: dict[str, str] = {
    "DIRECT_MATCH": "Exact-match polish",
    "BROAD_CATEGORY": "Collection routing",
    "CATEGORY_MAPPING": "Taxonomy mapping",
    "TYPO": "Typo recovery",
    "PARTIAL_QUERY": "Autocomplete intent",
    "SYNONYM": "Vocabulary mapping",
    "NATURAL_LANGUAGE": "Intent translation",
    "BRAND_SEARCH": "Brand protection",
    "FACET_EXTRACTION": "Attribute parsing",
    "NEGATIVE_INTENT": "Exclusion handling",
    "PRICE_ANCHORED": "Price parsing",
    "MULTI_ATTRIBUTE": "Constraint stacking",
    "PLURAL_SINGULAR": "Term normalization",
    "SUBJECTIVE_ATTRIBUTE": "Merchandising language",
    "SEASONAL_OCCASION": "Occasion matching",
}


def _coverage_status(category: str, critical: int, moderate: int, minor: int) -> str:
    if critical or moderate or minor:
        return _CATEGORY_SIGNAL_LABELS.get(category, "Pattern tuning")
    return "Stable in sample"


def _coverage_signal_summary(critical: int, moderate: int, minor: int, passed: int, total: int) -> str:
    parts = []
    if critical:
        parts.append(f"{critical} visible miss{'es' if critical != 1 else ''}")
    if moderate:
        parts.append(f"{moderate} friction point{'s' if moderate != 1 else ''}")
    if minor:
        parts.append(f"{minor} polish note{'s' if minor != 1 else ''}")
    if passed:
        parts.append(f"{passed} stable result{'s' if passed != 1 else ''}")
    if not parts:
        parts.append("no issues detected")
    return f"{total} probes reviewed: {', '.join(parts)}."


def _coverage_signal_note(critical: int, moderate: int, minor: int, total: int) -> str:
    # Reflect the actual number of failing probes (not a flat "at least one…"), so the line
    # varies per row and reads specifically. Lead with the most severe issue present.
    if critical:
        misses = "a shopper-visible miss" if critical == 1 else "shopper-visible misses"
        return f"{critical} of {total} probes returned {misses}; the clearest case is below."
    if moderate:
        return (
            f"{moderate} of {total} probes surfaced relevant products but not cleanly — "
            f"friction the shopper would feel; the clearest case is below."
        )
    if minor:
        verb = "needs" if minor == 1 else "need"
        return f"{minor} of {total} probes {verb} only ranking polish; retrieval itself is fine."
    return "No immediate tuning signal appeared in this sample."


def _trim_evidence(text: str, limit: int = 200) -> str:
    """Collapse whitespace and trim free-text evidence to a self-contained observation.

    The snippet must never read as cut off mid-sentence. We end on the fullest
    natural boundary that still fits within ``limit`` — sentence breaks are
    preferred over clause breaks, and we take the *last* qualifying boundary so
    the fragment carries as much of the observation as possible. Only when no
    boundary exists at all do we fall back to a hard word-boundary cut with an
    ellipsis.

    Note: figures like "0.621" contain a period but no following space, so a
    boundary requires the trailing space — this prevents cutting inside a score.
    """
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned

    # Prefer the last sentence break within the limit; fall back to the last
    # clause break. rfind requires the trailing space so decimals never match.
    for markers in ((". ", "; "), (", ", ": ")):
        cut = max((cleaned.rfind(m, 0, limit + 1) for m in markers), default=-1)
        if cut > 0:
            fragment = cleaned[:cut].rstrip(" ,;:")
            if fragment.endswith((".", "!", "?")):
                return fragment
            return fragment + "."

    return cleaned[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


_FRICTION_SIGNAL = re.compile(
    r"(#\s*\d+|\brank\b|\bposition\b|buried|shown first|displaced|duplicate|copies|"
    r"wasting|not even|zero result|no result|returned no|irrelevant|\bnothing\b|\bempty\b)",
    re.I,
)
_REASSURANCE_SIGNAL = re.compile(
    r"(fully satisfied|on[- ]topic|legitimate|correctly mapped|right department|never saw|all 15)",
    re.I,
)


def _friction_fragment(evidence: str, limit: int = 220) -> str:
    """Return the sentence(s) of the judge's evidence that describe the actual friction.

    A downgraded ranking judgment frequently opens with a reassurance or a setup
    line ("All 15 results are on-topic …", "The query should surface … first") and
    only later states the concrete problem ("the customer saw a hand wash at #1 …",
    "three copies … wasting page real estate"). Showcasing the preamble under a card
    that claims friction is self-contradictory. So skip to the first sentence that
    concretely describes the miss (a rank/position, a buried/duplicate/irrelevant
    signal), optionally include the next concrete sentence, and strip any leading
    "However,/but" reassurance clause. Returns "" when the evidence has no concrete
    friction sentence, so the caller can synthesise an honest line.
    """
    ev = " ".join((evidence or "").split())
    if not ev:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", ev)
    start = next((i for i, s in enumerate(sentences) if _FRICTION_SIGNAL.search(s)), None)
    if start is None:
        return ""
    frag = sentences[start]
    if (
        start + 1 < len(sentences)
        and len(frag) < limit - 40
        and _FRICTION_SIGNAL.search(sentences[start + 1])
    ):
        frag = frag + " " + sentences[start + 1]
    # Strip a leading reassurance clause within the fragment ("…, however <problem>").
    for marker in ("However, ", "However ", " but ", "But "):
        idx = frag.find(marker)
        if idx > 0 and _REASSURANCE_SIGNAL.search(frag[:idx]):
            frag = frag[idx:].lstrip()
            break
    # Drop a leading bare "However," so the fragment reads as a standalone statement.
    frag = re.sub(r"^However,?\s+", "", frag)
    if frag:
        frag = frag[0].upper() + frag[1:]
    return _trim_evidence(frag, limit)


def _coverage_example(matching: list[QueryJudgment]) -> dict | None:
    """Pick the single most illustrative failing probe in a calibration row.

    Worst-first by GENUINE customer-visible weakness: highest severity, then the
    weakest results actually shown to the shopper (lowest top-3 average relevance),
    then lowest peak relevance. We deliberately do NOT rank by positional
    displacement — for broad/generic queries a large displacement among all-relevant
    results is reranker-scoring noise (the discredited metric that used to surface a
    "best item buried at #13" probe whose results were actually fine). Returns the
    real query string plus a one-line observation focused on the friction, or None
    when nothing in the row failed.
    """
    failing = [j for j in matching if j.severity != Severity.PASS.value]
    if not failing:
        return None

    worst = max(
        failing,
        key=lambda j: (
            _SEVERITY_RANK.get(j.severity, 0),
            -j.top3_original_average,
            -j.max_relevance_score,
        ),
    )

    detail = _friction_fragment(sanitize_client_text(worst.evidence))
    if not detail:
        # No concrete friction sentence in the evidence — synthesise an honest line
        # from structured data rather than echoing a reassurance/setup preamble.
        if worst.severity != Severity.CRITICAL.value and worst.displacement:
            detail = (
                f'Relevant results appear, but the strongest match sits at position '
                f'{worst.displacement + 1} instead of near the top.'
            )
        else:
            mode = _FAILURE_MODE_DISPLAY.get(worst.failure_mode, worst.failure_mode)
            detail = f"{mode}."

    return {"query": worst.test_query.query, "detail": detail}


def _build_coverage_summary(judgments: list[QueryJudgment]) -> dict:
    cap_scores = build_capability_scores(judgments)
    items = []

    for cs in cap_scores:
        categories = []
        for judgment in cs.judgments:
            if judgment.test_query.category not in categories:
                categories.append(judgment.test_query.category)

        for category in categories:
            matching = [
                j for j in cs.judgments
                if j.test_query.category == category
            ]

            passed = sum(1 for j in matching if j.severity == Severity.PASS.value)
            minor = sum(1 for j in matching if j.severity == Severity.MINOR.value)
            moderate = sum(1 for j in matching if j.severity == Severity.MODERATE.value)
            critical = sum(1 for j in matching if j.severity == Severity.CRITICAL.value)
            total = len(matching)
            pass_rate = (passed / total) * 100
            items.append({
                "capability": _CAPABILITY_NAMES.get(cs.capability, cs.capability),
                "query_type": _CATEGORY_DISPLAY.get(category, category),
                # Stable rows (no issues) shouldn't pose the diagnostic question or a "next
                # tuning move" — there's nothing to tune. The template gates both on this.
                "has_issue": (critical + moderate + minor) > 0,
                "meaning": _CATEGORY_EXPLANATIONS.get(
                    category,
                    "This probe checks whether search handles this customer query pattern predictably.",
                ),
                "remedy": _CATEGORY_REMEDIES.get(
                    category,
                    "Review the failed examples and add this pattern to the search relevance regression set.",
                ),
                "status": _coverage_status(category, critical, moderate, minor),
                "signal_summary": _coverage_signal_summary(critical, moderate, minor, passed, total),
                "signal_note": _coverage_signal_note(critical, moderate, minor, total),
                "example": _coverage_example(matching),
                "pass_rate": f"{pass_rate:.0f}",
                "passed": passed,
                "minor": minor,
                "moderate": moderate,
                "critical": critical,
                "total": total,
                "class": _coverage_class(critical, moderate, minor),
            })

    return {"coverage_items": items}


def _build_improvement_map(judgments: list[QueryJudgment]) -> list[dict]:
    """Capability overview as proportional severity bars. Same order and priority label as the
    markdown scorecard (report_stats.capability_rows)."""
    rows = []
    for r in capability_rows(judgments):
        parts = []
        if r["critical"]:
            parts.append(f"{r['critical']} critical")
        if r["moderate"]:
            parts.append(f"{r['moderate']} friction")
        if r["minor"]:
            parts.append(f"{r['minor']} minor")
        rows.append({
            "capability": r["capability"],
            "total": r["total"],
            "critical": r["critical"],
            "moderate": r["moderate"],
            "minor": r["minor"],
            "passed": r["passed"],
            "counts_label": " · ".join(parts) if parts else "no issues in sample",
            "clean_pct": round((r["passed"] / r["total"]) * 100) if r["total"] else 0,
            "top_issue": r["top_issue"],
            "headline": r["priority"],
            "headline_class": _PRIORITY_CLASS.get(r["severity"], "r-clean"),
        })
    return rows


_PRIORITY_CLASS = {
    Severity.CRITICAL.value: "r-critical",
    Severity.MODERATE.value: "r-moderate",
    Severity.MINOR.value: "r-minor",
    Severity.PASS.value: "r-clean",
}


def _fix_guidance(j: QueryJudgment) -> str:
    mode = j.failure_mode
    if mode == "ZERO_RESULTS_OR_GARBAGE":
        return "Add query rewriting, token splitting, and fallback matching for this query pattern so customers do not hit a dead end."
    if mode == "CATEGORY_MAPPING_FAILURE":
        return "Map this phrase to the intended product category and prioritize category-relevant products above adjacent or generic results."
    if mode == "NO_FUZZY_MATCHING":
        return "Add typo and fuzzy matching for high-value product, category, and brand terms so small spelling errors still reach the right products."
    if mode == "CONSTRAINT_DROPPED":
        return "Extract the constraint in the query and enforce it in ranking so brand, attribute, price, or use-case requirements are not ignored."
    if mode == "NO_SEMANTIC_UNDERSTANDING":
        return "Add synonym and semantic mappings for this customer phrasing so the engine recognizes the intended product need."
    if mode == "BRAND_BLEED":
        return "Separate brand intent from generic product intent and prevent unrelated brands from outranking the requested brand."
    if mode == "PARTIAL_KEYWORD_MATCH":
        return "Reduce over-weighting of partial keyword overlap and boost products that satisfy the full query intent."
    if mode == "FACET_NOT_EXTRACTED":
        return "Extract this as a structured facet and use it as a ranking/filtering signal instead of treating it as loose text."
    if mode == "POOR_RANKING":
        return "Boost the products that match the full intent of the query so the strongest matches appear first, especially when they are already in the result set."
    if mode == "DUPLICATE_FLOODING":
        return "Collapse colour/size variants of the same product into a single result card so each model takes one slot and more distinct products are visible."
    return "Tune retrieval and ranking for this query pattern, then re-test it as part of the priority regression set."


def _result_rows(results) -> list[dict]:
    return [{"rank": r.original_rank, "title": r.title, "price": r.price} for r in results]


def _query_ctx(j: QueryJudgment, template: str, narratives: dict[str, str]) -> dict:
    """Everything the template shows about one failing search. Text is client-safe: the reviewed
    narrative when there is one, else sanitised evidence — never raw evidence or internal notes."""
    shown = by_original(j)[:5]
    q = j.test_query.query
    return {
        "query": q,
        "url": search_url(template, q),
        "category": _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
        "severity_class": _severity_class(j.severity),
        "severity_short": _severity_short(j.severity),
        "failure_label": _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode),
        # A zero-result query has no positions — never show a phantom "#N".
        "no_results": not shown,
        "best_position": j.displacement + 1,
        "displacement": j.displacement,
        "text": narratives.get(q) or client_observation(j),
        "fix": _fix_guidance(j),
        "actual_top": _result_rows(shown),
        "ideal_top": _result_rows(better_matches(j)),
    }


def _narratives_by_query(content: dict) -> dict[str, str]:
    return {
        e["query"]: e["narrative"]
        for s in content.get("deep_dives") or []
        for e in s.get("examples", [])
        if e.get("narrative")
    }


def _build_risk_cases(judgments: list[QueryJudgment], template: str, narratives: dict[str, str]) -> list[dict]:
    failing = [j for j in judgments if j.severity != Severity.PASS.value]
    # Worst severity first, then genuine customer-visible weakness (weakest results shown).
    failing.sort(key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), j.top3_original_average, j.max_relevance_score))
    cases = []
    for j in failing[:6]:
        ctx = _query_ctx(j, template, narratives)
        if ctx["no_results"]:
            ctx["fail"] = "The search returned zero results — the customer reached a dead end."
        elif j.displacement <= 0:
            ctx["fail"] = "The first result shown wasn't what the shopper asked for."
        else:
            ctx["fail"] = f"The best matching result appeared at position #{j.displacement + 1}, after weaker results."
        cases.append(ctx)
    return cases


def _build_deep_dives(judgments: list[QueryJudgment], content: dict, template: str) -> list[dict]:
    """Deep dives for the HTML: the reviewed narratives stored on the report when present
    (same text as the .md), else a deterministic version built from sanitised evidence."""
    by_q = {j.test_query.query: j for j in judgments}
    narratives = _narratives_by_query(content)
    sections = content.get("deep_dives")
    caps = []
    if sections:
        for s in sections:
            queries = [_query_ctx(by_q[e["query"]], template, narratives)
                       for e in s.get("examples", []) if e.get("query") in by_q]
            caps.append({"capability_name": s.get("capability_name") or _CAPABILITY_NAMES.get(s.get("capability"), ""),
                         "intro": s.get("intro", ""), "queries": queries})
        return caps

    for cs in build_capability_scores(judgments):
        failing_js = [j for j in cs.judgments if j.severity != Severity.PASS.value]
        if not failing_js:
            continue
        failing_js.sort(key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), j.top3_original_average, j.max_relevance_score))
        caps.append({
            "capability_name": _CAPABILITY_NAMES.get(cs.capability, cs.capability),
            "intro": "",
            "queries": [_query_ctx(j, template, narratives) for j in failing_js[:5]],
        })
    return caps


def _build_roadmap(content: dict, judgments: list[QueryJudgment]) -> list[dict]:
    """Structured roadmap stored on the report. Missing = report predates grounded roadmaps:
    fail loudly instead of rendering placeholder text."""
    items = content.get("roadmap")
    if items is None:
        raise ValueError(
            "report has no structured roadmap (run_metadata['report_content']['roadmap']); "
            "regenerate it with src.report_generator.generate_report before rendering"
        )
    out = []
    for it in items:
        effort = it.get("effort", "")
        out.append({
            "title": it.get("title", ""),
            "description": it.get("description", ""),
            "impact": it.get("impact", ""),
            "effort": effort,
            "owner": {"merch": "Merchandising", "dev": "Development"}.get(it.get("owner"), ""),
            "reach": roadmap_reach_text(it, judgments),
            "impact_class": {"Critical": "critical", "High": "high"}.get(it.get("impact"), "moderate"),
            "effort_class": "medium" if "Medium" in effort else "major" if "Major" in effort else "quick",
        })
    return out


def _build_appendix(judgments: list[QueryJudgment], template: str) -> list[dict]:
    rows = []
    for j in sorted(judgments, key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement)):
        if j.severity == Severity.PASS.value:
            fm, best_pos = "—", 1
        else:
            fm = _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode)
            best_pos = j.displacement + 1 if j.results else None  # None renders as an em dash
        rows.append({
            "query": j.test_query.query,
            "url": search_url(template, j.test_query.query),
            "category": _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
            "severity_class": _severity_class(j.severity),
            "severity_short": _severity_short(j.severity),
            "best_position": best_pos,
            "failure_mode": fm,
        })
    return rows


def _build_not_scored(judgments: list[QueryJudgment], template: str) -> list[dict]:
    return [
        {"query": j.test_query.query, "url": search_url(template, j.test_query.query),
         "reason": EXCLUDED_REASON_TEXT.get(j.excluded_reason, "Left out of scoring.")}
        for j in excluded(judgments)
    ]


def _site_lang(site_context) -> str:
    locale = (getattr(site_context, "locale", "") or "").strip()
    if locale:
        return locale.replace("_", "-")
    return _LANG_CODES.get((site_context.primary_language or "").strip().lower(), "")


# ---------------------------------------------------------------------------
# Cover screenshot
# ---------------------------------------------------------------------------

def encode_cover_screenshot(path: str | Path) -> tuple[str, str] | None:
    """Downscale + recompress the cover screenshot for embedding. Returns (base64, mime).

    Max ``_COVER_MAX_WIDTH`` px wide, JPEG at ``_COVER_QUALITY``; quality steps down until the
    image is under ``_COVER_MAX_BYTES`` so the whole page stays under HTML_SIZE_BUDGET.
    """
    sp = Path(path)
    if not sp.exists():
        return None
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is a declared dependency of the venv
        logger.warning("Pillow not installed — embedding the cover screenshot uncompressed")
        mime = mimetypes.guess_type(sp.name)[0] or "image/png"
        return base64.b64encode(sp.read_bytes()).decode("ascii"), mime

    with Image.open(sp) as im:
        im = im.convert("RGB")
        if im.width > _COVER_MAX_WIDTH:
            im = im.resize((_COVER_MAX_WIDTH, round(im.height * _COVER_MAX_WIDTH / im.width)), Image.LANCZOS)
        data = b""
        for quality in (_COVER_QUALITY, 70, 60, 50, 40):
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
            data = buf.getvalue()
            if len(data) <= _COVER_MAX_BYTES:
                break
    return base64.b64encode(data).decode("ascii"), "image/jpeg"


def html_size_bytes(html: str) -> int:
    """Size of the rendered page as published (UTF-8). The publish gate compares it to
    HTML_SIZE_BUDGET."""
    return len(html.encode("utf-8"))


# ---------------------------------------------------------------------------
# Main rendering functions
# ---------------------------------------------------------------------------

def _load_logo_svg() -> str:
    logo_path = _ASSETS_DIR / "logo.svg"
    if logo_path.exists():
        return logo_path.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"Find Sherpas report branding is required, but logo.svg was not found at {logo_path}"
    )


def _build_query_cloud(report: AuditReport, limit: int = 26) -> list[dict]:
    """A representative, balanced subset of tested queries for a word-cloud display.

    Round-robins across query categories (so every intent type is represented),
    prefers shorter/punchier phrases, dedupes, then assigns a deterministic size
    tier per query — skewed so a few render large and most medium/small.
    """
    by_cat: dict[str, list[str]] = defaultdict(list)
    for q in report.queries:
        # strip surrounding/trailing ASCII quotes so the CSS quote marks don't double up
        text = (q.query or "").strip().strip('"').strip()
        if text:
            by_cat[q.category].append(text)

    # within each category: dedupe (case-insensitive), drop very long phrases, shortest first
    for cat, items in list(by_cat.items()):
        seen: set[str] = set()
        uniq: list[str] = []
        for s in sorted(items, key=len):
            key = s.lower()
            if key not in seen and len(s) <= 40:
                seen.add(key)
                uniq.append(s)
        by_cat[cat] = uniq

    # round-robin across categories for balanced coverage
    cats = [c for c in by_cat if by_cat[c]]
    picked: list[str] = []
    idx = 0
    while len(picked) < limit and any(by_cat[c] for c in cats):
        c = cats[idx % len(cats)]
        if by_cat[c]:
            picked.append(by_cat[c].pop(0))
        idx += 1

    def _tier(s: str) -> int:
        h = int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16) % 100
        if h < 8:
            return 5
        if h < 24:
            return 4
        if h < 56:
            return 3
        if h < 82:
            return 2
        return 1

    items = [{"text": s, "size": _tier(s)} for s in picked]
    # deterministic, organic order (not grouped by category)
    items.sort(key=lambda it: hashlib.md5(it["text"].encode("utf-8")).hexdigest())
    return items


def render_html_report(
    report: AuditReport,
    screenshot_path: str | Path | None = None,
    peer_benchmark: dict | None = None,
) -> str:
    """Render an AuditReport into a self-contained HTML string.

    Every figure comes from src.report_stats over SCORED judgments; excluded ones appear only in
    the "Not scored" list. All template variables are autoescaped; only the logo SVG (a trusted
    asset file) is marked safe.
    """
    all_judgments: list[QueryJudgment] = [j for cs in report.capability_scores for j in cs.judgments]
    if not all_judgments:
        return "<html><body><p>No audit data available.</p></body></html>"
    judgments = scored(all_judgments)
    ctx_site = report.site_context
    template_url = ctx_site.search_url_template
    site_name = ctx_site.site_name or ctx_site.url
    content = report_content(report)
    stats = _build_stats(report, all_judgments)
    roadmap_items = _build_roadmap(content, judgments)
    narratives = _narratives_by_query(content)
    peer = peer_benchmark or (report.run_metadata or {}).get("peer_benchmark")
    audit_date = audit_date_text(report.run_metadata)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("master_report.html")

    screenshot_b64, screenshot_mime = None, "image/jpeg"
    if screenshot_path:
        encoded = encode_cover_screenshot(screenshot_path)
        if encoded:
            screenshot_b64, screenshot_mime = encoded

    context = {
        "site_name": site_name,
        "site_lang": _site_lang(ctx_site),
        "report_title": _build_report_title(site_name, stats),
        "report_subtitle": _build_report_subtitle(site_name),
        "audit_date": audit_date,
        "scope_line": scope_line(stats, audit_date, getattr(ctx_site, "locale", "") or ctx_site.primary_language),
        "logo_svg": Markup(_load_logo_svg()),
        "screenshot_b64": screenshot_b64,
        "screenshot_mime": screenshot_mime,
        "query_cloud": _build_query_cloud(report),
        "stats": stats,
        "labels": {
            "zero_result": ZERO_RESULT_LABEL,
            "zero_result_footnote": ZERO_RESULT_FOOTNOTE,
            "found_but_wrong": FOUND_BUT_WRONG_LABEL,
            "sample_note": SAMPLE_NOTE,
            "benchmark_note": BENCHMARK_NOTE,
        },
        "short_version": _build_short_version(site_name, stats, roadmap_items),
        "coverage_summary": _build_coverage_summary(judgments),
        "improvement_map": _build_improvement_map(judgments),
        "root_causes": root_causes(judgments),
        "advanced_diagnostics": build_advanced_diagnostics_sections(ctx_site, judgments),
        "deep_dives": _build_deep_dives(judgments, content, template_url),
        "risk_cases": _build_risk_cases(judgments, template_url, narratives),
        "whats_working": whats_working_items(judgments),
        "roadmap_items": roadmap_items,
        "benchmarks": benchmark_rows(stats, peer),
        "peer_label": peer_label(peer),
        "appendix": _build_appendix(judgments, template_url),
        "not_scored": _build_not_scored(all_judgments, template_url),
    }
    return template.render(**context)


# Filename patterns a cover screenshot is conventionally saved under, in priority order
# (see REPORT_PLAYBOOK Phase 7: `reports/{slug}/{slug}_cover.png`).
_COVER_PATTERNS = (
    "*_cover.png", "*_cover.jpg", "*_cover.jpeg",
    "*cover*.png", "*cover*.jpg", "*cover*.jpeg",
    "*screenshot*.png", "*screenshot*.jpg", "*screenshot*.jpeg",
)


def find_cover_screenshot(directory: str | Path) -> Path | None:
    """Locate an existing cover screenshot in a report directory. Lets a rerender pick the
    cover back up automatically instead of silently dropping it when the caller forgets to
    pass screenshot_path."""
    d = Path(directory)
    if not d.is_dir():
        return None
    for pattern in _COVER_PATTERNS:
        hits = sorted(d.glob(pattern))
        if hits:
            return hits[0]
    return None


def save_html_report(report: AuditReport, output_path: str | Path, screenshot_path: str | Path | None = None) -> Path:
    """Render and save the HTML report to a file. Returns the output path.

    If no screenshot_path is given, auto-discovers a cover screenshot already sitting in the
    output directory so rerenders never silently lose the cover (REPORT_PLAYBOOK Phase 7)."""
    path = Path(output_path)
    if screenshot_path is None:
        screenshot_path = find_cover_screenshot(path.parent)
    html = render_html_report(report, screenshot_path=screenshot_path)
    size = html_size_bytes(html)
    if size > HTML_SIZE_BUDGET:
        print(
            f"[html_renderer] WARNING: '{path.name}' is {size / 1e6:.2f} MB, over the "
            f"{HTML_SIZE_BUDGET / 1e6:.1f} MB budget (GitHub's contents API rejects files over 1 MB).",
            file=sys.stderr,
        )
    if "cover-screenshot" not in html:
        print(
            f"[html_renderer] WARNING: '{path.name}' was saved WITHOUT a cover screenshot. "
            f"Capture the live search page into '{path.parent}/{path.stem.replace('_report', '')}_cover.png' "
            "and re-save (see REPORT_PLAYBOOK Phase 7).",
            file=sys.stderr,
        )
    path.write_text(html, encoding="utf-8")
    return path
