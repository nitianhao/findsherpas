"""fetch_all_outcomes end to end with the transports stubbed (no network, no browsers):
probe/fast-fail, retries, timeouts, errors, evidence capture, checkpointing, search-API
cross-checks and the legacy wrappers."""

from __future__ import annotations

import gzip
import json
import os
import runpy
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import tests.helpers  # noqa: F401  (offline env)
from src import fetcher as f
from src.models import FetchOutcome, SiteContext, TestQuery

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fetcher"
AUDIT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = "https://shop.example.com/search?q={}"


def grid_page(query: str, n: int = 15) -> str:
    tiles = "".join(
        f"<li class='product-tile'><a href='/p/{query.replace(' ', '-')}-{i}'>"
        f"<h3 class='product-title'>{query.title()} product number {i}</h3></a><span class='price'>€{20 + i},00</span></li>"
        for i in range(n))
    return ("<html><head><title>Search</title></head><body><main><ul class='product-grid'>"
            f"{tiles}</ul>" + "<p>Free delivery over €50.</p>" * 200 + "</main></body></html>")


def zero_page(query: str) -> str:
    return ("<html><head><title>Search</title></head><body><main>"
            f"<h1>No results for “{query}”</h1>" + "<p>Try another search.</p>" * 300 + "</main></body></html>")


EMPTY_PAGE = ("<html><head><title>Search</title></head><body><main>" + "<p>Loading…</p>" * 400 +
              "<a href='/p/x'>x</a></main></body></html>")


def page(html: str, url: str, status: int = 200, browser: str = "static") -> f.PageFetch:
    return f.PageFetch(html=html, final_url=url, http_status=status, browser=browser)


def query_of(url: str) -> str:
    from urllib.parse import parse_qs, urlparse
    return parse_qs(urlparse(url).query).get("q", [""])[0]


class FlowBase(unittest.TestCase):
    def setUp(self):
        for target, value in (("_HAS_API_KEY", False), ("_sleep", lambda s: None)):
            p = mock.patch.object(f, target, value)
            p.start()
            self.addCleanup(p.stop)
        self.static_calls: list[str] = []
        self.pw_calls: list[str] = []

    def patch_transports(self, static=None, playwright=None):
        def _static(url, timeout=15):
            self.static_calls.append(url)
            return static(url) if static else f.PageFetch(final_url=url, error="no static")

        def _pw(url, quick_probe=False, force_browser=None, screenshot_path=None):
            self.pw_calls.append(url)
            return playwright(url) if playwright else f.PageFetch(final_url=url, error="no browser")

        for name, fn in (("_static_fetch", _static), ("_playwright_fetch", _pw)):
            p = mock.patch.object(f, name, side_effect=fn)
            p.start()
            self.addCleanup(p.stop)


class ProbeAndFastFailTests(FlowBase):
    def test_static_site_all_ok_in_input_order(self):
        self.patch_transports(static=lambda url: page(grid_page(query_of(url)), url))
        queries = ["boots", "tent", "stove"]
        out = f.fetch_all_outcomes(queries, TEMPLATE)
        self.assertEqual(list(out), queries)
        self.assertTrue(all(o.status == "ok" and len(o.results) == 15 for o in out.values()))
        self.assertEqual(self.pw_calls, [])  # static was good enough: no browser launched

    def test_testquery_input_and_duplicates(self):
        self.patch_transports(static=lambda url: page(grid_page(query_of(url)), url))
        tq = TestQuery(category="DIRECT_MATCH", query="boots", rationale="r")
        out = f.fetch_all_outcomes([tq, "boots", "tent"], TEMPLATE)
        self.assertEqual(list(out), ["boots", "tent"])

    def test_blocked_site_fails_fast_with_blocked_not_empty_zero(self):
        akamai = (FIXTURES / "akamai_access_denied.html").read_text()
        self.patch_transports(
            static=lambda url: page(akamai, url, status=403),
            playwright=lambda url: f.PageFetch(html=akamai, final_url=url, http_status=403, block="akamai",
                                               browser="chromium"),
        )
        out = f.fetch_all_outcomes(["a", "b", "c"], TEMPLATE)
        self.assertEqual({o.status for o in out.values()}, {"blocked"})
        self.assertEqual(out["b"].attempts, 0)
        self.assertEqual(len(self.pw_calls), 1)  # probed once, never hammered
        self.assertFalse(any(o.trusted for o in out.values()))

    def test_probe_timeout_marks_timeout_and_tries_next_probe(self):
        release = threading.Event()
        calls = []

        def fake_probe(url, query, max_results, evidence_dir=None, client=None):
            calls.append(query)
            if query == "slow":
                release.wait(5)
                return f.SiteMode.FAILED, f._outcome(query, f.FetchStatus.ERROR), ""
            return f.SiteMode.STATIC, f.FetchOutcome(query=query, status="ok", results=[]), ""

        with mock.patch.object(f, "_PROBE_TIMEOUT_S", 0.2), mock.patch.object(f, "_probe_outcome", fake_probe), \
                mock.patch.object(f, "_fetch_with_retries",
                                  side_effect=lambda url, q, *a, **k: (f.FetchOutcome(query=q, status="ok"), "")):
            out = f.fetch_all_outcomes(["slow", "fast", "next"], TEMPLATE)
        release.set()
        self.assertEqual(out["slow"].status, "timeout")
        self.assertEqual(calls, ["slow", "fast"])
        self.assertEqual(out["next"].status, "ok")

    def test_all_probes_fail_remaining_get_failure_status(self):
        self.patch_transports()  # nothing loads anywhere
        out = f.fetch_all_outcomes(["a", "b", "c", "d", "e"], TEMPLATE)
        self.assertEqual({o.status for o in out.values()}, {"error"})
        self.assertEqual(out["e"].attempts, 0)
        self.assertIn("not fetched", out["e"].evidence)

    def test_invalid_template(self):
        out = f.fetch_all_outcomes(["a"], "https://shop.example.com/search")
        self.assertEqual(out["a"].status, "error")


