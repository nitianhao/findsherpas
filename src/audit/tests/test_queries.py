"""Query generation: deterministic categories, reallocation, top-ups, validators, malformed output,
retry feedback and provenance. The LLM is stubbed with FakeClient (parsed_output = batch)."""

import json
import unittest
from unittest import mock

import tests.helpers  # noqa: F401 — sets offline API keys
from src import query_generator as qg
from src.models import QueryCategory as C
from src.models import QueryConstraints, SiteContext, SiteType, TestQuery
from tests.helpers import FakeClient, fake_text_response


def _batch(*entries):
    r = fake_text_response("{}")
    r.parsed_output = {"queries": list(entries)}
    return r


def _q(cat, query, target, constraints=None, rationale="grounded in sampled titles"):
    return {"category": cat.value, "query": query, "target_term": target, "rationale": rationale,
            "constraints": constraints}


def _ctx(**kw):
    base = dict(
        url="https://www.bergzeit.de",
        site_name="Bergzeit",
        site_type=SiteType.PHYSICAL_GOODS,
        primary_language="German",
        locale="de-DE",
        currency="EUR",
        nav_categories=["Jacken", "Schuhe", "Hosen"],
        brands=["Salomon", "Mammut", "Mini Rodini"],
        featured_items=["Salomon X Ultra 4 GTX", "Mini Rodini barnkläder", "Jacken"],
        catalog_sample=["Mammut Nordwand Jacke Herren", "Salomon Wanderschuhe Herren", "Mammut Handschuhe Damen",
                        "Vaude Pullover Wolle", "Ortovox Hose schwarz"],
    )
    base.update(kw)
    return SiteContext(**base)


def _syn(n, start=0):
    return [_q(C.SYNONYM, f"bergschuh variante {i}", "Schuhe") for i in range(start, start + n)]


