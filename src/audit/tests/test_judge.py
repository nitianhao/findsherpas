"""Judge: ranking caps, fallback path, exclusions, zero/gibberish rules, guards. Fully offline."""

import unittest
from unittest import mock

import anthropic
import httpx

from src import judge, judge_kb
from src.llm_compat import LLMResponseError
from src.models import FetchOutcome, QueryConstraints, ScoredResult, Severity, TestQuery
import tests.helpers  # noqa: F401  (sets offline API keys)


def R(rank, title, score, price=None, sponsored=False):
    return ScoredResult(rank=rank, title=title, price=price, relevance_score=score, original_rank=rank,
                        sponsored=sponsored)


def V(severity="PASS", failure_mode="OTHER", evidence="The first results match the query.", cited=None,
      fix="Do the fix.", explanation=None, observations="internal notes"):
    return judge.JudgeVerdict.model_construct(
        observations=observations, cited_results=cited or [], evidence=evidence, recommended_fix=fix,
        failure_mode=failure_mode, failure_mode_explanation=explanation, severity=severity)


def TQ(query, category="BROAD_CATEGORY", **kw):
    return TestQuery(category=category, query=query, rationale="test", **kw)


def ranked(top1, best, n=9):
    """#1 scores top1, #n scores best, filler in between never above either."""
    low = min(top1, best)
    rs = [R(1, "Product One", top1)]
    rs += [R(i, f"Filler Item {i}", round(low * 0.9, 4)) for i in range(2, n)]
    rs.append(R(n, "Best Product", best))
    return rs


class _Stub:
    """Replaces judge.structured_call; queue verdicts or exceptions, records calls."""

    def __init__(self, *items):
        self.items = list(items)
        self.calls = []

    def __call__(self, **kw):
        self.calls.append(kw)
        item = self.items.pop(0) if len(self.items) > 1 else self.items[0]
        if isinstance(item, BaseException):
            raise item
        return item


