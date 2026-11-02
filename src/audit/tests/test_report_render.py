"""Render every historical fixture through the report pipeline (LLM narratives stubbed) and
check what a client would read: branding, no internals, escaping, size, md/html agreement."""

from __future__ import annotations

import copy
import re
import unittest

from src.html_renderer import HTML_SIZE_BUDGET, find_cover_screenshot, html_size_bytes, render_html_report
from src.publish_gate import _FORBIDDEN_CLIENT_PATTERNS, _visible_html_text
from src.report_generator import (
    CAPABILITY_NAMES,
    CATEGORY_TO_CAPABILITY,
    failing_judgments,
    generate_report,
)
from src.report_stats import by_original, category, compute_stats, formatted_stats, root_causes
from tests.helpers import REPORTS_DIR, all_judgments, historical_reports

# Spelled out per the task, on top of the publish gate's own patterns.
_FORBIDDEN = [
    re.compile(p, re.I) for p in (
        r"relevance score", r"\brerank", r"\bvoyage\b", r"\bclaude\b", r"\bLLM\b", r"(?<![\d.,])0\.\d{3}(?!\d)",
        r"Roadmap section was not generated", r"user override", r"\[override", r"per calibration",
        r"MANUAL VERIFICATION REQUIRED", r"severity escalated",
    )
]


def stub_content(judgments):
    """Grounded deep dives + roadmap in stored format, built only from the data."""
    sections: dict[str, dict] = {}
    for j in failing_judgments(judgments):
        cap = CATEGORY_TO_CAPABILITY[category(j)]
        s = sections.setdefault(cap, {"capability": cap, "capability_name": CAPABILITY_NAMES[cap],
                                      "intro": "What this capability means for shoppers.", "examples": []})
        if len(s["examples"]) < 5:
            top = by_original(j)
            text = (f'Searching "{j.test_query.query}" showed "{top[0].title}" at #1.' if top
                    else f'Searching "{j.test_query.query}" returned nothing.')
            s["examples"].append({"query": j.test_query.query, "narrative": text})
    roadmap = [
        {"title": f"Fix: {rc['mechanism']}", "description": "Concrete change for shoppers.",
         "impact": "Critical" if rc["critical"] else "High", "effort": "Quick Win", "owner": "dev",
         "queries": rc["queries"]}
        for rc in root_causes(judgments)[:6]
    ]
    return list(sections.values()), roadmap


def build(report, screenshot=True, **kw):
    js = all_judgments(report)
    dd, rm = stub_content(js)
    new = generate_report(report.site_context, js, deep_dives=dd, roadmap=rm, **kw)
    return new


def forbidden_hits(text: str) -> list[str]:
    hits = [p.pattern for p in _FORBIDDEN if p.search(text)]
    hits += [name for name, p in _FORBIDDEN_CLIENT_PATTERNS if p.search(text)]
    return hits


class HistoricalRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = historical_reports()
        cls.rendered = {}
        for name, rep in cls.fixtures.items():
            new = build(rep)
            shot = find_cover_screenshot(REPORTS_DIR / name)
            cls.rendered[name] = (new, render_html_report(new, screenshot_path=shot), shot)

    def test_fixtures_present(self):
        self.assertGreaterEqual(len(self.fixtures), 5)

    def test_branding_and_cta(self):
        for name, (_, html, _) in self.rendered.items():
            with self.subTest(name):
                self.assertIn('class="cover-logo"', html)
                self.assertIn("<svg", html)
                self.assertIn("https://findsherpas.com/book-a-call", html)

    def test_no_internal_strings_in_client_text(self):
        for name, (report, html, _) in self.rendered.items():
            with self.subTest(name):
                self.assertEqual(forbidden_hits(_visible_html_text(html)), [])
                self.assertEqual(forbidden_hits(report.deep_dive_narrative), [])

    def test_size_budget_with_screenshot(self):
        with_shot = [(n, h) for n, (_, h, s) in self.rendered.items() if s]
        self.assertTrue(with_shot, "expected at least one fixture with a cover screenshot")
        for name, html in with_shot:
            with self.subTest(name):
                self.assertIn("cover-screenshot", html)
                self.assertLess(html_size_bytes(html), HTML_SIZE_BUDGET)

    def test_md_and_html_numbers_agree(self):
        for name, (report, html, _) in self.rendered.items():
            stats = compute_stats(all_judgments(report), report.site_context.nav_categories)
            f = formatted_stats(stats)
            text = _visible_html_text(html)
            for key in ("pct_no_relevant_first", "pct_zero_result", "zero_of_total", "found_wrong_of_total",
                        "avg_best_position", "pct_top3_irrelevant", "pct_top1_irrelevant", "pct_found_but_wrong"):
                with self.subTest(name, key=key):
                    self.assertIn(f[key], report.deep_dive_narrative)
                    self.assertIn(f[key], text)

    def test_average_position_one_decimal_everywhere(self):
        for name, (report, html, _) in self.rendered.items():
            with self.subTest(name):
                self.assertIsNone(re.search(r"position #\d(?!\.\d)\b", report.deep_dive_narrative))
                self.assertNotIn("past the first 3 results", report.deep_dive_narrative)

    def test_reproduction_links(self):
        _, html, _ = self.rendered["huckberry_com"]
        self.assertIn('href="https://huckberry.com/search?keywords=', html)
        self.assertIn('rel="noopener nofollow"', html)
        self.assertIn('target="_blank" rel="noopener nofollow"', html)

    def test_lang_dir_and_print(self):
        _, html, _ = self.rendered["bergzeit_de"]
        self.assertIn('lang="de" dir="auto"', html)
        self.assertIn("details::details-content", html)
        self.assertIn("beforeprint", html)
        self.assertIn("60 searches tested", html)

    def test_no_score_bars_or_revenue_wording(self):
        for name, (_, html, _) in self.rendered.items():
            with self.subTest(name):
                self.assertFalse('class="rel-fill' in html, "score bars rendered")
                self.assertFalse("revenue risk" in html.lower(), "revenue-risk wording rendered")
                self.assertIn("of tested searches fail the shopper", html)


