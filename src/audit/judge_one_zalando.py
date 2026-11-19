"""Judge ONE zalando query at a time (index-based) and patch the phase-6 checkpoint."""
import sys, json, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

from src.models import TestQuery, ScoredResult
from src.judge import _judge_single_query

SITE = 'zalando'
P3 = f'reports/_checkpoint_phase3_{SITE}.json'
P5 = f'reports/_checkpoint_phase5_{SITE}.json'
P1 = f'reports/_checkpoint_phase1_{SITE}.json'
P6 = f'reports/_checkpoint_phase6_{SITE}.json'

idx = int(sys.argv[1])
queries = [TestQuery.model_validate(q) for q in json.load(open(P3))]
scored_raw = json.load(open(P5))
ctx = json.load(open(P1))
tq = queries[idx]
results = [ScoredResult.model_validate(r) for r in scored_raw.get(tq.query, [])]

j = _judge_single_query(
    tq, results,
    language=ctx.get('primary_language'),
    site_categories=ctx.get('nav_categories'),
    site_brands=ctx.get('brands'),
)

print(f"=== [{idx}] {tq.category} | {tq.query!r}")
print(f"severity     : {j.severity}")
print(f"failure_mode : {j.failure_mode}")
print(f"evidence     : {j.evidence}")
print(f"recommended  : {j.recommended_fix}")
print("--- results (SITE order = original_rank; [relN] = relevance-sorted position) ---")
for r in sorted(results, key=lambda x: x.original_rank):
    print(f"  {r.original_rank:2d}. {r.title[:95]!r} | {r.price or '-'} | rel={r.relevance_score:.3f} [rel#{r.rank}]")

store = json.load(open(P6)) if os.path.exists(P6) else {}
store[str(idx)] = json.loads(j.model_dump_json())
json.dump(store, open(P6, 'w'), indent=2, ensure_ascii=False)
print(f"\n[saved] {P6} ({len(store)}/{len(queries)} judged)")
