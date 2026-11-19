"""Run the research evaluation stages from the Shopify subproject.

This deliberately reuses the main project's Python evaluator and stops at query
judgments. It never imports report generation, publishing, or CRM code.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urlparse


EVALUATION_DIR = Path(__file__).resolve().parent
REPOSITORY_DIR = EVALUATION_DIR.parents[1]
AUDIT_DIR = REPOSITORY_DIR / "src" / "audit"
DEFAULT_RUNS_DIR = EVALUATION_DIR / "runs"
CALIBRATION_DIR = EVALUATION_DIR / "knowledge" / "calibration"

CHECKPOINTS = {
    "start": "01_preflight.json",
    "discover": "02_discovery.json",
    "categories": "03_categories.json",
    "queries": "04_queries.json",
    "probe": "05_probe.json",
    "fetch_raw": "06_fetch_raw.json",
    "fetch": "06_fetch_clean.json",
    "score": "07_scores.json",
    "judge": "08_judgments.json",
}

JUNK_TITLES = {
    "+ zobrazit více", "zobrazit více", "porovnání produktů",
    "podobné fráze", "zapomněli jste heslo?", "povolit vše",
    "smazat vše", "přejít do košíku", "kategorie", "značky",
    "přihlásit se", "registrovat se", "show more",
    "compare products", "sign in", "accept all", "clear all",
}


def _load_engine(run_dir: Path) -> None:
    """Load credentials and select the copied KB before importing audit modules."""
    from dotenv import load_dotenv

    load_dotenv(AUDIT_DIR / ".env", override=False)
    os.environ["AUDIT_KB_DIR"] = str(CALIBRATION_DIR)
    os.environ["AUDIT_KB_HARVEST_DIR"] = str(run_dir / "proposed_calibration")
    sys.path.insert(0, str(AUDIT_DIR))


def _run_dir(runs_dir: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", run_id):
        raise ValueError("Run ID must use lowercase letters, digits, '-' or '_'.")
    path = runs_dir / run_id
    if not path.is_dir():
        raise FileNotFoundError(f"Run not found: {path}")
    return path


def _read(run_dir: Path, checkpoint: str):
    path = run_dir / CHECKPOINTS[checkpoint]
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path.name}; complete the preceding step first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _write(run_dir: Path, checkpoint: str, value) -> Path:
    path = run_dir / CHECKPOINTS[checkpoint]
    # Refuse accidental reruns that could erase expert edits or expensive results.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return path


def _require_unwritten(run_dir: Path, *checkpoints: str) -> None:
    existing = [CHECKPOINTS[key] for key in checkpoints if (run_dir / CHECKPOINTS[key]).exists()]
    if existing:
        raise FileExistsError(f"Checkpoint already exists: {', '.join(existing)}. Review or edit it instead of rerunning this step.")


def _models(data, model):
    return [model.model_validate(item) for item in data]


def _results(data, model):
    return {query: _models(items, model) for query, items in data.items()}


def _dump_results(data):
    return {query: [item.model_dump(mode="json") for item in items] for query, items in data.items()}


def _clean_results(data):
    cleaned = {}
    removed = 0
    for query, items in data.items():
        kept = []
        for item in items:
            title = item.title.strip().casefold()
            url = (item.url or "").strip()
            if not title or title in JUNK_TITLES or not url or url.startswith("#"):
                removed += 1
                continue
            kept.append(item.model_copy(update={"rank": len(kept) + 1}))
        cleaned[query] = kept
    return cleaned, removed


def _start(args, runs_dir: Path) -> None:
    # Parsing is local; no site request or model call occurs in this step.
    _load_engine(runs_dir)
    from src.discovery import parse_search_url

    template, sample_query = parse_search_url(args.url)
    host = urlparse(args.url).hostname or "store"
    slug = re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")
    run_id = args.id or f"{slug}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", run_id):
        raise ValueError("Run ID must use lowercase letters, digits, '-' or '_'.")
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    path = _write(run_dir, "start", {
        "search_results_url": args.url,
        "search_url_template": template,
        "sample_query": sample_query,
        "started_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"Run: {run_id}\nSaved: {path}\nNext: discover")


def _execute(args, runs_dir: Path) -> None:
    run_dir = _run_dir(runs_dir, args.run_id)
    stage = args.stage
    if stage == "status":
        for key, filename in CHECKPOINTS.items():
            print(f"{key:11} {'done' if (run_dir / filename).exists() else 'pending'}  {filename}")
        return

    _require_unwritten(run_dir, *("fetch_raw", "fetch") if stage == "fetch" else (stage,))
    _load_engine(run_dir)
    from src.models import SearchResult, ScoredResult, SiteContext, TestQuery

    if stage == "discover":
        from src.discovery import discover_from_search_url
        url = _read(run_dir, "start")["search_results_url"]
        context = discover_from_search_url(url)
        path = _write(run_dir, stage, context.model_dump(mode="json"))
        print(f"Saved: {path}\nSite: {context.site_name}\nSearch template: {context.search_url_template}")
        print(f"Categories: {context.nav_categories}\nBrands: {context.brands}\nFeatured items: {context.featured_items}")

    elif stage == "categories":
        from src.category_selector import select_categories
        context = SiteContext.model_validate(_read(run_dir, "discover"))
        categories = select_categories(context)
        path = _write(run_dir, stage, [item.value if hasattr(item, "value") else item for item in categories])
        print(f"Saved: {path}\nCategories ({len(categories)}): {categories}")

    elif stage == "queries":
        from src.models import QueryCategory
        from src.query_generator import generate_queries
        context = SiteContext.model_validate(_read(run_dir, "discover"))
        categories = [QueryCategory(item) for item in _read(run_dir, "categories")]
        queries = generate_queries(context, categories)
        path = _write(run_dir, stage, [item.model_dump(mode="json") for item in queries])
        print(f"Saved: {path}\nQueries ({len(queries)}):")
        for item in queries:
            print(f"  [{item.category}] {item.query} — {item.rationale}")

    elif stage == "probe":
        from src.fetcher import fetch_all_results
        context = SiteContext.model_validate(_read(run_dir, "discover"))
        queries = _models(_read(run_dir, "queries"), TestQuery)
        if not queries:
            raise ValueError("No queries to probe.")
        query = queries[0].query
        results = fetch_all_results(context.search_url_template, queries[:1])
        path = _write(run_dir, stage, _dump_results(results))
        print(f"Saved: {path}\nQuery: {query}")
        print(f"Live URL: {context.search_url_template.replace('{}', quote_plus(query))}")
        for item in results.get(query, []):
            print(f"  {item.rank}. {item.title} | {item.price or '-'} | {item.url or 'NO URL'}")
        print("Compare titles, product URLs, count, and order with the live site before full fetch.")

    elif stage == "fetch":
        from src.fetcher import fetch_all_results
        _read(run_dir, "probe")  # The first-fetch gate must have run.
        context = SiteContext.model_validate(_read(run_dir, "discover"))
        queries = _models(_read(run_dir, "queries"), TestQuery)
        results = fetch_all_results(context.search_url_template, queries)
        raw_path = _write(run_dir, "fetch_raw", _dump_results(results))
        cleaned, removed = _clean_results(results)
        clean_path = _write(run_dir, "fetch", _dump_results(cleaned))
        print(f"Saved raw: {raw_path}\nSaved clean: {clean_path}")
        print(f"Fetched {sum(map(len, results.values()))} results; removed {removed} obvious junk entries.")
        print(f"Zero-result queries: {[query for query, items in cleaned.items() if not items]}")
        print("Review for remaining poisoned results and correct the clean checkpoint before scoring.")

    elif stage == "score":
        from src.scorer import score_results
        queries = _models(_read(run_dir, "queries"), TestQuery)
        results = _results(_read(run_dir, "fetch"), SearchResult)
        scores = score_results(queries, results)
        path = _write(run_dir, stage, _dump_results(scores))
        low = [q for q, items in scores.items() if items and items[0].relevance_score < 0.3]
        print(f"Saved: {path}\nScored queries: {len(scores)}\nTop-result score below 0.3: {low}")

    elif stage == "judge":
        from collections import Counter
        from src.judge import judge_all_queries
        context = SiteContext.model_validate(_read(run_dir, "discover"))
        queries = _models(_read(run_dir, "queries"), TestQuery)
        scores = _results(_read(run_dir, "score"), ScoredResult)
        judgments = judge_all_queries(
            queries, scores, language=context.primary_language,
            provenance={
                "domain": urlparse(context.url).hostname or context.site_name,
                "url": context.url,
                "judged_at": datetime.now(timezone.utc).isoformat(),
            },
            site_categories=context.nav_categories,
            site_brands=context.brands,
        )
        path = _write(run_dir, stage, [item.model_dump(mode="json") for item in judgments])
        severity = Counter(item.severity.value if hasattr(item.severity, "value") else item.severity for item in judgments)
        print(f"Saved: {path}\nSeverity counts: {dict(severity)}")
        for item in judgments:
            label = item.severity.value if hasattr(item.severity, "value") else item.severity
            if label.startswith("Critical"):
                print(f"CRITICAL: {item.test_query.query} | {item.failure_mode} | {item.evidence} | {item.recommended_fix}")
        print("Stop here. Review verdicts and preserve corrections. No report or publish step exists in this runner.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    commands = parser.add_subparsers(dest="stage", required=True)
    start = commands.add_parser("start", help="1. Validate a search results URL and create a run")
    start.add_argument("url")
    start.add_argument("--id", help="Optional lowercase run ID")
    for stage, summary in (
        ("discover", "2. Discover site and search setup"),
        ("categories", "3. Select test categories"),
        ("queries", "4. Generate test queries"),
        ("probe", "5. Check extraction on one query"),
        ("fetch", "6. Fetch all results and clean obvious junk"),
        ("score", "7. Score result relevance"),
        ("judge", "8. Judge and save findings"),
        ("status", "Show saved checkpoints"),
    ):
        command = commands.add_parser(stage, help=summary)
        command.add_argument("run_id")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    runs_dir = args.runs_dir.expanduser().resolve()
    if args.stage == "start":
        _start(args, runs_dir)
    else:
        _execute(args, runs_dir)


if __name__ == "__main__":
    main()
