"""Advanced diagnostics: counts match their wording, buckets add up, excluded never counted."""

from __future__ import annotations

import copy
import unittest

from src.advanced_diagnostics import (
    _build_constraint_obedience,
    _build_ordering,
    _build_substitutions,
    _specificity_text,
    build_advanced_diagnostics,
)
from src.models import Severity
from tests.helpers import all_judgments, historical_reports
from tests.test_report_grounding import J


class DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = historical_reports()

    def test_constraint_buckets_sum_to_total(self):
        for name, rep in self.fixtures.items():
            c = _build_constraint_obedience(all_judgments(rep))
            with self.subTest(name):
                self.assertEqual(c["honored"] + c["violated"] + c["empty"] + c["other"], c["total"])

    def test_substitutions_exclude_ranking_modes(self):
        js = [
            J("a", ["X"], mode="POOR_RANKING"),
            J("b", ["Y"], mode="DUPLICATE_FLOODING"),
            J("c", ["Z"], mode="NO_SEMANTIC_UNDERSTANDING"),
        ]
        sub = _build_substitutions(js)
        self.assertEqual(sub["count"], 1)
        self.assertEqual(sub["examples"][0]["query"], "c")

    def test_ordering_names_better_match_only_when_clearly_on_topic(self):
        ranked = J("boots", ["Sock", "Boot"], mode="POOR_RANKING", sev=Severity.MODERATE,
                   scores=[0.3, 0.8], displacement=1)
        weak = J("tent", ["Mug", "Cup"], mode="PARTIAL_KEYWORD_MATCH", sev=Severity.MODERATE,
                 scores=[0.2, 0.4], displacement=1)
        rows = {r["query"]: r for r in _build_ordering([ranked, weak])["examples"]}
        self.assertEqual(rows["boots"]["better_title"], "Boot")
        self.assertIsNone(rows["tent"]["better_title"])

    def test_specificity_wording_follows_sign(self):
        self.assertIn("slides from 80% on broad searches to 40%", _specificity_text({"broad_rate": 80, "specific_rate": 40}))
        self.assertIn("rises from 40%", _specificity_text({"broad_rate": 40, "specific_rate": 80}))
        self.assertIn("holds at 50%", _specificity_text({"broad_rate": 50, "specific_rate": 50}))

    def test_excluded_judgments_not_counted(self):
        rep = copy.deepcopy(self.fixtures["huckberry_com"])
        js = all_judgments(rep)
        before = build_advanced_diagnostics(rep.site_context, js)["ordering"]["evaluated"]
        for j in js:
            if j.results:
                j.excluded_reason = "fetch_unverified"
                break
        after = build_advanced_diagnostics(rep.site_context, js)["ordering"]["evaluated"]
        self.assertEqual(after, before - 1)

    def test_violation_examples_are_client_safe(self):
        j = J("jacket not wool", ["Wool Jacket"], mode="CONSTRAINT_DROPPED", cat="NEGATIVE_INTENT",
              evidence="Every result is wool (relevance 0.812). User override: kept critical.")
        ex = _build_constraint_obedience([j])["examples"][0]["detail"]
        self.assertEqual(ex, "Every result is wool.")


if __name__ == "__main__":
    unittest.main()
