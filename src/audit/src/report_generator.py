from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date

import anthropic
from dotenv import load_dotenv

from src.category_selector import CATEGORY_DESCRIPTIONS
from src.models import (
    CAPABILITY_CATEGORY_MAP,
    AuditReport,
    CapabilityGroup,
    CapabilityScore,
    QueryCategory,
    QueryJudgment,
    Severity,
    SiteContext,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"

# Severity ordering for comparisons (higher index = worse)
_SEVERITY_RANK: dict[str, int] = {
    Severity.PASS.value: 0,
    Severity.MINOR.value: 1,
    Severity.MODERATE.value: 2,
    Severity.CRITICAL.value: 3,
}

# Human-readable capability names
_CAPABILITY_NAMES: dict[str, str] = {
    CapabilityGroup.TYPO_TOLERANCE.value: "Typo Tolerance",
    CapabilityGroup.LANGUAGE_UNDERSTANDING.value: "Language Understanding",
    CapabilityGroup.PRODUCT_DISCOVERY.value: "Product Discovery",
    CapabilityGroup.BRAND_MODEL_SEARCH.value: "Brand & Model Search",
    CapabilityGroup.FILTERS_CONSTRAINTS.value: "Filters & Constraints",
    CapabilityGroup.SHOPPING_CONTEXT.value: "Shopping Context",
}

# Scorecard emoji
_SEVERITY_EMOJI: dict[str, str] = {
    Severity.CRITICAL.value: "\U0001f534",   # red circle
    Severity.MODERATE.value: "\U0001f7e1",   # yellow circle
    Severity.MINOR.value: "\U0001f7e2",      # green circle
    Severity.PASS.value: "\u2705",           # white check mark
}

# Short severity labels for the scorecard table
_SEVERITY_SHORT: dict[str, str] = {
    Severity.CRITICAL.value: "Critical",
    Severity.MODERATE.value: "Moderate",
    Severity.MINOR.value: "Minor",
    Severity.PASS.value: "Pass",
}

# Pipeline brand name — used in methodology, headers, executive summary
PIPELINE_NAME = "Prism"

# Human-readable failure mode labels
_FAILURE_MODE_DISPLAY: dict[str, str] = {
    "PARTIAL_KEYWORD_MATCH": "Partial keyword match",
    "BRAND_BLEED": "Brand bleed",
    "CONSTRAINT_DROPPED": "Constraint dropped",
    "CATEGORY_MAPPING_FAILURE": "Category mapping failure",
    "FACET_NOT_EXTRACTED": "Facet not extracted",
    "NO_FUZZY_MATCHING": "No fuzzy matching",
    "NO_SEMANTIC_UNDERSTANDING": "No semantic understanding",
    "POOR_RANKING": "Poor ranking",
    "ZERO_RESULTS_OR_GARBAGE": "Zero results",
    "OTHER": "Other",
}

# Human-readable query category labels
_CATEGORY_DISPLAY: dict[str, str] = {
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
    "USE_CASE": "Use case",
    "SEASONAL_OCCASION": "Seasonal / occasion",
    "MULTI_ATTRIBUTE": "Multi-attribute",
    "STOP_WORD_HEAVY": "Stop-word heavy",
    "PARTIAL_QUERY": "Partial query",
    "LONG_VERBOSE_QUERY": "Long verbose query",
    "SEMANTIC_MEANING": "Semantic meaning",
    "CATEGORY_MAPPING": "Category mapping",
    "FACET_EXTRACTION": "Facet extraction",
}

# Reverse lookup: QueryCategory value -> CapabilityGroup value
_CATEGORY_TO_CAPABILITY: dict[str, str] = {}
for _cap, _cats in CAPABILITY_CATEGORY_MAP.items():
    for _cat in _cats:
        _CATEGORY_TO_CAPABILITY[_cat.value] = _cap.value


# ---------------------------------------------------------------------------
# PART 1 — Deterministic capability scoring
# ---------------------------------------------------------------------------


def build_capability_scores(judgments: list[QueryJudgment]) -> list[CapabilityScore]:
    """Group judgments by capability and compute the worst severity per group."""

    # Group judgments by capability
    grouped: dict[str, list[QueryJudgment]] = defaultdict(list)
    for j in judgments:
        cat_value = j.test_query.category
        cap_value = _CATEGORY_TO_CAPABILITY.get(cat_value)
        if cap_value:
            grouped[cap_value].append(j)
        else:
            logger.warning("Category %s not mapped to any capability group", cat_value)

    scores: list[CapabilityScore] = []

    for cap_value, cap_judgments in grouped.items():
        # Worst severity wins
        worst_sev_value = max(
            (j.severity for j in cap_judgments),
            key=lambda s: _SEVERITY_RANK.get(s, 0),
        )

        cap_name = _CAPABILITY_NAMES.get(cap_value, cap_value)
        total = len(cap_judgments)
        non_pass = sum(1 for j in cap_judgments if j.severity != Severity.PASS.value)

        if worst_sev_value == Severity.CRITICAL.value:
            summary = f"{non_pass} of {total} queries failed critically. {cap_name} is not functional."
        elif worst_sev_value == Severity.MODERATE.value:
            summary = f"{non_pass} of {total} queries showed issues. {cap_name} needs improvement."
        elif worst_sev_value == Severity.MINOR.value:
            summary = f"Minor issues detected in {non_pass} of {total} queries. {cap_name} is mostly functional."
        else:
            summary = f"All {total} queries passed. {cap_name} is working well."

        scores.append(CapabilityScore(
            capability=CapabilityGroup(cap_value),
            severity=Severity(worst_sev_value),
            summary=summary,
            judgments=cap_judgments,
        ))

    # Sort: CRITICAL first, then MODERATE, MINOR, PASS
    scores.sort(key=lambda s: _SEVERITY_RANK.get(s.severity, 0), reverse=True)
    return scores


def build_scorecard_markdown(capability_scores: list[CapabilityScore]) -> str:
    """Build the scorecard summary as a markdown table."""
    total = len(capability_scores)
    lines = [
        f"## Search Capability Scorecard\n",
        f"We tested your site's search across {total} core capabilities.\n",
        "",
        "| Status | Capability | Summary |",
        "|--------|-----------|---------|",
    ]

    pass_count = 0
    for cs in capability_scores:
        emoji = _SEVERITY_EMOJI.get(cs.severity, "")
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
        lines.append(f"| {emoji} | {cap_name} | {cs.summary} |")
        if cs.severity == Severity.PASS.value:
            pass_count += 1

    lines.append("")
    lines.append(f"**Result: Your search performed well on {pass_count} of {total} capabilities.**")
    return "\n".join(lines)


def build_whats_working_markdown(capability_scores: list[CapabilityScore]) -> str:
    """Build a section listing capabilities that passed, or partial wins if none passed."""
    passing = [cs for cs in capability_scores if cs.severity == Severity.PASS.value]

    if passing:
        lines = ["## What's Working\n"]
        for cs in passing:
            cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
            lines.append(f"- **{cap_name}**: {cs.summary}")
        return "\n".join(lines)

    # No capability passed — look for partial wins across all judgments
    lines = ["## What's Working\n"]
    bullets: list[str] = []

    # Collect all judgments from all capability scores
    all_judgments: list[QueryJudgment] = []
    for cs in capability_scores:
        all_judgments.extend(cs.judgments)

    # 1. MINOR capabilities — mostly functional
    minor_caps = [cs for cs in capability_scores if cs.severity == Severity.MINOR.value]
    for cs in minor_caps:
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
        bullets.append(f"**{cap_name} is mostly functional** — minor issues only. {cs.summary}")

    # 2. Retrieval worked (POOR_RANKING) vs recognition/retrieval failed
    poor_ranking_queries = [
        j for j in all_judgments
        if j.failure_mode == "POOR_RANKING" and j.max_relevance_score >= 0.60
    ]
    if poor_ranking_queries:
        count = len(poor_ranking_queries)
        total = len(all_judgments)
        bullets.append(
            f"**Retrieval is working** — relevant results were found in {count} of {total} queries. "
            f"The primary issue is ranking, not finding: the right results exist in the result set "
            f"but aren't being surfaced at the top."
        )

    # 3. Any query where best result was within top 3 (displacement <= 2)
    near_miss_queries = [
        j for j in all_judgments
        if j.displacement <= 2 and j.severity != Severity.PASS.value
    ]
    if near_miss_queries:
        examples = [f'"{j.test_query.query}"' for j in near_miss_queries[:3]]
        bullets.append(
            f"**Close to correct** on {len(near_miss_queries)} quer{'y' if len(near_miss_queries) == 1 else 'ies'} "
            f"({', '.join(examples)}): the best result was within the top 3, just not at #1."
        )

    # 4. Typo/merged queries where retrieval succeeded (failure mode is POOR_RANKING, not NO_FUZZY_MATCHING)
    typo_caps = [cs for cs in capability_scores if cs.capability == "TYPO_TOLERANCE"]
    for cs in typo_caps:
        retrieval_ok = [
            j for j in cs.judgments
            if j.failure_mode != "NO_FUZZY_MATCHING" and j.failure_mode != "ZERO_RESULTS_OR_GARBAGE"
        ]
        if retrieval_ok and len(retrieval_ok) == len(cs.judgments):
            bullets.append(
                f"**Your search correctly interprets typos and spelling variations** — "
                f"when we searched with misspellings, it recognized what customers meant. "
                f"The issue is ranking the corrected results, not recognising the typo."
            )
            break

    if not bullets:
        bullets.append(
            "No capabilities passed all tests. However, the search engine does retrieve relevant "
            "results for most queries — the primary issue is ranking, not retrieval."
        )

    lines.extend(f"- {b}" for b in bullets)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PART 2 — LLM-generated deep dives and roadmap
# ---------------------------------------------------------------------------

_SECTION_DELIMITER = "---SECTION_BREAK---"


def _build_narrative_prompt(
    site_context: SiteContext,
    capability_scores: list[CapabilityScore],
) -> str:
    """Build the Sonnet prompt for deep dives and roadmap."""

    failing = [cs for cs in capability_scores if cs.severity != Severity.PASS.value]

    if not failing:
        return ""

    capability_blocks = []
    for cs in failing:
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
        sev_short = _SEVERITY_SHORT.get(cs.severity, cs.severity)

        judgment_blocks = []
        for j in cs.judgments:
            # Top 5 by original rank
            by_original = sorted(j.results, key=lambda r: r.original_rank)[:5]
            original_lines = []
            for r in by_original:
                original_lines.append(
                    f"      #{r.original_rank} {r.title} (relevance: {r.relevance_score:.2f})"
                )

            # Top 3 by relevance
            by_relevance = sorted(j.results, key=lambda r: r.relevance_score, reverse=True)[:3]
            ideal_lines = []
            for r in by_relevance:
                ideal_lines.append(
                    f"      {r.title} (relevance: {r.relevance_score:.2f})"
                )

            fm_value = j.failure_mode
            j_sev_short = _SEVERITY_SHORT.get(j.severity, j.severity)

            judgment_blocks.append(
                f"    Query: \"{j.test_query.query}\"\n"
                f"    Category: {j.test_query.category}\n"
                f"    Failure mode: {fm_value}\n"
                f"    Severity: {j_sev_short}\n"
                f"    Displacement: {j.displacement}\n"
                f"    Evidence: {j.evidence}\n"
                f"    Recommended fix: {j.recommended_fix}\n"
                f"    What customer saw (top 5):\n" +
                "\n".join(original_lines) + "\n"
                f"    Ideal order (top 3):\n" +
                "\n".join(ideal_lines)
            )

        capability_blocks.append(
            f"### {cap_name} (Overall: {sev_short})\n\n" +
            "\n\n".join(judgment_blocks)
        )

    return f"""You are writing a search audit report for a business stakeholder. Write in plain language — no technical jargon. Be specific and reference actual product titles and query examples from the data below.

Use neutral, professional product terminology throughout: say "results", "items", or "products" — never site-specific terms like "deals", "listings", or "offers" unless directly quoting an actual product title.

## Site
- **Name**: {site_context.site_name or "(unknown)"}
- **URL**: {site_context.url}

## Failing Capabilities

{chr(10).join(capability_blocks)}

---

Write TWO clearly separated sections.

SECTION 1 — DEEP_DIVES:
Do NOT include a report title or any top-level heading (no "# Search Audit Report" or similar). Start directly with the first capability heading.

For each failing capability above, write a subsection:
- A heading (## capability name)
- 2-3 sentences explaining what this capability means and why it matters for their business. Do NOT use technical jargon like "fuzzy matching" or "tokenization". Write as if explaining to a smart business person.
- Then for the 4-5 WORST queries in that capability (pick by severity first, then by displacement):
  - Show the query the customer typed
  - 1-2 sentences in plain language referencing specific product titles from the results
  - A before/after comparison (label as "Customer saw:" and "Should have seen:"). You do NOT need to show exactly 3 items every time — show as many as makes the point clearly (sometimes 1 is enough; sometimes all 5).
  - State the displacement plainly: "The best match was buried at position #X." Do NOT add any phrase like "Most customers never scroll past position 3" or similar visibility warnings — that is already in the Executive Summary.
- Vary your lead-in style for each capability. Do NOT use the same opening structure twice in a row. Options:
  * Lead with the most absurd result: "When customers searched for [query], [irrelevant thing] ranked #1."
  * Lead with the displacement: "The best [thing] was buried at position #X out of #Y results."
  * Lead with the constraint violation: "Every single result exceeded the $50 budget — the cheapest was $X."
  * Lead with what worked, then what failed: "Your search correctly recognized the typo — but then ranked the corrected results poorly."
- Show 4-5 examples per capability to demonstrate the breadth of testing. Pick the most compelling ones.

SECTION 2 — ROADMAP:
Do NOT add any heading like "## Roadmap" or "## ROADMAP" — the heading is added by the report assembly code. Start directly with the numbered list.

A prioritized numbered list of fixes, ordered by business impact (Critical capabilities first). For each fix:
- One clear action item title (bold)
- One sentence describing what it fixes, referencing the capability name
- Impact level AND effort estimate on the same line, formatted as: "Impact: Critical | Effort: Quick Win"
  * Quick Win — configuration change or parameter tuning, days not weeks
  * Medium Effort — requires development work, 2-4 weeks
  * Major Project — significant engineering effort, 1-3 months
- Group related fixes — don't list the same fix twice for different queries
Keep the roadmap to 5-8 items maximum. Be specific but not overly technical.

Separate the two sections with this EXACT delimiter on its own line:
{_SECTION_DELIMITER}"""


_SCROLL_PHRASES = [
    "Most customers never scroll past position 3.",
    "Most customers never scroll past position 3",
    "most customers never scroll past position 3.",
    "most customers never scroll past position 3",
    "Most users never scroll past position 3.",
    "Most users never scroll past position 3",
    "most users never scroll past position 3.",
    "most users never scroll past position 3",
    "Most shoppers never scroll past position 3.",
    "most shoppers never scroll past position 3.",
]

# Top-level headings or section labels Sonnet sometimes adds that we strip
_REDUNDANT_HEADINGS = {
    "# search audit report",
    "## deep_dives",
    "## deep dives",
    "## roadmap",
    "## roadmap:",
    "## prioritized roadmap",
}


def _clean_sonnet_output(text: str, section: str) -> str:
    """Remove duplicate titles, redundant section headings, and scroll-warning boilerplate."""
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Drop lines that are just a redundant heading
        if stripped.lower() in _REDUNDANT_HEADINGS:
            continue
        # Drop lines that start with "# Search Audit Report"
        if stripped.lower().startswith("# search audit report"):
            continue
        cleaned.append(line)

    result = "\n".join(cleaned)

    # Strip repeated scroll-warning sentences
    for phrase in _SCROLL_PHRASES:
        result = result.replace(phrase, "")

    # Collapse any double-blank lines left by removals
    import re as _re
    result = _re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def generate_deep_dives_and_roadmap(
    site_context: SiteContext,
    capability_scores: list[CapabilityScore],
) -> tuple[str, str]:
    """Generate narrative deep dives and roadmap using Claude Sonnet.

    Returns (deep_dives_markdown, roadmap_markdown).
    """
    failing = [cs for cs in capability_scores if cs.severity != Severity.PASS.value]
    if not failing:
        return (
            "## Detailed Analysis\n\nAll capabilities passed. No deep dives needed.",
            "No fixes needed — all capabilities are performing well.",
        )

    prompt = _build_narrative_prompt(site_context, capability_scores)

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=8000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
    except Exception as e:
        logger.warning("Sonnet narrative generation failed: %s", e)
        # Fallback: build minimal deep dives from judgment data
        fallback_dives = _build_fallback_deep_dives(failing)
        fallback_roadmap = "Roadmap generation failed. Review the capability scores above for priority order."
        return fallback_dives, fallback_roadmap

    if _SECTION_DELIMITER in raw:
        parts = raw.split(_SECTION_DELIMITER, 1)
        deep_dives = _clean_sonnet_output(parts[0], section="dives")
        roadmap = _clean_sonnet_output(parts[1], section="roadmap")
    else:
        logger.warning("Section delimiter not found in Sonnet response — treating all as deep dives")
        deep_dives = _clean_sonnet_output(raw, section="dives")
        roadmap = "Roadmap section was not generated. Review the capability scores above for priority order."

    return deep_dives, roadmap


def _build_fallback_deep_dives(failing_scores: list[CapabilityScore]) -> str:
    """Build minimal deep dives from judgment data when LLM fails."""
    lines = ["## Detailed Analysis\n"]
    for cs in failing_scores:
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
        sev_short = _SEVERITY_SHORT.get(cs.severity, cs.severity)
        lines.append(f"### {cap_name} ({sev_short})\n")
        lines.append(f"{cs.summary}\n")
        for j in cs.judgments:
            lines.append(f"- **\"{j.test_query.query}\"**: {j.evidence}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PART 3 — Deterministic aggregate stats + executive summary
# ---------------------------------------------------------------------------


def compute_aggregate_stats(judgments: list[QueryJudgment]) -> dict:
    """Compute aggregate statistics across all judged queries.

    Returns a dict with keys:
        total_queries, critical_count, moderate_count, minor_count, pass_count,
        pct_top3_irrelevant, avg_best_position,
        pct_top1_irrelevant, worst_example_query, worst_example_displacement
    """
    total = len(judgments)
    if total == 0:
        return {
            "total_queries": 0,
            "critical_count": 0,
            "moderate_count": 0,
            "minor_count": 0,
            "pass_count": 0,
            "pct_top3_irrelevant": 0.0,
            "avg_best_position": 0.0,
            "pct_top1_irrelevant": 0.0,
            "worst_example_query": "",
            "worst_example_displacement": 0,
        }

    critical_count  = sum(1 for j in judgments if j.severity == Severity.CRITICAL.value)
    moderate_count  = sum(1 for j in judgments if j.severity == Severity.MODERATE.value)
    minor_count     = sum(1 for j in judgments if j.severity == Severity.MINOR.value)
    pass_count      = sum(1 for j in judgments if j.severity == Severity.PASS.value)

    # pct_top3_irrelevant: best result NOT in top 3 (displacement > 2)
    top3_irrelevant = sum(1 for j in judgments if j.displacement > 2)
    pct_top3_irrelevant = (top3_irrelevant / total) * 100

    # avg_best_position: average original_rank of the highest-scoring result
    avg_best_position = sum(j.displacement + 1 for j in judgments) / total

    # pct_top1_irrelevant: #1 result's relevance_score below 0.40
    top1_irrelevant = 0
    for j in judgments:
        if j.results:
            by_original = sorted(j.results, key=lambda r: r.original_rank)
            if by_original and by_original[0].relevance_score < 0.40:
                top1_irrelevant += 1
    pct_top1_irrelevant = (top1_irrelevant / total) * 100

    # worst example: highest displacement
    worst = max(judgments, key=lambda j: j.displacement)

    return {
        "total_queries": total,
        "critical_count": critical_count,
        "moderate_count": moderate_count,
        "minor_count": minor_count,
        "pass_count": pass_count,
        "pct_top3_irrelevant": pct_top3_irrelevant,
        "avg_best_position": avg_best_position,
        "pct_top1_irrelevant": pct_top1_irrelevant,
        "worst_example_query": worst.test_query.query,
        "worst_example_displacement": worst.displacement,
    }


def build_summary_statistics_markdown(
    stats: dict,
    judgments: list[QueryJudgment],
) -> str:
    """Build a summary statistics section showing severity distribution,
    failure mode breakdown, and key metrics."""
    total = stats["total_queries"]

    lines = [
        f"## {PIPELINE_NAME} Test Results Summary\n",
        f"We ran **{total} test queries** across multiple search capability categories. "
        f"Here is the breakdown.\n",
    ]

    # Severity distribution
    lines.append("### Severity Distribution\n")
    lines.append("| Severity | Queries |")
    lines.append("|----------|---------|")
    for sev_value, label in [
        (Severity.CRITICAL.value, "Critical"),
        (Severity.MODERATE.value, "Moderate"),
        (Severity.MINOR.value, "Minor"),
        (Severity.PASS.value, "Pass"),
    ]:
        emoji = _SEVERITY_EMOJI.get(sev_value, "")
        key = f"{label.lower()}_count"
        count = stats.get(key, 0)
        lines.append(f"| {emoji} {label} | {count} |")

    # Failure mode breakdown
    mode_counts = Counter(j.failure_mode for j in judgments if j.severity != Severity.PASS.value)
    if mode_counts:
        lines.append("")
        lines.append("### Failure Mode Breakdown\n")
        lines.append("| Failure Mode | Queries |")
        lines.append("|-------------|---------|")
        for mode, count in mode_counts.most_common():
            display = _FAILURE_MODE_DISPLAY.get(mode, mode)
            lines.append(f"| {display} | {count} |")

    # Key metrics
    lines.append("")
    lines.append("### Key Metrics\n")
    lines.append(f"- **Average best result position:** #{stats['avg_best_position']:.1f}")

    poor_ranking_count = sum(1 for j in judgments if j.failure_mode == "POOR_RANKING")
    if total > 0:
        pct_ranking = (poor_ranking_count / total) * 100
        lines.append(
            f"- **Retrieval OK, ranking failed:** {pct_ranking:.0f}% of queries "
            f"({poor_ranking_count} of {total}) — the right results were found but buried"
        )

    lines.append(
        f"- **Top-3 miss rate:** {stats['pct_top3_irrelevant']:.0f}% of queries "
        f"had their best result outside the top 3"
    )
    lines.append(
        f"- **Irrelevant #1 result:** {stats['pct_top1_irrelevant']:.0f}% of queries "
        f"showed an irrelevant result in the top position"
    )

    return "\n".join(lines)


def build_full_query_appendix_markdown(judgments: list[QueryJudgment]) -> str:
    """Build a full table of every query tested, sorted by severity then displacement."""
    total = len(judgments)

    lines = [
        f"## Appendix: Complete Test Results\n",
        f"All {total} queries tested by the {PIPELINE_NAME} audit pipeline.\n",
        "| # | Query | Category | Severity | Best Position | Failure Mode |",
        "|---|-------|----------|----------|--------------|-------------|",
    ]

    # Sort: worst first (CRITICAL -> MODERATE -> MINOR -> PASS), then by displacement desc
    sorted_judgments = sorted(
        judgments,
        key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
    )

    for idx, j in enumerate(sorted_judgments, 1):
        query = j.test_query.query
        category = _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category)
        emoji = _SEVERITY_EMOJI.get(j.severity, "")
        sev_label = _SEVERITY_SHORT.get(j.severity, j.severity)
        best_pos = f"#{j.displacement + 1}"
        failure = _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode)

        if j.severity == Severity.PASS.value:
            failure = "—"
            best_pos = "#1"

        lines.append(
            f"| {idx} | {query} | {category} | {emoji} {sev_label} | {best_pos} | {failure} |"
        )

    return "\n".join(lines)


