import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json
from src.query_generator import TestQuery
from src.fetcher import SearchResult
from src.scorer import score_results

qdata = json.loads(open('reports/_checkpoint_phase3.json').read())
queries = [TestQuery(**q) for q in qdata]
scraped_raw = json.load(open('reports/_checkpoint_phase4.json'))
scraped = {q: [SearchResult(**r) for r in v] for q, v in scraped_raw.items()}

# Hard rule: don't score zero-result queries. Score only non-empty, merge zeros back.
nonempty_queries = [q for q in queries if scraped.get(q.query)]
nonempty_scraped = {q.query: scraped[q.query] for q in nonempty_queries}
print(f"Scoring {len(nonempty_queries)} non-empty queries ({len(queries)-len(nonempty_queries)} zeros skipped)", flush=True)

scored = score_results(nonempty_queries, nonempty_scraped)

# Merge zeros back as empty
for q in queries:
    if q.query not in scored:
        scored[q.query] = []

# Serialize scored results
out = {}
for q, items in scored.items():
    out[q] = [r.model_dump() for r in items] if items else []
json.dump(out, open('reports/_checkpoint_phase5.json', 'w'))
print("saved phase5", flush=True)

# Stats
from collections import defaultdict
cat_of = {q.query: str(q.category) for q in queries}
cat_scores = defaultdict(list)
low_top = []
for q, items in scored.items():
    if not items: continue
    top = max((getattr(r,'relevance_score',0) or 0) for r in items)
    cat_scores[cat_of[q]].append(top)
    if top < 0.3:
        low_top.append((q, round(top,2)))
print("\n--- Avg TOP relevance per category ---")
for c in sorted(cat_scores):
    vals = cat_scores[c]
    print(f"  {c}: {sum(vals)/len(vals):.2f}  (n={len(vals)})")
print("\n--- Queries with top relevance < 0.3 (bounce risk) ---")
for q,s in low_top: print(f"  {s}  {q!r}")
print(f"\nzero-result queries: {sum(1 for v in scored.values() if not v)}")