class DeterministicTests(unittest.TestCase):
    def test_direct_match_titles_only(self):
        ctx = _ctx()
        cands = qg._direct_match_candidates(ctx)
        self.assertIn("Salomon X Ultra 4 GTX", cands)
        self.assertNotIn("Mini Rodini barnkläder", cands)  # brand + category phrase
        self.assertNotIn("Jacken", cands)                   # nav label / single word
        self.assertLess(cands.index("Salomon X Ultra 4 GTX"), cands.index("Mammut Nordwand Jacke Herren"))

    def test_direct_match_shortfall_reallocated(self):
        ctx = _ctx(catalog_sample=[])
        client = FakeClient([_batch(*_syn(3), _q(C.NATURAL_LANGUAGE, "warme schuhe für den winter", "Schuhe"),
                                    _q(C.NATURAL_LANGUAGE, "etwas für regen beim wandern", "Jacken"))])
        with mock.patch.object(qg, "MIN_QUERY_COUNT", 6):
            out = qg.generate_queries(ctx, [C.DIRECT_MATCH, C.SYNONYM, C.NATURAL_LANGUAGE], client=client)
        cats = [q.category for q in out]
        self.assertEqual(cats.count("DIRECT_MATCH"), 1)
        self.assertEqual(out[0].query, "Salomon X Ultra 4 GTX")
        self.assertEqual(out[0].target_term, "Salomon X Ultra 4 GTX")
        self.assertEqual(len(out), 6)
        prompt = client.messages.calls[0]["messages"][0]["content"]
        self.assertIn("SYNONYM (generate 3 queries)", prompt)  # 2 + 1 reallocated
        self.assertNotIn("DIRECT_MATCH (generate", prompt)
        self.assertIn("DIRECT_MATCH: 1/2", ctx.provenance["queries_notes"])

    def test_llm_direct_match_must_be_known_title(self):
        ctx = _ctx()
        g = qg._grounding(ctx)
        state = qg._ScreenState(seen=set(), used_bases=set(), capacity={C.DIRECT_MATCH: 3})
        ok, rej = qg._screen_batch([_q(C.DIRECT_MATCH, "salomon x  ultra 4 gtx", "x"),
                                    _q(C.DIRECT_MATCH, "Mini Rodini Kinderjacke", "x")],
                                   {C.DIRECT_MATCH: 3}, ctx, state, g)
        self.assertEqual([q.query for q in ok], ["salomon x ultra 4 gtx"])
        self.assertIn("exact title", rej[0][2])

    def test_gibberish_per_locale(self):
        cases = [("de-CH", "qwertzuiop"), ("de-AT", "qwertzuiop"), ("fr-CH", "qwertzuiop"),
                 ("fr-BE", "azertyuiop"), ("fr-FR", "azertyuiop"), ("en-GB", "qwertyuiop"), ("sv-SE", "qwertyuiop"),
                 ("de", "qwertzuiop"), ("", "qwertyuiop")]
        for locale, row in cases:
            with self.subTest(locale=locale):
                qs = qg.build_gibberish(_ctx(locale=locale, primary_language="German" if locale == "de" else "English"))
                self.assertEqual(len(qs), 4)
                self.assertEqual(qs[1].query, row)
                self.assertTrue(all(q.target_term is None and q.category == "GIBBERISH" for q in qs))
                self.assertGreaterEqual(len(qs[0].query), 50)
                self.assertFalse(set(qs[2].query) & set(qs[3].query))
        two = qg.build_gibberish(_ctx(), 2)
        self.assertEqual([q.query for q in two], [qg._GIBBERISH_CONSONANTS, qg._GIBBERISH_REPEATED])

    def test_gibberish_capped_and_no_llm_call(self):
        ctx = _ctx()
        out = qg.generate_queries(ctx, [C.GIBBERISH], counts={C.GIBBERISH: 6}, enforce_min=False,
                                  client=FakeClient([]))
        self.assertEqual(len(out), 4)

    def test_sku_from_codes_or_dropped(self):
        codes = [{"code": "4057651000000", "kind": "gtin13", "title": "Scarpa Mojito GTX"},
                 {"code": "SC-32605", "kind": "mpn", "title": "Scarpa Mojito GTX"}]
        ctx = _ctx(provenance={"catalog_codes": json.dumps(codes)})
        out = qg.generate_queries(ctx, [C.SKU_MODEL_NUMBER], counts={C.SKU_MODEL_NUMBER: 1}, enforce_min=False,
                                  client=FakeClient([]))
        self.assertEqual([(q.query, q.target_term) for q in out], [("SC-32605", "Scarpa Mojito GTX")])

        ctx2 = _ctx(catalog_sample=[])
        client = FakeClient([_batch(*_syn(3))])  # SYNONYM 1 + 2 reallocated from SKU
        with mock.patch.object(qg, "MIN_QUERY_COUNT", 4):
            out2 = qg.generate_queries(ctx2, [C.SKU_MODEL_NUMBER, C.SYNONYM, C.GIBBERISH], client=client)
        self.assertNotIn("SKU_MODEL_NUMBER", [q.category for q in out2])
        self.assertIn("never invent codes", ctx2.provenance["queries_notes"])


