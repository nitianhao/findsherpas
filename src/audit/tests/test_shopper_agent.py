"""Shopper prototype: guardrails, cost maths and the loop with a stubbed model + browser (offline)."""

import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src import shopper_agent as sa


def _usage(i=100, o=20, r=0, w=0):
    return SimpleNamespace(input_tokens=i, output_tokens=o, cache_read_input_tokens=r, cache_creation_input_tokens=w)


def _tool(name, args, id_="t1"):
    return SimpleNamespace(type="tool_use", name=name, input=args, id=id_)


class GuardrailTests(unittest.TestCase):
    def test_account_and_basket_controls_refused(self):
        url = "https://www.shop.example/lister.html?q=tent"
        for text in ("Add to bag", "Sign in", "Checkout", "My account", "Basket (2)", "Bag"):
            self.assertIsNotNone(sa._blocked_reason({"text": text, "href": ""}, url), text)

    def test_products_with_bag_in_the_name_allowed(self):
        url = "https://www.shop.example/lister.html?q=bag"
        for text in ("Rab Ascent 700 Sleeping Bag", "Osprey Daylite Bag 13L", "Load more", "Sort by price"):
            self.assertIsNone(sa._blocked_reason({"text": text, "href": "/p/x"}, url), text)

    def test_offsite_and_account_urls_refused(self):
        url = "https://www.shop.example/lister.html?q=x"
        self.assertIsNotNone(sa._blocked_reason({"text": "Partner", "href": "https://other.example/"}, url))
        self.assertIsNotNone(sa._blocked_reason({"text": "Orders", "href": "/account/orders"}, url))
        self.assertIsNone(sa._blocked_reason({"text": "Tent", "href": "https://shop.example/p/tent"}, url))


class CostTests(unittest.TestCase):
    def test_usage_cost(self):
        u = sa.Usage(input_tokens=1_000_000, output_tokens=100_000, cache_read_input_tokens=1_000_000,
                     cache_creation_input_tokens=0)
        self.assertAlmostEqual(u.cost("claude-sonnet-5-5"), 2.00 + 1.00 + 0.20)
        self.assertAlmostEqual(u.cost("claude-haiku-5-5"), 0.10 + 0.05 + 0.01)


class _FakeBrowser:
    def __init__(self):
        self.page = SimpleNamespace(url="https://www.shop.example/")
        self.visited = []

    def goto(self, url):
        self.visited.append(url)
        self.page.url = url

    def observe(self):
        shot = base64.b64encode(b"jpeg").decode()
        return self.page.url, "Title", shot, [{"ref": 1, "tag": "a", "text": "Women's Boot GTX", "href": "/p/1"}]

    def click(self, ref):
        self.page.url = "https://www.shop.example/p/1"
        return f"Clicked [{ref}]"

    def scroll(self, direction):
        return "Scrolled"

    def back(self):
        return "Went back"


class _FakeClient:
    def __init__(self, turns):
        self._turns = list(turns)
        self.requests = []
        verdict = sa.SessionVerdict(observations="x", goal_met=True, searches_needed=1, first_search_worked=True,
                                    friction=[], client_summary="Fine.", severity="PASS")
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.messages = SimpleNamespace(parse=lambda **k: SimpleNamespace(
            parsed_output=verdict, usage=_usage(500, 100), stop_reason="end_turn"))

    def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot, like the SDK serialising
        return SimpleNamespace(content=[self._turns.pop(0)], usage=_usage(100, 30, 1000, 200))


class LoopTests(unittest.TestCase):
    def test_search_click_finish_records_steps_and_cost(self):
        client = _FakeClient([
            _tool("search", {"query": "womens waterproof walking boots"}, "a"),
            _tool("click", {"ref": 1}, "b"),
            _tool("finish", {"outcome": "found", "product_title": "Women's Boot GTX",
                             "product_url": "https://www.shop.example/p/1", "reason": "waterproof, £110"}, "c"),
        ])
        browser = _FakeBrowser()
        res = sa.run_task(sa.Task("boots", "boots"), "https://www.shop.example/lister.html?q={}",
                          "claude-haiku-5-5", "claude-sonnet-5-5", browser, Path(tempfile.mkdtemp()), client=client)
        self.assertEqual(res.outcome, "found")
        self.assertEqual([s.action for s in res.steps], ["search", "click", "finish"])
        self.assertIn("q=womens+waterproof+walking+boots", browser.visited[-1])
        self.assertEqual(res.driver_usage.calls, 3)
        self.assertEqual(res.verdict["severity"], "PASS")
        self.assertGreater(res.cost, 0)
        # Append-only history: each request carries the previous assistant turn unchanged.
        last = client.requests[-1]["messages"]
        self.assertEqual([m["role"] for m in last], ["user", "assistant", "user", "assistant", "user"])
        self.assertEqual(client.requests[0]["tool_choice"], {"type": "auto", "disable_parallel_tool_use": True})

    def test_step_cap(self):
        client = _FakeClient([_tool("scroll", {"direction": "down"}, f"s{i}") for i in range(3)])
        res = sa.run_task(sa.Task("t", "t"), "https://www.shop.example/s?q={}", "claude-haiku-5-5",
                          "claude-sonnet-5-5", _FakeBrowser(), Path(tempfile.mkdtemp()), client=client, max_steps=3)
        self.assertEqual(res.outcome, "max_steps")
        self.assertEqual(len(res.steps), 3)


if __name__ == "__main__":
    unittest.main()
