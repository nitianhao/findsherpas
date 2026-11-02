"""End-to-end orchestration with every external phase stubbed: checkpoints, resume, controls,
fetch-trust abort and publish gating. No network, no LLM, no Voyage."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import orchestrator as orch
from src.models import (FetchOutcome, QueryJudgment, ScoredResult, SearchResult, SiteContext,
                        TestQuery)

_URL = "https://shop.example/search?q=boots"
_CTX = SiteContext(url=_URL, site_name="Shop", site_type="PHYSICAL_GOODS",
                   search_url_template="https://shop.example/search?q={}")
_QUERIES = [
    TestQuery(category="TYPO", query="bots", rationale="r", target_term="boots"),
    TestQuery(category="SYNONYM", query="wellies", rationale="r", target_term="rain boots"),
    TestQuery(category="BRAND_SEARCH", query="acme", rationale="r", target_term="acme"),
]


def _outcome(q, status="ok", n=3):
    return FetchOutcome(query=q, status=status,
                        results=[SearchResult(rank=i + 1, title=f"{q} item {i}") for i in range(n if status == "ok" else 0)])


class _Stubs:
    def __init__(self, fetch_map):
        self.fetch_map = fetch_map
        self.fetch_calls: list[list[str]] = []
        self.judge_kwargs = None
        self.published = False

    def fetch(self, queries, template, max_results=15, evidence_dir=None):
        self.fetch_calls.append(list(queries))
        return {q: self.fetch_map.get(q, _outcome(q)) for q in queries}

    def score(self, queries, scraped):
        return {q: [ScoredResult(**r.model_dump(), relevance_score=0.8, original_rank=r.rank) for r in rs]
                for q, rs in scraped.items()}

    def judge(self, queries, scored, **kwargs):
        self.judge_kwargs = kwargs
        return [QueryJudgment(test_query=tq, results=scored.get(tq.query, []), failure_mode="OTHER",
                              severity="Pass — Search handles this well.", evidence="Fine.",
                              recommended_fix="None.", displacement=0, max_relevance_score=0.8,
                              top3_original_average=0.8) for tq in queries]

    def publish(self, *a, **k):
        self.published = True
        from src.github_publisher import PublishResult
        return PublishResult(company="shop", slug="shop-1234", url="https://findsherpas.com/report/shop-1234/")


def _report_stub(ctx, judgments):
    from src.models import AuditReport, CapabilityScore
    return AuditReport(site_context=ctx, selected_categories=[], queries=[j.test_query for j in judgments],
                       capability_scores=[CapabilityScore(capability="TYPO_TOLERANCE",
                                                          severity="Pass — Search handles this well.",
                                                          summary="", judgments=judgments)],
                       deep_dive_narrative="Narrative.", roadmap_narrative="Roadmap.")


def _html_stub(report, path, screenshot_path=None):
    Path(path).write_text('<html><svg></svg><a href="https://findsherpas.com/book-a-call">x</a></html>')


class OrchestratorTests(unittest.TestCase):
    def _run(self, stubs, output_dir_override=None, **kwargs):
        out = output_dir_override or tempfile.mkdtemp()
        patches = [
            mock.patch.object(orch, "discover_from_search_url", return_value=_CTX.model_copy()),
            mock.patch.object(orch, "select_categories", return_value=["TYPO", "SYNONYM", "BRAND_SEARCH"]),
            mock.patch.object(orch, "generate_queries", return_value=list(_QUERIES)),
            mock.patch.object(orch, "fetch_all_outcomes", side_effect=stubs.fetch),
            mock.patch.object(orch, "score_results", side_effect=stubs.score),
            mock.patch.object(orch, "judge_all_queries", side_effect=stubs.judge),
            mock.patch.object(orch, "generate_report", side_effect=_report_stub),
            mock.patch.object(orch, "save_html_report", side_effect=_html_stub),
            mock.patch.object(orch, "publish_report_full", side_effect=stubs.publish),
            mock.patch.object(orch.sys.stdin, "isatty", return_value=False),
        ]
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])
        report = orch.run_audit(_URL, output_dir=out, **kwargs)
        return report, Path(out)

    def test_controls_and_full_judge_context(self):
        stubs = _Stubs({"bots": _outcome("bots", "zero_confirmed")})
        report, _ = self._run(stubs)
        self.assertEqual(stubs.fetch_calls[1], ["boots"])  # one control search for the zero-result typo
        kw = stubs.judge_kwargs
        self.assertIn("bots", kw["control_outcomes"])
        for key in ("site_categories", "site_brands", "fetch_outcomes", "language"):
            self.assertIn(key, kw)
        self.assertIn("models", report.run_metadata)
        self.assertEqual(report.run_metadata["fetch_status_counts"]["zero_confirmed"], 1)

    def test_untrusted_majority_aborts_then_resume_refetches_only_those(self):
        stubs = _Stubs({"bots": _outcome("bots", "blocked"), "wellies": _outcome("wellies", "timeout")})
        out = Path(tempfile.mkdtemp())
        with self.assertRaises(orch.FetchError):
            self._run(stubs, output_dir_override=out)
        run_dir = next((out / "shop_example").glob("run_*"))
        self.assertTrue((run_dir / "04_fetch.json").exists())  # paid fetch work survives the abort

        stubs2 = _Stubs({})  # site reachable now
        self._run(stubs2, output_dir_override=out, resume_dir=run_dir)
        self.assertEqual(sorted(stubs2.fetch_calls[0]), ["bots", "wellies"])  # only the untrusted ones

    def test_resume_skips_completed_phases(self):
        stubs = _Stubs({})
        _, out = self._run(stubs)
        run_dir = next((out / "shop_example").glob("run_*"))
        self.assertTrue((run_dir / "06_judgments.json").exists())
        stubs2 = _Stubs({})
        with mock.patch.object(orch, "generate_queries", side_effect=AssertionError("should not regenerate")):
            orch_out = run_dir.parent.parent
            report = None
            patches = [
                mock.patch.object(orch, "fetch_all_outcomes", side_effect=stubs2.fetch),
                mock.patch.object(orch, "judge_all_queries", side_effect=AssertionError("should not rejudge")),
                mock.patch.object(orch, "generate_report", side_effect=_report_stub),
                mock.patch.object(orch, "save_html_report", side_effect=_html_stub),
                mock.patch.object(orch.sys.stdin, "isatty", return_value=False),
            ]
            for p in patches:
                p.start()
            try:
                report = orch.run_audit(_URL, output_dir=orch_out, resume_dir=run_dir)
            finally:
                for p in patches:
                    p.stop()
        self.assertEqual(stubs2.fetch_calls, [])
        self.assertEqual(len(report.capability_scores[0].judgments), 3)

    def test_publish_is_opt_in_and_gated(self):
        stubs = _Stubs({})
        self._run(stubs)
        self.assertFalse(stubs.published)
        stubs = _Stubs({})
        self._run(stubs, publish=True)
        self.assertTrue(stubs.published)


if __name__ == "__main__":
    unittest.main()
