"""Judge ONE douglas query at a time (Phase 6, gated review).

Usage: python3 scripts/_judge_one_douglas.py <index>   # 0-based index into phase-3 queries
Prints the query, its scored results, and the judgment. Saves nothing unless --save.
"""
import json
import sys

sys.path.insert(0, ".")
from dotenv import load_dotenv

load_dotenv(override=True)

from src.judge import _judge_single_query  # noqa: E402
from src.models import ScoredResult, TestQuery  # noqa: E402

REPORTS = "reports"
JUDGE_CP = f"{REPORTS}/_checkpoint_phase6_douglas.json"


def load():
    queries = [TestQuery.model_validate(q) for q in json.load(open(f"{REPORTS}/_checkpoint_phase3_douglas.json"))]
    raw = json.load(open(f"{REPORTS}/_checkpoint_phase5_douglas.json"))
    scored = {k: [ScoredResult.model_validate(r) for r in v] for k, v in raw.items()}
    ctx = json.load(open(f"{REPORTS}/_checkpoint_phase1_douglas.json"))
    return queries, scored, ctx


def main():
    idx = int(sys.argv[1])
    save = "--save" in sys.argv
    queries, scored, ctx = load()
    tq = queries[idx]
    results = scored.get(tq.query, [])

    print(f"=== [{idx + 1}/{len(queries)}] {tq.category}: {tq.query!r}")
    print(f"rationale: {tq.rationale}")
    print(f"live: {ctx['search_url_template'].format(tq.query)}")
    print(f"results: {len(results)}")
    for r in sorted(results, key=lambda x: x.original_rank):
        print(f"  {r.original_rank:>2}. rel={r.relevance_score:.2f}  {r.title}  | {r.price or '-'}")

    j = _judge_single_query(
        tq,
        results,
        language=ctx.get("primary_language"),
        site_categories=ctx.get("nav_categories"),
        site_brands=ctx.get("brands"),
    )
    d = j.model_dump(mode="json")
    print("\n--- JUDGMENT ---")
    for k, v in d.items():
        print(f"{k}: {v}")

    if save:
        try:
            store = json.load(open(JUDGE_CP))
        except FileNotFoundError:
            store = {}
        store[tq.query] = d
        json.dump(store, open(JUDGE_CP, "w"), ensure_ascii=False, indent=2)
        print(f"\nsaved -> {JUDGE_CP} ({len(store)} judged)")


if __name__ == "__main__":
    main()
