"""Judge KB: language normalisation, retrieval filtering, pending harvest, promote, migrated files."""

import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from src import judge, judge_kb
from src.models import QueryJudgment, ScoredResult, Severity, TestQuery
from tests.helpers import AUDIT_ROOT

RV = judge.JUDGE_RULES_VERSION


def _judgment(query="Regenjacke", status="llm", excluded=None, severity=Severity.PASS, fm="OTHER", cat="SYNONYM"):
    return QueryJudgment(
        test_query=TestQuery(category=cat, query=query, rationale="t"),
        results=[ScoredResult(rank=1, title=f"{query} Pro", relevance_score=0.8, original_rank=1),
                 ScoredResult(rank=2, title=f"{query} Lite", relevance_score=0.7, original_rank=2)],
        failure_mode=fm, severity=severity, evidence="The first result is a rain jacket.",
        recommended_fix="", displacement=0, max_relevance_score=0.8, top3_original_average=0.75,
        judge_status=status, excluded_reason=excluded,
    )


class _TempKB(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("_KB_DIR", "_KB_HARVEST_DIR"):
            p = mock.patch.object(judge_kb, name, self.tmp)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(judge_kb, "_embed", return_value=None)  # offline
        p.start()
        self.addCleanup(p.stop)

    def records(self, code):
        path = self.tmp / f"{code}.jsonl"
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


class LanguageTests(unittest.TestCase):
    def test_normalise(self):
        table = {"German": "de", "Deutsch": "de", "de": "de", "de-CH": "de", "de_DE": "de", "GER": "de",
                 "Swedish": "sv", "svenska": "sv", "sv-SE": "sv", "sv": "sv", "Danish": "da", "Norwegian": "no",
                 "nb": "no", "Bokmål": "no", "Dutch": "nl", "English": "en", "en-GB": "en", "Français": "fr",
                 "": "unknown", None: "unknown", "Klingon": "klingon"}
        for raw, code in table.items():
            with self.subTest(raw=raw):
                self.assertEqual(judge_kb.normalize_language(raw), code)
        self.assertEqual(judge_kb.kb_path("German").name, "de.jsonl")
        self.assertEqual(judge_kb.kb_path("sv").name, judge_kb.kb_path("Swedish").name)

    def test_domain(self):
        self.assertEqual(judge_kb.normalize_domain("https://www.Bergzeit.de/search?q=x"), "bergzeit.de")
        self.assertEqual(judge_kb.normalize_domain("bergzeit_de"), "bergzeit.de")


class RetrievalTests(_TempKB):
    def test_filtering(self):
        base = {"category": "SYNONYM", "severity": "PASS", "failure_mode": "OTHER", "evidence": "e",
                "recommended_fix": "", "language": "de"}
        rows = [
            {**base, "query": "ok-current", "status": "active", "rules_version": RV, "domain": "a.de"},
            {**base, "query": "ok-reviewed", "status": "active", "rules_version": "legacy", "human_reviewed": True},
            {**base, "query": "stale", "status": "active", "rules_version": "legacy"},
            {**base, "query": "pending", "status": "pending", "rules_version": RV},
            {**base, "query": "retired", "status": "retired", "rules_version": RV},
            {**base, "query": "same-site", "status": "active", "rules_version": RV, "domain": "bergzeit.de"},
        ]
        judge_kb.write_records(self.tmp / "de.jsonl", rows)
        got = judge_kb.load_calibration_examples("German", "SYNONYM", "Jacke", top_k=10,
                                                 domain="https://www.bergzeit.de", rules_version=RV)
        self.assertEqual(sorted(r["query"] for r in got), ["ok-current", "ok-reviewed"])

    def test_format_strips_scores(self):
        out = judge_kb.format_calibration_section([{"query": "q", "evidence": "Top hit (relevance 0.91) is right.",
                                                    "recommended_fix": "", "severity": "PASS"}])
        self.assertNotIn("0.91", out)


class HarvestTests(_TempKB):
    def test_pending_with_metadata(self):
        n = judge_kb.harvest([_judgment()], "German", {"domain": "bergzeit_de"}, model=judge._DEFAULT_MODEL)
        self.assertEqual(n, 1)
        rec = self.records("de")[0]
        self.assertEqual(rec["status"], "pending")
        self.assertEqual(rec["language"], "de")
        self.assertEqual(rec["domain"], "bergzeit.de")
        self.assertEqual(rec["rules_version"], RV)
        self.assertEqual(rec["model"], judge._DEFAULT_MODEL)
        self.assertFalse(rec["human_reviewed"])
        self.assertEqual((rec["top1"], rec["max"], rec["n_results"]), (0.8, 0.8, 2))
        self.assertEqual(rec["titles"], ["Regenjacke Pro", "Regenjacke Lite"])
        # Pending is never retrieved.
        self.assertEqual(judge_kb.load_calibration_examples("de", "SYNONYM", "x", rules_version=RV), [])

    def test_skips_fallback_excluded_deterministic(self):
        js = [_judgment("a", status="fallback"), _judgment("b", excluded="catalog_gap"),
              _judgment("c", status="deterministic"), _judgment("d")]
        self.assertEqual(judge_kb.harvest(js, "de", {"domain": "x.de"}), 1)
        self.assertEqual([r["query"] for r in self.records("de")], ["d"])

    def test_refuses_non_default_model(self):
        self.assertEqual(judge_kb.harvest([_judgment()], "de", {}, model="claude-haiku-4-5"), 0)
        self.assertEqual(self.records("de"), [])

    def test_dedup_domain_query(self):
        judge_kb.harvest([_judgment("Regenjacke")], "de", {"domain": "x.de"})
        judge_kb.harvest([_judgment("regenjacke "), _judgment("Hose")], "de", {"domain": "x.de"})
        judge_kb.harvest([_judgment("Regenjacke")], "de", {"domain": "y.de"})
        self.assertEqual(sorted((r["domain"], r["query"]) for r in self.records("de")),
                         [("x.de", "Hose"), ("x.de", "Regenjacke"), ("y.de", "Regenjacke")])

    def test_promote_command(self):
        spec = importlib.util.spec_from_file_location("kb_prune", AUDIT_ROOT / "scripts" / "kb_prune.py")
        kb_prune = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kb_prune)
        judge_kb.harvest([_judgment("Regenjacke"), _judgment("Hose")], "de", {"domain": "x.de"})
        with mock.patch.object(kb_prune, "kb_path", lambda lang: self.tmp / f"{judge_kb.normalize_language(lang)}.jsonl"):
            kb_prune.cmd_promote(Namespace(language="German", match="Regen", all_pending=False, domain=None, dry_run=False))
        recs = {r["query"]: r for r in self.records("de")}
        self.assertEqual(recs["Regenjacke"]["status"], "active")
        self.assertTrue(recs["Regenjacke"]["human_reviewed"])
        self.assertEqual(recs["Hose"]["status"], "pending")
        got = judge_kb.load_calibration_examples("de", "SYNONYM", "x", rules_version=RV)
        self.assertEqual([r["query"] for r in got], ["Regenjacke"])


