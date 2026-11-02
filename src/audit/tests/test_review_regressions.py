"""Regression tests for bugs found by the independent post-implementation review (2026-11-02)."""

import json
import unittest
from unittest import mock

from src import fetcher as f
from src.judge import _control_is_zero
from src.models import FetchOutcome, SearchResult
from src.report_stats import sanitize_client_text
from src.scorer import clean_title_for_rerank
from tests.test_fetcher_flow import FlowBase, TEMPLATE, grid_page, page, query_of


class ControlOutcomeTests(unittest.TestCase):
    def test_failed_control_fetch_is_not_a_catalog_gap(self):
        for status in ("timeout", "blocked", "error"):
            self.assertFalse(_control_is_zero(FetchOutcome(query="x", status=status)), status)
        self.assertTrue(_control_is_zero(FetchOutcome(query="x", status="zero_confirmed")))
        self.assertFalse(_control_is_zero(FetchOutcome(
            query="x", status="ok", results=[SearchResult(rank=1, title="Boot")])))


class ApiZeroWithRecommendationTiles(unittest.TestCase):
    def test_api_zero_beats_recommendation_grid(self):
        api = [("algolia", "https://x.algolia.net/1/indexes/*/queries",
                json.dumps({"results": [{"query": "boots", "nbHits": 0, "hits": []}]}))]
        with mock.patch.object(f, "_HAS_API_KEY", False):
            o = f._analyse_page(html=grid_page("bestseller", 8), url=TEMPLATE.format("boots"),
                                final_url=TEMPLATE.format("boots"), query="boots", max_results=15, search_api=api)
        self.assertEqual(o.status, "zero_confirmed")
        self.assertEqual(o.results, [])


class ConsecutiveTimeoutFailFast(FlowBase):
    def test_timeouts_after_a_good_probe_stop_early(self):
        def static(url):
            if query_of(url) == "q0":
                return page(grid_page("q0"), url)
            return f.PageFetch(final_url=url, timed_out=True, error="timed out")

        self.patch_transports(static=static)
        queries = [f"q{i}" for i in range(12)]
        out = f.fetch_all_outcomes(queries, TEMPLATE)
        self.assertEqual(out["q0"].status, "ok")
        fetched = {query_of(u) for u in self.static_calls + self.pw_calls}
        self.assertLess(len(fetched), 12)  # gave up after a run of timeouts
        skipped = [o for o in out.values() if o.attempts == 0]
        self.assertTrue(skipped)
        self.assertTrue(all(o.status in ("timeout", "error") for o in skipped))


class TextCleaningTests(unittest.TestCase):
    def test_price_evidence_survives(self):
        text = ("3 of 5 results are outside the price limit (under 80), e.g. 'Trail Jacket' at £129.95. "
                "The first result already breaks the limit.")
        self.assertEqual(sanitize_client_text(text), text)

    def test_scores_still_removed(self):
        self.assertNotIn("0.703", sanitize_client_text("The cooler is buried. Relevance 0.703 here."))

    def test_discount_badges_stripped(self):
        self.assertEqual(clean_title_for_rerank("-20% Trail Jacket"), "Trail Jacket")
        self.assertEqual(clean_title_for_rerank("Trail Jacket -20%"), "Trail Jacket")
        self.assertEqual(clean_title_for_rerank("New Balance 574"), "New Balance 574")


if __name__ == "__main__":
    unittest.main()


class GroundingRealCatalogTests(unittest.TestCase):
    """Live smoke test (2026-11-02): a real product named with different punctuation, and taken
    from another search's results, was rejected as invented and made generate_report raise."""

    def test_real_product_from_other_search_is_accepted_and_proves_stock(self):
        from src.report_generator import grounding_violations
        from tests.helpers import all_judgments, historical_reports
        rep = historical_reports()["huckberry_com"]
        js = all_judgments(rep)
        scope = [j for j in js if j.test_query.query == "something to cook pizza outdoors"]
        text = ('The store carries pizza ovens — searching "Gozeny pizza oven" surfaces the '
                '"Gozney Tread Portable Pizza Oven" — yet this search did not find it.')
        self.assertEqual(grounding_violations(text, scope, js, rep.site_context, "t"), [])

    def test_invented_product_still_rejected(self):
        from src.report_generator import grounding_violations
        from tests.helpers import all_judgments, historical_reports
        rep = historical_reports()["huckberry_com"]
        js = all_judgments(rep)
        scope = [j for j in js if j.test_query.query == "something to cook pizza outdoors"]
        problems = grounding_violations('The store carries the "Ooni Volt 12 Electric Oven".', scope, js,
                                        rep.site_context, "t")
        self.assertTrue(problems)