def build_executive_summary(
    site_context: SiteContext,
    capability_scores: list[CapabilityScore],
    stats: dict,
) -> str:
    """Build a deterministic executive summary (no LLM)."""
    site_name = site_context.site_name or site_context.url
    total_cap = len(capability_scores)
    pass_cap = sum(1 for cs in capability_scores if cs.severity == Severity.PASS.value)

    total_queries       = stats["total_queries"]
    avg_best_position   = stats["avg_best_position"]
    pct_top3_irrelevant = stats["pct_top3_irrelevant"]
    pct_top1_irrelevant = stats["pct_top1_irrelevant"]
    worst_query         = stats["worst_example_query"]
    worst_disp          = stats["worst_example_displacement"]

    return (
        f"## Executive Summary\n\n"
        f"Our {PIPELINE_NAME} audit tested {site_name}'s internal search engine across "
        f"{total_cap} core capabilities using {total_queries} realistic customer queries. "
        f"**Your search performed well on {pass_cap} of {total_cap} capabilities.**\n\n"
        f"On average, the most relevant result for a query appeared at "
        f"**position #{avg_best_position:.0f}** — while most customers only look at the first 3 results. "
        f"In **{pct_top3_irrelevant:.0f}% of queries**, the best matching result wasn't even in the top 3. "
        f"In **{pct_top1_irrelevant:.0f}% of queries**, the #1 result shown to customers "
        f"was not relevant to what they searched for.\n\n"
        f'The most severe example: a customer searching "{worst_query}" '
        f"had to scroll to position #{worst_disp + 1} to find the best matching result."
    )