class MigratedKBTests(unittest.TestCase):
    """The checked-in KB after the 2026-10-30 migration."""

    def load(self, code):
        path = AUDIT_ROOT / "kb" / f"{code}.jsonl"
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def test_files_are_iso_coded_and_versioned(self):
        names = sorted(p.name for p in (AUDIT_ROOT / "kb").glob("*.jsonl"))
        self.assertEqual(names, ["de.jsonl", "sv.jsonl"])
        for code in ("de", "sv"):
            for r in self.load(code):
                self.assertEqual(r["language"], code)
                self.assertIn("rules_version", r)
                self.assertIn("human_reviewed", r)

    def test_stale_records_retired(self):
        sv = [r for r in self.load("sv") if r["status"] == "active"]
        self.assertFalse([r for r in sv if r["failure_mode"] == "POOR_RANKING" and r["severity"] in ("CRITICAL", "MINOR")])
        self.assertFalse([r for r in sv if r["category"] == "USE_CASE"])
        de = {r["query"]: r for r in self.load("de")}
        self.assertEqual(de["Tischleuchte Sonnenglas®"]["status"], "retired")
        for r in self.load("sv") + self.load("de"):
            if r["status"] == "retired":
                self.assertTrue(r.get("retired_reason"))


if __name__ == "__main__":
    unittest.main()
