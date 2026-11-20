"""
Deterministic scoring logic for scanner probe results.

Scoring rules:
- PASS: Probe behavior matches expected outcome
- PARTIAL: Some but not all expected behavior
- FAIL: Probe behavior does not match expected outcome
- BLOCKED: Site blocked the scan attempt
- ERROR: Technical error during probe execution
"""

from __future__ import annotations

import logging
from typing import Optional

from .models import (
    ProbeType,
    ProbeResult,
    ProbeScore,
    ProbeStatus,
    ScoredProbe,
    CapabilityScore,
    ScanResult,
)
from .models import PROBE_FAILURE_MODES

# Capability groupings for scoring - maps capability area to relevant probe types
CAPABILITY_PROBES = {
    "basic_retrieval": [ProbeType.EXACT_PRODUCT_NAME, ProbeType.CATEGORY_TERM, ProbeType.CONTROL_QUERY],
    "typo_tolerance": [ProbeType.TYPO],
    "language_understanding": [ProbeType.SYNONYM, ProbeType.PLURAL_SINGULAR, ProbeType.ABBREVIATION],
    "locale_handling": [ProbeType.DIACRITICS, ProbeType.FORMAT_VARIANT],
    "compound_handling": [ProbeType.COMPOUND_SPLIT, ProbeType.MERGED_WORDS],
    "constraint_handling": [ProbeType.CONSTRAINT_QUERY, ProbeType.PRICE_CONSTRAINT, ProbeType.NATURAL_LANGUAGE],
    "brand_model_search": [ProbeType.BRAND_SEARCH, ProbeType.SKU_SEARCH],
    "coverage_ranking": [ProbeType.COVERAGE_CHECK, ProbeType.RANKING_CHECK],
    "zero_result_handling": [ProbeType.ZERO_RESULT_CHECK],
}

logger = logging.getLogger(__name__)


def score_probe_result(probe: ProbeResult) -> ScoredProbe:
    """Score a single probe result deterministically."""
    
    if probe.status == ProbeStatus.BLOCKED:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.BLOCKED,
            score_reason="Site blocked the scan"
        )
    
    if probe.status == ProbeStatus.TIMEOUT:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.ERROR,
            score_reason="Request timeout"
        )
    
    if probe.status == ProbeStatus.ERROR:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.ERROR,
            score_reason=probe.error_message or "Unknown error"
        )
    
    if probe.status == ProbeStatus.SKIPPED:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.ERROR,
            score_reason="Probe was skipped"
        )
    
    # Redirect can still be scored (may have extracted results from redirect destination)
    if probe.status == ProbeStatus.REDIRECT and probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason="Search redirected to different page"
        )
    
    if probe.status == ProbeStatus.PARTIAL:
        return ScoredProbe(probe=probe, score=ProbeScore.ERROR,
                           score_reason="Incomplete extraction; cannot judge search behavior")
    if probe.control_query and not probe.control_count:
        return ScoredProbe(probe=probe, score=ProbeScore.ERROR,
                           score_reason="No positive control; comparison is inconclusive")

    if probe.control_results and probe.probe_type not in (ProbeType.ZERO_RESULT_CHECK, ProbeType.CONTROL_QUERY):
        from .evidence import score_evidence
        return score_evidence(probe)

    # Score based on probe type
    scorer = PROBE_SCORERS.get(probe.probe_type, _score_generic)
    return scorer(probe)


def _score_exact_product_name(probe: ProbeResult) -> ScoredProbe:
    """Score exact product name search."""
    if probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason=f"No results for exact product search: '{probe.query}'"
        )
    
    # Check if query terms appear in top result
    query_words = set(probe.query.lower().split())
    if probe.results:
        top_title = probe.results[0].title.lower()
        matches = sum(1 for w in query_words if w in top_title)
        match_ratio = matches / len(query_words) if query_words else 0
        
        if match_ratio >= 0.5:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PASS,
                score_reason=f"Top result matches query ({matches}/{len(query_words)} words)"
            )
        else:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PARTIAL,
                score_reason=f"Results found but top result may not match ({matches}/{len(query_words)} words)"
            )
    
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.PARTIAL,
        score_reason="Results found but could not verify relevance"
    )


