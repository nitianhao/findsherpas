from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from src.category_selector import select_categories
from src.discovery import discover_from_search_url, discover_site, parse_search_url
from src.fetcher import fetch_all_results
from src.judge import judge_all_queries
from src.models import AuditReport
from src.query_generator import generate_queries
from src.report_generator import (
    _CAPABILITY_NAMES,
    _SEVERITY_SHORT,
    build_capability_scores,
    generate_report,
)
from src.github_publisher import publish_report
from src.html_renderer import save_html_report
from src.sales_materials_generator import generate_sales_materials
from src.scorer import score_results

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify_domain(url: str) -> str:
    """Turn a URL into a filesystem-safe slug."""
    host = urlparse(url).netloc or url
    host = host.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", host).strip("_")
    return slug


def _find_report_screenshot(out_path: Path) -> Path | None:
    """Return the preferred screenshot for this report directory, if present."""
    preferred_names = (
        "screenshot.png",
        "screenshot.jpg",
        "screenshot.jpeg",
    )
    for name in preferred_names:
        path = out_path / name
        if path.exists():
            return path

    for pattern in ("*screenshot*.png", "*screenshot*.jpg", "*screenshot*.jpeg"):
        matches = sorted(out_path.glob(pattern))
        if matches:
            return matches[0]

    return None


def _print_banner(target_url: str) -> None:
    url_line = f"     Target: {target_url}"
    width = max(46, len(url_line) + 6)
    border = "\u2550" * (width - 2)
    print(f"\u2554{border}\u2557")
    print(f"\u2551{'     SEARCH AUDIT TOOL v2.0':<{width - 2}}\u2551")
    print(f"\u2551{url_line:<{width - 2}}\u2551")
    print(f"\u255a{border}\u255d")
    print()


