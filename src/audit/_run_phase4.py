import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json, logging, time
from urllib.parse import quote_plus
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', stream=sys.stdout)
for noisy in ('urllib3', 'httpx', 'anthropic'):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from src.models import SiteContext, TestQuery
from src.fetcher import _fetch_with_mode, SiteMode

CKPT = 'reports/_checkpoint_phase4_huckberry.json'

ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
qdata = json.load(open('reports/_checkpoint_phase3.json'))
queries = [TestQuery.model_validate(q) for q in qdata]
template = ctx.search_url_template

# Resume: load any already-fetched queries.
import os
out = {}
if os.path.exists(CKPT):
    try:
        out = json.load(open(CKPT))
        print(f'RESUME: {len(out)} queries already saved, skipping those', flush=True)
    except Exception:
        out = {}

def save():
    json.dump(out, open(CKPT, 'w'), default=str)

print(f'START full fetch: {len(queries)} queries (incremental save → {CKPT})', flush=True)
# Huckberry forces headed chromium internally; mode is PLAYWRIGHT_CHROMIUM.
mode = SiteMode.PLAYWRIGHT_CHROMIUM
for i, tq in enumerate(queries, 1):
    if tq.query in out:
        print(f'[{i}/{len(queries)}] SKIP (cached): {tq.query!r}', flush=True)
        continue
    url = template.replace('{}', quote_plus(tq.query))
    t0 = time.time()
    try:
        results, redirected = _fetch_with_mode(url, tq.query, 15, mode)
    except Exception as e:
        print(f'[{i}/{len(queries)}] ERROR {tq.query!r}: {e}', flush=True)
        results = []
    out[tq.query] = [r.model_dump() for r in results]
    save()  # save after EVERY query
    print(f'[{i}/{len(queries)}] {tq.query!r} -> {len(results)} results ({time.time()-t0:.0f}s) [saved]', flush=True)

print('=== FETCH COMPLETE ===', flush=True)
print('queries:', len(out))
print('total results:', sum(len(rs) for rs in out.values()))
thin = {q: len(rs) for q, rs in out.items() if len(rs) < 15}
print(f'queries with <15 results ({len(thin)}):')
for q, n in sorted(thin.items(), key=lambda x: x[1]):
    print(f'  {n:2d}  {q}')