def _score_category_term(probe: ProbeResult) -> ScoredProbe:
    """Score category term search."""
    if probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason=f"No results for category: '{probe.query}'"
        )
    
    if probe.result_count >= 3:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PASS,
            score_reason=f"Good result count ({probe.result_count}) for category search"
        )
    
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.PARTIAL,
        score_reason=f"Few results ({probe.result_count}) for category search"
    )


def _score_typo(probe: ProbeResult) -> ScoredProbe:
    """Score typo tolerance."""
    if probe.result_count == 0 and probe.control_count and probe.control_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason=f"Zero results for typo '{probe.query}' vs {probe.control_count} for correct spelling"
        )
    
    if probe.control_count is not None and probe.control_count > 0:
        ratio = probe.result_count / probe.control_count
        if ratio >= 0.5:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PASS,
                score_reason=f"Good typo tolerance: {probe.result_count} vs {probe.control_count} results"
            )
        elif ratio >= 0.1:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PARTIAL,
                score_reason=f"Partial typo tolerance: {probe.result_count} vs {probe.control_count} results"
            )
        else:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.FAIL,
                score_reason=f"Poor typo tolerance: {probe.result_count} vs {probe.control_count} results"
            )
    
    # No control comparison available
    if probe.result_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason="Results found but no control comparison"
        )
    
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.FAIL,
        score_reason="No results and no control comparison"
    )


def _score_synonym(probe: ProbeResult) -> ScoredProbe:
    """Score synonym handling."""
    return _score_comparative(probe, "synonym")


def _score_plural_singular(probe: ProbeResult) -> ScoredProbe:
    """Score plural/singular handling."""
    return _score_comparative(probe, "plural/singular")


def _score_diacritics(probe: ProbeResult) -> ScoredProbe:
    """Score diacritics handling."""
    return _score_comparative(probe, "diacritics")


def _score_compound_split(probe: ProbeResult) -> ScoredProbe:
    """Score compound word splitting."""
    return _score_comparative(probe, "compound split")


def _score_merged_words(probe: ProbeResult) -> ScoredProbe:
    """Score merged word handling."""
    return _score_comparative(probe, "merged words")


def _score_comparative(probe: ProbeResult, test_type: str = "variant") -> ScoredProbe:
    """Generic scoring for comparative probes (variant vs control)."""
    # Determine test type from probe type if not specified
    if test_type == "variant" and probe.probe_type:
        test_type = probe.probe_type.value.replace("_", " ")
    
    if probe.result_count == 0 and probe.control_count and probe.control_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason=f"Zero results for {test_type}: '{probe.query}' vs {probe.control_count} for control"
        )
    
    if probe.control_count is not None and probe.control_count > 0:
        ratio = probe.result_count / probe.control_count
        if ratio >= 0.5:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PASS,
                score_reason=f"Good {test_type} handling: {probe.result_count} vs {probe.control_count}"
            )
        elif ratio >= 0.1:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PARTIAL,
                score_reason=f"Partial {test_type}: {probe.result_count} vs {probe.control_count}"
            )
        else:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.FAIL,
                score_reason=f"Poor {test_type}: {probe.result_count} vs {probe.control_count}"
            )
    
    if probe.result_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason=f"Results found but no control comparison for {test_type}"
        )
    
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.FAIL,
        score_reason=f"No results for {test_type} test"
    )


def _score_format_variant(probe: ProbeResult) -> ScoredProbe:
    """Score format variant handling (F004: USB-C vs USB C)."""
    return _score_comparative(probe, "format variant")


def _score_abbreviation(probe: ProbeResult) -> ScoredProbe:
    """Score abbreviation handling (F005: TV vs television)."""
    return _score_comparative(probe, "abbreviation")


def _score_constraint(probe: ProbeResult) -> ScoredProbe:
    """Score constraint query handling."""
    if probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason=f"No results for constraint query: '{probe.query}'"
        )
    
    if probe.result_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason=f"Results found ({probe.result_count}) but could not verify constraint applied"
        )
    
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.FAIL,
        score_reason="No results for constraint query"
    )


