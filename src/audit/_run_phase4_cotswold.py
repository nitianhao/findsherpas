import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

import json
import os
from urllib.parse import quote_plus

from src.discovery import SiteContext
from src.query_generator import TestQuery
from src.fetcher import _probe_site, _fetch_with_mode, SiteMode

CHECKPOINT = 'reports/_checkpoint_phase4.json'
MAX_RESULTS = 15

sc = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
qdata = json.loads(open('reports/_checkpoint_phase3.json').read())
queries = [TestQuery(**q) for q in qdata]

# Resume: load existing checkpoint, skip queries already present.
if os.path.exists(CHECKPOINT):
    with open(CHECKPOINT) as f:
        done = json.load(f)
else:
    done = {}

remaining = [q for q in queries if q.query not in done]
print(f"Resuming: {len(done)} already done, {len(remaining)} remaining", flush=True)

if not remaining:
    print("Nothing to do.", flush=True)
    sys.exit(0)

# Probe once with the first remaining query to establish site mode.
first = remaining[0]
first_url = sc.search_url_template.replace('{}', quote_plus(first.query))
mode, results, html, was_redirected = _probe_site(first_url, first.query, MAX_RESULTS)
print(f"Site mode: {mode}", flush=True)

done[first.query] = [r.model_dump() for r in results]
with open(CHECKPOINT, 'w') as f:
    json.dump(done, f)
print(f"[{len(done)}/{len(queries)}] {len(results):3d} results | [{first.category}] {first.query!r}", flush=True)

for q in remaining[1:]:
    url = sc.search_url_template.replace('{}', quote_plus(q.query))
    try:
        results, was_redirected = _fetch_with_mode(url, q.query, MAX_RESULTS, mode)
    except Exception as e:
        print(f"ERROR on {q.query!r}: {e}", flush=True)
        results = []
    done[q.query] = [r.model_dump() for r in results]
    with open(CHECKPOINT, 'w') as f:
        json.dump(done, f)
    print(f"[{len(done)}/{len(queries)}] {len(results):3d} results | [{q.category}] {q.query!r}", flush=True)

print("DONE", flush=True)