class RetryTests(FlowBase):
    def test_transient_empty_page_recovers_on_retry(self):
        seen: dict[str, int] = {}

        def static(url):
            q = query_of(url)
            seen[q] = seen.get(q, 0) + 1
            if q == "flaky" and seen[q] == 1:  # flaky's first attempt renders nothing
                return page(EMPTY_PAGE, url)
            return page(grid_page(q), url)

        self.patch_transports(static=static)
        out = f.fetch_all_outcomes(["boots", "flaky"], TEMPLATE)
        self.assertEqual(out["flaky"].status, "ok")
        self.assertEqual(out["flaky"].attempts, 2)
        self.assertIn("zero_unverified", out["flaky"].evidence)

    def test_zero_confirmed_is_rechecked_once(self):
        self.patch_transports(static=lambda url: page(
            zero_page(query_of(url)) if query_of(url) == "gibberish" else grid_page(query_of(url)), url))
        out = f.fetch_all_outcomes(["boots", "gibberish"], TEMPLATE)
        self.assertEqual(out["gibberish"].status, "zero_confirmed")
        self.assertEqual(out["gibberish"].attempts, 2)
        self.assertEqual(out["gibberish"].results, [])

    def test_unverified_zero_is_retried_three_times_then_stays_unverified(self):
        self.patch_transports(static=lambda url: page(
            EMPTY_PAGE if query_of(url) == "ghost" else grid_page(query_of(url)), url))
        out = f.fetch_all_outcomes(["boots", "ghost"], TEMPLATE)
        self.assertEqual(out["ghost"].status, "zero_unverified")
        self.assertEqual(out["ghost"].attempts, f._MAX_ATTEMPTS)

    def test_thin_result_with_matching_hit_count_is_not_retried(self):
        def static(url):
            q = query_of(url)
            html = grid_page(q, 2).replace("<main>", "<main><h1>2 results</h1>") if q == "rare" else grid_page(q)
            return page(html, url)

        self.patch_transports(static=static)
        out = f.fetch_all_outcomes(["boots", "rare"], TEMPLATE)
        self.assertEqual((out["rare"].status, out["rare"].attempts), ("ok", 1))

    def test_per_query_timeout_and_exception(self):
        self.patch_transports(static=lambda url: page(grid_page(query_of(url)), url))
        release = threading.Event()
        real_once = f._fetch_once

        def once(url, query, *a, **k):
            if query == "hang":
                release.wait(5)
            if query == "boom":
                raise RuntimeError("kaboom")
            return real_once(url, query, *a, **k)

        with mock.patch.object(f, "_PER_ATTEMPT_TIMEOUT_S", 0.2), mock.patch.object(f, "_fetch_once", once):
            out = f.fetch_all_outcomes(["boots", "hang", "boom", "tent"], TEMPLATE)
        release.set()
        self.assertEqual(out["hang"].status, "timeout")
        self.assertEqual(out["boom"].status, "error")
        self.assertIn("kaboom", out["boom"].evidence)
        self.assertEqual(out["tent"].status, "ok")

    def test_consecutive_blocks_stop_the_run(self):
        akamai = (FIXTURES / "akamai_access_denied.html").read_text()
        self.patch_transports(static=lambda url: page(
            grid_page("boots") if query_of(url) == "boots" else akamai, url, 200 if query_of(url) == "boots" else 403))
        out = f.fetch_all_outcomes(["boots", "a", "b", "c", "d", "e"], TEMPLATE)
        self.assertEqual([out[q].status for q in "abcde"], ["blocked"] * 5)
        self.assertEqual([out[q].attempts for q in "abcde"], [1, 1, 1, 0, 0])


