"""Discovery: language/locale, currency, search-URL parsing, refinement provenance, catalog sampling.

Fully offline: the LLM client, the fetcher and HTTP are stubbed.
"""

import json
import os
import unittest
from unittest import mock

import requests
from bs4 import BeautifulSoup

import tests.helpers  # noqa: F401 — sets offline API keys
from src import discovery
from src.discovery import (
    RefinedProfile,
    _currency_from_text,
    _default_seed_fetch,
    _detect_currency,
    _detect_language,
    _detect_site_type,
    _fetch_html,
    _page_problem,
    _refine_with_llm,
    build_catalog_sample,
    discover_from_search_url,
    discover_site,
    parse_search_url,
)
from src.llm_compat import LLMResponseError
from src.models import FetchOutcome, SearchResult, SiteType
from tests.helpers import FakeClient, fake_text_response

DE_TEXT = ("Die besten Wanderschuhe für Herren und Damen. Jetzt mit kostenlosem Versand, "
           "die Rückgabe ist einfach und das Sortiment ist groß. Wählen Sie aus über 500 Marken "
           "für Ihre nächste Tour auf den Berg. Unsere Jacken sind wasserdicht und nicht schwer. ") * 4
FR_TEXT = ("Les meilleures chaussures de randonnée pour vous. Livraison gratuite avec nos offres, "
           "le retour est simple et des milliers de produits pour la montagne sont sur le site. ") * 4
SV_TEXT = ("Köp skor och jackor för hela familjen. Fri frakt på alla ordrar och det är enkelt att "
           "returnera. Vår butik har märken som inte finns på andra ställen. ") * 4


def _page(body: str, lang: str | None = None, head: str = "") -> BeautifulSoup:
    lang_attr = f' lang="{lang}"' if lang else ""
    return BeautifulSoup(f"<html{lang_attr}><head>{head}</head><body><p>{body}</p></body></html>", "html.parser")


def _parsed_response(obj):
    r = fake_text_response("{}")
    r.parsed_output = obj
    return r


class LanguageDetectionTests(unittest.TestCase):
    def test_table(self):
        cases = [
            # (description, soup, url, expected language, expected locale)
            ("en-GB page with a de-de alternate stays English",
             _page("Shop jackets", "en-GB",
                   '<link rel="alternate" hreflang="de-de" href="https://shop.example.com/de/">'),
             "https://shop.example.com/", "English", "en-GB"),
            ("no lang: hreflang counts only when its href is this page",
             _page("Shop", None,
                   '<link rel="canonical" href="https://shop.example.com/uk/">'
                   '<link rel="alternate" hreflang="de-de" href="https://shop.example.com/de/">'
                   '<link rel="alternate" hreflang="en-gb" href="https://shop.example.com/uk/">'),
             "https://shop.example.com/uk/?utm_source=x", "English", "en-GB"),
            ("German page without lang (ä/ö must not read as Swedish)",
             _page(DE_TEXT), "https://www.example.com/", "German", "de"),
            (".ch with lang fr", _page(FR_TEXT, "fr"), "https://www.baechli-bergsport.ch/", "French", "fr-CH"),
            (".ch without lang, French text", _page(FR_TEXT), "https://www.example.ch/", "French", "fr-CH"),
            (".ch without lang, German text", _page(DE_TEXT), "https://www.example.ch/", "German", "de-CH"),
            (".be without lang, French text", _page(FR_TEXT), "https://www.example.be/", "French", "fr-BE"),
            ("Swedish text without lang on .com", _page(SV_TEXT), "https://www.example.com/", "Swedish", "sv"),
            (".se without lang", _page("x"), "https://www.example.se/", "Swedish", "sv-SE"),
            ("lang without region picks the TLD region", _page("x", "en"), "https://www.example.co.uk/", "English", "en-GB"),
            ("path prefix", _page("x"), "https://lyko.com/sv/sok?q=fresh", "Swedish", "sv"),
            ("og:locale", _page("x", None, '<meta property="og:locale" content="da_DK">'),
             "https://www.example.com/", "Danish", "da-DK"),
            ("nothing → English", _page("hello"), "https://www.example.com/", "English", "en"),
        ]
        for desc, soup, url, lang, locale in cases:
            with self.subTest(desc):
                got_lang, got_locale, _src = _detect_language(soup, url)
                self.assertEqual((got_lang, got_locale), (lang, locale))

    def test_wrapper_returns_name(self):
        self.assertEqual(discovery._detect_primary_language(_page(DE_TEXT), "https://x.com/"), "German")


