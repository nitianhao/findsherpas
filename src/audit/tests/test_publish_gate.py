import copy
import unittest

from src.models import ScoredResult
from src.publish_gate import _unrelated_query_count, check_report
from tests.helpers import all_judgments, historical_reports

_CLEAN_HTML = '<html><svg></svg><p>Clean text.</p><a href="https://findsherpas.com/book-a-call">Book</a></html>'


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = historical_reports()

    def _fresh(self, name="huckberry_com"):
        r = copy.deepcopy(self.reports[name])
        for j in all_judgments(r):
            j.evidence = "Plain observation."
            j.recommended_fix = "Plain fix."
        r.deep_dive_narrative = "Narrative."
        r.roadmap_narrative = "Roadmap."
        return r

    def test_clean_report_passes(self):
        res = check_report(self._fresh(), _CLEAN_HTML)
        self.assertTrue(res.ok, res.format())

    def test_cotswold_widget_detected(self):
        res = check_report(self.reports["cotswoldoutdoor_com"], _CLEAN_HTML)
        self.assertTrue(any("identical top 5" in e for e in res.errors))

    def test_related_queries_sharing_results_are_fine(self):
        self.assertEqual(_unrelated_query_count(["Hängematte Garten", "Hängematten", "Hängematte CHICO"]), 1)
        self.assertEqual(_unrelated_query_count(["walkinboots", "waterprooftrousers", "softshelljakket"]), 3)

    def test_fallback_and_unverified_fetch_block(self):
        r = self._fresh()
        js = all_judgments(r)
        js[0].judge_status = "fallback"
        for j in js[:20]:
            j.fetch_status = "blocked"
        res = check_report(r, _CLEAN_HTML)
        self.assertTrue(any("fallback" in e for e in res.errors))
        self.assertTrue(any("never observed" in e for e in res.errors))
        self.assertTrue(any("excluded_reason missing" in e for e in res.errors))

    def test_leaks_in_html_block(self):
        for leak in ("Max relevance score is 0.000", "User override: x", "[MANUAL VERIFICATION REQUIRED]",
                     "Roadmap section was not generated", "an LLM-based rewriter"):
            res = check_report(self._fresh(), _CLEAN_HTML.replace("Clean text.", leak))
            self.assertFalse(res.ok, leak)

    def test_missing_cta_blocks(self):
        res = check_report(self._fresh(), "<html><svg></svg></html>")
        self.assertFalse(res.ok)

    def test_missing_judgment_blocks(self):
        r = self._fresh()
        r.capability_scores[0].judgments.pop(0)
        self.assertFalse(check_report(r, _CLEAN_HTML).ok)


if __name__ == "__main__":
    unittest.main()


class ManualCheckTests(unittest.TestCase):
    def test_unresolved_manual_check_blocks_until_marked_manual(self):
        r = GateTests()._fresh.__func__(type("X", (), {"reports": historical_reports()})())
        j = all_judgments(r)[0]
        j.internal_notes = "MANUAL CHECK: colour not in titles"
        self.assertFalse(check_report(r, _CLEAN_HTML).ok)
        j.judge_status = "manual"
        self.assertTrue(check_report(r, _CLEAN_HTML).ok)


class FalsePositiveTests(unittest.TestCase):
    def test_realistic_text_does_not_block(self):
        r = GateTests()._fresh.__func__(type("X", (), {"reports": historical_reports()})())
        for text in ("Sac de voyage cabine", "Zapatillas todo terreno", "Thermosflasche 0.750 L",
                     "Rotwein 0,75 l", "Jacket at £129.95"):
            res = check_report(r, _CLEAN_HTML.replace("Clean text.", text))
            self.assertTrue(res.ok, (text, res.errors))