def _score_sku(probe: ProbeResult) -> ScoredProbe:
    """Score SKU/model number search."""
    if probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason=f"No results for SKU: '{probe.query}'"
        )
    
    # SKU search should ideally return 1 result
    if probe.result_count == 1:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PASS,
            score_reason="Single result for SKU search - ideal"
        )
    elif probe.result_count <= 5:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PASS,
            score_reason=f"Few results ({probe.result_count}) for SKU search"
        )
    else:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason=f"Many results ({probe.result_count}) for SKU - may not be filtering properly"
        )


def _score_zero_result(probe: ProbeResult) -> ScoredProbe:
    """Score zero-result handling (gibberish query should return 0)."""
    if probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PASS,
            score_reason="Correctly returned zero results for gibberish query"
        )
    else:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason=f"Nonzero items for gibberish ({probe.result_count}); verify fallback labeling before judging relevance"
        )


def _score_ranking(probe: ProbeResult) -> ScoredProbe:
    """Score ranking quality - F056/F057: accessories vs main product, buried matches."""
    if probe.result_count == 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.FAIL,
            score_reason="No results to evaluate ranking"
        )
    
    # Check if query terms appear in top result
    if probe.results:
        query_words = set(probe.query.lower().split())
        top_title = probe.results[0].title.lower()
        matches = sum(1 for w in query_words if w in top_title)
        match_ratio = matches / len(query_words) if query_words else 0
        
        if match_ratio >= 0.6:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PASS,
                score_reason=f"Top result matches query well ({matches}/{len(query_words)} key terms)"
            )
        elif match_ratio >= 0.3:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.PARTIAL,
                score_reason=f"Top result partially matches ({matches}/{len(query_words)} terms)"
            )
        else:
            return ScoredProbe(
                probe=probe,
                score=ProbeScore.FAIL,
                score_reason=f"Top result may not match query ({matches}/{len(query_words)} terms)"
            )
    
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.PARTIAL,
        score_reason="Could not evaluate ranking quality"
    )


def _score_control(probe: ProbeResult) -> ScoredProbe:
    """Score control query (should definitely return results)."""
    if probe.result_count >= 3:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PASS,
            score_reason=f"Control query returned {probe.result_count} results"
        )
    elif probe.result_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PARTIAL,
            score_reason=f"Control query returned only {probe.result_count} results"
        )
    else:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.ERROR,
            score_reason="No positive control; catalog seed/search discovery needs verification"
        )


def _score_generic(probe: ProbeResult) -> ScoredProbe:
    """Generic scoring fallback."""
    if probe.result_count > 0:
        return ScoredProbe(
            probe=probe,
            score=ProbeScore.PASS,
            score_reason=f"Query returned {probe.result_count} results"
        )
    return ScoredProbe(
        probe=probe,
        score=ProbeScore.FAIL,
        score_reason="Query returned no results"
    )


PROBE_SCORERS = {
    ProbeType.EXACT_PRODUCT_NAME: _score_exact_product_name,
    ProbeType.CATEGORY_TERM: _score_category_term,
    ProbeType.TYPO: _score_typo,
    ProbeType.SYNONYM: _score_synonym,
    ProbeType.PLURAL_SINGULAR: _score_plural_singular,
    ProbeType.DIACRITICS: _score_diacritics,
    ProbeType.FORMAT_VARIANT: _score_format_variant,
    ProbeType.ABBREVIATION: _score_abbreviation,
    ProbeType.COMPOUND_SPLIT: _score_compound_split,
    ProbeType.MERGED_WORDS: _score_merged_words,
    ProbeType.CONSTRAINT_QUERY: _score_constraint,
    ProbeType.PRICE_CONSTRAINT: _score_constraint,
    ProbeType.BRAND_SEARCH: _score_exact_product_name,
    ProbeType.SKU_SEARCH: _score_sku,
    ProbeType.COVERAGE_CHECK: _score_category_term,
    ProbeType.RANKING_CHECK: _score_ranking,
    ProbeType.ZERO_RESULT_CHECK: _score_zero_result,
    ProbeType.CONTROL_QUERY: _score_control,
}


