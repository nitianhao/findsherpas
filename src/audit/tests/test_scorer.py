"""Scorer: title cleaning, no price in documents, retry classification, resume. Stub Voyage client."""

import unittest
from types import SimpleNamespace
from unittest import mock

import voyageai.error as verr

from src import scorer
from src.models import SearchResult, TestQuery
import tests.helpers  # noqa: F401


def _ok(n):
    return SimpleNamespace(results=[SimpleNamespace(index=i, relevance_score=0.9 - i * 0.1) for i in range(n)])


class FakeVoyage:
    def __init__(self, *items):
        self.items = list(items)
        self.calls = []

    def rerank(self, **kw):
        self.calls.append(kw)
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _q(q):
    return TestQuery(category="TYPO", query=q, rationale="t")


def _res(*titles):
    return [SearchResult(rank=i, title=t, price="€99,95") for i, t in enumerate(titles, 1)]


class TitleCleaningTests(unittest.TestCase):
    def test_table(self):
        table = {
            "Pre Sale Salewa | T-Shirts Herren Pedroc Dry Hyb T-Shirt": "Salewa Herren Pedroc Dry Hyb T-Shirt",
            "Pre Sale +2 Sweet Protection | Fahrradhelme Falconer Aero": "Sweet Protection Fahrradhelme Falconer Aero",
            "Mammut | Wanderjacken Damen Nordwand Pro HS": "Mammut Damen Nordwand Pro HS",
            "Samarbetsföretag Geggamoja Solglasögon Baby": "Geggamoja Solglasögon Baby",
            "RIKIKI Badrock i frotté TINTIN Medlemspris": "RIKIKI Badrock i frotté TINTIN",
            "Red Wing Blacksmith Herren, Braun (3343)": "Red Wing Blacksmith Herren, Braun",
            "New Balance 574 Kids": "New Balance 574 Kids",
            "New: Arc Jacket": "Arc Jacket",
            "Trail Shoe ★★★★☆ 4.5 out of 5": "Trail Shoe",
        }
        for raw, clean in table.items():
            with self.subTest(raw=raw):
                self.assertEqual(scorer.clean_title_for_rerank(raw), clean)

    def test_document_has_no_price_and_result_keeps_title(self):
        r = SearchResult(rank=1, title="Pre Sale Vaude | Jacken Damen Escape", price="€199,95", snippet="Light")
        doc = scorer._build_document(r)
        self.assertNotIn("199", doc)
        self.assertEqual(doc, "Vaude Damen Escape | Light")
        client = FakeVoyage(_ok(1))
        out = scorer.score_results([_q("jacke")], {"jacke": [r]}, client=client)
        self.assertEqual(out["jacke"][0].title, "Pre Sale Vaude | Jacken Damen Escape")
        self.assertEqual(out["jacke"][0].price, "€199,95")


class RetryTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(scorer.time, "sleep")
        self.sleep = p.start()
        self.addCleanup(p.stop)

    def test_classification(self):
        for e in (verr.RateLimitError("x"), verr.ServiceUnavailableError("x"), verr.Timeout("x"),
                  verr.APIConnectionError("x"), verr.ServerError("x"), verr.TryAgain("x")):
            self.assertTrue(scorer.is_transient(e), type(e).__name__)
        for e in (verr.AuthenticationError("x"), verr.InvalidRequestError("x"), verr.MalformedRequestError("x"),
                  ValueError("x")):
            self.assertFalse(scorer.is_transient(e), type(e).__name__)

    def test_transient_retried(self):
        client = FakeVoyage(verr.RateLimitError("429"), verr.ServerError("500"), _ok(2))
        out = scorer.score_results([_q("a")], {"a": _res("A1", "A2")}, client=client)
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(len(out["a"]), 2)

    def test_auth_fails_fast_with_partial(self):
        client = FakeVoyage(_ok(1), verr.AuthenticationError("401"))
        with self.assertRaises(scorer.ScoringError) as cm:
            scorer.score_results([_q("a"), _q("b")], {"a": _res("A1"), "b": _res("B1")}, client=client)
        self.assertEqual(len(client.calls), 2)          # no retries on 401
        self.assertEqual(list(cm.exception.partial), ["a"])
        self.sleep.assert_not_called()

    def test_exhausted_retries_carry_partial(self):
        client = FakeVoyage(_ok(1), *[verr.Timeout("t")] * scorer._MAX_ATTEMPTS)
        with self.assertRaises(scorer.ScoringError) as cm:
            scorer.score_results([_q("a"), _q("b")], {"a": _res("A1"), "b": _res("B1")}, client=client)
        self.assertIn("a", cm.exception.partial)

    def test_resume_skips_scored_queries(self):
        first = scorer.score_results([_q("a")], {"a": _res("A1")}, client=FakeVoyage(_ok(1)))
        client = FakeVoyage(_ok(1))
        out = scorer.score_results([_q("a"), _q("b")], {"a": _res("A1"), "b": _res("B1")},
                                   already_scored=first, client=client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["query"], "b")
        self.assertEqual(set(out), {"a", "b"})

    def test_missing_index_is_error(self):
        client = FakeVoyage(SimpleNamespace(results=[SimpleNamespace(index=0, relevance_score=0.5)]))
        with self.assertRaises(scorer.ScoringError):
            scorer.score_results([_q("a")], {"a": _res("A1", "A2")}, client=client)

    def test_sponsored_flag_carried(self):
        r = [SearchResult(rank=1, title="Ad", sponsored=True), SearchResult(rank=2, title="Organic")]
        out = scorer.score_results([_q("a")], {"a": r}, client=FakeVoyage(_ok(2)))
        self.assertEqual({s.title: s.sponsored for s in out["a"]}, {"Ad": True, "Organic": False})


if __name__ == "__main__":
    unittest.main()
