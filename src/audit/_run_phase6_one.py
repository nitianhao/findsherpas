import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json, os
from src.discovery import SiteContext
from src.query_generator import TestQuery
from src.models import ScoredResult, QueryJudgment
from src.judge import _judge_single_query

CHECKPOINT = 'reports/_checkpoint_phase6.json'

sc = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
queries = [TestQuery(**q) for q in json.loads(open('reports/_checkpoint_phase3.json').read())]
scored_raw = json.load(open('reports/_checkpoint_phase5.json'))
scored = {q: [ScoredResult(**r) for r in v] for q, v in scored_raw.items()}

if os.path.exists(CHECKPOINT):
    done = json.load(open(CHECKPOINT))
else:
    done = {}

# Next unjudged query, in phase3 order
nxt = next((q for q in queries if q.query not in done), None)
if nxt is None:
    print("ALL_JUDGED")
    sys.exit(0)

results = scored.get(nxt.query, [])
j = _judge_single_query(
    nxt, results,
    language=sc.primary_language,
    site_categories=sc.nav_categories,
    site_brands=sc.brands,
)

done[nxt.query] = j.model_dump()
json.dump(done, open(CHECKPOINT, 'w'))

sev = j.severity.value if hasattr(j.severity, 'value') else j.severity
fm = j.failure_mode.value if hasattr(j.failure_mode, 'value') else j.failure_mode
idx = [q.query for q in queries].index(nxt.query) + 1
print(f"=== [{idx}/{len(queries)}] {nxt.category} | {nxt.query!r} ===")
print(f"SEVERITY: {sev}")
print(f"FAILURE_MODE: {fm}")
print(f"#results: {len(results)} | max_rel: {j.max_relevance_score:.2f} | top3avg: {j.top3_original_average:.2f} | displacement: {j.displacement}")
print(f"\nEVIDENCE:\n{j.evidence}")
print(f"\nRECOMMENDED FIX:\n{j.recommended_fix}")
if results:
    print("\nRESULTS (rank | rel | title | price):")
    for r in results[:15]:
        print(f"  {r.original_rank:2d} | {r.relevance_score:.2f} | {r.title[:70]} | {r.price or '-'}")
remaining = sum(1 for q in queries if q.query not in done)
print(f"\n[{len(done)} judged, {remaining} remaining]")
