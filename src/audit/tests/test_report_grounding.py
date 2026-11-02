"""Grounded narratives: validator, structured LLM path (stubbed), sanitiser, language cap,
proof of stock and the shared stats rules. Fully offline."""

from __future__ import annotations

import copy
import unittest
from types import SimpleNamespace

from src.llm_compat import LLMResponseError
from src.models import QueryJudgment, ScoredResult, Severity, SiteContext, TestQuery
from src.report_generator import (
    DeepDiveExampleOut,
    DeepDiveSectionOut,
    DeepDivesOut,
    GroundingError,
    RoadmapItemOut,
    RoadmapOut,
    _limit_language_mentions,
    build_executive_summary,
    build_full_query_appendix_markdown,
    failing_judgments,
    generate_deep_dives,
    generate_report,
    generate_roadmap,
    grounding_violations,
)
from src.report_stats import (
    by_original,
    compute_stats,
    pick_worst_example,
    proof_of_stock,
    sanitize_client_text,
    search_url,
    whats_working_items,
)
from tests.helpers import FakeClient, all_judgments, historical_reports


def parsed(obj, stop_reason="end_turn"):
    return SimpleNamespace(parsed_output=obj, stop_reason=stop_reason, content=[],
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1, cache_read_input_tokens=0,
                                                 cache_creation_input_tokens=0))


def J(query, titles=(), sev=Severity.CRITICAL, mode="NO_SEMANTIC_UNDERSTANDING", cat="SYNONYM",
      evidence="Plain observation.", scores=None, displacement=0, target_term=None):
    scores = scores or [0.2] * len(titles)
    results = [ScoredResult(rank=i + 1, title=t, relevance_score=s, original_rank=i + 1)
               for i, (t, s) in enumerate(zip(titles, scores))]
    return QueryJudgment(
        test_query=TestQuery(category=cat, query=query, rationale="r", target_term=target_term),
        results=results, failure_mode=mode, severity=sev, evidence=evidence, recommended_fix="f",
        displacement=displacement, max_relevance_score=max(scores, default=0.0),
        top3_original_average=sum(scores[:3]) / 3 if scores else 0.0,
    )


SITE = SiteContext(url="https://shop.example", site_name="Shop", site_type="PHYSICAL_GOODS",
                   nav_categories=["Rain Jackets"], primary_language="German",
                   search_url_template="https://shop.example/s?q={}")


class GroundingValidatorTests(unittest.TestCase):
    def setUp(self):
        self.a = J("regenjacke herren", ["Vaude Regenjacke Escape", "Socken Merino"], displacement=0)
        self.b = J("hängematte groß", [])
        self.all = [self.a, self.b]

    def test_clean_text_passes(self):
        text = 'Searching "regenjacke herren" showed "Vaude Regenjacke Escape" at #1, then "Socken Merino" at #2.'
        self.assertEqual(grounding_violations(text, [self.a], self.all), [])

    def test_invented_title_caught(self):
        v = grounding_violations('The shopper saw "Patagonia Torrentshell 3L" first.', [self.a], self.all)
        self.assertTrue(any("Patagonia Torrentshell 3L".casefold() in p for p in v), v)

    def test_invented_query_caught(self):
        v = grounding_violations('A shopper typing "waterproof trail runners size 44" got nothing.', [self.b], self.all)
        self.assertTrue(v)

    def test_wrong_position_caught(self):
        v = grounding_violations('The better match sat at #9.', [self.a], self.all)
        self.assertTrue(any("#9" in p for p in v))
        self.assertTrue(grounding_violations('It was at #1.', [self.b], self.all))  # zero results: no #N

    def test_carry_claim_needs_proof(self):
        claim = 'Searching "hängematte groß" returned nothing, even though the store carries hammocks.'
        self.assertTrue(any("carries" in p for p in grounding_violations(claim, [self.b], self.all)))
        proven = J("hängematte groß", [], evidence="Zero results. Searching 'Hängematte' returns products such as 'Hängematte CHICO'.")
        self.assertEqual(grounding_violations(claim, [proven], [self.a, proven]), [])

    def test_single_quoted_word_and_partial_title_ok(self):
        self.assertEqual(grounding_violations('Every result ignored "herren"; "Vaude Regenjacke" led.', [self.a], self.all), [])