class CurrencyTests(unittest.TestCase):
    def test_jsonld_wins(self):
        soup = BeautifulSoup('<script type="application/ld+json">{"@type":"Product","name":"A b",'
                             '"offers":{"@type":"Offer","priceCurrency":"CHF","price":"89.90"}}</script>'
                             "<p>€ 12</p>", "html.parser")
        self.assertEqual(_detect_currency(soup, "€ 12", "de-CH"), ("CHF", "jsonld"))

    def test_price_text_table(self):
        cases = [
            ("1 299 kr", "sv-SE", "SEK"), ("1 299 kr", "da-DK", "DKK"), ("399 kr.", "nb-NO", "NOK"),
            ("49,99 zł", "pl-PL", "PLN"), ("1 290 Kč", "cs-CZ", "CZK"), ("CHF 89.90", "de-CH", "CHF"),
            ("€ 49,95 and 12 €", "de-DE", "EUR"), ("£25.00", "en-GB", "GBP"), ("$40", "en-CA", "CAD"),
            ("$40", "en", "USD"), ("100 SEK", "en", "SEK"), ("1 299 kr", "en", ""), ("no prices", "en", ""),
        ]
        for text, locale, want in cases:
            with self.subTest(text=text, locale=locale):
                self.assertEqual(_currency_from_text(text, locale), want)


