"""Resilient chunked fetch for the synthetic search audit.

Fetches queries in small chunks, saving the merged checkpoint after each chunk
so an interruption never loses completed work. Resumes automatically by skipping
queries already present in the checkpoint.
"""
import sys, json, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

from src.models import SiteContext, TestQuery, SearchResult
from src.fetcher import fetch_all_results

CHUNK = 10
MAX_RESULTS = 10
CKPT = 'reports/_checkpoint_phase4.json'

def log(msg):
    print(msg, flush=True)

ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
queries = [TestQuery.model_validate(q) for q in json.load(open('reports/_checkpoint_phase3.json'))]

# Resume: load existing checkpoint if present
done = {}
if os.path.exists(CKPT):
    done = json.load(open(CKPT))
    log(f"Resuming: {len(done)} queries already fetched")

remaining = [q for q in queries if q.query not in done]
log(f"Total queries: {len(queries)} | remaining: {len(remaining)}")

for i in range(0, len(remaining), CHUNK):
    chunk = remaining[i:i+CHUNK]
    res = fetch_all_results(ctx.search_url_template, chunk, max_results=MAX_RESULTS)
    for k, v in res.items():
        done[k] = [r.model_dump() for r in v]
    json.dump(done, open(CKPT, 'w'), indent=2)
    fetched_now = sum(len(v) for v in res.values())
    log(f"CHUNK {i//CHUNK + 1}: +{len(chunk)} queries, {fetched_now} results | total done: {len(done)}/{len(queries)}")

tot = sum(len(v) for v in done.values())
zero = [k for k, v in done.items() if not v]
log(f"FETCH DONE. queries: {len(done)} total_results: {tot} zero_result_queries: {len(zero)}")
log(f"ZERO: {zero}")