def build_methodology(
    total_queries: int,
    num_capabilities: int,
    num_categories: int,
) -> str:
    """Build a detailed methodology section describing the full audit pipeline."""
    return (
        f"## Methodology: The {PIPELINE_NAME} Audit Pipeline\n\n"
        f"This audit was conducted using our {PIPELINE_NAME} pipeline — a seven-phase automated "
        f"search quality assessment. {total_queries} test queries were generated across "
        f"{num_categories} query categories, grouped into {num_capabilities} core capabilities.\n\n"
        f"**1. Site Discovery**\n"
        f"Automated analysis of your site's structure, navigation categories, brands, and "
        f"featured products to understand what your search engine should be able to find.\n\n"
        f"**2. Test Design**\n"
        f"Site-type-aware selection from a library of 26 test categories. Categories are chosen "
        f"based on your site's commerce model to ensure the audit tests what matters most for "
        f"your customers.\n\n"
        f"**3. Query Generation**\n"
        f"AI-generated realistic customer queries grounded in the actual products, brands, and "
        f"categories found on your site — not generic templates.\n\n"
        f"**4. Result Collection**\n"
        f"Automated search execution collecting the top results for each test query exactly as "
        f"your customers would see them.\n\n"
        f"**5. Relevance Scoring**\n"
        f"Each result scored on a 0.0–1.0 scale by a specialized relevance model, producing an "
        f"objective measure of how well each result matches the query intent.\n\n"
        f"**6. Failure Analysis**\n"
        f"Each query classified by failure mode (e.g., poor ranking, constraint dropped, no "
        f"fuzzy matching) and severity based on how far the best result was buried below "
        f"irrelevant ones.\n\n"
        f"**7. Report Assembly**\n"
        f"Findings synthesized into this actionable narrative with prioritized recommendations "
        f"ordered by business impact."
    )


