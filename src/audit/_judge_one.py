import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json, os, logging
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
from src.models import SiteContext, TestQuery, ScoredResult
from src.judge import _judge_single_query

idx = int(sys.argv[1])  # 1-based query index
CKPT = 'reports/_checkpoint_phase6.json'

ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
queries = [TestQuery.model_validate(q) for q in json.load(open('reports/_checkpoint_phase3.json'))]
scored_raw = json.load(open('reports/_checkpoint_phase5.json'))
scored = {q: [ScoredResult.model_validate(r) for r in rs] for q, rs in scored_raw.items()}

tq = queries[idx-1]
results = scored.get(tq.query, [])
j = _judge_single_query(tq, results, language=ctx.primary_language,
                        site_categories=ctx.nav_categories, site_brands=ctx.brands)

existing = []
if os.path.exists(CKPT):
    existing = json.load(open(CKPT))
existing = [e for e in existing if (e.get('test_query') or {}).get('query') != tq.query]
existing.append(j.model_dump(mode='json'))
json.dump(existing, open(CKPT, 'w'), default=str, ensure_ascii=False)

sev = j.severity.value if hasattr(j.severity,'value') else j.severity
fm = j.failure_mode.value if hasattr(j.failure_mode,'value') else j.failure_mode
cat = tq.category.value if hasattr(tq.category,'value') else tq.category
print(f'QUERY {idx}/{len(queries)}  [{cat}]')
print(f'  query:        {tq.query!r}')
print(f'  results:      {len(results)}')
for r in results[:8]:
    rs = getattr(r,'relevance_score',None)
    print(f'     {r.rank}. {r.title!r} | {r.price or "-"} | rel={rs:.2f}' if rs is not None else f'     {r.rank}. {r.title!r}')
print(f'  --> SEVERITY:    {sev}')
print(f'  --> FAILURE_MODE:{fm}')
print(f'  --> EVIDENCE:    {j.evidence}')
print(f'  --> FIX:         {j.recommended_fix}')
print(f'  (saved {len(existing)}/{len(queries)})')