class StructuredPathTests(unittest.TestCase):
    def setUp(self):
        self.report = copy.deepcopy(historical_reports()["huckberry_com"])
        self.js = all_judgments(self.report)
        self.fails = failing_judgments(self.js)

    def _dives(self, invent=False):
        from src.report_generator import _capability_groups
        groups = _capability_groups(self.fails, self.js)
        sections = []
        for cid, (_, ids) in enumerate(groups):
            exs = []
            for i in ids[:2]:
                j = self.fails[i]
                top = by_original(j)
                title = "Totally Invented Jacket 9000" if invent else (top[0].title if top else None)
                text = f'"{j.test_query.query}" showed "{title}" first.' if title else f'"{j.test_query.query}" returned nothing.'
                exs.append(DeepDiveExampleOut(query_id=i, narrative=text))
            sections.append(DeepDiveSectionOut(capability_id=cid, intro="Why this matters.", examples=exs))
        return DeepDivesOut(sections=sections)

    def _roadmap(self, ids):
        return RoadmapOut(items=[RoadmapItemOut(query_ids=ids, title="Treat price phrases as a filter",
                                                description="Shoppers see items within their limit.",
                                                impact="Critical", effort="Quick Win", owner="dev")])

    def test_regenerates_once_then_accepts(self):
        client = FakeClient([parsed(self._dives(invent=True)), parsed(self._dives())])
        out = generate_deep_dives(self.report.site_context, self.js, client=client)
        self.assertEqual(len(client.messages.calls), 2)
        self.assertIn("REJECTED", client.messages.calls[1]["messages"][0]["content"])
        self.assertTrue(out and all(s["examples"] for s in out))

    def test_raises_after_second_violation(self):
        client = FakeClient([parsed(self._dives(invent=True)), parsed(self._dives(invent=True))])
        with self.assertRaises(GroundingError):
            generate_deep_dives(self.report.site_context, self.js, client=client)

    def test_roadmap_bad_ids_regenerated_and_reach_from_ids(self):
        client = FakeClient([parsed(self._roadmap([999])), parsed(self._roadmap([0, 1]))])
        items = generate_roadmap(self.report.site_context, self.js, client=client)
        self.assertEqual(items[0]["queries"], [self.fails[0].test_query.query, self.fails[1].test_query.query])

    def test_llm_failure_never_yields_placeholder(self):
        client = FakeClient([parsed(None), parsed(None)])
        with self.assertRaises(LLMResponseError):
            generate_report(self.report.site_context, self.js, client=client)
        client = FakeClient([parsed(self._dives(), stop_reason="max_tokens")])
        with self.assertRaises(LLMResponseError):
            generate_deep_dives(self.report.site_context, self.js, client=client)

    def test_full_report_via_structured_calls(self):
        client = FakeClient([parsed(self._dives()), parsed(self._roadmap([0, 2]))])
        rep = generate_report(self.report.site_context, self.js, client=client)
        content = rep.run_metadata["report_content"]
        self.assertTrue(content["deep_dives"] and content["roadmap"])
        self.assertIn("Treat price phrases as a filter", rep.deep_dive_narrative)
        self.assertNotIn("not generated", rep.deep_dive_narrative)
        # system rules are static (cacheable); per-site data only in the user turn
        self.assertNotIn(self.fails[0].test_query.query, client.messages.calls[0]["system"][0]["text"])
        self.assertNotIn("Avoca", client.messages.calls[0]["system"][0]["text"])
        self.assertNotIn("$50", client.messages.calls[0]["system"][0]["text"])

    def test_supplied_ungrounded_content_rejected(self):
        bad = [{"title": "Fix", "description": 'Stop showing "Imaginary Boot".', "impact": "High",
                "effort": "Quick Win", "owner": "dev", "queries": [self.fails[0].test_query.query]}]
        with self.assertRaises(GroundingError):
            generate_report(self.report.site_context, self.js, deep_dives=[], roadmap=bad)


