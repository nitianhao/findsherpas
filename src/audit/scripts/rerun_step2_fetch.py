"""Step 2: Live fetch on shop-apotheke.com for all queries in step1b checkpoint.

Saves raw SearchResult data to _rerun/step2_fetch.json for the next (scoring) phase.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

from src.fetcher import fetch_all_results
from src.models import TestQuery

OUT = ROOT / "reports" / "www_shop-apotheke_com" / "_rerun"


def main() -> None:
    ckpt = json.loads((OUT / "step1b.json").read_text(encoding="utf-8"))
    template = ckpt["site_context"]["search_url_template"]
    queries = [TestQuery.model_validate(q) for q in ckpt["queries"]]

    print(f"Template:  {template}")
    print(f"Queries:   {len(queries)}")
    print()

    raw = fetch_all_results(template, queries, max_results=15)

    # Summarise
    print("\n== Per-query counts ==")
    per_cat: dict[str, list[tuple[str, int]]] = {}
    zero: list[tuple[str, str]] = []
    for tq in queries:
        cat = getattr(tq.category, "value", tq.category)
        n = len(raw.get(tq.query, []))
        per_cat.setdefault(cat, []).append((tq.query, n))
        if n == 0:
            zero.append((cat, tq.query))
    for cat, pairs in per_cat.items():
        print(f"\n  [{cat}]")
        for q, n in pairs:
            marker = " (ZERO)" if n == 0 else ""
            print(f"    {n:>3}  '{q}'{marker}")

    total = sum(len(v) for v in raw.values())
    print(f"\nTotal results: {total}")
    print(f"Zero-result queries: {len(zero)}/{len(queries)}")
    if zero:
        print("\nZero-result list:")
        for cat, q in zero:
            print(f"  [{cat}] {q}")

    # Persist raw results
    serialized = {
        q: [r.model_dump(mode="json") for r in results]
        for q, results in raw.items()
    }
    (OUT / "step2_fetch.json").write_text(
        json.dumps(
            {
                "search_url_template": template,
                "queries": [q.model_dump(mode="json") for q in queries],
                "results": serialized,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nCheckpoint written: {OUT / 'step2_fetch.json'}")


if __name__ == "__main__":
    main()
