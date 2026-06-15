import sys, json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from collections import defaultdict
from src.query_generator import TestQuery
from src.fetcher import SearchResult
from src.scorer import score_results

all_q = [TestQuery.model_validate(q) for q in json.load(open('reports/_checkpoint_phase3.json'))]
screen = json.load(open('reports/_redirect_screen.json'))
keep_set = {s for _, s in screen['keep']}
queries = [q for q in all_q if q.query in keep_set]

raw = json.load(open('reports/_checkpoint_phase4.json'))
scraped = {q: [SearchResult.model_validate(r) for r in rows] for q, rows in raw.items()}

scored = score_results(queries, scraped)

# Serialize
out = {q: [r.model_dump() for r in rs] for q, rs in scored.items()}
json.dump(out, open('reports/_checkpoint_phase5.json', 'w'), ensure_ascii=False)

# Aggregate by category
qcat = {q.query: q.category for q in queries}
cat_scores = defaultdict(list)
low_top = []
for q, rs in scored.items():
    cat = qcat.get(q, '?')
    top = rs[0].relevance_score if rs else 0.0
    cat_scores[cat].append(top)
    if rs and top < 0.3:
        low_top.append((q, round(top, 2)))

print('=== Avg TOP-result relevance per category ===', flush=True)
for cat in sorted(cat_scores):
    vals = cat_scores[cat]
    print(f'  {cat:18} n={len(vals):2}  avg_top={sum(vals)/len(vals):.2f}', flush=True)

print(f'\n=== Queries with top-result relevance < 0.3 ({len(low_top)}) ===', flush=True)
for q, s in sorted(low_top, key=lambda x: x[1]):
    print(f'  [{s}] {q}', flush=True)

total_results = sum(len(v) for v in scored.values())
print(f'\nTotal scored results: {total_results} across {len(scored)} queries', flush=True)
