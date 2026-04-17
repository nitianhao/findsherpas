from __future__ import annotations

import json
import logging
from collections import Counter

import anthropic
from dotenv import load_dotenv

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

_MODEL = "claude-sonnet-4-20250514"

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

_SEVERITY_EMOJI: dict[str, str] = {
    Severity.CRITICAL.value: "[X]",
    Severity.MODERATE.value: "[!]",
    Severity.MINOR.value: "[~]",
    Severity.PASS.value: "[OK]",
}


# ---------------------------------------------------------------------------
# Deterministic stats
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_prompt(
    test_query: TestQuery,
    results: list[ScoredResult],
    max_relevance: float,
    top3_avg: float,
    displacement: int,
) -> str:
    """Build the user message for the LLM judge."""

    cat = QueryCategory(test_query.category)
    cat_desc = CATEGORY_DESCRIPTIONS.get(cat, "")

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
- Total results: {len(results)}

## Failure Mode Menu
Pick the SINGLE most important failure mode:
{chr(10).join(fm_lines)}

## Severity Criteria
- **CRITICAL**: The best matching result is buried 7+ positions deep, OR the max relevance score is below 0.25, OR results are completely unrelated to the query. Business impact: customers searching this way see irrelevant results and leave.
- **MODERATE**: The best matching result is 3-6 positions deep, OR results are partially relevant but miss a key aspect of the query. Business impact: degraded experience, customers may bounce.
- **MINOR**: The best matching result is within top 3 but not #1, OR results are mostly relevant with small issues. Business impact: edge case, low frequency.
- **PASS**: Top 3 results are relevant and well-ordered. Displacement 0-2 and top 3 average above 0.60.

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
        sev = Severity.CRITICAL
    elif displacement > 2:
        fm = FailureMode.POOR_RANKING
        sev = Severity.MODERATE
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
) -> QueryJudgment:
    """Judge a single query's results using deterministic stats + LLM analysis."""

    max_relevance, top3_avg, displacement = _compute_stats(results)

    prompt = _build_prompt(test_query, results, max_relevance, top3_avg, displacement)
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

    # Parse text fields
    evidence = llm_response.get("evidence", "No evidence provided by LLM.")
    recommended_fix = llm_response.get("recommended_fix", "No fix provided by LLM.")
    fm_explanation = llm_response.get("failure_mode_explanation")

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
) -> list[QueryJudgment]:
    """Judge every query's results and produce QueryJudgment objects.

    Processes sequentially. Logs each verdict. Returns list[QueryJudgment].
    """
    judgments: list[QueryJudgment] = []
    total = len(queries)
    severity_counts: Counter[str] = Counter()

    for i, tq in enumerate(queries, 1):
        results = scored_results.get(tq.query, [])
        logger.info("[%d/%d] Judging: '%s' (%d results)", i, total, tq.query, len(results))

        judgment = _judge_single_query(tq, results)
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