class JudgeTestCase(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(judge_kb, "_embed", side_effect=AssertionError("network: embed"))
        p.start()
        self.addCleanup(p.stop)

    def run_one(self, tq, results, *verdicts, **kw):
        stub = _Stub(*verdicts) if verdicts else _Stub(AssertionError("LLM must not be called"))
        with mock.patch.object(judge, "structured_call", stub):
            j = judge._judge_single_query(tq, results, **kw)
        return j, stub

    def sev(self, j):
        return judge._sev_short(j.severity)


class RankingCapBoundaryTests(JudgeTestCase):
    def test_boundary_table(self):
        # (top1, best, llm severity, expected severity)
        table = [
            (0.05, 0.22, "CRITICAL", "CRITICAL"),   # garbage set: never eased (was -> PASS)
            (0.24, 0.249, "CRITICAL", "CRITICAL"),  # max < 0.25: never eased
            (0.05, 0.22, "MINOR", "MINOR"),         # garbage set: MINOR not turned into PASS
            (0.50, 0.69, "CRITICAL", "PASS"),       # gap 0.19, on-topic #1: cosmetic -> MINOR -> PASS
            (0.50, 0.70, "CRITICAL", "MODERATE"),   # gap exactly 0.20: material, #1 on-topic
            (0.50, 0.60, "MODERATE", "PASS"),       # cosmetic MODERATE -> MINOR -> PASS
            (0.29, 0.60, "CRITICAL", "CRITICAL"),   # off-topic #1 + material gap: CRITICAL allowed
            (0.30, 0.60, "CRITICAL", "MODERATE"),   # #1 exactly at floor counts as on-topic
            (0.28, 0.40, "CRITICAL", "MODERATE"),   # small gap, weak #1: not materially broken
            (0.28, 0.40, "MINOR", "MINOR"),         # weak #1: MINOR is not a cosmetic PASS
        ]
        for top1, best, llm_sev, expected in table:
            with self.subTest(top1=top1, best=best, llm=llm_sev):
                j, _ = self.run_one(TQ("jackets"), ranked(top1, best), V(llm_sev, "POOR_RANKING"))
                self.assertEqual(self.sev(j), expected)

    def test_lowercase_failure_mode_still_capped(self):
        j, _ = self.run_one(TQ("jackets"), ranked(0.5, 0.69), V("critical", "poor_ranking"))
        self.assertEqual(self.sev(j), "PASS")

    def test_generic_critical_cap_needs_cited_top3_title(self):
        res = ranked(0.5, 0.75)
        j, _ = self.run_one(TQ("pullover", "SYNONYM"), res, V("CRITICAL", "PARTIAL_KEYWORD_MATCH"))
        self.assertEqual(self.sev(j), "MODERATE")
        cited = [judge.CitedResult(position=1, title="Product One", problem="wrong type")]
        j, _ = self.run_one(TQ("pullover", "SYNONYM"), res, V("CRITICAL", "PARTIAL_KEYWORD_MATCH", cited=cited))
        self.assertEqual(self.sev(j), "CRITICAL")

    def test_generic_cap_exempt_categories(self):
        for cat in ("DIRECT_MATCH", "BRAND_SEARCH"):
            with self.subTest(cat=cat):
                res = [R(1, "Acme Jacket", 0.6), R(2, "Acme Jacket", 0.6)]
                j, _ = self.run_one(TQ("Acme Jacket", cat), res, V("CRITICAL", "BRAND_BLEED"))
                if cat == "BRAND_SEARCH":
                    self.assertEqual(self.sev(j), "CRITICAL")

    def test_sponsored_excluded_from_ranking_stats(self):
        res = [R(1, "Ad Deodorant", 0.10, sponsored=True), R(2, "Hiking Boot", 0.80), R(3, "Hiking Boot GTX", 0.78)]
        self.assertEqual(judge._compute_stats(res)[2], 0)
        self.assertAlmostEqual(judge._top1_seen_relevance(res), 0.80)
        self.assertFalse(judge._ranking_materially_broken(res))

    def test_zero_results_stats(self):
        self.assertEqual(judge._compute_stats([]), (0.0, 0.0, 0))


class FallbackTests(JudgeTestCase):
    def test_llm_response_error_retried_once_then_fallback_with_guards(self):
        # Weak set on a CATEGORY_MAPPING query: fallback garbage -> category guard still applied.
        res = [R(1, "Gift Card", 0.10), R(2, "Candle", 0.12), R(3, "Mug", 0.09)]
        j, stub = self.run_one(TQ("bedtime wear", "CATEGORY_MAPPING"), res,
                               LLMResponseError("truncated"), LLMResponseError("truncated"))
        self.assertEqual(len(stub.calls), 2)
        self.assertEqual(j.judge_status, "fallback")
        self.assertEqual(j.failure_mode, "CATEGORY_MAPPING_FAILURE")
        self.assertIn("FALLBACK", j.internal_notes)
        self.assertNotIn("LLM", j.evidence)
        self.assertTrue(judge.needs_manual_check(j))

    def test_fallback_pass_runs_weak_filler_guard(self):
        res = [R(1, "Body Oil", 0.30), R(2, "Manuka Honey", 0.31), R(3, "Eye Cream", 0.29)]
        j, _ = self.run_one(TQ("luxury throws", "SUBJECTIVE_ATTRIBUTE"), res, LLMResponseError("x"))
        self.assertEqual(j.judge_status, "fallback")
        self.assertEqual(j.failure_mode, "NO_SEMANTIC_UNDERSTANDING")
        self.assertEqual(self.sev(j), "MODERATE")

    def test_api_error_not_retried(self):
        err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
        j, stub = self.run_one(TQ("jackets"), ranked(0.6, 0.65), err)
        self.assertEqual(len(stub.calls), 1)
        self.assertEqual(j.judge_status, "fallback")

    def test_unparseable_severity_is_failure_not_moderate(self):
        j, stub = self.run_one(TQ("jackets"), ranked(0.6, 0.65), V("SEVERE", "POOR_RANKING"))
        self.assertEqual(len(stub.calls), 2)
        self.assertEqual(j.judge_status, "fallback")
        self.assertEqual(self.sev(j), "PASS")  # stats-only: displacement cosmetic

    def test_fallback_not_harvested(self):
        tq = TQ("jackets")
        with mock.patch.object(judge, "structured_call", _Stub(LLMResponseError("x"))), \
                mock.patch.object(judge_kb, "harvest", return_value=0) as harvest:
            js = judge.judge_all_queries([tq], {"jackets": ranked(0.6, 0.65)}, language=None)
        harvest.assert_not_called()
        self.assertFalse(judge_kb._is_anchor_worthy(js[0]))

    def test_coercion(self):
        self.assertEqual(judge._coerce_failure_mode("poor_ranking"), judge.FailureMode.POOR_RANKING)
        self.assertEqual(judge._coerce_failure_mode("Poor Ranking"), judge.FailureMode.POOR_RANKING)
        self.assertEqual(judge._coerce_failure_mode(judge.FailureModeChoice.BRAND_BLEED), judge.FailureMode.BRAND_BLEED)
        self.assertEqual(judge._coerce_failure_mode("PASS"), judge.FailureMode.OTHER)
        self.assertEqual(judge._coerce_severity("critical"), Severity.CRITICAL)
        self.assertEqual(judge._coerce_severity(Severity.MINOR.value), Severity.MINOR)
        for bad in ("SEVERE", "", "HIGH"):
            with self.assertRaises(ValueError):
                judge._coerce_severity(bad)
        with self.assertRaises(ValueError):
            judge._coerce_failure_mode("BAD_RANKING")


class ExclusionAndZeroTests(JudgeTestCase):
    def outcome(self, q, status="ok", results=(), total_hits=None):
        from src.models import SearchResult
        rs = [SearchResult(rank=i, title=t) for i, t in enumerate(results, 1)]
        return FetchOutcome(query=q, status=status, results=rs, total_hits=total_hits)

    def test_untrusted_fetch_excluded_without_llm(self):
        for status in ("blocked", "timeout", "error", "zero_unverified"):
            with self.subTest(status=status):
                j, stub = self.run_one(TQ("jacket"), [], fetch_outcome=self.outcome("jacket", status))
                self.assertEqual(j.excluded_reason, "fetch_unverified")
                self.assertEqual(j.judge_status, "deterministic")
                self.assertEqual(j.fetch_status, status)
                self.assertEqual(stub.calls, [])

    def test_catalog_gap(self):
        tq = TQ("Wandersch uhe", "SPLIT_WORD", target_term="Wanderschuhe")
        j, stub = self.run_one(tq, [], fetch_outcome=self.outcome(tq.query, "zero_confirmed"),
                               control_outcome=self.outcome("Wanderschuhe", "zero_confirmed"))
        self.assertEqual(j.excluded_reason, "catalog_gap")
        self.assertEqual(stub.calls, [])
        # Untrusted-zero control also counts as a gap.
        j, _ = self.run_one(tq, [], control_outcome=self.outcome("Wanderschuhe", "zero_unverified"))
        self.assertEqual(j.excluded_reason, "catalog_gap")

    def test_zero_with_control_inventory_is_critical_and_cites_control(self):
        tq = TQ("Wandersch uhe", "SPLIT_WORD", target_term="Wanderschuhe")
        j, stub = self.run_one(tq, [], fetch_outcome=self.outcome(tq.query, "zero_confirmed", total_hits=0),
                               control_outcome=self.outcome("Wanderschuhe", "ok", ["Lowa Renegade GTX Mid"]))
        self.assertIsNone(j.excluded_reason)
        self.assertEqual(self.sev(j), "CRITICAL")
        self.assertEqual(j.failure_mode, "NO_FUZZY_MATCHING")
        self.assertIn("Lowa Renegade GTX Mid", j.evidence)
        self.assertEqual(j.displacement, 0)
        self.assertEqual(j.total_hits, 0)
        self.assertEqual(stub.calls, [])

    def test_zero_without_control_makes_no_inventory_claim(self):
        j, _ = self.run_one(TQ("Patago", "PARTIAL_QUERY"), [])
        self.assertEqual(self.sev(j), "CRITICAL")
        for phrase in ("carries", "carry", "stock", "inventory", "almost certainly"):
            self.assertNotIn(phrase, j.evidence.lower())
        self.assertIn("catalog gap is not ruled out", j.internal_notes)

    def test_zero_failure_mode_mapping(self):
        table = {
            "TYPO": "NO_FUZZY_MATCHING", "SPLIT_WORD": "NO_FUZZY_MATCHING", "MERGED_WORDS": "NO_FUZZY_MATCHING",
            "SPECIAL_CHARACTER": "NO_FUZZY_MATCHING", "NATURAL_LANGUAGE": "NO_SEMANTIC_UNDERSTANDING",
            "SEMANTIC_MEANING": "NO_SEMANTIC_UNDERSTANDING", "OCCASION": "NO_SEMANTIC_UNDERSTANDING",
            "PRICE_ANCHORED": "FACET_NOT_EXTRACTED", "NEGATIVE_INTENT": "CONSTRAINT_DROPPED",
            "CATEGORY_MAPPING": "CATEGORY_MAPPING_FAILURE", "SKU_MODEL_NUMBER": "ZERO_RESULTS_OR_GARBAGE",
        }
        for cat, fm in table.items():
            with self.subTest(cat=cat):
                j, _ = self.run_one(TQ("waterproof jacket under £100", cat), [],
                                    site_categories=["Waterproof Jackets"])
                self.assertEqual(j.failure_mode, fm)
                self.assertEqual(j.judge_status, "deterministic")

    def test_gibberish_rules(self):
        j, stub = self.run_one(TQ("xqzvkj", "GIBBERISH"), [])
        self.assertEqual(self.sev(j), "PASS")
        self.assertEqual(j.judge_status, "deterministic")
        j, stub = self.run_one(TQ("xqzvkj", "GIBBERISH"), [R(1, "Wool Socks", 0.9), R(2, "Mug", 0.8)])
        self.assertEqual(self.sev(j), "CRITICAL")
        self.assertEqual(j.failure_mode, "ZERO_RESULTS_OR_GARBAGE")
        self.assertIn("Wool Socks", j.evidence)
        self.assertEqual(stub.calls, [])

    def test_prompt_shows_original_order_and_total_hits_no_ideal_ranking(self):
        tq = TQ("jacket", target_term="jacket")
        res = [R(1, "Rain Jacket", 0.6), R(2, "Down Jacket", 0.8)]
        j, stub = self.run_one(tq, res, V(), fetch_outcome=self.outcome("jacket", "ok", ["a", "b"], total_hits=120),
                               language=None)
        user = stub.calls[0]["user"]
        self.assertIn("Hit count the page itself reports: 120", user)
        self.assertNotIn("SHOULD", user)
        self.assertNotIn("#16", user)
        self.assertLess(user.index("Rain Jacket"), user.index("Down Jacket"))
        self.assertIn("Severity criteria", stub.calls[0]["system"])
        self.assertNotIn("Severity criteria", user)
        self.assertEqual(j.total_hits, 120)
        self.assertEqual(j.fetch_status, "ok")

    def test_kb_examples_come_last_in_user_message(self):
        recs = [{"query": "Regenjacke", "category": "SYNONYM", "severity": "PASS", "failure_mode": "OTHER",
                 "evidence": "Good (relevance 0.91).", "recommended_fix": ""}]
        with mock.patch.object(judge_kb, "load_calibration_examples", return_value=recs):
            _, stub = self.run_one(TQ("Jacke", "SYNONYM"), [R(1, "Jacke", 0.7)], V(), language="German")
        user = stub.calls[0]["user"]
        self.assertTrue(user.rstrip().endswith("fix:"))
        self.assertGreater(user.index("Calibration examples"), user.index("Key stats"))
        self.assertNotIn("0.91", user)

    def test_dedupe_queries(self):
        tq = TQ("Fahrradhelm")
        with mock.patch.object(judge, "structured_call", _Stub(V())):
            js = judge.judge_all_queries([tq, TQ("fahrradhelm "), tq], {"Fahrradhelm": [R(1, "Fahrradhelm X", 0.8)]})
        self.assertEqual(len(js), 1)


class GuardTests(JudgeTestCase):
    def test_multilingual_negation_parsing(self):
        table = {
            "running shoes not Nike": "nike", "Tasche nicht Leder": "leder", "Tasche ohne Leder": "leder",
            "Laufschuhe keine Nike": "nike", "hårbalsam utan silikon": "silikon", "deodorant inte Rexona": "rexona",
            "sko uden snørebånd": "snoreband", "jakke uten hette": "hette", "jas zonder capuchon": "capuchon",
            "sac sans cuir": "cuir", "shampoo fragrance free": "fragrance", "schampo parfymfritt": "parfym",
        }
        for q, term in table.items():
            with self.subTest(q=q):
                self.assertEqual(judge._excluded_term(q), term)
        self.assertIsNone(judge._excluded_term("winter jacket"))

    def test_constraints_exclude_preferred(self):
        tq = TQ("jacket for rain", "NEGATIVE_INTENT", constraints=QueryConstraints(exclude=["Gore-Tex"]))
        self.assertEqual(judge._excluded_term(tq), "gore tex")

    def test_word_boundary_violations(self):
        cases = [
            ("sneakers without laces", "Laceless Sneaker", False),
            ("sneakers without laces", "Sneaker with laces", True),
            ("Tasche ohne Leder", "Lederjacke Classic", True),
            ("Tasche ohne Leder", "Kunstleder Shopper", True),
            ("Tasche ohne Leder", "Lederfreie Tasche", False),
            ("bag not leather", "Faux Leather Tote", True),
            ("schampo utan parfym", "Schampo parfymfri 250 ml", False),
            ("shampoo not perfume", "Shampoo perfume free", False),
            ("knitwear not wool", "Woolrich Parka", False, "en"),
            ("Pullover ohne Wolle", "Wollpullover Classic", True, "de"),
            ("boots not waterproof", "Salomon XT-6 GTX Trail Sneaker", True, "en"),
            ("jumper not wool", "Merino Crew Jumper", True, "en"),
            ("jumper not wool", "Cotton Crew Jumper", False, "en"),
        ]
        for q, title, violates, *lang in cases:
            with self.subTest(q=q, title=title):
                frac, bad, _ = judge._exclusion_violations(q, [R(1, title, 0.7)], None, (lang or [None])[0])
                self.assertEqual(bool(bad), violates)

    def test_negative_intent_guard_end_to_end(self):
        res = [R(i, f"Ledertasche Modell {i}", 0.7) for i in range(1, 6)]
        j, _ = self.run_one(TQ("Tasche nicht Leder", "NEGATIVE_INTENT"), res, V("PASS"))
        self.assertEqual(j.failure_mode, "CONSTRAINT_DROPPED")
        self.assertEqual(self.sev(j), "CRITICAL")
        self.assertIn("Ledertasche Modell", j.evidence)

    def test_negative_intent_under_retrieval_keeps_constraint_dropped(self):
        j, _ = self.run_one(TQ("Gartenleuchte nicht solar", "NEGATIVE_INTENT"), [R(1, "Bodenleuchte Piek Mini", 0.42)],
                            V("CRITICAL", "CONSTRAINT_DROPPED"), language="de")
        self.assertEqual((j.failure_mode, self.sev(j)), ("CONSTRAINT_DROPPED", "CRITICAL"))

    def test_facet_flooding_pass_with_title_invisible_rest(self):
        res = [R(i, "Knabstrup Keramik Colorit Skål", 0.88) for i in range(1, 9)] + \
              [R(9, "Lyngby Porcelæn Rhombe Skål", 0.8), R(10, "Kähler Hammershøi Skål", 0.8)]
        j, _ = self.run_one(TQ("skål keramik", "FACET_EXTRACTION"), res, V("PASS"), language="Danish")
        self.assertEqual(self.sev(j), "PASS")
        self.assertIn("MANUAL CHECK", j.internal_notes)
        res[0] = R(1, "Glas Skål Klar", 0.88)
        j, _ = self.run_one(TQ("skål keramik", "FACET_EXTRACTION"), res, V("PASS"), language="Danish")
        self.assertEqual(j.failure_mode, "DUPLICATE_FLOODING")

    def test_category_resemblance(self):
        self.assertIsNone(judge._resembles_site_category("new home present", ["House & Home"]))
        self.assertEqual(judge._resembles_site_category("Father's Day gift ideas", ["Father's Day Gifting"]),
                         "Father's Day Gifting")
        self.assertIsNone(judge._resembles_site_category("jacket under 100", ["Jackets"], "PRICE_ANCHORED"))
        self.assertIsNone(judge._resembles_site_category("jacket not leather", ["Jackets"], "NEGATIVE_INTENT"))
        # OCCASION zero is never reclassified to a category mapping failure.
        j, _ = self.run_one(TQ("new home present", "OCCASION"), [], site_categories=["House & Home"])
        self.assertEqual(j.failure_mode, "NO_SEMANTIC_UNDERSTANDING")
        j, _ = self.run_one(TQ("Gartenmöbel", "LOCALE_VARIATION"), [], site_categories=["Gartenmöbel"])
        self.assertEqual(j.failure_mode, "CATEGORY_MAPPING_FAILURE")
        self.assertIn("'Gartenmöbel' category", j.evidence)

    def test_unicode_core_terms(self):
        self.assertEqual(judge._tokens("Kök & Skål"), ["kok", "skal"])
        self.assertFalse(judge._core_terms_absent("skål keramik", [R(1, "Skål i keramik", 0.4)]))
        self.assertFalse(judge._core_terms_absent("kök", [R(1, "Köksredskap kök", 0.4)]))
        self.assertTrue(judge._core_terms_absent("skål", [R(1, "Bodylotion", 0.4)]))
        self.assertFalse(judge._core_terms_absent("Kaffeekanne", [R(1, "Kaffeekannen Set", 0.4)]))

    def test_lexicons_and_synonyms(self):
        self.assertEqual(judge._attr_values("Damen Laufschuhe blau", "colour", "de"), {"blue"})
        self.assertEqual(judge._attr_values("svarta skor", "colour", "sv"), {"black"})
        self.assertEqual(judge._attr_values("Mammut Nordwand GTX", "material", "en"), {"waterproof"})
        self.assertEqual(judge._attr_values("Gore-Tex Jacket", "material", "en"), {"waterproof"})
        self.assertEqual(judge._attr_values("Fair Isle Jumper", "material", "en"), {"wool"})
        self.assertEqual(judge._attr_values("Merino Crew", "material", "en"), {"wool"})
        self.assertEqual(judge._attr_values("Lederjacke", "material", "de"), {"leather"})
        self.assertEqual(judge._attr_values("downhill ski", "material", "en"), set())
        self.assertEqual(judge._attr_values("fishing rod", "colour", "en"), set())
        res = [R(1, "Mammut Nordwand GTX", 0.8)]
        self.assertIsNone(judge._unverifiable_constraint_token("Wanderjacke wasserdicht", res, "de"))
        self.assertEqual(judge._unverifiable_constraint_token("Laufschuhe blau", [R(1, "Pegasus 41", 0.8)], "de"), "blue")

    def test_price_parser(self):
        table = {"1.299,00 €": 1299.0, "kr 499": 499.0, "£45": 45.0, "$1,299.99": 1299.99, "499:-": 499.0,
                 "29,99 €": 29.99, "1 299 kr": 1299.0, "€99.50 €129.00": 99.5, "49,- €": 49.0, None: None, "": None}
        for raw, val in table.items():
            with self.subTest(raw=raw):
                self.assertEqual(judge.parse_price(raw), val)
        self.assertEqual(judge._price_bounds(TQ("Fahrradhelm unter 80 Euro", "PRICE_ANCHORED")), (None, 80.0))
        self.assertEqual(judge._price_bounds(TQ("jacket", "PRICE_ANCHORED",
                                                constraints=QueryConstraints(price_max=100))), (None, 100.0))

    def test_price_guard_end_to_end(self):
        res = [R(i, f"Fahrradhelm {i}", 0.8, price=f"{90 + i},50 €") for i in range(1, 6)]
        j, _ = self.run_one(TQ("Fahrradhelm unter 80 Euro", "PRICE_ANCHORED"), res, V("MINOR", "POOR_RANKING"))
        self.assertEqual(j.failure_mode, "CONSTRAINT_DROPPED")
        self.assertEqual(self.sev(j), "CRITICAL")
        self.assertIn("Fahrradhelm 1", j.evidence)

    def test_constraint_dropped_requires_citation(self):
        res = [R(1, "Sport-BH Pro", 0.8), R(2, "Sport-BH Run", 0.8)]
        j, _ = self.run_one(TQ("Sport-BH schwarz", "MULTI_ATTRIBUTE"), res, V("MODERATE", "CONSTRAINT_DROPPED"),
                            language="German")
        self.assertEqual(self.sev(j), "PASS")
        self.assertIn("MANUAL CHECK", j.internal_notes)
        self.assertNotIn("MANUAL", j.evidence)
        cited = [judge.CitedResult(position=2, title="Sport-BH Run", problem="is pink")]
        j, _ = self.run_one(TQ("Sport-BH schwarz", "MULTI_ATTRIBUTE"), res,
                            V("MODERATE", "CONSTRAINT_DROPPED", cited=cited), language="German")
        self.assertEqual(j.failure_mode, "CONSTRAINT_DROPPED")

    def test_flooding_only_passes_for_resolved_capabilities(self):
        res = [R(i, "Le Creuset Signature Gryde", 0.8) for i in range(1, 7)] + [R(7, "Kasserolle", 0.7)]
        for cat in ("TYPO", "SYNONYM", "ABBREVIATION", "PLURAL_SINGULAR"):
            with self.subTest(cat=cat):
                j, _ = self.run_one(TQ("Le Crueset gryder", cat), res, V("MODERATE", "DUPLICATE_FLOODING"))
                self.assertEqual(self.sev(j), "PASS")
        j, _ = self.run_one(TQ("Le Creuset", "BRAND_SEARCH"), res, V("PASS"))
        self.assertEqual(j.failure_mode, "DUPLICATE_FLOODING")

    def test_direct_match_tolerant_and_near_miss(self):
        q = "Beauty of Joseon Glow Serum Propolis + Niacinamide 30 ml"
        res = [R(1, "Glow Serum Beauty of Joseon Propolis+Niacinamide 30ml", 0.95)]
        j, _ = self.run_one(TQ(q, "DIRECT_MATCH"), res, V("MODERATE", "PARTIAL_KEYWORD_MATCH"))
        self.assertEqual(self.sev(j), "PASS")
        res = [R(1, "Scarpa Womens Mojito Wrap GTX Shoes", 0.9), R(2, "Scarpa Womens Mojito GTX Shoes", 0.95)]
        j, _ = self.run_one(TQ("Scarpa Womens Mojito GTX Shoes", "DIRECT_MATCH"), res, V("MODERATE", "PARTIAL_KEYWORD_MATCH"))
        self.assertEqual(self.sev(j), "MINOR")
        res = [R(1, "Other Brand Boot", 0.4), R(2, "Another Thing", 0.3), R(3, "Scarpa Womens Mojito GTX Shoes", 0.95)]
        j, _ = self.run_one(TQ("Scarpa Womens Mojito GTX Shoes", "DIRECT_MATCH"), res, V("PASS"))
        self.assertEqual(self.sev(j), "MODERATE")

    def test_client_evidence_is_sanitised(self):
        ev = ("The first result is a rain jacket (relevance 0.82). The reranker scored it 0.82. "
              "It costs 1.299,00 € and is the right type.")
        j, _ = self.run_one(TQ("Regenjacke", "SYNONYM"), [R(1, "Regenjacke", 0.82)], V("PASS", evidence=ev))
        self.assertNotIn("0.82", j.evidence)
        self.assertNotIn("reranker", j.evidence.lower())
        self.assertIn("1.299,00 €", j.evidence)
        self.assertIn("Raw evidence", j.internal_notes)
        self.assertIn("internal notes", j.internal_notes)


if __name__ == "__main__":
    unittest.main()