def score_capability(capability: str, probes: list[ScoredProbe]) -> CapabilityScore:
    """Score a capability area based on its probes."""
    if not probes:
        return CapabilityScore(
            capability=capability,
            score=ProbeScore.ERROR,
            probes=[],
            summary="No probes available"
        )
    
    # Determine overall score (worst of all probes)
    scores = [p.score for p in probes]
    
    if ProbeScore.BLOCKED in scores:
        overall = ProbeScore.BLOCKED
    elif ProbeScore.FAIL in scores:
        overall = ProbeScore.FAIL
    elif ProbeScore.ERROR in scores:
        overall = ProbeScore.ERROR
    elif ProbeScore.PARTIAL in scores:
        overall = ProbeScore.PARTIAL
    else:
        overall = ProbeScore.PASS
    
    # Generate summary
    pass_count = scores.count(ProbeScore.PASS)
    fail_count = scores.count(ProbeScore.FAIL)
    partial_count = scores.count(ProbeScore.PARTIAL)
    
    summary = f"{pass_count}/{len(probes)} passed"
    if fail_count:
        summary += f", {fail_count} failed"
    if partial_count:
        summary += f", {partial_count} partial"
    if ProbeScore.ERROR in scores:
        summary += f", {scores.count(ProbeScore.ERROR)} technical errors"
    
    return CapabilityScore(
        capability=capability,
        score=overall,
        probes=probes,
        summary=summary
    )


def score_scan(scan_result: ScanResult) -> ScanResult:
    """Calculate capability scores and overall score for a scan."""
    # Group probes by capability
    capability_probes: dict[str, list[ScoredProbe]] = {cap: [] for cap in CAPABILITY_PROBES}
    
    for scored_probe in scan_result.probes:
        probe_type = scored_probe.probe.probe_type
        for cap, types in CAPABILITY_PROBES.items():
            if probe_type in types:
                capability_probes[cap].append(scored_probe)
    
    # Score each capability
    capabilities = []
    for cap, probes in capability_probes.items():
        if probes:
            capabilities.append(score_capability(cap, probes))
        else:
            kinds = CAPABILITY_PROBES[cap]
            reasons = [scan_result.inapplicable[k.value] for k in kinds if k.value in scan_result.inapplicable]
            capabilities.append(CapabilityScore(capability=cap, probes=[],
                score=ProbeScore.INAPPLICABLE if reasons else ProbeScore.ERROR,
                summary="Inapplicable to sampled catalog: " + "; ".join(sorted(set(reasons))) if reasons
                        else "Not reached: discovery/control failed"))
    
    scan_result.capabilities = capabilities
    
    # Calculate overall score
    if scan_result.blocked:
        scan_result.overall_score = ProbeScore.BLOCKED
    elif not capabilities:
        scan_result.overall_score = ProbeScore.ERROR
    else:
        cap_scores = [c.score for c in capabilities]
        if ProbeScore.BLOCKED in cap_scores:
            scan_result.overall_score = ProbeScore.BLOCKED
            scan_result.blocked = True
        elif ProbeScore.FAIL in cap_scores:
            scan_result.overall_score = ProbeScore.FAIL
        elif ProbeScore.ERROR in cap_scores:
            scan_result.overall_score = ProbeScore.ERROR
        elif ProbeScore.PARTIAL in cap_scores:
            scan_result.overall_score = ProbeScore.PARTIAL
        else:
            scan_result.overall_score = ProbeScore.PASS
    
    return scan_result


class ScanScore:
    """Utility class for working with scan scores."""
    
    @staticmethod
    def to_numeric(score: ProbeScore) -> float:
        """Convert score to numeric value (0-100)."""
        return {
            ProbeScore.INAPPLICABLE: -1.0,
            ProbeScore.PASS: 100.0,
            ProbeScore.PARTIAL: 50.0,
            ProbeScore.FAIL: 0.0,
            ProbeScore.BLOCKED: -1.0,
            ProbeScore.ERROR: -1.0,
        }.get(score, -1.0)
    
    @staticmethod
    def aggregate_scores(scores: list[ProbeScore]) -> float:
        """Calculate average numeric score, ignoring errors/blocked."""
        valid = [ScanScore.to_numeric(s) for s in scores if s not in (ProbeScore.BLOCKED, ProbeScore.ERROR, ProbeScore.INAPPLICABLE)]
        return sum(valid) / len(valid) if valid else 0.0