class TopUpTests(unittest.TestCase):
    def test_single_category_regeneration_asks_for_requested_count(self):
        ctx = _ctx()
        existing = [TestQuery(category=C.SYNONYM, query="bergschuh variante 0", rationale="r", target_term="Schuhe")]
        client = FakeClient([_batch(*_syn(3))])  # includes the existing one → deduped
        out = qg.generate_queries(ctx, [C.SYNONYM], counts={C.SYNONYM: 2}, existing=existing, enforce_min=False,
                                  client=client)
        self.assertEqual([q.query for q in out], ["bergschuh variante 1", "bergschuh variante 2"])
        prompt = client.messages.calls[0]["messages"][0]["content"]
        self.assertIn("SYNONYM (generate 2 queries)", prompt)
        self.assertIn("bergschuh variante 0", prompt)  # existing shown as do-not-repeat

    def test_default_topup_uses_weights_not_sixty(self):
        deterministic, llm_counts, _ = qg._plan(_ctx(), [C.TYPO], None, [], False, None, set(), qg._grounding(_ctx()))
        self.assertEqual(llm_counts, {C.TYPO: qg.QUERY_COUNTS[C.TYPO]})

    def test_enforce_min_counts_existing(self):
        ctx = _ctx()
        existing = [TestQuery(category=C.SYNONYM, query=f"e{i}", rationale="r", target_term="x") for i in range(3)]
        with mock.patch.object(qg, "MIN_QUERY_COUNT", 6), self.assertRaises(RuntimeError):
            qg.generate_queries(ctx, [C.SYNONYM], counts={C.SYNONYM: 2}, existing=existing,
                                client=FakeClient([_batch(*_syn(2))]))


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.ctx = _ctx()
        self.g = qg._grounding(self.ctx)

    def screen(self, *entries, used=()):
        cats = {C(e["category"]) if isinstance(e, dict) and e.get("category") in C._value2member_map_ else None
                for e in entries} - {None}
        cap = {c: 10 for c in cats}
        state = qg._ScreenState(seen=set(), used_bases=set(used), capacity=dict(cap))
        return qg._screen_batch(list(entries), cap, self.ctx, state, self.g)

    def test_typo(self):
        ok, rej = self.screen(
            _q(C.TYPO, "Wandaschuhe Herren", "Wanderschuhe"),    # collides with Handschuhe
            _q(C.TYPO, "Pullofer", "Pullover"),                  # fine
            _q(C.TYPO, "Hose", "Hose"),                          # unchanged
            _q(C.TYPO, "Mamuth Jacke", "Mammut Jake"),           # two words changed
            _q(C.TYPO, "Xyzzyqw", "Pullover"),                   # too far
        )
        self.assertEqual([q.query for q in ok], ["Pullofer"])
        reasons = [r for _, _, r in rej]
        self.assertIn("handschuhe", reasons[0])
        self.assertIn("unchanged", reasons[1])
        self.assertIn("one perturbation", reasons[2])
        self.assertIn("edits", reasons[3])

    def test_split_word(self):
        ok, rej = self.screen(
            _q(C.SPLIT_WORD, "s hoes", "shoes"),
            _q(C.SPLIT_WORD, "Wander schuhe", "Wanderschuhe"),
            _q(C.SPLIT_WORD, "Pullov er", "Pullover"),
        )
        self.assertEqual([q.query for q in ok], ["Pullov er"])
        self.assertIn("too short", rej[0][2])

    def test_special_character(self):
        ok, rej = self.screen(
            _q(C.SPECIAL_CHARACTER, "Sal&omon", "Salomon"),
            _q(C.SPECIAL_CHARACTER, "&Hose", "Hose"),
            _q(C.SPECIAL_CHARACTER, "Ja**cke", "Jacke"),
        )
        self.assertEqual([q.query for q in ok], ["Sal&omon"])
        self.assertIn("edge", rej[0][2])
        self.assertIn("exactly one", rej[1][2])

    def test_merged_words(self):
        ok, rej = self.screen(
            _q(C.MERGED_WORDS, "wanderschuheherren", "Wanderschuhe Herren"),
            _q(C.MERGED_WORDS, "wanderschuhe herren", "Wanderschuhe Herren"),
            _q(C.MERGED_WORDS, "jackenhosen", "Jacke Hose"),
        )
        self.assertEqual([q.query for q in ok], ["wanderschuheherren"])
        self.assertIn("no space", rej[0][2])
        self.assertIn("space removed", rej[1][2])

    def test_base_word_reuse_across_perturbations(self):
        ok, rej = self.screen(
            _q(C.TYPO, "Pullofer", "Pullover"),
            _q(C.SPLIT_WORD, "Pullov er", "Pullover"),
            _q(C.SPECIAL_CHARACTER, "Pull#over", "Pullover"),
            _q(C.SPECIAL_CHARACTER, "Sal&omon", "Salomon"),
            used={"salomon"},
        )
        self.assertEqual([q.query for q in ok], ["Pullofer"])
        self.assertEqual(len(rej), 3)
        self.assertTrue(all("already used" in r for _, _, r in rej))

    def test_brand_search(self):
        sample = [f"Mammut Jacke Modell {i}" for i in range(30)] + ["Salomon Wanderschuhe"]
        self.ctx = _ctx(catalog_sample=sample)
        self.g = qg._grounding(self.ctx)
        ok, rej = self.screen(
            _q(C.BRAND_SEARCH, "mammut jacke", "Mammut"),
            _q(C.BRAND_SEARCH, "mammut mascara", "Mammut"),   # brand seen, never with mascara
            _q(C.BRAND_SEARCH, "patagonia", "Patagonia"),      # not a known brand
        )
        self.assertEqual([q.query for q in ok], ["mammut jacke"])
        self.assertIn("mismatch", rej[0][2])
        self.assertIn("no brand", rej[1][2])

    def test_constraint_categories(self):
        ok, rej = self.screen(
            _q(C.PRICE_ANCHORED, "jacke unter 100 euro", "Jacke", {"price_max": 100, "price_min": None, "exclude": [], "attributes": []}),
            _q(C.PRICE_ANCHORED, "jacke unter €100", "Jacke", {"price_max": 100}),
            _q(C.PRICE_ANCHORED, "jacke günstig", "Jacke", None),
            _q(C.NEGATIVE_INTENT, "pullover ohne wolle", "Pullover", {"exclude": ["wolle"]}),
            _q(C.NEGATIVE_INTENT, "pullover ohne daunen", "Pullover", {"exclude": []}),
            _q(C.MULTI_ATTRIBUTE, "hose schwarz herren", "Hose", {"attributes": ["schwarz", "herren"]}),
            _q(C.MULTI_ATTRIBUTE, "jacke rot", "Jacke", {"attributes": ["rot"]}),
            _q(C.FACET_EXTRACTION, "jacke damen", "Jacke", {"attributes": ["damen"]}),
            _q(C.FACET_EXTRACTION, "jacke damen herren", "Jacke", {"attributes": ["damen", "herren"]}),
        )
        self.assertEqual([q.query for q in ok], ["jacke unter 100 euro", "pullover ohne wolle",
                                                 "hose schwarz herren", "jacke damen"])
        self.assertEqual(ok[0].constraints.price_max, 100.0)
        self.assertEqual(ok[2].constraints.attributes, ["schwarz", "herren"])
        reasons = [r for _, _, r in rej]
        self.assertIn("currency as a word", reasons[0])
        self.assertIn("price_max", reasons[1])
        self.assertIn("exactly one", reasons[2])
        self.assertIn("exactly 2", reasons[3])
        self.assertIn("exactly 1", reasons[4])

    def test_title_visibility_with_large_sample(self):
        sample = [f"Foundation Matte {i} 30 ml" for i in range(30)]
        self.ctx = _ctx(catalog_sample=sample)
        self.g = qg._grounding(self.ctx)
        ok, rej = self.screen(
            _q(C.FACET_EXTRACTION, "foundation 30 ml", "foundation", {"attributes": ["30 ml"]}),
            _q(C.FACET_EXTRACTION, "foundation 100 ml", "foundation", {"attributes": ["100 ml"]}),
        )
        self.assertEqual([q.query for q in ok], ["foundation 30 ml"])
        self.assertIn("title-visible", rej[0][2])

    def test_malformed_entries_do_not_crash(self):
        ok, rej = self.screen(
            {"category": "SYNONYM", "query": 501, "target_term": "Jeans", "rationale": None, "constraints": "x"},
            {"category": "SYNONYM", "query": None, "target_term": "x"},
            {"category": "SYNONYM", "query": ["a"], "target_term": "x"},
            {"category": None, "query": "abc"},
            {"category": "SYNONYM", "query": "  Berg   Stiefel ", "target_term": None},
            "not a dict",
            42,
            {"category": "SYNONYM", "query": "BERG  stiefel", "target_term": "Stiefel"},
            {"category": "SYNONYM", "query": "berg stiefel", "target_term": "Stiefel"},
        )
        self.assertEqual([q.query for q in ok], ["501", "BERG stiefel"])
        self.assertIsNone(ok[0].constraints)
        reasons = [r for _, _, r in rej]
        self.assertEqual(reasons.count("empty or non-text query"), 2)
        self.assertIn("target_term missing", reasons)
        self.assertEqual(reasons.count("malformed entry (not an object)"), 2)
        self.assertIn("duplicate query", reasons)

    def test_category_not_requested_is_rejected_not_kept(self):
        state = qg._ScreenState(seen=set(), used_bases=set(), capacity={C.SYNONYM: 5})
        ok2, rej2 = qg._screen_batch([_q(C.OCCASION, "geschenk für papa", "Geschenk")], {C.SYNONYM: 5},
                                     self.ctx, state, self.g)
        self.assertEqual(ok2, [])
        self.assertIn("not requested", rej2[0][2])

    def test_concentration_flag(self):
        qs = [TestQuery(category=C.SYNONYM, query=f"jacke {i}", rationale="r", target_term="Jacke") for i in range(6)]
        qs += [TestQuery(category=C.SYNONYM, query=f"hose {i}", rationale="r", target_term="Hose") for i in range(4)]
        self.assertEqual(qg._concentration(qs)[0], "jacke")
        self.assertIsNone(qg._concentration(qs[4:]))