def build_industry_benchmarks_markdown(stats: dict) -> str:
    """Build a section comparing the client's scores against published industry benchmarks."""
    pct_top3_relevant = 100 - stats["pct_top3_irrelevant"]
    avg_best = stats["avg_best_position"]
    pct_top1_irrelevant = stats["pct_top1_irrelevant"]

    lines = [
        "## How You Compare: Industry Benchmarks\n",
        "Your results in context of published ecommerce search research.\n",
        "| Metric | Your Score | Industry Target | Source |",
        "|--------|-----------|----------------|--------|",
        f"| Relevant result in top 3 | {pct_top3_relevant:.0f}% | 80%+ | Baymard Institute |",
        f"| Average best result position | #{avg_best:.1f} | #1–2 | Industry best practice |",
        f"| Irrelevant #1 result | {pct_top1_irrelevant:.0f}% | <10% | Industry best practice |",
        "",
        "### Why This Matters\n",
        "- **70% of ecommerce sites cannot handle typos** in their site search "
        "(Baymard Institute). Sites that do handle them gain a significant edge.\n"
        "- **~30% of ecommerce visitors use site search**, but they generate a "
        "disproportionate share of revenue — search users convert at **1.8–3x the rate** "
        "of browse-only visitors (Econsultancy, Algolia).\n"
        "- **31% of site searches end at a dead end** — irrelevant results or zero "
        "results — across the average ecommerce site (Baymard Institute).\n"
        "- The top 3 results capture **~55–60% of all clicks**. Results below position 3 "
        "are seen by a rapidly shrinking share of customers.",
    ]

    return "\n".join(lines)


