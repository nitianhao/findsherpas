"""Render an AuditReport into a branded HTML file using the Jinja2 template."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.advanced_diagnostics import build_advanced_diagnostics_sections
from src.models import (
    AuditReport,
    QueryJudgment,
    Severity,
)
from src.report_generator import (
    PIPELINE_NAME,
    _CAPABILITY_NAMES,
    _CATEGORY_DISPLAY,
    _CATEGORY_TO_CAPABILITY,
    _FAILURE_MODE_DISPLAY,
    _SEVERITY_RANK,
    _SEVERITY_SHORT,
    build_capability_scores,
    compute_aggregate_stats,
)

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


def _priority_label(severity_value: str) -> str:
    return {
        Severity.CRITICAL.value: "Focus area",
        Severity.MODERATE.value: "Watch",
        Severity.MINOR.value: "Fine-tune",
        Severity.PASS.value: "Working well",
    }.get(severity_value, _severity_short(severity_value))


# ---------------------------------------------------------------------------
# Data builders
# ---------------------------------------------------------------------------

def _build_stats(report: AuditReport, judgments: list[QueryJudgment]) -> dict:
    raw = compute_aggregate_stats(judgments)
    cap_scores = build_capability_scores(judgments)
    total_cap = len(cap_scores)
    pass_cap = sum(1 for cs in cap_scores if cs.severity == Severity.PASS.value)
    num_categories = len({j.test_query.category for j in judgments})

    poor_ranking_count = sum(1 for j in judgments if j.failure_mode == "POOR_RANKING")
    pct_retrieval = (poor_ranking_count / raw["total_queries"] * 100) if raw["total_queries"] else 0
    critical_count = raw["critical_count"]
    friction_count = raw["moderate_count"] + raw["minor_count"]
    working_count = raw["pass_count"]
    risk_pct = (critical_count / raw["total_queries"] * 100) if raw["total_queries"] else 0

    avg_pos = raw["avg_best_position"]
    pct_top3 = raw["pct_top3_irrelevant"]
    pct_top1 = raw["pct_top1_irrelevant"]

    return {
        "total_capabilities": total_cap,
        "pass_count": pass_cap,
        "total_queries": raw["total_queries"],
        "critical_count": critical_count,
        "moderate_count": raw["moderate_count"],
        "minor_count": raw["minor_count"],
        "pass_count_queries": raw["pass_count"],
        "friction_count": friction_count,
        "working_count": working_count,
        "risk_pct": f"{risk_pct:.0f}",
        "risk_pct_num": risk_pct,
        "avg_best_position": f"{avg_pos:.0f}",
        "avg_best_position_num": avg_pos,
        "pct_top3_irrelevant": f"{pct_top3:.0f}",
        "pct_top3_irrelevant_num": pct_top3,
        "pct_top1_irrelevant": f"{pct_top1:.0f}",
        "pct_top1_irrelevant_num": pct_top1,
        "worst_query": raw["worst_example_query"],
        "worst_displacement": raw["worst_example_displacement"] + 1,
        "worst_example": raw.get("worst_example", ""),
        "pct_retrieval_ok": f"{pct_retrieval:.0f}",
        "retrieval_ok_count": poor_ranking_count,
        "num_categories": num_categories,
    }


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


def _build_report_title(site_name: str, stats: dict, judgments: list[QueryJudgment]) -> str:
    if stats["critical_count"] > 0:
        return (
            f"{stats['total_queries']} {site_name} Searches. "
            f"{stats['critical_count']} Revenue-Risk Moments."
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
    return {
        "intro": (
            f"We tested {stats['total_queries']} realistic customer queries against {site_name}'s search, "
            "live on site. The audit checks whether customers see a relevant top result, not just whether "
            "the search engine returns something."
        ),
        "risk": (
            f"This report focuses on the {stats['critical_count']} queries where a customer likely hits a dead end: "
            "an off-topic result, a missing interpretation, a dropped constraint, or a relevant product buried too far down."
        ),
        "fix": _build_short_version_fix(roadmap_items),
    }


def _build_short_version_fix(roadmap_items: list[dict]) -> str:
    """Derive the headline 'first fix to ship' line from the site's top roadmap item.

    Falls back to a generic recommendation only when no roadmap is available.
    """
    if roadmap_items:
        top = roadmap_items[0]
        title = " ".join((top.get("title") or "").split()).rstrip(".")
        description = " ".join((top.get("description") or "").split())
        if title and description:
            return f"The first fix to ship: {title} — {description}"
        if title:
            return f"The first fix to ship: {title}."
    return (
        "The first fix to ship: add an intent layer before ranking, so sale, bestseller, price, "
        "negative, and brand terms act as filters or boosts before generic keyword matches take over."
    )


def _coverage_class(critical: int, moderate: int, minor: int, pass_rate: float) -> str:
    if critical:
        return "hm-gap"
    if moderate:
        return "hm-mixed"
    if minor:
        return "hm-developing"
    if pass_rate >= 75:
        return "hm-good"
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


def _coverage_signal_note(critical: int, moderate: int, minor: int) -> str:
    if critical:
        return "At least one probe showed a shopper-visible miss. The example below is the clearest case."
    if moderate:
        return "The pattern works in places, but the experience is not consistently clean."
    if minor:
        return "The pattern mostly surfaces relevant products; the remaining work is ranking polish."
    return "No immediate tuning signal appeared in this sample."


_SEVERITY_RANK: dict[str, int] = {
    Severity.CRITICAL.value: 3,
    Severity.MODERATE.value: 2,
    Severity.MINOR.value: 1,
    Severity.PASS.value: 0,
}


def _trim_evidence(text: str, limit: int = 160) -> str:
    """Collapse whitespace and trim free-text evidence to a single short observation."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    # Prefer cutting at the first sentence boundary when it yields a usable line.
    for end in (". ", "; "):
        idx = cleaned.find(end)
        if 0 < idx <= limit:
            return cleaned[: idx + 1].strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _coverage_example(matching: list[QueryJudgment]) -> dict | None:
    """Pick the single most illustrative failing probe in a calibration row.

    Worst-first: highest severity, then most buried best match, then lowest peak
    relevance. Returns the real query string plus a one-line observation, or None
    when nothing in the row failed.
    """
    failing = [j for j in matching if j.severity != Severity.PASS.value]
    if not failing:
        return None

    worst = max(
        failing,
        key=lambda j: (
            _SEVERITY_RANK.get(j.severity, 0),
            j.displacement,
            -j.max_relevance_score,
        ),
    )

    detail = _trim_evidence(worst.evidence)
    if not detail:
        mode = _FAILURE_MODE_DISPLAY.get(worst.failure_mode, worst.failure_mode)
        if worst.displacement:
            detail = f"{mode}: best match buried at position {worst.displacement + 1}."
        else:
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
                "signal_note": _coverage_signal_note(critical, moderate, minor),
                "example": _coverage_example(matching),
                "pass_rate": f"{pass_rate:.0f}",
                "passed": passed,
                "minor": minor,
                "moderate": moderate,
                "critical": critical,
                "total": total,
                "class": _coverage_class(critical, moderate, minor, pass_rate),
            })

    return {"coverage_items": items}


