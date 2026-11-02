"""Fetcher page analysis: every page maps to a FetchStatus, and an empty result list is
only ever ZERO_CONFIRMED when the page itself says "no results". Offline, no browsers."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import tests.helpers  # noqa: F401  (offline env)
from src import fetcher as f

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fetcher"
REPORTS = Path(__file__).resolve().parent.parent / "reports"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def tile(i: int, title: str, price: str = "€19,99", cls: str = "product-tile", href: str | None = None) -> str:
    href = href or f"/p/item-{i}/{100 + i}/"
    return (f'<li class="{cls}"><a href="{href}"><h3 class="product-title">{title}</h3></a>'
            f'<span class="price">{price}</span></li>')


def results_page(titles: list[str], header: str = "", title: str = "Search", extra: str = "") -> str:
    tiles = "".join(tile(i, t) for i, t in enumerate(titles))
    filler = "<p>" + "Free delivery over €50. Easy returns. " * 80 + "</p>"
    return (f"<html><head><title>{title}</title></head><body><header><nav><a href='/'>Home</a></nav></header>"
            f"<main><h1>{header}</h1><ul class='product-grid'>{tiles}</ul>{extra}{filler}</main></body></html>")


def analyse(html: str, url: str = "https://shop.example.com/search?q=boots", query: str = "boots",
            final_url: str | None = None, **kw):
    return f._analyse_page(html=html, url=url, final_url=final_url or url, query=query, max_results=15, **kw)


class OfflineLLM(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(f, "_HAS_API_KEY", False)
        p.start()
        self.addCleanup(p.stop)
        f._site_extraction_profile = None


class BlockDetectionTests(OfflineLLM):
    def test_akamai_access_denied(self):
        o = analyse(fixture("akamai_access_denied.html"), url="https://www.douglas.de/de/search?q=x", query="x")
        self.assertEqual(o.status, "blocked")
        self.assertIn("akamai", o.evidence)
        self.assertFalse(o.trusted)

    def test_datadome(self):
        o = analyse(fixture("datadome.html"))
        self.assertEqual(o.status, "blocked")
        self.assertIn("datadome", o.evidence)

    def test_perimeterx_press_and_hold(self):
        o = analyse(fixture("perimeterx.html"))
        self.assertEqual(o.status, "blocked")
        self.assertIn("perimeterx", o.evidence)

    def test_cloudflare_challenge(self):
        self.assertEqual(f._classify_response(fixture("cloudflare_challenge.html")), "cloudflare")
        self.assertEqual(analyse(fixture("cloudflare_challenge.html")).status, "blocked")

    def test_waf_status_codes(self):
        small = "<html><head><title>Error</title></head><body><p>Request refused.</p></body></html>"
        for code in (403, 429, 503, 400):
            o = analyse(small, http_status=code)
            self.assertEqual(o.status, "blocked", code)
            self.assertIn(f"http_{code}", o.evidence)

    def test_403_with_a_full_real_page_is_not_blocked(self):
        # Headed-challenge hosts: the goto status belongs to the challenge, the content is real.
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(15)], header="15 results")
        self.assertEqual(analyse(html, http_status=403).status, "ok")

    def test_tiny_product_less_body_is_blocked(self):
        o = analyse("<html><body><div id='app'></div></body></html>")
        self.assertEqual(o.status, "blocked")
        self.assertIn("tiny_page", o.evidence)

    def test_tiny_page_with_no_results_marker_is_a_zero(self):
        o = analyse("<html><head><title>Suche</title></head><body><main><h1>Keine Treffer</h1></main></body></html>")
        self.assertEqual(o.status, "zero_confirmed")

    def test_shopify_challenge(self):
        html = results_page([f"Boot {i} with a long product name" for i in range(5)])
        o = analyse(html, final_url="https://shop.example.com/challenge")
        self.assertEqual(o.status, "blocked")

    def test_recaptcha_script_on_a_real_results_page_is_not_a_block(self):
        extra = '<script src="https://www.google.com/recaptcha/api.js"></script><div class="g-recaptcha"></div>'
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(15)], extra=extra)
        self.assertEqual(analyse(html).status, "ok")


class NoResultsMarkerTests(OfflineLLM):
    def test_german_no_results_with_carousel_is_zero_confirmed_and_empty(self):
        html = fixture("no_results_de_carousel.html")
        for url in ("https://www.bergzeit.de/search/?q=was+soll+ich", "https://shop.example.de/suche?q=was+soll+ich"):
            o = analyse(html, url=url, query="was soll ich beim Wandern im Winter anziehen")
            self.assertEqual(o.status, "zero_confirmed", url)
            self.assertEqual(o.results, [])
            self.assertEqual(o.total_hits, 0)
            self.assertIn("keine Treffer", o.evidence)

    def test_swedish_no_results_with_carousel(self):
        o = analyse(fixture("no_results_sv_carousel.html"), url="https://www.ahlens.se/sok?q=barnstol+tr%C3%A4",
                    query="barnstol trä")
        self.assertEqual(o.status, "zero_confirmed")
        self.assertEqual(o.results, [])

    def test_english_no_results_with_carousel(self):
        o = analyse(fixture("no_results_en_carousel.html"), query="qwxzv jacket")
        self.assertEqual(o.status, "zero_confirmed")
        self.assertEqual(o.results, [])

    def test_marker_skips_cached_selectors(self):
        f._site_extraction_profile = f.SiteExtractionProfile("ul.product-list", "li.product-tile", "h3")
        try:
            o = analyse(fixture("no_results_en_carousel.html"), query="qwxzv jacket")
        finally:
            f._site_extraction_profile = None
        self.assertEqual(o.status, "zero_confirmed")
        self.assertEqual(o.results, [])

    def test_zero_regex_is_word_bounded(self):
        rx = f._NO_RESULTS_RE
        for text in ("10 results", "Showing 100 Treffer", "20 Ergebnisse", "1.0 results", "30 träffar"):
            self.assertIsNone(rx.search(text), text)
        for text in ("0 results", "Showing 0 result", "0 Ergebnisse für „x“", "keine Treffer", "Inga träffar på x",
                     "ingen resultater", "geen resultaten", "aucun résultat", "nessun risultato",
                     "brak wyników", "žádné výsledky", "ei tuloksia", "Suchergebnis für »lampe« (0)"):
            self.assertIsNotNone(rx.search(text), text)
        # End-of-list messages on REAL result pages are not zeros.
        self.assertIsNone(rx.search("Keine weiteren Ergebnisse"))
        self.assertIsNone(rx.search("No more results"))

    def test_ten_results_page_is_ok_not_zero(self):
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(10)], header="Showing 10 results")
        o = analyse(html)
        self.assertEqual(o.status, "ok")
        self.assertEqual(len(o.results), 10)
        self.assertEqual(o.total_hits, 10)

    def test_marker_in_header_autocomplete_is_ignored(self):
        extra_header = '<div class="search-suggest"><p>No results</p></div>'
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(15)]).replace(
            "<header>", f"<header>{extra_header}")
        self.assertEqual(analyse(html).status, "ok")

    def test_hidden_template_marker_is_ignored(self):
        extra = '<div hidden><p>No results found</p></div><div style="display: none">0 results</div>'
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(15)], extra=extra)
        self.assertEqual(analyse(html).status, "ok")

    def test_browser_visible_text_is_preferred(self):
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(6)])
        o = analyse(html, visible_text="Sorry, no results found for boots. You may also like ...")
        self.assertEqual(o.status, "zero_confirmed")

    def test_autocorrect_with_results_keeps_results(self):
        header = "Keine Treffer für „shampooo“. Wir zeigen dir Ergebnisse für „shampoo“ (27 Treffer)"
        html = results_page([f"Anti-Schuppen Shampoo Sorte {i}" for i in range(15)], header=header)
        o = analyse(html, query="shampooo", url="https://shop.example.de/suche?q=shampooo")
        self.assertEqual(o.status, "ok")
        self.assertEqual(len(o.results), 15)
        self.assertIn("corrected", o.evidence)

    def test_marker_and_positive_hit_count_is_unverified(self):
        header = "Leider keine Treffer für „x“"
        extra = '<div class="result-count">Showing 48 results</div>'
        html = results_page([f"Boot {i} with a long name" for i in range(6)], header=header, extra=extra)
        o = analyse(html, query="x")
        self.assertEqual(o.status, "zero_unverified")
        self.assertFalse(o.trusted)


class CountsAndEmptyPagesTests(OfflineLLM):
    def test_count_header_partial(self):
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(4)], header="124 results for “boots”")
        o = analyse(html)
        self.assertEqual(o.status, "partial")
        self.assertEqual(o.total_hits, 124)
        self.assertEqual(len(o.results), 4)
        self.assertTrue(o.trusted)

    def test_hit_count_smaller_than_tiles_truncates_padding(self):
        html = results_page([f"Waterproof hiking boot model {i}" for i in range(8)], header="3 results")
        o = analyse(html)
        self.assertEqual(o.status, "ok")
        self.assertEqual(len(o.results), 3)
        self.assertEqual([r.rank for r in o.results], [1, 2, 3])

    def test_query_digits_are_not_a_hit_count(self):
        html = results_page([f"Sock bundle colour {i} assorted" for i in range(15)],
                            title="Search: pack of 6 items")
        o = analyse(html, query="pack of 6 items")
        self.assertIsNone(o.total_hits)
        self.assertEqual(o.status, "ok")

    def test_nothing_extracted_no_marker_is_unverified(self):
        html = "<html><head><title>Search</title></head><body><main>" + "<p>Lorem ipsum dolor.</p>" * 400 + \
               "<a href='/p/x'>x</a></main></body></html>"
        o = analyse(html)
        self.assertEqual(o.status, "zero_unverified")
        self.assertFalse(o.trusted)

    def test_readiness_timeout_turns_empty_into_timeout(self):
        html = "<html><head><title>Search</title></head><body><main>" + "<p>Lorem ipsum dolor.</p>" * 400 + \
               "<a href='/p/x'>x</a></main></body></html>"
        self.assertEqual(analyse(html, ready="timeout").status, "timeout")

    def test_dedicated_host_empty_without_marker_is_unverified(self):
        html = "<html><head><title>Avoca</title></head><body><main>" + "<p>Our story.</p>" * 400 + \
               "<a href='/products/x'>x</a></main></body></html>"
        o = analyse(html, url="https://avoca.com/search?q=knitwear", query="knitwear")
        self.assertEqual(o.status, "zero_unverified")

    @unittest.skipUnless((REPORTS / "_avoca_noresults.html").exists(), "historical capture not present")
    def test_real_avoca_captures(self):
        url = "https://avoca.com/search?q=scuba+diving+oxygen+tank"
        o = analyse((REPORTS / "_avoca_noresults.html").read_text(), url=url, query="scuba diving oxygen tank")
        self.assertEqual(o.status, "zero_confirmed")
        url = "https://avoca.com/search?q=knitwear"
        o = analyse((REPORTS / "_avoca_knitwear.html").read_text(), url=url, query="knitwear")
        self.assertEqual(o.total_hits, 384)
        self.assertEqual(o.status, "partial")  # capture holds 12 of 384 tiles
        self.assertEqual(len(o.results), 12)


class HostProfileTests(OfflineLLM):
    def douglas_page(self, title: str, h1: str = "", tiles: int = 0) -> str:
        grid = "".join(
            f'<div class="product-tile"><a href="/de/p/{5000 + i}"><span>Lippenstift für Unisex DIOR Rouge Nummer {i}</span></a>'
            f'<span>39,99 €</span></div>' for i in range(tiles))
        body = f"<h1>{h1}</h1>" if h1 else ""
        return (f"<html><head><title>{title}</title></head><body><main>{body}<div class='product-grid'>{grid}</div>"
                + "<p>Douglas Beauty Card.</p>" * 300 + "</main></body></html>")

    def test_douglas_stale_zero_heading_does_not_wipe_tiles(self):
        html = self.douglas_page("Suche | DOUGLAS", h1="0 Ergebnisse für „lankome maskara“", tiles=6)
        o = analyse(html, url="https://www.douglas.de/de/search?q=lankome+maskara", query="lankome maskara")
        self.assertEqual(o.status, "ok")
        self.assertEqual(len(o.results), 6)

    def test_douglas_title_marker_confirms_zero(self):
        html = self.douglas_page("Keine Ergebnisse gefunden | DOUGLAS")
        o = analyse(html, url="https://www.douglas.de/de/search?q=x", query="x")
        self.assertEqual(o.status, "zero_confirmed")

    def test_douglas_empty_without_title_marker_is_unverified(self):
        html = self.douglas_page("Suche | DOUGLAS")
        o = analyse(html, url="https://www.douglas.de/de/search?q=x", query="x")
        self.assertEqual(o.status, "zero_unverified")
        self.assertIn("Akamai", o.evidence)

    def manufactum_page(self, h1: str, tiles: int) -> str:
        grid = "".join(
            f'<div data-test-sell-product-tile="true"><a data-test-sell-product-link="true" href="/topf-a{70 + i}/">'
            f'<span data-test-sell-product-name="true">Topf {i}</span></a>'
            f'<span data-test-stelar-price-price="true">{39 + i},90 €</span></div>' for i in range(tiles))
        return (f"<html><head><title>Manufactum</title></head><body><main><h1>{h1}</h1>{grid}"
                + "<p>Es gibt sie noch, die guten Dinge.</p>" * 200 + "</main></body></html>")

    def test_manufactum_zero_header(self):
        o = analyse(self.manufactum_page("Suchergebnis für »lampe xyz« (0)", 8),
                    url="https://www.manufactum.de/suche?q=lampe+xyz", query="lampe xyz")
        self.assertEqual(o.status, "zero_confirmed")
        self.assertEqual(o.results, [])

    def test_manufactum_header_caps_tiles_and_keeps_short_titles(self):
        o = analyse(self.manufactum_page("Suchergebnis für »topf« (2)", 8),
                    url="https://www.manufactum.de/suche?q=topf", query="topf")
        self.assertEqual([r.title for r in o.results], ["Topf 0", "Topf 1"])  # <8 chars, still kept
        self.assertEqual(o.total_hits, 2)

    def test_manufactum_unparseable_header_never_scrapes_all_tiles(self):
        o = analyse(self.manufactum_page("Unsere Empfehlungen", 8),
                    url="https://www.manufactum.de/suche?q=topf", query="topf")
        self.assertEqual(o.status, "zero_unverified")
        self.assertEqual(o.results, [])

    def zalando_page(self, with_count: bool = True, marker: bool = False) -> str:
        def art(i, name):
            return (f'<article><a href="/brand-{name.lower().replace(" ", "-")}-{i}.html">'
                    f'<div>Brand{i}</div><div>{name}</div><div>€{20 + i}.95</div></a></article>')
        grid = "".join(art(i, f"Running shoe {i}") for i in range(4))
        reco = "".join(art(10 + i, f"Baggy jeans {i}") for i in range(6))
        count = '<div data-testid="product-count">4 items</div>' if with_count else ""
        msg = "<p>Try a different search term or check the spelling.</p>" if marker else ""
        return (f"<html><head><title>Zalando</title></head><body><main>{msg}{count}<ul role='list'>{grid}</ul>"
                f"<h2>Recommended for you</h2><ul role='list'>{reco}</ul>"
                + "<p>Free delivery.</p>" * 200 + "</main></body></html>")

    def test_zalando_stops_at_recommendation_heading(self):
        o = analyse(self.zalando_page(), url="https://www.zalando.ie/catalog/?q=running+shoe", query="running shoe")
        self.assertEqual(o.status, "ok")
        self.assertEqual(len(o.results), 4)
        self.assertTrue(all("Running shoe" in r.title for r in o.results))

    def test_zalando_without_count_header_is_unverified(self):
        o = analyse(self.zalando_page(with_count=False), url="https://www.zalando.de/katalog/?q=x", query="x")
        self.assertEqual(o.status, "zero_unverified")

    def test_zalando_marker(self):
        o = analyse(self.zalando_page(with_count=False, marker=True),
                    url="https://www.zalando.co.uk/catalog/?q=asdf", query="asdf")
        self.assertEqual(o.status, "zero_confirmed")

    def test_zalando_is_headed_on_every_market(self):
        for host in ("www.zalando.de", "www.zalando.co.uk", "www.zalando.ie", "en.zalando.pl"):
            self.assertTrue(f._needs_headed_chromium(f"https://{host}/catalog/?q=x"), host)

    def test_bergzeit_never_scrapes_whole_page_p_links(self):
        carousel = "".join(f'<a href="/p/reco-{i}/{900 + i}/">Empfehlung {i} Jacke 49,95 €</a>' for i in range(8))
        html = (f"<html><head><title>Suche | Bergzeit</title></head><body><main><div class='teaser'>{carousel}</div>"
                + "<p>Bergsport.</p>" * 300 + "</main></body></html>")
        o = analyse(html, url="https://www.bergzeit.de/search/?q=winter", query="winter")
        self.assertEqual(o.results, [])
        self.assertEqual(o.status, "zero_unverified")


if __name__ == "__main__":
    unittest.main()