def build_call_to_action() -> str:
    """Build a deterministic call-to-action section (no LLM)."""
    return (
        "## Next Steps\n\n"
        "We'd welcome the opportunity to walk you through these findings in detail and discuss "
        "a remediation plan tailored to your team's priorities and timeline. The issues "
        "identified in this audit are fixable — most ecommerce search platforms support the "
        "capabilities tested here, and the roadmap above is ordered by impact to help you "
        "prioritize.\n\n"
        "**Contact us to schedule a 30-minute walkthrough of this report.**"
    )


# ---------------------------------------------------------------------------
# Main report assembly
# ---------------------------------------------------------------------------


def generate_report(
    site_context: SiteContext,
    judgments: list[QueryJudgment],
) -> AuditReport:
    """Assemble the full audit report: deterministic scoring + LLM narratives."""

    # Part 1: Deterministic
    capability_scores = build_capability_scores(judgments)
    scorecard_md = build_scorecard_markdown(capability_scores)
    whats_working_md = build_whats_working_markdown(capability_scores)

    # Part 2: LLM narratives
    deep_dives_md, roadmap_md = generate_deep_dives_and_roadmap(
        site_context, capability_scores
    )

    # Part 3: Deterministic stats + framing sections
    stats = compute_aggregate_stats(judgments)
    num_categories = len({j.test_query.category for j in judgments})
    executive_summary_md = build_executive_summary(site_context, capability_scores, stats)
    summary_stats_md = build_summary_statistics_markdown(stats, judgments)
    benchmarks_md = build_industry_benchmarks_markdown(stats)
    appendix_md = build_full_query_appendix_markdown(judgments)
    methodology_md = build_methodology(
        total_queries=stats["total_queries"],
        num_capabilities=len(capability_scores),
        num_categories=num_categories,
    )
    cta_md = build_call_to_action()

    # Assemble markdown in specified order
    site_name = site_context.site_name or site_context.url
    today = date.today().strftime("%B %d, %Y")

    full_narrative = "\n\n".join([
        f"# Search Audit Report: {site_name}\n\n*Generated on {today} | Powered by {PIPELINE_NAME}*",
        executive_summary_md,
        scorecard_md,
        summary_stats_md,
        deep_dives_md,
        whats_working_md,
        f"## Prioritized Roadmap\n\n{roadmap_md}",
        benchmarks_md,
        methodology_md,
        appendix_md,
        cta_md,
    ])

    # Collect all selected categories and queries from judgments
    all_categories = list({
        QueryCategory(j.test_query.category) for j in judgments
    })
    all_queries = [j.test_query for j in judgments]

    return AuditReport(
        site_context=site_context,
        selected_categories=all_categories,
        queries=all_queries,
        capability_scores=capability_scores,
        deep_dive_narrative=full_narrative,
        roadmap_narrative=roadmap_md,
    )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.models import FailureMode, ScoredResult, SiteType, TestQuery

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Fake site context
    site_ctx = SiteContext(
        url="https://www.kicksworld.com",
        site_name="KicksWorld",
        site_type=SiteType.PHYSICAL_GOODS,
        nav_categories=["Men's Shoes", "Women's Shoes", "Running", "Casual", "Sale"],
        brands=["Nike", "Adidas", "New Balance", "Puma"],
        featured_items=["Nike Air Max 90", "Adidas Ultraboost 22", "New Balance 574"],
        search_url_template="https://www.kicksworld.com/search?q={}",
        raw_meta_description="KicksWorld — sneakers, running shoes, and casual footwear.",
    )

    # --- PASS judgments (Product Discovery: DIRECT_MATCH) ---
    j_direct = QueryJudgment(
        test_query=TestQuery(
            category="DIRECT_MATCH", query="Nike Air Max 90",
            rationale="Exact product name lookup",
        ),
        results=[
            ScoredResult(rank=1, title="Nike Air Max 90 - White/Black", price="$130",
                         relevance_score=0.95, original_rank=1),
            ScoredResult(rank=2, title="Nike Air Max 90 Premium", price="$150",
                         relevance_score=0.90, original_rank=2),
        ],
        failure_mode=FailureMode.OTHER,
        failure_mode_explanation="No failure — query passed",
        severity=Severity.PASS,
        evidence="Top results are all Air Max 90 variants. Relevance scores above 0.90.",
        recommended_fix="No fix needed.",
        displacement=0, max_relevance_score=0.95, top3_original_average=0.925,
    )

    # --- PASS judgment (Brand & Model Search: BRAND_SEARCH) ---
    j_brand = QueryJudgment(
        test_query=TestQuery(
            category="BRAND_SEARCH", query="Adidas",
            rationale="Brand-only search should return Adidas products",
        ),
        results=[
            ScoredResult(rank=1, title="Adidas Ultraboost 22", price="$190",
                         relevance_score=0.88, original_rank=1),
            ScoredResult(rank=2, title="Adidas Stan Smith", price="$100",
                         relevance_score=0.85, original_rank=2),
        ],
        failure_mode=FailureMode.OTHER,
        failure_mode_explanation="No failure — query passed",
        severity=Severity.PASS,
        evidence="All results are Adidas products. Well ordered.",
        recommended_fix="No fix needed.",
        displacement=0, max_relevance_score=0.88, top3_original_average=0.865,
    )

    # --- CRITICAL judgments (Typo Tolerance: TYPO, MERGED_WORDS) ---
    j_typo = QueryJudgment(
        test_query=TestQuery(
            category="TYPO", query="nkie air max",
            rationale="Misspelling of Nike — tests fuzzy matching",
        ),
        results=[
            ScoredResult(rank=1, title="Air Freshener 3-Pack", price="$8.99",
                         relevance_score=0.05, original_rank=1),
            ScoredResult(rank=2, title="Max Hair Gel 16oz", price="$12.50",
                         relevance_score=0.03, original_rank=2),
            ScoredResult(rank=3, title="Air Pump for Bikes", price="$24.99",
                         relevance_score=0.04, original_rank=3),
        ],
        failure_mode=FailureMode.NO_FUZZY_MATCHING,
        severity=Severity.CRITICAL,
        evidence="All 3 results are completely unrelated. The engine matched 'air' and 'max' as separate keywords and ignored the misspelled brand.",
        recommended_fix="Enable fuzzy matching / Levenshtein distance matching. 'nkie' is 1 transposition from 'Nike' — this should be caught by any basic typo tolerance.",
        displacement=15, max_relevance_score=0.05, top3_original_average=0.04,
    )

    j_merged = QueryJudgment(
        test_query=TestQuery(
            category="MERGED_WORDS", query="runningshoes",
            rationale="Merged compound word — tests token splitting",
        ),
        results=[
            ScoredResult(rank=1, title="Shoe Cleaning Kit", price="$15.99",
                         relevance_score=0.10, original_rank=1),
            ScoredResult(rank=2, title="Nike Pegasus 40", price="$130",
                         relevance_score=0.65, original_rank=4),
            ScoredResult(rank=3, title="Running Socks 6-Pack", price="$18.00",
                         relevance_score=0.20, original_rank=2),
        ],
        failure_mode=FailureMode.PARTIAL_KEYWORD_MATCH,
        severity=Severity.CRITICAL,
        evidence="Engine matched 'shoes' as a keyword but didn't split 'runningshoes' into 'running shoes'. Best result (Nike Pegasus) buried at position 4.",
        recommended_fix="Implement compound word splitting so 'runningshoes' is tokenized as 'running shoes' before matching.",
        displacement=3, max_relevance_score=0.65, top3_original_average=0.317,
    )

    # --- MODERATE judgments (Language Understanding: SYNONYM, NATURAL_LANGUAGE) ---
    j_synonym = QueryJudgment(
        test_query=TestQuery(
            category="SYNONYM", query="sneakers",
            rationale="Synonym for shoes — should return same results as 'shoes'",
        ),
        results=[
            ScoredResult(rank=1, title="Snack Bar Variety Pack", price="$22.99",
                         relevance_score=0.02, original_rank=1),
            ScoredResult(rank=2, title="Nike Dunk Low", price="$110",
                         relevance_score=0.72, original_rank=3),
            ScoredResult(rank=3, title="Vans Old Skool", price="$70",
                         relevance_score=0.68, original_rank=5),
        ],
        failure_mode=FailureMode.NO_SEMANTIC_UNDERSTANDING,
        severity=Severity.MODERATE,
        evidence="The term 'sneakers' is not in the product catalog vocabulary. Best matches exist but are buried. Position 1 is a snack bar — completely irrelevant.",
        recommended_fix="Add 'sneakers' as a synonym for the shoes category. Map it to the same results as 'shoes' or 'casual shoes'.",
        displacement=2, max_relevance_score=0.72, top3_original_average=0.473,
    )

    j_natural = QueryJudgment(
        test_query=TestQuery(
            category="NATURAL_LANGUAGE", query="comfortable shoes for standing all day",
            rationale="Natural language use-case query",
        ),
        results=[
            ScoredResult(rank=1, title="Standing Desk Converter", price="$249",
                         relevance_score=0.05, original_rank=1),
            ScoredResult(rank=2, title="New Balance 574", price="$85",
                         relevance_score=0.60, original_rank=4),
            ScoredResult(rank=3, title="Day Planner Journal", price="$15",
                         relevance_score=0.01, original_rank=2),
        ],
        failure_mode=FailureMode.PARTIAL_KEYWORD_MATCH,
        severity=Severity.MODERATE,
        evidence="Engine matched 'standing' to standing desks and 'day' to planners. Ignored the actual intent: comfortable footwear. Best shoe result at position 4.",
        recommended_fix="Implement intent-based search that understands 'shoes for standing' is a footwear query, not a furniture query.",
        displacement=3, max_relevance_score=0.60, top3_original_average=0.22,
    )

    all_judgments = [j_direct, j_brand, j_typo, j_merged, j_synonym, j_natural]

    print("Generating report...\n")
    report = generate_report(site_ctx, all_judgments)

    print(report.deep_dive_narrative)
    print("\n\n--- Full roadmap narrative ---\n")
    print(report.roadmap_narrative)
    print(f"\nCapability scores: {len(report.capability_scores)}")
    for cs in report.capability_scores:
        sev_short = _SEVERITY_SHORT.get(cs.severity, cs.severity)
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
        print(f"  {sev_short:>8} | {cap_name}: {cs.summary}")
