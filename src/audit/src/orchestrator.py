from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pydantic import TypeAdapter

from src import llm_compat
from src.category_selector import select_categories
from src.discovery import discover_from_search_url, discover_site, parse_search_url
from src.fetcher import fetch_all_outcomes
from src.github_publisher import publish_report_full
from src.html_renderer import save_html_report
from src.judge import judge_all_queries
from src.models import AuditReport, FetchOutcome, QueryCategory, QueryJudgment, ScoredResult, SiteContext, TestQuery
from src.publish_gate import MAX_UNVERIFIED_FETCH_SHARE, check_report
from src.query_generator import generate_queries
from src.report_generator import generate_report
from src.scorer import score_results

logger = logging.getLogger(__name__)


class FetchError(RuntimeError):
    """Too many queries could not be observed reliably to produce a trustworthy audit.

    The same principle as ``scorer.ScoringError``: an empty result list for a page the fetcher
    never actually saw (bot wall, timeout) is indistinguishable downstream from a genuine
    zero-result search, and would be published as a CRITICAL finding. Stop instead.
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify_domain(url: str) -> str:
    """Turn a URL into a filesystem-safe slug."""
    host = urlparse(url).netloc or url
    host = host.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", host).strip("_")
    return slug


def _find_report_screenshot(out_path: Path, run_dir: Path | None = None) -> Path | None:
    """Return the preferred screenshot for this report directory, if present.

    An operator-supplied screenshot in the report folder wins; otherwise fall back to the first
    results-page screenshot the fetcher saved as evidence for this run.
    """
    preferred_names = (
        "screenshot.png",
        "screenshot.jpg",
        "screenshot.jpeg",
    )
    for name in preferred_names:
        path = out_path / name
        if path.exists():
            return path

    for pattern in ("*screenshot*.png", "*screenshot*.jpg", "*screenshot*.jpeg", "*_cover.png"):
        matches = sorted(out_path.glob(pattern))
        if matches:
            return matches[0]

    if run_dir is not None:
        evidence = sorted((run_dir / "evidence").glob("*.png"))
        if evidence:
            return evidence[0]
    return None


def _print_banner(target_url: str) -> None:
    url_line = f"     Target: {target_url}"
    width = max(46, len(url_line) + 6)
    border = "═" * (width - 2)
    print(f"╔{border}╗")
    print(f"║{'     SEARCH AUDIT TOOL v3.0':<{width - 2}}║")
    print(f"║{url_line:<{width - 2}}║")
    print(f"╚{border}╝")
    print()


def _phase_header(num: int, name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Phase {num}/7: {name}")
    print(f"{'='*60}\n")


def _fold(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())


# ---------------------------------------------------------------------------
# Run directory checkpoints
#
# Each phase writes its output to <report dir>/run_<timestamp>/NN_<phase>.json the moment it
# finishes (atomic tmp + os.replace). `--resume <run dir>` skips every phase whose checkpoint
# exists, so a crash in judging or rendering never throws away paid fetch/score/judge work.
# ---------------------------------------------------------------------------

_CHECKPOINTS = {
    "site_context": "01_site_context.json",
    "categories": "02_categories.json",
    "queries": "03_queries.json",
    "fetch": "04_fetch.json",
    "controls": "04b_controls.json",
    "scored": "05_scored.json",
    "judgments": "06_judgments.json",
}

_ADAPTERS = {
    "site_context": TypeAdapter(SiteContext),
    "categories": TypeAdapter(list[QueryCategory]),
    "queries": TypeAdapter(list[TestQuery]),
    "fetch": TypeAdapter(dict[str, FetchOutcome]),
    "controls": TypeAdapter(dict[str, FetchOutcome]),
    "scored": TypeAdapter(dict[str, list[ScoredResult]]),
    "judgments": TypeAdapter(list[QueryJudgment]),
}


def _save_checkpoint(run_dir: Path, name: str, value) -> None:
    path = run_dir / _CHECKPOINTS[name]
    tmp = path.with_suffix(".json.tmp")
    tmp.write_bytes(_ADAPTERS[name].dump_json(value, indent=2))
    os.replace(tmp, path)


def _load_checkpoint(run_dir: Path, name: str):
    """Return the phase output, or None when the phase has not completed in this run.

    A checkpoint that exists but does not parse raises: silently treating a corrupt file as
    "not done" would re-run (and re-pay for) the phase and overwrite whatever was salvageable.
    """
    path = run_dir / _CHECKPOINTS[name]
    if not path.exists():
        return None
    return _ADAPTERS[name].validate_json(path.read_bytes())


# ---------------------------------------------------------------------------
# Fetch: statuses and control queries
# ---------------------------------------------------------------------------


def _print_fetch_summary(outcomes: dict[str, FetchOutcome]) -> None:
    counts: dict[str, int] = {}
    for o in outcomes.values():
        counts[o.status] = counts.get(o.status, 0) + 1
    total_results = sum(len(o.results) for o in outcomes.values())
    print(f"\n  Total results fetched:   {total_results}")
    for status, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {status:<22} {n}")


def _untrusted(outcomes: dict[str, FetchOutcome]) -> list[str]:
    return [q for q, o in outcomes.items() if not o.trusted]


def _control_terms(queries: list[TestQuery], outcomes: dict[str, FetchOutcome]) -> dict[str, str]:
    """Original query -> target term, for every trusted zero-result query worth a control search.

    A zero-result page is only a *search* failure if the store actually stocks what the shopper
    meant. Searching the plain target term is the cheapest proof: if "Wanderschuhe" returns
    products, then "Wandersch uhe" returning nothing is the engine's fault; if it returns nothing
    too, the test measured the catalog and must not be scored.
    """
    out: dict[str, str] = {}
    for tq in queries:
        o = outcomes.get(tq.query)
        if o is None or not o.trusted or o.results:
            continue
        if tq.category == QueryCategory.GIBBERISH.value or not tq.target_term:
            continue
        if _fold(tq.target_term) == _fold(tq.query):
            continue
        out[tq.query] = tq.target_term
    return out


def _fetch_controls(
    queries: list[TestQuery],
    outcomes: dict[str, FetchOutcome],
    template: str,
    evidence_dir: Path | None,
) -> dict[str, FetchOutcome]:
    terms = _control_terms(queries, outcomes)
    if not terms:
        return {}
    unique_terms = list(dict.fromkeys(terms.values()))
    print(f"  Running {len(unique_terms)} control searches for {len(terms)} zero-result queries…")
    by_term = fetch_all_outcomes(unique_terms, template, evidence_dir=str(evidence_dir) if evidence_dir else None)
    return {q: by_term[t] for q, t in terms.items() if t in by_term}


# ---------------------------------------------------------------------------
# Reproducibility record
# ---------------------------------------------------------------------------


def _phase_models() -> dict[str, str]:
    """Resolved model id per phase, read from each module (all are env-overridable)."""
    import importlib

    found: dict[str, str] = {}
    for phase, module_name in (
        ("discovery", "src.discovery"),
        ("categories", "src.category_selector"),
        ("queries", "src.query_generator"),
        ("fetcher", "src.fetcher"),
        ("judge", "src.judge"),
        ("report", "src.report_generator"),
        ("scorer", "src.scorer"),
        ("kb_embeddings", "src.judge_kb"),
    ):
        module = importlib.import_module(module_name)
        for attr in ("_MODEL", "_HAIKU_MODEL", "_EMBED_MODEL"):
            value = getattr(module, attr, None)
            if isinstance(value, str):
                found[phase] = value
                break
    return found


def _git_revision() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent,
                             capture_output=True, text=True, timeout=5)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "."], cwd=Path(__file__).parent,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return (out.stdout.strip() + ("-dirty" if dirty else "")) or None
    except Exception:
        return None


def _run_metadata(run_dir: Path, outcomes: dict[str, FetchOutcome], controls: dict[str, FetchOutcome]) -> dict:
    try:
        from src.judge import JUDGE_RULES_VERSION
    except ImportError:
        JUDGE_RULES_VERSION = None
    statuses: dict[str, int] = {}
    for o in outcomes.values():
        statuses[o.status] = statuses.get(o.status, 0) + 1
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "source_revision": _git_revision(),
        "models": _phase_models(),
        "judge_rules_version": JUDGE_RULES_VERSION,
        "fetch_status_counts": statuses,
        "control_searches": len(controls),
        "llm_usage": llm_compat.usage_summary(),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


# Reports live next to the pipeline (src/audit/reports/), not at the repo root.
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "reports"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def run_audit(
    target_url: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    search_url_template: str | None = None,
    crm_company_id: str | None = None,
    publish: bool = False,
    resume_dir: str | Path | None = None,
    allow_unverified: bool = False,
    run_controls: bool = True,
    claim_legacy_slug: bool = False,
) -> AuditReport:
    """Run the full search audit pipeline end to end.

    Nothing leaves the machine unless ``publish=True`` *and* the publish gate passes. The CRM
    writeback only runs after a successful publish.
    """

    start_time = time.time()
    _print_banner(target_url)
    llm_compat.reset_usage()

    domain_slug = _slugify_domain(target_url)
    out_path = Path(output_dir).expanduser().resolve() / domain_slug
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(resume_dir).expanduser().resolve() if resume_dir else out_path / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = run_dir / "evidence"
    print(f"  Run directory: {run_dir}{'  (resuming)' if resume_dir else ''}")

    # ── Phase 1/7: Site Discovery ───────────────────────────────────────
    # Auto-detect whether the caller provided a search results page URL
    # (e.g. https://www.groupon.com/search?query=spa) or a homepage URL.
    # Search results URLs are preferred: they yield a reliable template
    # directly from the URL instead of guessing from a homepage form.
    _phase_header(1, "Site Discovery")
    site_context = _load_checkpoint(run_dir, "site_context")
    if site_context is None:
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

        if not site_context.search_url_template:
            raise RuntimeError(
                "Could not detect search URL template. Pass a search results page URL "
                "directly (e.g. https://example.com/search?q=shoes) or provide the "
                "template via run_audit(url, search_url_template='https://example.com/search?q={}')"
            )
        _save_checkpoint(run_dir, "site_context", site_context)

    print(f"  Site name:          {site_context.site_name}")
    print(f"  Site type:          {site_context.site_type}")
    print(f"  Language / locale:  {site_context.primary_language} {site_context.locale or ''}".rstrip())
    print(f"  Nav categories:     {len(site_context.nav_categories)} found")
    print(f"  Brands:             {len(site_context.brands)} found")
    print(f"  Featured items:     {len(site_context.featured_items)} found")
    print(f"  Catalog sample:     {len(site_context.catalog_sample)} titles")
    print(f"  Search URL:         {site_context.search_url_template or '(not detected)'}")
    for key, value in sorted(site_context.provenance.items()):
        if str(value).startswith("fallback"):
            print(f"  [WARN] {key}: {value}")

    # ── Phase 2/7: Category Selection ──────────────────────────────────
    _phase_header(2, "Category Selection")
    selected_categories = _load_checkpoint(run_dir, "categories")
    if selected_categories is None:
        selected_categories = select_categories(site_context)
        _save_checkpoint(run_dir, "categories", selected_categories)
        # Category selection may correct site_type and records provenance on the context.
        _save_checkpoint(run_dir, "site_context", site_context)
    print(f"  Selected {len(selected_categories)} categories:")
    for cat in selected_categories:
        print(f"    - {getattr(cat, 'value', cat)}")

    # ── Phase 3/7: Query Generation ────────────────────────────────────
    _phase_header(3, "Query Generation")
    queries = _load_checkpoint(run_dir, "queries")
    if queries is None:
        queries = generate_queries(site_context, selected_categories)
        _save_checkpoint(run_dir, "queries", queries)
        _save_checkpoint(run_dir, "site_context", site_context)  # query-generation provenance
    print(f"  {len(queries)} test queries:\n")
    current_cat = None
    for tq in queries:
        if tq.category != current_cat:
            current_cat = tq.category
            print(f"  [{current_cat}]")
        print(f"    \"{tq.query}\"")

    # ── Phase 4/7: Fetching Search Results ─────────────────────────────
    _phase_header(4, "Fetching Search Results")
    template = site_context.search_url_template
    outcomes = _load_checkpoint(run_dir, "fetch")
    if outcomes is None:
        outcomes = fetch_all_outcomes([tq.query for tq in queries], template, evidence_dir=str(evidence_dir))
        _save_checkpoint(run_dir, "fetch", outcomes)
    elif _untrusted(outcomes) and not (run_dir / _CHECKPOINTS["scored"]).exists():
        # Resuming before scoring: give queries that were blocked / timed out another chance.
        # (Once scoring has run, downstream checkpoints were built from these outcomes; a
        # re-fetch would silently disagree with them, so it is skipped.)
        retry = _untrusted(outcomes)
        print(f"  Re-fetching {len(retry)} queries that were not observed reliably last time…")
        outcomes.update(fetch_all_outcomes(retry, template, evidence_dir=str(evidence_dir)))
        _save_checkpoint(run_dir, "fetch", outcomes)
        (run_dir / _CHECKPOINTS["controls"]).unlink(missing_ok=True)  # controls depend on outcomes
    _print_fetch_summary(outcomes)

    untrusted = _untrusted(outcomes)
    if untrusted and len(untrusted) / len(queries) > MAX_UNVERIFIED_FETCH_SHARE and not allow_unverified:
        raise FetchError(
            f"{len(untrusted)}/{len(queries)} queries could not be observed reliably "
            f"(e.g. {untrusted[:3]}). Fix the fetch (see docs/FETCHER_PLAYBOOK.md) and resume with "
            f"--resume {run_dir}, or pass --allow-unverified to exclude them from scoring."
        )

    controls = _load_checkpoint(run_dir, "controls")
    if controls is None:
        controls = _fetch_controls(queries, outcomes, template, evidence_dir) if run_controls else {}
        _save_checkpoint(run_dir, "controls", controls)

    # ── Phase 5/7: Scoring Relevance ───────────────────────────────────
    _phase_header(5, "Scoring Relevance")
    scored_results = _load_checkpoint(run_dir, "scored")
    if scored_results is None:
        # Untrusted pages are never scored: the judge excludes them from the audit.
        scraped = {q: (o.results if o.trusted else []) for q, o in outcomes.items()}
        scored_results = score_results(queries, scraped)
        _save_checkpoint(run_dir, "scored", scored_results)
    scored_count = sum(1 for v in scored_results.values() if v)
    print(f"  Queries with scored results: {scored_count}/{len(queries)}")

    # ── Phase 6/7: Analyzing Results ───────────────────────────────────
    _phase_header(6, "Analyzing Results")
    judgments = _load_checkpoint(run_dir, "judgments")
    if judgments is None:
        kb_provenance = {
            "domain": domain_slug,
            "url": target_url,
            "judged_at": datetime.now().isoformat(),
        }
        judgments = judge_all_queries(
            queries,
            scored_results,
            language=site_context.primary_language,
            provenance=kb_provenance,
            site_categories=site_context.nav_categories,
            site_brands=site_context.brands,
            fetch_outcomes=outcomes,
            control_outcomes=controls,
        )
        _save_checkpoint(run_dir, "judgments", judgments)
    excluded = [j for j in judgments if j.excluded_reason]
    fallbacks = [j for j in judgments if j.judge_status == "fallback"]
    print(f"  Judged {len(judgments)} queries ({len(excluded)} excluded from scoring, {len(fallbacks)} fallbacks)")

    # ── Phase 7/7: Generating Report ───────────────────────────────────
    _phase_header(7, "Generating Report")
    report = generate_report(site_context, judgments)
    # Merge: generate_report already stored the accepted narratives under run_metadata.
    report.run_metadata = {**report.run_metadata, **_run_metadata(run_dir, outcomes, controls)}
    print("  Report assembled")

    # ── Save outputs ───────────────────────────────────────────────────
    slug = f"{domain_slug}_{timestamp}"
    md_file = out_path / f"{slug}_report.md"
    json_file = out_path / f"{slug}_data.json"
    html_file = out_path / f"{slug}_report.html"
    access_file = out_path / f"{slug}_access.json"

    md_file.write_text(report.deep_dive_narrative, encoding="utf-8")
    json_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"\n  Saved: {md_file}")
    print(f"  Saved: {json_file}")

    # ── Screenshot ─────────────────────────────────────────────────────
    # The fetcher's first results-page screenshot is used automatically. An interactive operator
    # can drop a better one into the report folder first. Never block a non-interactive run.
    if sys.stdin.isatty():
        print(f"\n  ── Screenshot ──────────────────────────────────────────────")
        print(f"  Optional: place a screenshot of the site's search results page into:")
        print(f"    {out_path}")
        print(f"  Name it:  screenshot.png  (or .jpg / .jpeg)")
        try:
            input("  [press ENTER to continue] ")
        except EOFError:
            pass
        print()

    # ── HTML report (PDF-ready, styled via master_report.html template) ────
    screenshot_path = _find_report_screenshot(out_path, run_dir)
    save_html_report(report, html_file, screenshot_path=screenshot_path)
    print(f"  Saved: {html_file}")
    if screenshot_path:
        print(f"  Screenshot: {screenshot_path}")

    # ── Publish gate ───────────────────────────────────────────────────
    html_content = html_file.read_text(encoding="utf-8")
    gate = check_report(report, html_content)
    print()
    print(gate.format())

    # ── Publish HTML to findsherpas.com/report/{company}/ ─────────────────
    report_url: str | None = None
    if not publish:
        print("\n  Not published (pass --publish to publish once the report is reviewed).")
    elif not gate.ok:
        print("\n  [BLOCKED] Not published: fix the gate errors above, then re-run with --resume.")
    else:
        result = publish_report_full(
            html_content,
            domain_slug,
            data_json=json_file.read_text(encoding="utf-8"),
            report_md=md_file.read_text(encoding="utf-8"),
            claim_legacy=claim_legacy_slug,
        )
        report_url = result.url
        access_file.write_text(
            json.dumps(
                {
                    "company_slug": result.company,
                    "report_slug": result.slug,
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

    # ── Final summary ──────────────────────────────────────────────────
    elapsed = time.time() - start_time
    usage = llm_compat.usage_summary()
    print(f"\n{'='*60}")
    print(f"  COMPLETE")
    print(f"{'='*60}")
    print(f"  Scored queries: {len(judgments) - len(excluded)} of {len(judgments)}")
    if usage:
        tokens_in = sum(u["input_tokens"] + u["cache_read_input_tokens"] + u["cache_creation_input_tokens"] for u in usage)
        tokens_out = sum(u["output_tokens"] for u in usage)
        print(f"  LLM tokens: {tokens_in:,} in / {tokens_out:,} out across {sum(u['calls'] for u in usage)} calls")
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
            "writes audit variables plus report_url to CRM (only after a publish)."
        ),
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish to findsherpas.com once the publish gate passes. Off by default.",
    )
    parser.add_argument(
        "--resume",
        dest="resume_dir",
        default=None,
        help="Resume a previous run directory (reports/<site>/run_<timestamp>); completed phases are skipped.",
    )
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Continue when more than 20%% of pages could not be observed; those queries are excluded from scoring.",
    )
    parser.add_argument(
        "--no-controls",
        dest="run_controls",
        action="store_false",
        help="Skip control searches for zero-result queries (faster; zero-result findings stay unverified).",
    )

    parser.add_argument(
        "--claim-legacy-slug",
        action="store_true",
        help="Re-publish over a registry entry created before domains were recorded (same market only).",
    )

    args = parser.parse_args()

    run_audit(
        target_url=args.target_url,
        output_dir=args.output_dir,
        search_url_template=args.search_url,
        crm_company_id=args.crm_company_id,
        publish=args.publish,
        resume_dir=args.resume_dir,
        allow_unverified=args.allow_unverified,
        run_controls=args.run_controls,
        claim_legacy_slug=args.claim_legacy_slug,
    )