class EvidenceAndWrapperTests(FlowBase):
    def test_evidence_html_saved_and_noted(self):
        self.patch_transports(static=lambda url: page(grid_page(query_of(url)), url))
        with tempfile.TemporaryDirectory() as tmp:
            out = f.fetch_all_outcomes(["Arc'teryx jacket"], TEMPLATE, evidence_dir=os.path.join(tmp, "ev"))
            o = out["Arc'teryx jacket"]
            self.assertIn("[evidence: ", o.evidence)
            path = o.evidence.split("[evidence: ")[1].rstrip("]").split(",")[0]
            self.assertTrue(Path(path).name.startswith("arc-teryx-jacket-"))
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                self.assertIn("product-grid", fh.read())

    def test_on_outcome_called_per_query(self):
        self.patch_transports(static=lambda url: page(grid_page(query_of(url)), url))
        seen = []
        f.fetch_all_outcomes(["a1", "b2", "c3"], TEMPLATE, on_outcome=lambda o: seen.append(o.query))
        self.assertEqual(seen, ["a1", "b2", "c3"])

    def test_fetch_all_results_wrapper(self):
        self.patch_transports(static=lambda url: page(
            zero_page("x") if query_of(url) == "x" else grid_page(query_of(url)), url))
        res = f.fetch_all_results(TEMPLATE, [TestQuery(category="TYPO", query="boots", rationale="r"), "x"])
        self.assertEqual(len(res["boots"]), 15)
        self.assertEqual(res["x"], [])

    def test_legacy_fetch_with_mode_and_extract_results(self):
        self.patch_transports(static=lambda url: page(grid_page(query_of(url)), url))
        results, redirected = f._fetch_with_mode(TEMPLATE.format("boots"), "boots", 15, f.SiteMode.STATIC)
        self.assertEqual((len(results), redirected), (15, False))
        self.assertEqual(f._extract_results(zero_page("x"), 15, url=TEMPLATE.format("x")), [])