class EscapingTests(unittest.TestCase):
    def test_script_in_title_and_query_is_escaped(self):
        rep = copy.deepcopy(historical_reports()["huckberry_com"])
        js = all_judgments(rep)
        target = next(j for j in failing_judgments(js) if j.results)
        by_original(target)[0].title = "<script>alert(1)</script> Jacket"
        target.test_query.query = 'jacket <img src=x onerror="alert(2)">'
        new = build(rep)
        html = render_html_report(new)
        self.assertFalse("<script>alert(1)" in html, "unescaped title")
        self.assertFalse('<img src=x onerror="alert(2)">' in html, "unescaped query")
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)


class ExclusionTests(unittest.TestCase):
    def test_excluded_judgments_absent_from_rates(self):
        rep = copy.deepcopy(historical_reports()["huckberry_com"])
        js = all_judgments(rep)
        before = compute_stats(js)
        dropped = [j for j in js if not j.results and j.severity.startswith("Critical")][:3]
        self.assertEqual(len(dropped), 3)
        for j in dropped:
            j.excluded_reason = "catalog_gap"
        after = compute_stats(js)
        self.assertEqual(after["total_queries"], before["total_queries"] - 3)
        self.assertEqual(after["critical_count"], before["critical_count"] - 3)
        self.assertEqual(after["zero_result_count"], before["zero_result_count"] - 3)
        self.assertEqual(after["excluded_count"], 3)

        new = build(rep)
        md, html = new.deep_dive_narrative, render_html_report(new)
        appendix_md = md.split("## Appendix: Complete Test Results")[1].split("## Not Scored")[0]
        not_scored_md = md.split("## Not Scored")[1]
        appendix_html = html.split('class="appendix-table"')[1].split("</table>")[0]
        for j in dropped:
            q = j.test_query.query
            self.assertNotIn(q, appendix_md)
            self.assertIn(q, not_scored_md)
            self.assertNotIn(q, appendix_html)
        self.assertIn("Not scored", html)
        self.assertIn(formatted_stats(after)["critical_of_total"], html)
        self.assertIn(f"{after['total_tested']} searches tested ({after['total_queries']} scored)", html)


class RoadmapRenderTests(unittest.TestCase):
    def test_reach_and_owner_rendered(self):
        new = build(historical_reports()["avoca_com"])
        html = render_html_report(new)
        self.assertRegex(html, r"Fixes \d+ tested search(es)?( \(\d+ critical\))?")
        self.assertRegex(new.deep_dive_narrative, r"Fixes \d+ tested search")
        self.assertIn("Development", html)

    def test_legacy_report_without_structured_roadmap_fails_loudly(self):
        legacy = historical_reports()["avoca_com"]  # as persisted: markdown roadmap only
        with self.assertRaises(ValueError):
            render_html_report(legacy)

    def test_peer_benchmark_hook(self):
        rep = historical_reports()["avoca_com"]
        peer = {"label": "Outdoor retailers 2026", "sample_size": 12, "values": {"pct_no_relevant_first": 21.0}}
        new = build(rep, peer_benchmark=peer)
        html = render_html_report(new)
        self.assertIn("Outdoor retailers 2026 (n=12)", html)
        self.assertIn("21%", html)
        self.assertNotIn("Baymard", html)
        self.assertNotIn("Baymard", new.deep_dive_narrative)


if __name__ == "__main__":
    unittest.main()