def _build_capability_scores_ctx(judgments: list[QueryJudgment]) -> list[dict]:
    scores = build_capability_scores(judgments)
    return [
        {
            "capability_name": _CAPABILITY_NAMES.get(cs.capability, cs.capability),
            "severity_class": _severity_class(cs.severity),
            "priority_label": _priority_label(cs.severity),
            "summary": cs.summary,
        }
        for cs in scores
    ]


def _improvement_headline(critical: int, moderate: int, minor: int) -> tuple[str, str]:
    """The row's priority chip: the count that actually drives its ranking.

    Returns (label, css_class). Distinct per row (it's a count) and consistent
    with the sort, instead of a share-based grade that clumps every row together.
    """
    if critical:
        return f"{critical} at risk", "r-critical"
    if moderate:
        return f"{moderate} friction", "r-moderate"
    if minor:
        return f"{minor} to polish", "r-minor"
    return "clean", "r-clean"


def _build_improvement_map(judgments: list[QueryJudgment]) -> list[dict]:
    """Capability-level overview as proportional severity bars, most-urgent first."""
    rows = []
    for cs in build_capability_scores(judgments):
        critical = sum(1 for j in cs.judgments if j.severity == Severity.CRITICAL.value)
        moderate = sum(1 for j in cs.judgments if j.severity == Severity.MODERATE.value)
        minor = sum(1 for j in cs.judgments if j.severity == Severity.MINOR.value)
        passed = sum(1 for j in cs.judgments if j.severity == Severity.PASS.value)
        total = len(cs.judgments)

        # dominant failure mode among the non-passing probes
        fail_modes = Counter(
            _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode)
            for j in cs.judgments
            if j.severity != Severity.PASS.value
        )
        top_issue = fail_modes.most_common(1)[0][0] if fail_modes else ""

        # human-readable counts for the non-zero issue segments
        parts = []
        if critical:
            parts.append(f"{critical} critical")
        if moderate:
            parts.append(f"{moderate} friction")
        if minor:
            parts.append(f"{minor} minor")
        counts_label = " · ".join(parts) if parts else "no issues in sample"

        headline, headline_class = _improvement_headline(critical, moderate, minor)

        rows.append({
            "capability": _CAPABILITY_NAMES.get(cs.capability, cs.capability),
            "total": total,
            "critical": critical,
            "moderate": moderate,
            "minor": minor,
            "passed": passed,
            "counts_label": counts_label,
            "clean_pct": round((passed / total) * 100) if total else 0,
            "top_issue": top_issue,
            "headline": headline,
            "headline_class": headline_class,
        })

    rows.sort(
        key=lambda r: (r["critical"], r["moderate"], r["minor"], -r["passed"]),
        reverse=True,
    )
    return rows