class RetryLoopTests(unittest.TestCase):
    def test_rejections_fed_back_and_provenance_recorded(self):
        ctx = _ctx()
        client = FakeClient([
            _batch(_q(C.TYPO, "Wandaschuhe", "Wanderschuhe"), _q(C.TYPO, "Pullofer", "Pullover")),
            _batch(_q(C.TYPO, "Mamuth", "Mammut")),
        ])
        out = qg.generate_queries(ctx, [C.TYPO], counts={C.TYPO: 2}, enforce_min=False, client=client)
        self.assertEqual([q.query for q in out], ["Pullofer", "Mamuth"])
        second = client.messages.calls[1]["messages"][0]["content"]
        self.assertIn("Rejected Last Round", second)
        self.assertIn("Wandaschuhe", second)
        self.assertIn("handschuhe", second)
        self.assertIn("pullover", second)  # base word already used
        self.assertIn("TYPO (generate 1 queries)", second)
        call = client.messages.calls[0]
        self.assertIs(call["output_format"], qg.GeneratedBatch)
        self.assertIn("Hard rules", call["system"][0]["text"])
        for key in ("queries_model", "queries_prompt_sha256", "queries_system_sha256", "queries_generated_at"):
            self.assertTrue(ctx.provenance[key])
        self.assertEqual(ctx.provenance["queries_attempts"], "2")

    def test_llm_failures_then_missing_coverage_raises(self):
        ctx = _ctx()
        client = FakeClient([RuntimeError("down")] * qg.MAX_QUERY_GENERATION_ATTEMPTS)
        with self.assertRaises(RuntimeError) as cm:
            qg.generate_queries(ctx, [C.SYNONYM], counts={C.SYNONYM: 2}, enforce_min=False, client=client)
        self.assertIn("Missing required coverage: SYNONYM: 2", str(cm.exception))
        self.assertIn("down", ctx.provenance["queries_last_error"])

    def test_prompt_examples_follow_playbook(self):
        system = qg._SYSTEM_PROMPT
        self.assertNotIn("ultra boost", system)
        self.assertNotIn("AM90", system)
        self.assertNotIn("under €50", system)
        self.assertIn("EXACTLY TWO", system)
        self.assertIn("price_max", system)

    def test_validate_queries_wrapper(self):
        out = qg._validate_queries([_q(C.SYNONYM, "stiefel", "Schuhe"), {"category": "SYNONYM", "query": 7}],
                                   [C.SYNONYM], {C.SYNONYM: 5})
        self.assertEqual([q.query for q in out], ["stiefel"])


if __name__ == "__main__":
    unittest.main()
