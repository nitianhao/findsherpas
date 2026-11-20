"""Tests for the scanner scoring logic."""

import pytest

from scanner.models import ProbeType, ProbeResult, ProbeStatus, ProbeScore
from scanner.scorer import score_probe_result, score_capability, CAPABILITY_PROBES


class TestScoreProbeResult:
    """Tests for the score_probe_result function."""

    def test_blocked_status_returns_blocked_score(self):
        probe = ProbeResult(
            probe_type=ProbeType.CONTROL_QUERY,
            query="test",
            status=ProbeStatus.BLOCKED,
            result_count=0,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.BLOCKED
        assert "blocked" in result.score_reason.lower()

    def test_error_status_returns_error_score(self):
        probe = ProbeResult(
            probe_type=ProbeType.CONTROL_QUERY,
            query="test",
            status=ProbeStatus.ERROR,
            result_count=0,
            error_message="Connection failed",
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.ERROR
        assert "Connection failed" in result.score_reason

    def test_timeout_status_returns_error_score(self):
        probe = ProbeResult(
            probe_type=ProbeType.CONTROL_QUERY,
            query="test",
            status=ProbeStatus.TIMEOUT,
            result_count=0,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.ERROR
        assert "timeout" in result.score_reason.lower()

    def test_control_query_with_results_passes(self):
        probe = ProbeResult(
            probe_type=ProbeType.CONTROL_QUERY,
            query="shoes",
            status=ProbeStatus.SUCCESS,
            result_count=50,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PASS

    def test_control_query_with_zero_results_is_inconclusive(self):
        probe = ProbeResult(
            probe_type=ProbeType.CONTROL_QUERY,
            query="shoes",
            status=ProbeStatus.SUCCESS,
            result_count=0,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.ERROR

    def test_typo_with_good_ratio_passes(self):
        probe = ProbeResult(
            probe_type=ProbeType.TYPO,
            query="sheos",
            control_query="shoes",
            status=ProbeStatus.SUCCESS,
            result_count=40,
            control_count=50,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PASS

    def test_typo_with_zero_results_fails(self):
        probe = ProbeResult(
            probe_type=ProbeType.TYPO,
            query="sheos",
            control_query="shoes",
            status=ProbeStatus.SUCCESS,
            result_count=0,
            control_count=50,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.FAIL

    def test_typo_with_low_ratio_fails(self):
        probe = ProbeResult(
            probe_type=ProbeType.TYPO,
            query="sheos",
            control_query="shoes",
            status=ProbeStatus.SUCCESS,
            result_count=2,
            control_count=50,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.FAIL

    def test_zero_result_check_with_zero_results_passes(self):
        probe = ProbeResult(
            probe_type=ProbeType.ZERO_RESULT_CHECK,
            query="xyzqwk12345nonsense",
            status=ProbeStatus.SUCCESS,
            result_count=0,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PASS

    def test_zero_result_check_with_results_needs_fallback_review(self):
        probe = ProbeResult(
            probe_type=ProbeType.ZERO_RESULT_CHECK,
            query="xyzqwk12345nonsense",
            status=ProbeStatus.SUCCESS,
            result_count=10,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PARTIAL

    def test_exact_product_name_with_matching_results_passes(self):
        from scanner.models import SearchResult
        probe = ProbeResult(
            probe_type=ProbeType.EXACT_PRODUCT_NAME,
            query="Nike Air Max 90",
            status=ProbeStatus.SUCCESS,
            result_count=5,
            results=[
                SearchResult(rank=1, title="Nike Air Max 90 White", price="$120"),
            ],
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PASS

    def test_exact_product_name_with_zero_results_fails(self):
        probe = ProbeResult(
            probe_type=ProbeType.EXACT_PRODUCT_NAME,
            query="Nike Air Max 90",
            status=ProbeStatus.SUCCESS,
            result_count=0,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.FAIL

    def test_category_term_with_many_results_passes(self):
        probe = ProbeResult(
            probe_type=ProbeType.CATEGORY_TERM,
            query="running shoes",
            status=ProbeStatus.SUCCESS,
            result_count=100,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PASS

    def test_category_term_with_few_results_is_partial(self):
        probe = ProbeResult(
            probe_type=ProbeType.CATEGORY_TERM,
            query="running shoes",
            status=ProbeStatus.SUCCESS,
            result_count=2,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PARTIAL

    def test_sku_search_with_one_result_passes(self):
        probe = ProbeResult(
            probe_type=ProbeType.SKU_SEARCH,
            query="ABC12345",
            status=ProbeStatus.SUCCESS,
            result_count=1,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.PASS

    def test_sku_search_with_zero_results_fails(self):
        probe = ProbeResult(
            probe_type=ProbeType.SKU_SEARCH,
            query="ABC12345",
            status=ProbeStatus.SUCCESS,
            result_count=0,
        )
        result = score_probe_result(probe)
        assert result.score == ProbeScore.FAIL


class TestScoreCapability:
    """Tests for the score_capability function."""

    def test_all_pass_scores_pass(self):
        from scanner.models import ScoredProbe
        probes = [
            ScoredProbe(
                probe=ProbeResult(
                    probe_type=ProbeType.TYPO,
                    query="test",
                    status=ProbeStatus.SUCCESS,
                    result_count=10,
                ),
                score=ProbeScore.PASS,
                score_reason="Good",
            ),
        ]
        result = score_capability("typo_tolerance", probes)
        assert result.score == ProbeScore.PASS

    def test_any_fail_scores_fail(self):
        from scanner.models import ScoredProbe
        probes = [
            ScoredProbe(
                probe=ProbeResult(
                    probe_type=ProbeType.TYPO,
                    query="test",
                    status=ProbeStatus.SUCCESS,
                    result_count=10,
                ),
                score=ProbeScore.PASS,
                score_reason="Good",
            ),
            ScoredProbe(
                probe=ProbeResult(
                    probe_type=ProbeType.TYPO,
                    query="test2",
                    status=ProbeStatus.SUCCESS,
                    result_count=0,
                ),
                score=ProbeScore.FAIL,
                score_reason="Bad",
            ),
        ]
        result = score_capability("typo_tolerance", probes)
        assert result.score == ProbeScore.FAIL

    def test_blocked_scores_blocked(self):
        from scanner.models import ScoredProbe
        probes = [
            ScoredProbe(
                probe=ProbeResult(
                    probe_type=ProbeType.TYPO,
                    query="test",
                    status=ProbeStatus.BLOCKED,
                    result_count=0,
                ),
                score=ProbeScore.BLOCKED,
                score_reason="Blocked",
            ),
        ]
        result = score_capability("typo_tolerance", probes)
        assert result.score == ProbeScore.BLOCKED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