def _build_failure_modes(judgments: list[QueryJudgment]) -> list[dict]:
    counts = Counter(
        j.failure_mode for j in judgments if j.severity != Severity.PASS.value
    )
    return [
        {"name": _FAILURE_MODE_DISPLAY.get(mode, mode), "count": count}
        for mode, count in counts.most_common()
    ]


def _build_critical_failures(judgments: list[QueryJudgment]) -> list[dict]:
    """Extract the 3-5 most severe query failures for the Critical Failure Examples section."""
    critical = [
        j for j in judgments if j.severity == Severity.CRITICAL.value
    ]
    # Sort by displacement descending (worst buried results first)
    critical.sort(key=lambda j: -j.displacement)
    top = critical[:5] if len(critical) >= 3 else sorted(
        [j for j in judgments if j.severity != Severity.PASS.value],
        key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
    )[:5]

    results = []
    for j in top:
        by_original = sorted(j.results, key=lambda r: r.original_rank)
        actual_top_title = by_original[0].title if by_original else "N/A"
        cap_name = _CAPABILITY_NAMES.get(
            _CATEGORY_TO_CAPABILITY.get(j.test_query.category, ""),
            _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
        )
        results.append({
            "query": j.test_query.query,
            "expected_intent": cap_name,
            "actual_result": actual_top_title,
            "explanation": j.evidence,
            "severity_class": _severity_class(j.severity),
            "severity_short": _severity_short(j.severity),
            "best_position": j.displacement + 1,
        })
    return results


