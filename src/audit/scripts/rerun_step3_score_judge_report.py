"""Step 3: Score (Voyage) + Judge (LLM) + Report + Sales materials.

Reads step1b.json (site context, queries) and step2_fetch.json (raw results).
Writes final report artifacts to reports/www_shop-apotheke_com/.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

from src.judge import judge_all_queries
from src.models import ScoredResult, SearchResult, SiteContext, TestQuery
from src.report_generator import generate_report
from src.sales_materials_generator import generate_sales_materials
from src.scorer import score_results

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("step3")

RUN_DIR = ROOT / "reports" / "www_shop-apotheke_com"
CKPT = RUN_DIR / "_rerun"


def main() -> None:
    t0 = time.time()

    # ── Load checkpoints ────────────────────────────────────────────────
    ctx_payload = json.loads((CKPT / "step1b.json").read_text(encoding="utf-8"))
    fetch_payload = json.loads((CKPT / "step2_fetch.json").read_text(encoding="utf-8"))

    site_ctx = SiteContext.model_validate(ctx_payload["site_context"])
    queries = [TestQuery.model_validate(q) for q in ctx_payload["queries"]]
    raw_results: dict[str, list[SearchResult]] = {
        q: [SearchResult.model_validate(r) for r in rs]
        for q, rs in fetch_payload["results"].items()
    }

    print(f"Loaded: {len(queries)} queries, {sum(len(v) for v in raw_results.values())} raw results")

    # ── Phase 5: Score via Voyage rerank-2.5 ────────────────────────────
    print("\n== Phase 5: Scoring (Voyage AI rerank-2.5) ==")
    scored = score_results(queries, raw_results)
    scored_count = sum(1 for v in scored.values() if v)
    print(f"  scored {scored_count}/{len(queries)} queries")
    (CKPT / "step3_scored.json").write_text(
        json.dumps(
            {q: [r.model_dump(mode="json") for r in rs] for q, rs in scored.items()},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"  checkpoint: {CKPT / 'step3_scored.json'}")

    # ── Phase 6: Judge via LLM ───────────────────────────────────────────
    print("\n== Phase 6: Judging (LLM) ==")
    judgments = judge_all_queries(queries, scored)
    print(f"  produced {len(judgments)} judgments")
    (CKPT / "step3_judgments.json").write_text(
        json.dumps([j.model_dump(mode="json") for j in judgments], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  checkpoint: {CKPT / 'step3_judgments.json'}")

    # ── Phase 7: Report ─────────────────────────────────────────────────
    print("\n== Phase 7: Report assembly ==")
    report = generate_report(site_ctx, judgments)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"www_shop-apotheke_com_{timestamp}"
    md_file = RUN_DIR / f"{slug}_report.md"
    json_file = RUN_DIR / f"{slug}_data.json"
    md_file.write_text(report.deep_dive_narrative, encoding="utf-8")
    json_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"  wrote: {md_file.name}")
    print(f"  wrote: {json_file.name}")

    # Sales materials
    print("\n== Phase 7b: Sales materials ==")
    generate_sales_materials(report, RUN_DIR, slug)

    elapsed = time.time() - t0
    cap_scores = report.capability_scores
    pass_count = sum(
        1 for cs in cap_scores
        if cs.severity == "Pass \u2014 Search handles this well."
    )
    print(f"\nCOMPLETE: {pass_count}/{len(cap_scores)} capabilities pass — {elapsed:.0f}s")
    print(f"Slug: {slug}")


if __name__ == "__main__":
    main()
