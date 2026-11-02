"""Fetcher extraction fidelity: ranks in DOM order, real prices, clean JSON-LD, sponsored
flags, grounded LLM extraction, redirect handling. Offline; LLM calls use a stub client."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from bs4 import BeautifulSoup

from tests.helpers import FakeClient, FakeResponse
from src import fetcher as f
from src.models import SearchResult


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def parsed_response(obj):
    return FakeResponse(content=[], stop_reason="end_turn", parsed_output=obj,
                        usage=SimpleNamespace(input_tokens=1, output_tokens=1, cache_read_input_tokens=0,
                                              cache_creation_input_tokens=0))


class Offline(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(f, "_HAS_API_KEY", False)
        p.start()
        self.addCleanup(p.stop)
        f._site_extraction_profile = None


class PriceTests(Offline):
    def price(self, inner: str):
        return f._extract_price(soup(f"<div class='card'>{inner}</div>").div)

    def test_struck_through_original_is_skipped(self):
        self.assertEqual(self.price("<span class='price'><del>€99,00</del> <ins>€79,00</ins></span>"), "€79,00")
        self.assertEqual(self.price("<s class='price-item'>$120.00</s><span class='price-item'>$89.00</span>"), "$89.00")

    def test_old_was_unit_classes_are_skipped(self):
        self.assertEqual(self.price("<span class='price--old'>49,95 €</span><span class='price'>39,95 €</span>"), "39,95 €")
        self.assertEqual(self.price("<span class='was-price'>£30</span><span class='price'>£20</span>"), "£20")
        self.assertEqual(self.price("<span class='price'>12,99 €</span><span class='unit-price'>25,98 €/l</span>"), "12,99 €")
        self.assertEqual(self.price("<span class='price-per-unit'>€1.20 / 100 g</span><span class='price'>€3.60</span>"), "€3.60")

    def test_review_count_does_not_collide_with_currency(self):
        # "(7) £240.00" used to come back as "7 £".
        self.assertEqual(self.price("<span class='stars'>4.5</span><span>7</span><span>£240.00</span>"), "£240.00")
        self.assertEqual(f._first_price("7 £240.00"), "£240.00")

    def test_sale_price_preferred_over_regular(self):
        html = ("<div class='price-box'><span class='price-regular'>€60</span>"
                "<span class='price-sale'>€45</span></div>")
        self.assertEqual(self.price(html), "€45")

    def test_locale_formats(self):
        self.assertEqual(self.price("<span>199 kr</span>"), "199 kr")
        self.assertEqual(self.price("<span>CHF 99.00</span>"), "CHF 99.00")
        self.assertEqual(self.price("<span itemprop='price' content='19.90'></span><meta itemprop='priceCurrency' content='EUR'>"),
                         "EUR 19.90")

    def test_kr_inside_a_word_is_not_a_price(self):
        self.assertIsNone(f._first_price("Krem 50 ml"))


class JsonLdTests(Offline):
    def page(self, *blocks) -> BeautifulSoup:
        scripts = "".join(f'<script type="application/ld+json">{json.dumps(b)}</script>' for b in blocks)
        return soup(f"<html><head>{scripts}</head><body></body></html>")

    def test_itemlist_ordered_by_position_and_not_duplicated(self):
        block = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": 3, "item": {"@type": "Product", "name": "Third boot", "url": "/p/3"}},
            {"@type": "ListItem", "position": 1, "item": {"@type": "Product", "name": "First boot", "url": "/p/1",
                                                          "offers": {"price": 99, "priceCurrency": "EUR"}}},
            {"@type": "ListItem", "position": 2, "item": {"@type": "Product", "name": "Second boot", "url": "/p/2"}},
        ]}
        res = f._try_schema_org(self.page(block), 15)
        self.assertEqual([r.title for r in res], ["First boot", "Second boot", "Third boot"])
        self.assertEqual([r.rank for r in res], [1, 2, 3])
        self.assertEqual(res[0].price, "EUR 99")

    def test_related_variants_and_offered_items_are_not_results(self):
        block = {"@type": "Product", "name": "Trail runner", "url": "/p/tr",
                 "isRelatedTo": [{"@type": "Product", "name": "Socks"}],
                 "hasVariant": [{"@type": "Product", "name": "Trail runner size 42"}],
                 "offers": [{"@type": "Offer", "price": "120", "itemOffered": {"@type": "Product", "name": "Gift box"}}]}
        res = f._try_schema_org(self.page(block), 15)
        self.assertEqual([r.title for r in res], ["Trail runner"])
        self.assertEqual(res[0].price, "120")

    def test_graph_and_weird_types_do_not_crash(self):
        blocks = [
            {"@graph": [{"@type": ["http://schema.org/Product"], "name": {"@value": "Graph product"}, "url": "/p/g",
                         "offers": ["not-a-dict", {"lowPrice": 5, "priceCurrency": "GBP"}]},
                        {"@type": None, "name": 12}, {"@type": {"weird": True}}]},
            [{"@type": "schema:Product", "name": ["List-named product"], "@id": "/p/l"}],
            "just a string",
        ]
        res = f._try_schema_org(self.page(*blocks), 15)
        self.assertEqual([r.title for r in res], ["Graph product", "List-named product"])
        self.assertEqual(res[0].price, "GBP 5")

    def test_short_real_names_survive(self):
        block = {"@type": "ItemList", "itemListElement": [{"@type": "Product", "name": "Talon 6", "url": "/p/t6"}]}
        self.assertEqual([r.title for r in f._try_schema_org(self.page(block), 15)], ["Talon 6"])


def tile(i, title, price="€29,99", cls="product-tile"):
    price_html = f"<span class='price'>{price}</span>" if price else ""
    return f"<div class='{cls}'><a href='/p/{i}'><h3 class='product-title'>{title}</h3></a>{price_html}</div>"


class OrderTests(Offline):
    def test_product_cards_keep_dom_order(self):
        # Rank 1 has no price; the old _card_score sort pushed it below priced cards.
        cards = tile(0, "Rank one hiking boot no price", price="") + "".join(
            tile(i, f"Rank {i + 1} hiking boot with price") for i in range(1, 8))
        html = f"<html><body><main><div class='product-grid'>{cards}</div></main></body></html>"
        res = f._try_product_cards(soup(html), 15)
        self.assertEqual(res[0].title, "Rank one hiking boot no price")
        self.assertEqual([r.rank for r in res], list(range(1, len(res) + 1)))

    def test_split_grid_is_merged_in_dom_order_and_carousel_is_not_preferred(self):
        block1 = "".join(tile(i, f"Grid A item number {i}") for i in range(4))
        block2 = "".join(tile(10 + i, f"Grid B item number {i}") for i in range(8))
        reco = "".join(tile(50 + i, f"Carousel item number {i}") for i in range(15))
        html = ("<html><body><main><div class='results'>"
                f"<div class='product-grid'>{block1}</div><div class='editorial'>Our picks</div>"
                f"<div class='product-grid'>{block2}</div></div>"
                f"<h2>Recommended for you</h2><div class='carousel'><div class='product-grid'>{reco}</div></div>"
                "</main></body></html>")
        cards = f._detect_repeated_structure(soup(html), 15)
        titles = [c.get_text(" ", strip=True) for c in cards]
        self.assertTrue(titles[0].startswith("Grid A item number 0"))
        self.assertEqual(len(cards), 12)
        self.assertFalse(any("Carousel" in t for t in titles))

    def test_small_real_grid_beats_big_carousel(self):
        grid = "".join(tile(i, f"Real result number {i}") for i in range(4))
        reco = "".join(tile(50 + i, f"Bestseller carousel item {i}") for i in range(15))
        html = (f"<html><body><main><div class='search-results'>{grid}</div>"
                f"<section class='recommendations'><h2>Bestsellers</h2><div class='slider'>{reco}</div></section>"
                "</main></body></html>")
        res, strategy = f._extract_page(soup(html), html, "https://shop.example.com/search?q=x", 15, allow_llm=False)
        self.assertEqual([r.title for r in res], [f"Real result number {i}" for i in range(4)])

    def test_score_strategy_is_mean_quality_times_capped_count(self):
        good = [SearchResult(rank=i, title=f"A real product title number {i}", url=f"/p/{i}", price="€1")
                for i in range(4)]
        many = [SearchResult(rank=i, title=f"A real product title number {i}", url=f"/p/{i}", price="€1")
                for i in range(40)]
        self.assertAlmostEqual(f._score_strategy(good, 15), 4.0)
        self.assertAlmostEqual(f._score_strategy(many, 15), 15.0)


class JunkAndSponsoredTests(Offline):
    def test_cookie_named_products_survive_cookie_links_do_not(self):
        self.assertFalse(f._is_cookie_junk(SearchResult(rank=1, title="Cookie cutter set Christmas", url="/p/cc")))
        self.assertTrue(f._is_cookie_junk(SearchResult(rank=1, title="Read more", url="/cookie-policy")))
        self.assertTrue(f._is_cookie_junk(SearchResult(rank=1, title="Accept all cookies", url=None)))

    def test_dutch_voor_binnen_titles_are_not_junk(self):
        res = f._filter_junk_results([SearchResult(rank=1, title="Voor de keuken: koekenpan 28 cm"),
                                      SearchResult(rank=2, title="Binnenzool wol maat 42")])
        self.assertEqual(len(res), 2)

    def test_sponsored_label_attribute_and_prefix(self):
        labelled = soup("<div class='product-tile'><span class='badge'>Gesponsert</span><a href='/p/1'>X</a></div>").div
        attr = soup("<div class='product-tile' data-sponsored='true'><a href='/p/1'>X</a></div>").div
        plain = soup("<div class='product-tile'><a href='/p/1'>Sponsored by nobody: a plain tile</a></div>").div
        self.assertTrue(f._detect_sponsored(labelled))
        self.assertTrue(f._detect_sponsored(attr))
        self.assertFalse(f._detect_sponsored(plain))
        r = f._strip_sponsored_prefix(SearchResult(rank=1, title="Sponsored Nike Air Zoom Pegasus"))
        self.assertEqual((r.title, r.sponsored), ("Nike Air Zoom Pegasus", True))

    def test_sponsored_tile_in_generic_grid_is_kept_and_flagged(self):
        cards = "".join(tile(i, f"Hiking boot model {i} leather") for i in range(6))
        cards = cards.replace("<h3 class='product-title'>Hiking boot model 2",
                              "<span>Anzeige</span><h3 class='product-title'>Hiking boot model 2")
        html = f"<html><body><main><div class='product-grid'>{cards}</div></main></body></html>"
        res = f._try_product_cards(soup(html), 15)
        self.assertEqual([r.sponsored for r in res], [False, False, True, False, False, False])

    def test_douglas_gesponsert_tile(self):
        html = ("<div class='product-grid'>"
                "<div class='product-tile'><a href='/de/p/1'><span>Lippenstift für Unisex DIOR Rouge 999</span></a><span>39,99 €</span></div>"
                "<div class='product-tile'><span>Gesponsert</span><a href='/de/p/2'><span>Mascara für Weiblich Lancôme Hypnôse</span></a><span>29,99 €</span></div>"
                "</div>")
        res = f._try_douglas(soup(html), 15)
        self.assertEqual([r.sponsored for r in res], [False, True])


class RedirectTests(Offline):
    def test_token_comparison(self):
        k = f._redirect_kind
        self.assertIsNone(k("https://s.com/search?q=red+shoes", "https://s.com/search/?q=red%20shoes", "red shoes"))
        self.assertIsNone(k("https://s.com/search?q=Arc%27teryx", "https://s.com/suche?q=Arc'teryx&p=2", "Arc'teryx"))
        self.assertIsNone(k("https://s.com/search?q=x", "https://s.com/search?q=x&sort=1", "x"))
        self.assertEqual(k("https://s.com/search?q=Arc%27teryx", "https://s.com/brands/arcteryx.html", "Arc'teryx"), "away")
        self.assertEqual(k("https://www.zalando.ie/catalog/?q=PI954K02Z-O11",
                           "https://www.zalando.ie/pieces-top-pi954k02z-o11.html", "PI954K02Z-O11"), "away")
        self.assertEqual(k("https://www.cotswoldoutdoor.com/lister.html?q=backpack",
                           "https://www.cotswoldoutdoor.com/c/equipment/rucksacks.html?q=backpack&sred=1",
                           "backpack"), "landing")
        self.assertEqual(k("https://www.bergzeit.de/search/?q=Regenjacke+Herren",
                           "https://www.bergzeit.de/bekleidung/jacken/?bzsearch=Regenjacke%20Herren&filter.gender=Herren",
                           "Regenjacke Herren"), "landing")
        self.assertEqual(k("https://s.de/suche?q=W%C3%A4rmflasche", "https://s.de/haushalt/?term=w%C3%A4rmflasche",
                           "Wärmflasche"), "landing")
        # Typographic apostrophe in the destination still matches.
        self.assertEqual(k("https://s.com/search?q=Arc%27teryx", "https://s.com/brands/x.html?q=Arc%E2%80%99teryx",
                           "Arc'teryx"), "landing")
        self.assertTrue(f._is_search_redirect("https://s.com/search?q=x", "https://s.com/p/123", "x"))
        # Query moved from the parameter into a search path: same results page.
        self.assertIsNone(k("https://s.com/search?q=red+shoes", "https://s.com/search/red-shoes", "red shoes"))

    def analyse(self, html, final_url, url="https://shop.example.com/search?q=trail+runner", query="trail runner"):
        return f._analyse_page(html=html, url=url, final_url=final_url, query=query, max_results=15)

    def test_redirect_to_pdp_is_one_result(self):
        html = ("<html><head><meta property='og:type' content='product'>"
                "<meta property='product:price:amount' content='129.00'><meta property='product:price:currency' content='CHF'>"
                "<link rel='canonical' href='https://shop.example.com/p/trail-runner-x'></head>"
                "<body><main><h1>Trail Runner X</h1>" + "<p>Product details and care.</p>" * 300 + "</main></body></html>")
        o = self.analyse(html, "https://shop.example.com/p/trail-runner-x")
        self.assertEqual(o.status, "redirect")
        self.assertEqual([(r.title, r.price) for r in o.results], [("Trail Runner X", "CHF 129.00")])
        self.assertTrue(o.trusted)

    def test_redirect_to_brand_page_is_a_listing_not_a_fake_product(self):
        grid = "".join(tile(i, f"Arc'teryx jacket model {i}") for i in range(6))
        html = (f"<html><head><title>Arc'teryx</title></head><body><main><h1>Arc'teryx</h1>"
                f"<div class='product-grid'>{grid}</div>" + "<p>Brand story.</p>" * 200 + "</main></body></html>")
        o = self.analyse(html, "https://shop.example.com/brands/arcteryx.html",
                         url="https://shop.example.com/search?q=Arc%27teryx", query="Arc'teryx")
        self.assertEqual(o.status, "redirect")
        self.assertEqual(len(o.results), 6)
        self.assertNotIn("Arc'teryx", [r.title for r in o.results])

    def test_cotswold_brand_page_never_becomes_a_pdp(self):
        html = ("<html><head><meta property='og:type' content='product'></head><body><h1>Arc'teryx</h1></body></html>")
        self.assertIsNone(f._extract_pdp(soup(html), "https://www.cotswoldoutdoor.com/brands/arcteryx.html"))

    def test_cotswold_no_results_destination(self):
        o = self.analyse("<html><body>" + "<p>x</p>" * 400 + "</body></html>",
                         "https://www.cotswoldoutdoor.com/lister/no-results.html?q=x",
                         url="https://www.cotswoldoutdoor.com/lister.html?q=x", query="x")
        self.assertEqual(o.status, "zero_confirmed")

    def test_redirect_with_nothing_readable_is_unverified(self):
        o = self.analyse("<html><head><title>Inspiration</title></head><body><main>" + "<p>Stories.</p>" * 400 +
                         "<a href='/p/x'>x</a></main></body></html>", "https://shop.example.com/inspiration/")
        self.assertEqual(o.status, "zero_unverified")


class LLMTests(unittest.TestCase):
    def setUp(self):
        f._site_extraction_profile = None

    def test_grounding_drops_hallucinated_items(self):
        cards = "".join(f"<div class='x{i}'><a href='/shop/real-{i}'>Real Product Number {i}</a> €{i}9</div>"
                        for i in range(3))
        html = f"<html><body><main><div class='wrap'>{cards}</div></main></body></html>"
        items = f._LLMExtraction(items=[
            f._LLMExtractedItem(title="Real Product Number 0", url="/shop/real-0", price="€09"),
            f._LLMExtractedItem(title="Invented Super Boot 3000", url="/shop/real-1"),
            f._LLMExtractedItem(title="Real Product Number 2", url="https://elsewhere.example/fake"),
            f._LLMExtractedItem(title="Real  product number 1", url=None),
        ])
        client = FakeClient([parsed_response(items), parsed_response(items)])
        res = f._extract_with_llm(html, "secret query words", 15, url="https://shop.example.com/s?q=x", client=client)
        self.assertEqual([r.title for r in res], ["Real Product Number 0", "Real  product number 1"])
        self.assertEqual([r.rank for r in res], [1, 2])
        for call in client.messages.calls:
            self.assertNotIn("secret query words", json.dumps(call, default=str))
            self.assertEqual(call["output_format"], f._LLMExtraction)

    def test_validation_prompt_has_no_query(self):
        results = [SearchResult(rank=i, title=f"Thing {i} for sale", url=f"#x{i}") for i in range(1, 4)]
        client = FakeClient([parsed_response(f._LLMValidation(product_indices=[1, 3]))])
        kept = f._validate_results_with_llm(results, "secret query words", client=client)
        self.assertEqual([r.title for r in kept], ["Thing 1 for sale", "Thing 3 for sale"])
        self.assertNotIn("secret query words", json.dumps(client.messages.calls[0], default=str))

    def test_main_content_by_product_link_density(self):
        header = "<header><div class='flex items-center'>" + "<a href='/c/cat'>Cat</a>" * 30 + "</div></header>"
        grid = "<div class='grid-x'>" + "".join(f"<a href='/products/p{i}'>P{i}</a>" for i in range(10)) + "</div>"
        html = f"<html><body>{header}<div class='items-center'>menu</div><main><section>{grid}</section></main></body></html>"
        container = f._best_product_container(soup(html))
        self.assertEqual(container.get("class"), ["grid-x"])

    def test_no_key_no_client_means_no_call(self):
        with mock.patch.object(f, "_HAS_API_KEY", False):
            self.assertEqual(f._extract_with_llm("<html></html>", "q", 15), [])
            res = [SearchResult(rank=1, title="Thing for sale", url="#x")]
            self.assertEqual(f._validate_results_with_llm(res, "q"), res)


if __name__ == "__main__":
    unittest.main()