def _score_class(score: float) -> str:
    if score >= 0.70:
        return "rel-good"
    if score >= 0.50:
        return "rel-warn"
    return "rel-bad"


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
        return "Re-rank returned products so the strongest intent matches appear first, especially when the right products already exist in the result set."
    return "Tune retrieval and ranking for this query pattern, then re-test it as part of the priority regression set."


def _build_risk_cases(judgments: list[QueryJudgment]) -> list[dict]:
    failing = [j for j in judgments if j.severity != Severity.PASS.value]
    sorted_js = sorted(
        failing,
        key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement, -j.max_relevance_score),
    )

    cases = []
    for j in sorted_js[:6]:
        by_original = sorted(j.results, key=lambda r: r.original_rank)[:5]
        by_relevance = sorted(j.results, key=lambda r: r.relevance_score, reverse=True)[:5]
        failure_label = _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode)
        best_position = j.displacement + 1
        no_results = not by_original
        if no_results:
            fail = "The search returned zero results — the customer reached a dead end."
        elif best_position <= 1:
            fail = "The best matching result was not surfaced cleanly."
        else:
            fail = f"The best matching result appeared at position #{best_position}, after weaker results."

        cases.append({
            "query": j.test_query.query,
            "failure_label": failure_label,
            "fail": fail,
            "no_results": no_results,
            "evidence_text": j.evidence,
            "fix": _fix_guidance(j),
            "actual_results": [
                {
                    "rank": r.original_rank,
                    "title": r.title,
                    "price": r.price,
                    "score": f"{r.relevance_score:.2f}",
                    "score_pct": round(r.relevance_score * 100),
                    "score_class": _score_class(r.relevance_score),
                }
                for r in by_original
            ],
            "ideal_results": [
                {
                    "rank": r.original_rank,
                    "title": r.title,
                    "price": r.price,
                    "score": f"{r.relevance_score:.2f}",
                    "score_pct": round(r.relevance_score * 100),
                    "score_class": _score_class(r.relevance_score),
                }
                for r in by_relevance
            ],
        })
    return cases


def _build_deep_dives(judgments: list[QueryJudgment]) -> list[dict]:
    """Build structured deep-dive data for each failing capability."""
    scores = build_capability_scores(judgments)
    failing = [cs for cs in scores if cs.severity != Severity.PASS.value]

    caps = []
    for cs in failing:
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)

        # Sort judgments: worst severity first, then highest displacement
        sorted_js = sorted(
            cs.judgments,
            key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
        )
        # Take up to 5 worst
        top_js = sorted_js[:5]

        queries = []
        for j in top_js:
            by_original = sorted(j.results, key=lambda r: r.original_rank)[:5]
            by_relevance = sorted(j.results, key=lambda r: r.relevance_score, reverse=True)[:3]

            queries.append({
                "query": j.test_query.query,
                "category": _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
                "severity_class": _severity_class(j.severity),
                "severity_short": _severity_short(j.severity),
                "best_position": j.displacement + 1,
                "displacement": j.displacement,
                "evidence": j.evidence,
                "actual_top": [
                    {"title": r.title, "price": r.price}
                    for r in by_original
                ],
                "ideal_top": [
                    {"title": r.title, "price": r.price}
                    for r in by_relevance
                ],
            })

        caps.append({
            "capability_name": cap_name,
            "severity_class": _severity_class(cs.severity),
            "queries": queries,
        })

    return caps