class ParseSearchUrlTests(unittest.TestCase):
    def test_cases(self):
        cases = [
            ("https://www.groupon.com/search?query=spa", ("https://www.groupon.com/search?query={}", "spa")),
            ("https://x.com/search?utm_source=news&q=", ("https://x.com/search?q={}", "")),
            ("https://x.com/s?q=boots&page=2&utm_campaign=a", ("https://x.com/s?q={}", "boots")),
            ("https://www.baechli-bergsport.ch/de/suche/search?Query=jacke",
             ("https://www.baechli-bergsport.ch/de/suche/search?Query={}", "jacke")),
            ("https://x.com/shop?lang=en&sort=price&currency=EUR&kw2=red shoes",
             ("https://x.com/shop?lang=en&sort=price&currency=EUR&kw2={}", "red shoes")),
            ("https://x.com/search/red%20shoes?page=3", ("https://x.com/search/{}", "red shoes")),
            ("https://x.com/de/suche/wanderschuhe", ("https://x.com/de/suche/{}", "wanderschuhe")),
        ]
        for url, want in cases:
            with self.subTest(url=url):
                self.assertEqual(parse_search_url(url), want)

    def test_non_search_params_are_never_guessed(self):
        for url in ("https://x.com/?utm_source=newsletter", "https://x.com/?lang=english&sort=newest",
                    "https://x.com/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_search_url(url)


class SiteTypeHeuristicTests(unittest.TestCase):
    def test_word_boundaries(self):
        # "facebook", "space", "current" used to count as book / spa / rent.
        text = "facebook space current " * 5
        self.assertEqual(_detect_site_type([], [], "", text), SiteType.MARKETPLACE_MIXED)
        self.assertEqual(
            _detect_site_type([], [], "", "book a spa appointment, tickets and tours"),
            SiteType.SERVICES_EXPERIENCES,
        )

    def test_nordic_and_swiss_prices_count_as_goods(self):
        self.assertEqual(_detect_site_type([], [], "", "Jacka 1 299 kr Skor 899 kr Mössa 199 kr"),
                         SiteType.PHYSICAL_GOODS)
        self.assertEqual(_detect_site_type([], [], "", "Jacke CHF 249 Hose CHF 129 Shirt CHF 49"),
                         SiteType.PHYSICAL_GOODS)


class RefineTests(unittest.TestCase):
    kwargs = dict(
        site_name="Shop", meta_description="", nav_categories=["Jackets", "Patagonia", "Boots"],
        brands=["Rab"], featured_items=["Rab Kit Bag II - 80L", "Privacy Policy"],
        html_text="Jackets Boots Patagonia Rab Kit Bag II - 80L Privacy Policy",
        heuristic_site_type=SiteType.SERVICES_EXPERIENCES,
    )

    def test_success_drops_hallucinations_and_records_provenance(self):
        out = RefinedProfile(site_type_evidence="sells gear", site_type=SiteType.PHYSICAL_GOODS,
                             brands=["Rab", "Patagonia", "Arc'teryx"], nav_categories=["Jackets", "Tents"],
                             featured_items=["Rab Kit Bag II - 80L"])
        prov: dict = {}
        res = _refine_with_llm(**self.kwargs, provenance=prov, client=FakeClient([_parsed_response(out)]))
        self.assertEqual(res["site_type"], "PHYSICAL_GOODS")
        self.assertEqual(res["brands"], ["Rab", "Patagonia"])  # Arc'teryx not in the page
        self.assertEqual(res["nav_categories"], ["Jackets"])
        self.assertEqual(prov["refine"], "llm")
        self.assertIn("Arc'teryx", prov["refine_dropped"])
        for key in ("discovery_model", "discovery_prompt_sha256", "discovery_generated_at"):
            self.assertTrue(prov[key])

    def test_failure_is_recorded_not_silent(self):
        truncated = fake_text_response("{", stop_reason="max_tokens")
        prov: dict = {}
        with mock.patch.dict(os.environ, {"AUDIT_STRICT_LLM": "0"}):
            res = _refine_with_llm(**self.kwargs, provenance=prov, client=FakeClient([truncated]))
        self.assertIsNone(res)
        self.assertTrue(prov["refine"].startswith("fallback: LLMResponseError"))

    def test_strict_mode_raises(self):
        prov: dict = {}
        with mock.patch.dict(os.environ, {"AUDIT_STRICT_LLM": "1"}), self.assertRaises(LLMResponseError):
            _refine_with_llm(**self.kwargs, provenance=prov,
                             client=FakeClient([fake_text_response("{", stop_reason="max_tokens")]))
        self.assertTrue(prov["refine"].startswith("fallback:"))

    def test_strict_is_default(self):
        env = {k: v for k, v in os.environ.items() if k != "AUDIT_STRICT_LLM"}
        with mock.patch.dict(os.environ, env, clear=True), self.assertRaises(RuntimeError):
            _refine_with_llm(**self.kwargs, provenance={}, client=FakeClient([RuntimeError("boom")]))


class CatalogSamplingTests(unittest.TestCase):
    def test_merge_dedupe_and_seed_choice(self):
        calls = []

        def fake_fetch(queries, template):
            calls.append((list(queries), template))
            return {
                "Jackets": ["Rab Neutrino Jacket", "rab  neutrino jacket", SearchResult(rank=1, title="Rab Kinetic", price="£120")],
                "Boots": ["Scarpa Mojito GTX", "Rab Neutrino Jacket"],
                "Tents": [],
            }

        titles, prices, note = build_catalog_sample(
            search_url_template="https://x.co.uk/s?q={}",
            nav_categories=["Sale", "Jackets", "New In", "Boots", "Tents", "-50% Deals", "Brands"],
            brands=[], page_titles=["Seed Page Item One"], homepage_titles=["Home Hero Item"],
            seed_query="running shoes", fetch_fn=fake_fetch,
        )
        self.assertEqual(calls[0][0], ["Jackets", "Boots", "Tents"])
        self.assertEqual(len(titles), len({t.casefold() for t in titles}))
        self.assertEqual(set(titles), {"Home Hero Item", "Rab Neutrino Jacket", "Rab Kinetic",
                                       "Scarpa Mojito GTX", "Seed Page Item One"})
        # Round-robin: the first title from each source before any source's second.
        self.assertEqual(titles[:4], ["Home Hero Item", "Rab Neutrino Jacket", "Scarpa Mojito GTX", "Seed Page Item One"])
        self.assertEqual(prices, ["£120"])
        self.assertIn("2/3 seed searches", note)

    def test_brands_top_up_thin_nav_and_failures_are_noted(self):
        def boom(queries, template):
            raise RuntimeError("blocked")

        titles, _, note = build_catalog_sample(
            search_url_template="https://x.com/s?q={}", nav_categories=["Jackets"],
            brands=["Rab", "Scarpa", "Hoka", "Garmin", "MSR", "Vango"], page_titles=["A b"], fetch_fn=boom,
        )
        self.assertEqual(titles, ["A b"])
        self.assertIn("seed searches failed", note)

    def test_default_fetch_uses_outcomes_and_skips_untrusted(self):
        outcomes = {
            "Jackets": FetchOutcome(query="Jackets", status="ok", results=[SearchResult(rank=1, title="Rab Jacket")]),
            "Boots": FetchOutcome(query="Boots", status="blocked", results=[SearchResult(rank=1, title="Captcha")]),
        }
        fake = mock.Mock(return_value=outcomes)
        with mock.patch("src.fetcher.fetch_all_outcomes", fake, create=True):
            got = _default_seed_fetch(["Jackets", "Boots"], "https://x.com/s?q={}")
        fake.assert_called_once()
        self.assertEqual(fake.call_args.kwargs["queries"], ["Jackets", "Boots"])
        self.assertEqual([r.title for r in got["Jackets"]], ["Rab Jacket"])
        self.assertNotIn("Boots", got)


SEARCH_HTML = """<html lang="de-CH"><head><title>Suche | Bächli</title>
<meta name="description" content="Bergsport Ausrüstung">
<script type="application/ld+json">{"@type":"ItemList","itemListElement":[
 {"@type":"Product","name":"Mammut Nordwand Jacke","sku":"1010-29770","brand":{"name":"Mammut"},
  "offers":{"@type":"Offer","priceCurrency":"CHF","price":"499"}},
 {"@type":"Product","name":"Scarpa Mojito GTX","mpn":"SC-32605","gtin13":4057651000000}]}</script>
</head><body><nav><a href="/jacken">Jacken</a><a href="/schuhe">Schuhe</a><a href="/marken/mammut">Mammut</a></nav>
<p>Die besten Jacken und Schuhe für den Berg. CHF 499</p></body></html>"""


class EntryPointTests(unittest.TestCase):
    def _refined(self):
        return RefinedProfile(site_type_evidence="gear", site_type=SiteType.PHYSICAL_GOODS, brands=["Mammut"],
                              nav_categories=["Jacken", "Schuhe"], featured_items=["Mammut Nordwand Jacke"])

    def test_search_url_builds_full_context(self):
        fetched = {"https://www.baechli-bergsport.ch/de/suche/search?Query=jacke":
                   (SEARCH_HTML, "https://www.baechli-bergsport.ch/de/suche/search?Query=jacke"),
                   "https://www.baechli-bergsport.ch/de/": ("<html><body><p>Home</p></body></html>", "x")}
        seed = mock.Mock(return_value={"Schuhe": ["Lowa Renegade GTX Mid"]})
        with mock.patch.object(discovery, "_fetch_html", side_effect=lambda u: fetched[u]), \
             mock.patch("src.llm_compat.get_client", return_value=FakeClient([_parsed_response(self._refined())])):
            ctx = discover_from_search_url("https://www.baechli-bergsport.ch/de/suche/search?Query=jacke", fetch_fn=seed)
        self.assertEqual(ctx.search_url_template, "https://www.baechli-bergsport.ch/de/suche/search?Query={}")
        self.assertEqual((ctx.primary_language, ctx.locale, ctx.currency), ("German", "de-CH", "CHF"))
        self.assertEqual(ctx.site_type, "PHYSICAL_GOODS")
        self.assertEqual(seed.call_args.args[0], ["Jacken", "Schuhe", "Mammut"])  # thin nav topped up with a brand
        self.assertIn("Lowa Renegade GTX Mid", ctx.catalog_sample)
        self.assertIn("Mammut Nordwand Jacke", ctx.catalog_sample)
        self.assertEqual(ctx.provenance["refine"], "llm")
        codes = json.loads(ctx.provenance[discovery.CATALOG_CODES_KEY])
        self.assertEqual({c["code"] for c in codes}, {"1010-29770", "SC-32605", "4057651000000"})

    def test_homepage_path_also_refines_and_sampling_is_skippable(self):
        client = FakeClient([_parsed_response(self._refined())])
        with mock.patch.object(discovery, "_fetch_html", return_value=(SEARCH_HTML, "https://x.ch/")), \
             mock.patch("src.llm_compat.get_client", return_value=client):
            ctx = discover_site("https://x.ch/", sample_catalog=False)
        self.assertEqual(len(client.messages.calls), 1)
        self.assertEqual(ctx.provenance["refine"], "llm")
        self.assertTrue(ctx.provenance["catalog_sample"].startswith("skipped"))
        self.assertIn("Mammut Nordwand Jacke", ctx.catalog_sample)


class FetchFallbackTests(unittest.TestCase):
    def _resp(self, html, status=200):
        r = mock.Mock()
        r.status_code = status
        r.url = "https://x.com/s?q=a"
        r.headers = {"content-type": "text/html; charset=utf-8"}
        r.content = html.encode()
        r.raise_for_status = mock.Mock()
        return r

    def test_request_exception_falls_back_to_playwright(self):
        with mock.patch("requests.get", side_effect=requests.ConnectionError("reset")), \
             mock.patch.object(discovery, "_fetch_with_playwright", return_value=("<html>ok</html>", "firefox", "https://x.com/f")):
            self.assertEqual(_fetch_html("https://x.com/s?q=a"), ("<html>ok</html>", "https://x.com/f"))

    def test_bot_challenge_and_near_empty_fall_back(self):
        for html in ("<html><title>Just a moment...</title></html>", "<html><body><div id=app></div></body></html>"):
            with self.subTest(html=html), mock.patch("requests.get", return_value=self._resp(html)), \
                 mock.patch.object(discovery, "_fetch_with_playwright", return_value=("<p>rendered</p>", "c", "")) as pw:
                html_out, _ = _fetch_html("https://x.com/s?q=a")
                pw.assert_called_once()
                self.assertEqual(html_out, "<p>rendered</p>")

    def test_no_browser_html_reraises(self):
        with mock.patch("requests.get", side_effect=requests.Timeout("slow")), \
             mock.patch.object(discovery, "_fetch_with_playwright", return_value=("", "", "")), \
             self.assertRaises(requests.Timeout):
            _fetch_html("https://x.com/s?q=a")

    def test_page_problem(self):
        self.assertIsNone(_page_problem("<html><body><p>" + "real text " * 100 + "</p>"
                                        "<script src='recaptcha'></script></body></html>"))
        self.assertIn("near-empty", _page_problem("<html><body>hi</body></html>"))


if __name__ == "__main__":
    unittest.main()
