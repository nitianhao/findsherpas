"""Category selection: structured call, site-type override, bounds, retired categories, provenance."""

import os
import unittest
from unittest import mock

import tests.helpers  # noqa: F401 — sets offline API keys
from src import category_selector as cs
from src.category_selector import (
    CATEGORY_DESCRIPTIONS,
    CategoryAdjustments,
    CategoryChange,
    MAX_CATEGORIES,
    MIN_CATEGORIES,
    select_categories,
)
from src.models import SITE_TYPE_DEFAULTS, QueryCategory, SiteContext, SiteType
from tests.helpers import FakeClient, fake_text_response


def _resp(obj):
    r = fake_text_response("{}")
    r.parsed_output = obj
    return r


def _adj(add=(), remove=(), override=None):
    return CategoryAdjustments(
        site_type_reason="because",
        site_type_override=override,
        add=[CategoryChange(category=c, reason="r") for c in add],
        remove=[CategoryChange(category=c, reason="r") for c in remove],
    )


def _ctx(site_type=SiteType.SERVICES_EXPERIENCES):
    return SiteContext(url="https://bergzeit.de", site_type=site_type, nav_categories=["Jacken"])


class DescriptionTests(unittest.TestCase):
    def test_every_category_described(self):
        self.assertEqual(set(CATEGORY_DESCRIPTIONS), set(QueryCategory))

    def test_prompt_count_matches_library(self):
        system = cs._system_prompt()
        self.assertIn(f"({len(cs.OFFERABLE_CATEGORIES)} total)", system)
        self.assertIn("GIBBERISH", system)
        self.assertNotIn("BROAD_CATEGORY", system)


class SelectCategoriesTests(unittest.TestCase):
    def test_override_updates_site_type_and_reasks_against_new_defaults(self):
        ctx = _ctx(SiteType.SERVICES_EXPERIENCES)
        client = FakeClient([
            # Round 1: corrects the type; its adjustments were reasoned against the wrong defaults.
            _resp(_adj(add=[QueryCategory.OCCASION], override=SiteType.PHYSICAL_GOODS)),
            # Round 2: against PHYSICAL_GOODS defaults.
            _resp(_adj(add=[QueryCategory.PRICE_ANCHORED], remove=[QueryCategory.SKU_MODEL_NUMBER])),
        ])
        cats = select_categories(ctx, client=client)
        self.assertEqual(ctx.site_type, "PHYSICAL_GOODS")
        self.assertEqual(len(client.messages.calls), 2)
        self.assertIn("Current Default Categories for PHYSICAL_GOODS", client.messages.calls[1]["messages"][0]["content"])
        expected = [c for c in SITE_TYPE_DEFAULTS[SiteType.PHYSICAL_GOODS] if c != QueryCategory.SKU_MODEL_NUMBER]
        self.assertEqual(cats, expected + [QueryCategory.PRICE_ANCHORED])
        self.assertIn("SERVICES_EXPERIENCES -> PHYSICAL_GOODS", ctx.provenance["categories_site_type_override"])
        self.assertEqual(ctx.provenance["categories"], "llm")
        for key in ("categories_model", "categories_prompt_sha256", "categories_generated_at"):
            self.assertTrue(ctx.provenance[key])

    def test_floor_and_cap_enforced(self):
        defaults = SITE_TYPE_DEFAULTS[SiteType.PHYSICAL_GOODS]
        low = select_categories(_ctx(SiteType.PHYSICAL_GOODS),
                                client=FakeClient([_resp(_adj(remove=defaults[:8]))]))
        self.assertEqual(len(low), MIN_CATEGORIES)
        many = [c for c in cs.OFFERABLE_CATEGORIES if c not in defaults]
        high = select_categories(_ctx(SiteType.PHYSICAL_GOODS), client=FakeClient([_resp(_adj(add=many))]))
        self.assertEqual(len(high), MAX_CATEGORIES)
        self.assertEqual(high[: len(defaults)], defaults)

    def test_broad_category_rejected(self):
        cats = select_categories(_ctx(SiteType.PHYSICAL_GOODS),
                                 client=FakeClient([_resp(_adj(add=[QueryCategory.BROAD_CATEGORY]))]))
        self.assertNotIn(QueryCategory.BROAD_CATEGORY, cats)

    def test_fallback_recorded_when_not_strict(self):
        ctx = _ctx(SiteType.PHYSICAL_GOODS)
        with mock.patch.dict(os.environ, {"AUDIT_STRICT_LLM": "0"}):
            cats = select_categories(ctx, client=FakeClient([fake_text_response("{", stop_reason="max_tokens")]))
        self.assertEqual(cats, SITE_TYPE_DEFAULTS[SiteType.PHYSICAL_GOODS])
        self.assertTrue(ctx.provenance["categories"].startswith("fallback: LLMResponseError"))

    def test_strict_raises(self):
        ctx = _ctx(SiteType.PHYSICAL_GOODS)
        with mock.patch.dict(os.environ, {"AUDIT_STRICT_LLM": "1"}), self.assertRaises(RuntimeError):
            select_categories(ctx, client=FakeClient([RuntimeError("api down")]))
        self.assertIn("api down", ctx.provenance["categories"])

    def test_apply_adjustments_tolerates_dict_and_garbage(self):
        base = list(SITE_TYPE_DEFAULTS[SiteType.PHYSICAL_GOODS])
        out = cs._apply_adjustments(base, {"add": [{"category": "NOPE"}, "x", {"category": "OCCASION"}],
                                           "remove": None}, _ctx())
        self.assertEqual(out, base + [QueryCategory.OCCASION])


if __name__ == "__main__":
    unittest.main()
