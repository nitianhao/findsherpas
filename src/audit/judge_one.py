import sys, json
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
from src.models import TestQuery, ScoredResult, SiteContext
from src.judge import _judge_single_query

idx = int(sys.argv[1])  # 0-based query index

queries = [TestQuery.model_validate(q) for q in json.loads(open('reports/_checkpoint_phase3.json').read())]
scored_raw = json.loads(open('reports/_checkpoint_phase5_scored.json').read())
ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())

tq = queries[idx]
results = [ScoredResult.model_validate(r) for r in scored_raw.get(tq.query, [])]

j = _judge_single_query(
    tq, results, language='sv',
    site_categories=ctx.nav_categories, site_brands=ctx.brands,
)

cat = tq.category.value if hasattr(tq.category, 'value') else tq.category
print(f'QUERY #{idx+1}/{len(queries)}  [{cat}]  {tq.query!r}')
print(f'  severity     : {j.severity.value if hasattr(j.severity,"value") else j.severity}')
print(f'  failure_mode : {j.failure_mode.value if hasattr(j.failure_mode,"value") else j.failure_mode}')
print(f'  evidence     : {j.evidence}')
print(f'  recommended  : {j.recommended_fix}')
print()
print('  Results (TRUE site order = original_rank; rel = relevance):')
for r in sorted(results, key=lambda x: (x.original_rank if x.original_rank is not None else x.rank)):
    orank = r.original_rank if r.original_rank is not None else r.rank
    print(f'    site#{orank}. {r.title!r} | {r.price or "-"} | rel={r.relevance_score:.2f}')

# persist into phase6 checkpoint
ck = 'reports/_checkpoint_phase6.json'
try:
    data = json.loads(open(ck).read())
except FileNotFoundError:
    data = {}
data[tq.query] = j.model_dump()
open(ck, 'w').write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