def _build_whats_working(judgments: list[QueryJudgment]) -> list[str]:
    """Return plain-text bullets for the What's Working section."""
    scores = build_capability_scores(judgments)
    bullets: list[str] = []

    # Minor capabilities
    for cs in scores:
        if cs.severity == Severity.MINOR.value:
            cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
            bullets.append(f"<strong>{cap_name} is mostly functional</strong> — minor issues only. {cs.summary}")

    # Retrieval worked
    poor_ranking = [j for j in judgments if j.failure_mode == "POOR_RANKING" and j.max_relevance_score >= 0.60]
    if poor_ranking:
        bullets.append(
            f"<strong>Retrieval is working</strong> — relevant results were found in {len(poor_ranking)} of "
            f"{len(judgments)} queries. The primary issue is ranking, not finding: the right results exist "
            f"in the result set but aren't being surfaced at the top."
        )

    # Near misses
    near_miss = [j for j in judgments if j.displacement <= 2 and j.severity != Severity.PASS.value]
    if near_miss:
        examples = [f'"{j.test_query.query}"' for j in near_miss[:3]]
        bullets.append(
            f"<strong>Close to correct</strong> on {len(near_miss)} queries ({', '.join(examples)}): "
            f"the best result was within the top 3, just not at #1."
        )

    # Typo recognition
    typo_caps = [cs for cs in scores if cs.capability == "TYPO_TOLERANCE"]
    for cs in typo_caps:
        retrieval_ok = [
            j for j in cs.judgments
            if j.failure_mode != "NO_FUZZY_MATCHING" and j.failure_mode != "ZERO_RESULTS_OR_GARBAGE"
        ]
        if retrieval_ok and len(retrieval_ok) == len(cs.judgments):
            bullets.append(
                "<strong>Your search correctly interprets typos and spelling variations</strong> — "
                "when we searched with misspellings, it recognized what customers meant. "
                "The issue is ranking the corrected results, not recognising the typo."
            )
            break

    if not bullets:
        bullets.append(
            "No capabilities passed all tests. However, the search engine does retrieve relevant "
            "results for most queries — the primary issue is ranking, not retrieval."
        )

    return bullets


def _parse_roadmap(roadmap_markdown: str) -> list[dict]:
    """Parse the LLM-generated roadmap markdown into structured items."""
    items = []
    # Match numbered items: "1. **Title**\n   Description\n   Impact: X | Effort: Y"
    pattern = re.compile(
        r"^\d+\.\s+\*\*(.+?)\*\*\s*\n\s+(.+?)(?:\n\s+Impact:\s*(\w+).*?\|\s*Effort:\s*(.+?))?$",
        re.MULTILINE,
    )

    # Simpler approach: split on numbered items
    chunks = re.split(r"\n(?=\d+\.\s+\*\*)", roadmap_markdown.strip())
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # Extract title
        title_match = re.search(r"\*\*(.+?)\*\*", chunk)
        title = title_match.group(1) if title_match else chunk[:80]

        # Extract impact/effort from the last line
        impact = effort = ""
        impact_match = re.search(r"Impact:\s*(\w+)", chunk)
        effort_match = re.search(r"Effort:\s*(.+?)(?:\n|$)", chunk)
        if impact_match:
            impact = impact_match.group(1)
        if effort_match:
            effort = effort_match.group(1).strip()

        # Description: everything between title and impact line
        desc_text = chunk
        desc_text = re.sub(r"^\d+\.\s+\*\*.+?\*\*\s*", "", desc_text).strip()
        desc_text = re.sub(r"\s*Impact:.*$", "", desc_text, flags=re.MULTILINE).strip()

        impact_class = {
            "Critical": "critical",
            "High": "high",
            "Moderate": "moderate",
        }.get(impact, "moderate")

        effort_class = "quick"
        if "Medium" in effort:
            effort_class = "medium"
        elif "Major" in effort:
            effort_class = "major"

        items.append({
            "title": title,
            "description": desc_text,
            "impact": impact,
            "effort": effort,
            "impact_class": impact_class,
            "effort_class": effort_class,
        })

    return items


