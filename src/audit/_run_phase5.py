import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json
from collections import defaultdict
from src.models import TestQuery, SearchResult
from src.scorer import score_results

qdata = json.load(open('reports/_checkpoint_phase3.json'))
queries = [TestQuery.model_validate(q) for q in qdata]
raw = json.load(open('reports/_checkpoint_phase4_huckberry.json'))
scraped = {q: [SearchResult.model_validate(r) for r in rs] for q, rs in raw.items()}

scored = score_results(queries, scraped)

# Persist phase 5
out = {q: [r.model_dump() for r in rs] for q, rs in scored.items()}
json.dump(out, open('reports/_checkpoint_phase5_huckberry.json', 'w'), default=str)

# Stats
cat_of = {q.query: (q.category.value if hasattr(q.category,'value') else q.category) for q in queries}
def topscore(rs):
    return max((getattr(r,'relevance_score',None) or 0) for r in rs) if rs else 0.0
by_cat = defaultdict(list)
zero=[]; low_top=[]
for q, rs in scored.items():
    c = cat_of.get(q,'?')
    # avg relevance across results for this query
    vals=[getattr(r,'relevance_score',None) or 0 for r in rs]
    if not rs:
        zero.append(q)
    avgq = sum(vals)/len(vals) if vals else 0.0
    by_cat[c].append(avgq)
    if topscore(rs) < 0.3:
        low_top.append((c,q,len(rs),round(topscore(rs),2)))

print('=== SCORING COMPLETE ===')
print('queries scored:', len(scored))
print('\nAvg relevance by category:')
for c in sorted(by_cat):
    vs=by_cat[c]
    print(f'  {sum(vs)/len(vs):.2f}   {c}  (n={len(vs)})')
print(f'\nZero-result queries ({len(zero)}):')
for q in zero: print('  -', q, '['+cat_of.get(q,'?')+']')
print(f'\nTop-result relevance < 0.30 ({len(low_top)}):')
for c,q,n,t in sorted(low_top):
    print(f'  top={t} n={n:2d}  [{c}] {q}')
