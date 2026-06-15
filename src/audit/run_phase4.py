import sys, json, time
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from src.discovery import SiteContext
from src.query_generator import TestQuery
from src.fetcher import fetch_all_results

ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
tmpl = ctx.search_url_template
all_q = [TestQuery.model_validate(q) for q in json.load(open('reports/_checkpoint_phase3.json'))]

screen = json.load(open('reports/_redirect_screen.json'))
keep_set = {s for _, s in screen['keep']}
queries = [q for q in all_q if q.query in keep_set]
print(f'Kept {len(queries)} of {len(all_q)} queries (dropped {len(all_q)-len(queries)} redirects)', flush=True)

t0 = time.time()
results = fetch_all_results(tmpl, queries)
elapsed = time.time() - t0

# Serialize: dict[query] -> list[SearchResult dicts]
out = {q: [r.model_dump() for r in rs] for q, rs in results.items()}
json.dump(out, open('reports/_checkpoint_phase4.json', 'w'), ensure_ascii=False)

total = sum(len(v) for v in out.values())
zero = [q for q, v in out.items() if len(v) == 0]
priced = sum(1 for v in out.values() for r in v if r.get('price'))
print(f'DONE in {elapsed:.0f}s', flush=True)
print(f'Queries fetched: {len(out)}', flush=True)
print(f'Total results: {total}  | with price: {priced}', flush=True)
print(f'Zero-result queries ({len(zero)}): {zero}', flush=True)