def _build_benchmarks(stats: dict) -> list[dict]:
    pct_top3_relevant = 100 - float(stats["pct_top3_irrelevant"])
    return [
        {
            "metric": "Relevant result in top 3",
            "your_score": f"{pct_top3_relevant:.0f}%",
            "target": "80%+",
            "source": "Baymard Institute",
            "score_class": "below" if pct_top3_relevant < 80 else "meets",
        },
        {
            "metric": "Average best result position",
            "your_score": f"#{stats['avg_best_position']}",
            "target": "#1\u20132",
            "source": "Industry best practice",
            "score_class": "below" if float(stats["avg_best_position"]) > 2 else "meets",
        },
        {
            "metric": "Irrelevant #1 result",
            "your_score": f"{stats['pct_top1_irrelevant']}%",
            "target": "<10%",
            "source": "Industry best practice",
            "score_class": "below" if float(stats["pct_top1_irrelevant"]) > 10 else "meets",
        },
    ]


def _build_appendix(judgments: list[QueryJudgment]) -> list[dict]:
    sorted_js = sorted(
        judgments,
        key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
    )
    rows = []
    for j in sorted_js:
        sev_class = _severity_class(j.severity)
        sev_short = _severity_short(j.severity)
        fm = _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode)

        if j.severity == Severity.PASS.value:
            fm = "\u2014"
            best_pos = 1
        else:
            best_pos = j.displacement + 1

        rows.append({
            "query": j.test_query.query,
            "category": _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
            "severity_class": sev_class,
            "severity_short": sev_short,
            "best_position": best_pos,
            "failure_mode": fm,
        })
    return rows


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


def render_html_report(report: AuditReport, screenshot_path: str | Path | None = None) -> str:
    """Render an AuditReport into a self-contained HTML string."""
    # Reconstruct judgments from capability_scores
    judgments: list[QueryJudgment] = []
    for cs in report.capability_scores:
        judgments.extend(cs.judgments)

    # If no judgments in capability_scores, the report has no data
    if not judgments:
        return "<html><body><p>No audit data available.</p></body></html>"

    site_name = report.site_context.site_name or report.site_context.url
    stats = _build_stats(report, judgments)
    roadmap_items = _parse_roadmap(report.roadmap_narrative)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,  # we control the HTML
    )
    template = env.get_template("master_report.html")

    screenshot_b64 = None
    screenshot_mime = "image/png"
    if screenshot_path:
        sp = Path(screenshot_path)
        if sp.exists():
            screenshot_b64 = base64.b64encode(sp.read_bytes()).decode("ascii")
            screenshot_mime = mimetypes.guess_type(sp.name)[0] or screenshot_mime

    context = {
        "site_name": site_name,
        "report_title": _build_report_title(site_name, stats, judgments),
        "report_subtitle": _build_report_subtitle(site_name),
        "date": date.today().strftime("%B %d, %Y"),
        "pipeline_name": PIPELINE_NAME,
        "logo_svg": _load_logo_svg(),
        "screenshot_b64": screenshot_b64,
        "screenshot_mime": screenshot_mime,
        "query_cloud": _build_query_cloud(report),
        "stats": stats,
        "short_version": _build_short_version(site_name, stats, roadmap_items),
        "coverage_summary": _build_coverage_summary(judgments),
        "capability_scores": _build_capability_scores_ctx(judgments),
        "improvement_map": _build_improvement_map(judgments),
        "failure_modes": _build_failure_modes(judgments),
        "advanced_diagnostics": build_advanced_diagnostics_sections(report.site_context, judgments),
        "deep_dives": _build_deep_dives(judgments),
        "critical_failures": _build_critical_failures(judgments),
        "risk_cases": _build_risk_cases(judgments),
        "whats_working": _build_whats_working(judgments),
        "roadmap_items": roadmap_items,
        "benchmarks": _build_benchmarks(stats),
        "appendix": _build_appendix(judgments),
    }

    return template.render(**context)


def save_html_report(report: AuditReport, output_path: str | Path, screenshot_path: str | Path | None = None) -> Path:
    """Render and save the HTML report to a file. Returns the output path."""
    html = render_html_report(report, screenshot_path=screenshot_path)
    path = Path(output_path)
    path.write_text(html, encoding="utf-8")
    return path
