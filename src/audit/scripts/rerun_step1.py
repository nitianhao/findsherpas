"""Step 1 of shop-apotheke rerun: Phases 1-3 (discovery, category select, query gen).

Checkpoints intermediate state to reports/www_shop-apotheke_com/_rerun/step1.json
so step 2 (fetch + score) can resume without re-running discovery.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

from src.category_selector import select_categories
from src.discovery import discover_from_search_url
from src.query_generator import generate_queries

TARGET = "https://www.shop-apotheke.com/search.htm?eventName=search-submit&i=1&q=spa&searchChannel=algolia"
OUT = ROOT / "reports" / "www_shop-apotheke_com" / "_rerun"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("== Phase 1: Discovery (from search URL) ==")
    ctx = discover_from_search_url(TARGET)
    print(f"  site_name:   {ctx.site_name}")
    print(f"  site_type:   {ctx.site_type}")
    print(f"  nav:         {len(ctx.nav_categories)}")
    print(f"  brands:      {len(ctx.brands)}")
    print(f"  featured:    {len(ctx.featured_items)}")
    print(f"  search_url:  {ctx.search_url_template}")

    print("\n== Phase 2: Category Selection ==")
    cats = select_categories(ctx)
    print(f"  selected ({len(cats)}):")
    for c in cats:
        # c may be an enum or str (use_enum_values=True on models)
        print(f"    - {getattr(c, 'value', c)}")

    print("\n== Phase 3: Query Generation ==")
    queries = generate_queries(ctx, cats)
    print(f"  generated {len(queries)} queries")
    current = None
    for tq in queries:
        cat = getattr(tq.category, "value", tq.category)
        if cat != current:
            current = cat
            print(f"\n  [{cat}]")
        print(f'    "{tq.query}"   — {tq.rationale[:90]}')

    # Persist checkpoint
    payload = {
        "target_url": TARGET,
        "site_context": ctx.model_dump(mode="json"),
        "selected_categories": [getattr(c, "value", c) for c in cats],
        "queries": [tq.model_dump(mode="json") for tq in queries],
    }
    (OUT / "step1.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Checkpoint written: {OUT / 'step1.json'}")


if __name__ == "__main__":
    main()