def _phase_header(num: int, name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Phase {num}/7: {name}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "reports"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def run_audit(
    target_url: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    search_url_template: str | None = None,
    crm_company_id: str | None = None,
) -> AuditReport:
    """Run the full search audit pipeline end to end."""

    start_time = time.time()
    _print_banner(target_url)

    # ── Phase 1/7: Site Discovery ───────────────────────────────────────
    # Auto-detect whether the caller provided a search results page URL
    # (e.g. https://www.groupon.com/search?query=spa) or a homepage URL.
    # Search results URLs are preferred: they yield a reliable template
    # directly from the URL instead of guessing from a homepage form.
    _phase_header(1, "Site Discovery")
    try:
        _is_search_url = False
        try:
            parse_search_url(target_url)
            _is_search_url = True
        except ValueError:
            pass

        if _is_search_url:
            print(f"  Detected search results URL — using direct URL parsing.")
            site_context = discover_from_search_url(target_url)
        else:
            print(f"  Detected homepage URL — scraping for search form.")
            site_context = discover_site(target_url)

            # Override search URL template if provided explicitly.
            if search_url_template:
                site_context.search_url_template = search_url_template
                print(f"  Using provided search URL template: {search_url_template}")

        print(f"  Site name:          {site_context.site_name}")
        print(f"  Site type:          {site_context.site_type}")
        print(f"  Nav categories:     {len(site_context.nav_categories)} found")
        print(f"  Brands:             {len(site_context.brands)} found")
        print(f"  Featured items:     {len(site_context.featured_items)} found")
        print(f"  Search URL:         {site_context.search_url_template or '(not detected)'}")

        if not site_context.search_url_template:
            raise RuntimeError(
                "Could not detect search URL template. Pass a search results page URL "
                "directly (e.g. https://example.com/search?q=shoes) or provide the "
                "template via run_audit(url, search_url_template='https://example.com/search?q={}')"
            )
    except Exception as e:
        print(f"\n  [ERROR] Phase 1 failed: {e}")
        raise

    # ── Phase 2/7: Category Selection ──────────────────────────────────
    _phase_header(2, "Category Selection")
    try:
        selected_categories = select_categories(site_context)
        print(f"  Selected {len(selected_categories)} categories:")
        for cat in selected_categories:
            print(f"    - {cat.value}")
    except Exception as e:
        print(f"\n  [ERROR] Phase 2 failed: {e}")
        raise

    # ── Phase 3/7: Query Generation ────────────────────────────────────
    _phase_header(3, "Query Generation")
    try:
        queries = generate_queries(site_context, selected_categories)
        print(f"  Generated {len(queries)} test queries:\n")

        current_cat = None
        for tq in queries:
            if tq.category != current_cat:
                current_cat = tq.category
                print(f"  [{current_cat}]")
            print(f"    \"{tq.query}\"")
    except Exception as e:
        print(f"\n  [ERROR] Phase 3 failed: {e}")
        raise

    # ── Phase 4/7: Fetching Search Results ─────────────────────────────
    _phase_header(4, "Fetching Search Results")
    try:
        scraped_results = fetch_all_results(
            site_context.search_url_template, queries
        )
        total_results = sum(len(v) for v in scraped_results.values())
        empty_count = sum(1 for v in scraped_results.values() if not v)
        print(f"\n  Total results fetched:   {total_results}")
        print(f"  Queries with 0 results:  {empty_count}")
    except Exception as e:
        print(f"\n  [ERROR] Phase 4 failed: {e}")
        raise

    # ── Phase 5/7: Scoring Relevance ───────────────────────────────────
    _phase_header(5, "Scoring Relevance")
    try:
        scored_results = score_results(queries, scraped_results)
        scored_count = sum(1 for v in scored_results.values() if v)
        print(f"  All results scored via Voyage AI rerank-2.5")
        print(f"  Queries with scored results: {scored_count}/{len(queries)}")
    except Exception as e:
        print(f"\n  [ERROR] Phase 5 failed: {e}")
        raise

    # ── Phase 6/7: Analyzing Results ───────────────────────────────────
    _phase_header(6, "Analyzing Results")
    try:
        judgments = judge_all_queries(queries, scored_results)
    except Exception as e:
        print(f"\n  [ERROR] Phase 6 failed: {e}")
        raise

    # ── Phase 7/7: Generating Report ───────────────────────────────────
    _phase_header(7, "Generating Report")
    try:
        report = generate_report(site_context, judgments)
        print("  Report assembled")
    except Exception as e:
        print(f"\n  [ERROR] Phase 7 failed: {e}")
        raise

    # ── Save outputs ───────────────────────────────────────────────────
    domain_slug = _slugify_domain(target_url)
    out_path = Path(output_dir).expanduser().resolve() / domain_slug
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"{domain_slug}_{timestamp}"

    md_file = out_path / f"{slug}_report.md"
    json_file = out_path / f"{slug}_data.json"
    html_file = out_path / f"{slug}_report.html"
    access_file = out_path / f"{slug}_access.json"

    md_file.write_text(report.deep_dive_narrative, encoding="utf-8")
    json_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(f"\n  Saved: {md_file}")
    print(f"  Saved: {json_file}")

    # ── Screenshot prompt ──────────────────────────────────────────────────
    # Ask the operator to drop a screenshot into the report folder before
    # the HTML is rendered.  Named screenshot.png / .jpg / .jpeg is picked up
    # automatically by _find_report_screenshot().
    print(f"\n  ── Screenshot ──────────────────────────────────────────────")
    print(f"  Place a screenshot of the site's search results page into:")
    print(f"    {out_path}")
    print(f"  Name it:  screenshot.png  (or .jpg / .jpeg)")
    print(f"  Then press ENTER to continue and generate the HTML report.")
    try:
        input("  [waiting for screenshot — press ENTER when ready] ")
    except EOFError:
        pass  # non-interactive run — skip the prompt
    print()

    # ── HTML report (PDF-ready, styled via master_report.html template) ────
    try:
        screenshot_path = _find_report_screenshot(out_path)
        save_html_report(report, html_file, screenshot_path=screenshot_path)
        print(f"  Saved: {html_file}")
        if screenshot_path:
            print(f"  Screenshot: {screenshot_path}")
    except Exception as e:
        print(f"  [WARN] HTML report generation failed: {e}")

    # ── Publish HTML to findsherpas.com/report/{company}/ ─────────────────
    report_url: str | None = None
    try:
        html_content = html_file.read_text(encoding="utf-8")
        report_url = publish_report(html_content, domain_slug)
        access_file.write_text(
            json.dumps(
                {
                    "company_slug": re.sub(
                        r"_(?:com|net|org|io|co_\w+|cz|de|uk|fr|es|pl|at|nl|be|ch|se|dk|fi|no|pt|hu|ro|sk|si)$",
                        "",
                        re.sub(r"^www_", "", domain_slug),
                    ),
                    "report_url": report_url,
                    "published_at": datetime.now().isoformat(),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"  Published: {report_url}")
        print(f"  Access:    {access_file}")
    except Exception as e:
        print(f"  [WARN] GitHub publish failed: {e}")

    # ── CRM writeback for email sequence variables ────────────────────────
    if crm_company_id and report_url:
        try:
            cmd = [
                "npx",
                "tsx",
                "--tsconfig",
                "tsconfig.json",
                "src/enrichment/scripts/writeAuditToCRM.ts",
                "--company-id",
                crm_company_id,
                "--report",
                str(json_file),
                "--report-url",
                report_url,
            ]
            subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
            print(f"  CRM updated: {crm_company_id}")
        except Exception as e:
            print(f"  [WARN] CRM writeback failed: {e}")
    elif crm_company_id:
        print("  [WARN] CRM writeback skipped: report was not published.")
    elif report_url:
        print(
            "  CRM writeback: pass --crm-company-id to store report_url "
            "and audit variables on the company."
        )

    # ── Sales materials (exec summary, brief, cold email) ──────────────────
    generate_sales_materials(report, out_path, slug)

    # ── Final summary ──────────────────────────────────────────────────
    elapsed = time.time() - start_time
    cap_scores = report.capability_scores
    pass_count = sum(
        1 for cs in cap_scores
        if cs.severity == "Pass \u2014 Search handles this well."
    )
    total_caps = len(cap_scores)

    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"{'='*60}")
    print(f"  Result: Your search performed well on {pass_count} of {total_caps} capabilities.")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print()

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Run a full search audit on an ecommerce site.",
    )
    parser.add_argument(
        "target_url",
        help=(
            "URL to audit. Preferred: a search results page URL with the query "
            "visible (e.g. https://www.groupon.com/search?query=spa). "
            "Also accepts a homepage URL, but search URL detection may be less reliable."
        ),
    )
    parser.add_argument(
        "--search-url",
        dest="search_url",
        default=None,
        help=(
            "Override: manual search URL template with {} placeholder "
            "(e.g., 'https://www.example.com/search?q={}'). "
            "Only needed when passing a homepage URL and auto-detection fails."
        ),
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory for output files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--crm-company-id",
        dest="crm_company_id",
        default=None,
        help=(
            "Optional InstantDB company id. When provided, the completed audit "
            "writes audit variables plus report_url to CRM."
        ),
    )

    args = parser.parse_args()

    run_audit(
        target_url=args.target_url,
        output_dir=args.output_dir,
        search_url_template=args.search_url,
        crm_company_id=args.crm_company_id,
    )