class SearchApiTests(unittest.TestCase):
    def test_vendor_detection(self):
        self.assertEqual(f._search_api_vendor("https://abc-dsn.algolia.net/1/indexes/*/queries?x"), "algolia")
        self.assertEqual(f._search_api_vendor("https://eucs1.ksearchnet.com/cs/v2/search"), "klevu")
        self.assertEqual(f._search_api_vendor("https://ac.cnstrc.com/search/boots?key=k"), "constructor")
        self.assertEqual(f._search_api_vendor("https://core.dxpapi.com/api/v1/core/?q=boots"), "bloomreach")
        self.assertIsNone(f._search_api_vendor("https://shop.example.com/api/cart"))

    def test_parsers(self):
        cases = {
            "algolia": ({"results": [{"query": "boots", "nbHits": 120, "hits": [{"name": "Boot A"}]},
                                     {"query": "", "nbHits": 5000, "hits": []}]}, "https://x.algolia.net/1/indexes/*/queries", 120),
            "klevu": ({"queryResults": [{"id": "productSearch", "meta": {"totalResultsFound": 42, "searchedTerm": "boots"},
                                         "records": [{"name": "Boot A"}]}]}, "https://eucs.ksearchnet.com/cs/v2/search", 42),
            "constructor": ({"request": {"term": "boots"}, "response": {"total_num_results": 7, "results": [{"value": "Boot A"}]}},
                            "https://ac.cnstrc.com/search/boots", 7),
            "bloomreach": ({"response": {"numFound": 9, "docs": [{"title": "Boot A"}]}},
                           "https://core.dxpapi.com/api/v1/core/?q=boots", 9),
            "doofinder": ({"query": "boots", "total": 3, "results": [{"title": "Boot A"}]},
                          "https://eu1-search.doofinder.com/5/search?query=boots", 3),
            "searchspring": ({"pagination": {"totalResults": 11}, "results": [{"name": "Boot A"}]},
                             "https://abc.a.searchspring.io/api/search/search.json?q=boots", 11),
            "boost": ({"total_product": 13, "products": [{"title": "Boot A"}]},
                      "https://services.mybcapps.com/bc-sf-filter/search?q=boots", 13),
            "nosto": ({"data": {"search": {"query": "boots", "products": {"total": 4, "hits": [{"name": "Boot A"}]}}}},
                      "https://search.nosto.com/v1/graphql", 4),
        }
        for vendor, (payload, url, total) in cases.items():
            parsed = f.parse_search_api_payload(vendor, url, json.dumps(payload))
            self.assertTrue(parsed, vendor)
            self.assertEqual(parsed[0].total, total, vendor)
            self.assertEqual(parsed[0].titles[0], "Boot A", vendor)
            summary = f._search_api_summary([(vendor, url, json.dumps(payload))], "Boots")
            self.assertIsNotNone(summary, vendor)
            self.assertEqual(summary.total, total, vendor)

    def test_garbage_payloads_never_raise(self):
        for vendor in f._SEARCH_API_PARSERS:
            for body in ("", "not json", "[]", '{"results": "x"}', '{"response": 5}'):
                self.assertIsInstance(f.parse_search_api_payload(vendor, "https://x/?q=a", body), list)

    def test_api_zero_confirms_an_empty_page_and_other_queries_are_ignored(self):
        api = [("algolia", "https://x.algolia.net/1/indexes/*/queries",
                json.dumps({"results": [{"query": "boots", "nbHits": 0, "hits": []},
                                        {"query": "popular", "nbHits": 99, "hits": []}]}))]
        with mock.patch.object(f, "_HAS_API_KEY", False):
            o = f._analyse_page(html=EMPTY_PAGE, url=TEMPLATE.format("boots"), final_url=TEMPLATE.format("boots"),
                                query="boots", max_results=15, search_api=api)
            self.assertEqual(o.status, "zero_confirmed")
            self.assertIn("algolia", o.evidence)
            o = f._analyse_page(html=EMPTY_PAGE, url=TEMPLATE.format("tent"), final_url=TEMPLATE.format("tent"),
                                query="tent", max_results=15, search_api=api)
            self.assertEqual(o.status, "zero_unverified")


class ChunkedFetchScriptTests(unittest.TestCase):
    def test_resume_refetches_only_unsettled_and_saves_per_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1, p3, ck = (os.path.join(tmp, n) for n in ("p1.json", "p3.json", "p4.json"))
            Path(p1).write_text(SiteContext(url="https://shop.example.com", site_type="PHYSICAL_GOODS",
                                            search_url_template=TEMPLATE).model_dump_json())
            qs = [TestQuery(category="TYPO", query=q, rationale="r").model_dump(mode="json")
                  for q in ("kept", "legacy", "blocked", "new")]
            Path(p3).write_text(json.dumps(qs))
            Path(ck).write_text(json.dumps({
                "kept": {"query": "kept", "status": "ok", "results": []},
                "legacy": [{"rank": 1, "title": "Old style result"}],
                "blocked": {"query": "blocked", "status": "blocked", "results": []},
            }))
            fetched = []

            def fake_fetch(queries, template, max_results=15, evidence_dir=None, on_outcome=None):
                self.assertEqual(max_results, 15)
                for q in queries:
                    fetched.append(q)
                    on_outcome(FetchOutcome(query=q, status="zero_confirmed"))
                    self.assertFalse(os.path.exists(ck + ".tmp"))
                    self.assertEqual(json.loads(Path(ck).read_text())[q]["status"], "zero_confirmed")
                return {}

            cwd = os.getcwd()
            try:
                os.chdir(AUDIT_ROOT)
                with mock.patch.object(f, "fetch_all_outcomes", fake_fetch), \
                        mock.patch.object(sys, "argv", ["chunked_fetch.py", p1, p3, ck]), \
                        mock.patch("builtins.print"):
                    runpy.run_path(str(AUDIT_ROOT / "scripts" / "chunked_fetch.py"), run_name="__main__")
            finally:
                os.chdir(cwd)
            self.assertEqual(fetched, ["legacy", "blocked", "new"])
            saved = json.loads(Path(ck).read_text())
            self.assertEqual(saved["kept"]["status"], "ok")
            self.assertEqual(saved["legacy"]["status"], "zero_confirmed")


if __name__ == "__main__":
    unittest.main()