class SanitiserTests(unittest.TestCase):
    def test_strips_scores_and_markers(self):
        raw = ("The best-scoring result (Inked Cherry Coin Purse, relevance 0.777) was ranked #2. "
               "Max relevance score is 0.000 and total results returned is 0. "
               "User override: downgraded per calibration. [MANUAL VERIFICATION REQUIRED] "
               "The relevance gap is only 0.012. Instead the customer saw two throws first.")
        out = sanitize_client_text(raw)
        for bad in ("0.", "relevance", "override", "calibration", "MANUAL", "score"):
            self.assertNotIn(bad, out)
        self.assertIn("best-matching result was ranked #2", out)
        self.assertIn("Instead the customer saw two throws first.", out)

    def test_historical_evidence_is_clean_after_sanitising(self):
        from tests.test_report_render import forbidden_hits
        for name, rep in historical_reports().items():
            for j in all_judgments(rep):
                self.assertEqual(forbidden_hits(sanitize_client_text(j.evidence)), [], (name, j.evidence[:80]))


class LanguageCapTests(unittest.TestCase):
    def test_never_edits_quotes_and_recapitalises_only_edits(self):
        text = ('German synonym mapping is missing. Map "German army knife" too. '
                '**Bold** text stays. Add German category terms.')
        out, n = _limit_language_mentions(text, "German", already_kept=1)
        self.assertIn('"German army knife"', out)
        self.assertTrue(out.startswith("Synonym mapping is missing."))
        self.assertIn("**Bold** text stays.", out)
        self.assertIn("Add category terms.", out)
        self.assertEqual(n, 3)

    def test_noun_use_kept(self):
        out, _ = _limit_language_mentions("Searches written in German.", "German", already_kept=5)
        self.assertEqual(out, "Searches written in German.")


class StatsRuleTests(unittest.TestCase):
    def test_proof_of_stock_unicode(self):
        a = J("hängematte groß", [])
        b = J("hängematte", ["Hängematte CHICO", "Hängematten-Gestell"], sev=Severity.PASS, mode="OTHER")
        proof = proof_of_stock(a, [a, b])
        self.assertIsNotNone(proof)
        self.assertEqual(proof["example_title"], "Hängematte CHICO")

    def test_worst_example_category_claim_needs_real_nav_category(self):
        j = J("cosy loungewear", [], mode="CATEGORY_MAPPING_FAILURE", cat="CATEGORY_MAPPING",
              evidence="Zero results despite a matching category 'Sleep & Loungewear'.")
        self.assertNotIn("you have", pick_worst_example([j], nav_categories=[]))
        self.assertIn("you have a \"Sleep & Loungewear\" category",
                      pick_worst_example([j], nav_categories=["Sleep & Loungewear"]))

    def test_exec_summary_never_claims_stock_without_proof(self):
        j = J("summer things", [])
        summary = build_executive_summary(SITE, [j], compute_stats([j]))
        self.assertNotIn("carries", summary)

    def test_position_wording_follows_value(self):
        top = J("boots", ["Boot A", "Boot B"], sev=Severity.MINOR, mode="POOR_RANKING", scores=[0.7, 0.8])
        s = build_executive_summary(SITE, [top], compute_stats([top]))
        self.assertIn("#1.0", s)
        self.assertNotIn("past the first three", s)

    def test_whats_working_fallback_is_true(self):
        js = [J(f"q{i}", ["Item"], mode="POOR_RANKING", sev=Severity.MODERATE, displacement=1, scores=[0.5])
              for i in range(5)]
        js.append(J("nkie", [], mode="NO_FUZZY_MATCHING", cat="TYPO"))
        items = {i["label"]: i["text"] for i in whats_working_items(js)}
        self.assertIn("for 5 of 6 tested searches", items["Search returns products"])
        self.assertNotIn("Misspellings are often recognised", items)

    def test_md_table_escapes_pipes_and_links(self):
        j = J("a | b", ["X"], mode="POOR_RANKING", sev=Severity.MINOR, displacement=1, scores=[0.5])
        md = build_full_query_appendix_markdown([j], "https://shop.example/s?q={}")
        self.assertIn("a \\| b", md)
        self.assertIn("(https://shop.example/s?q=a+%7C+b)", md)

    def test_search_url(self):
        self.assertEqual(search_url("https://x.test/s?q={query}&p=1", "rot & grün"), "https://x.test/s?q=rot+%26+gr%C3%BCn&p=1")
        self.assertIsNone(search_url("", "x"))


if __name__ == "__main__":
    unittest.main()
