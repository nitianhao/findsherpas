"""Resumable, incremental Phase 4 fetch for zalando.ie.

Playbook hard rule: write the checkpoint after EVERY query, not once at the end.
The full run is ~60s/query x 63 queries (~1h, headed Chromium), so a mid-list
failure or an externally-killed process must not discard completed work. On
restart, queries already present in the checkpoint are skipped.

Replicates two behaviours of fetch_all_results that matter for correctness:
  * retry-on-zero for dedicated-extractor hosts (zalando is authoritative-empty,
    so a transient client-render lapse is indistinguishable from a real zero).
  * was_redirected handling (a redirect away from search => no results).
Mode is pinned to headed Chromium (proven at 4a) instead of re-probing per query.
"""
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)

import json
import os
import time
from urllib.parse import quote_plus

from src.models import SiteContext, TestQuery
from src.fetcher import _fetch_with_mode, SiteMode

CKPT = 'reports/_checkpoint_phase4_zalando.json'
MAX_RESULTS = 15
MODE = SiteMode.PLAYWRIGHT_CHROMIUM

sc = SiteContext.model_validate_json(open('reports/_checkpoint_phase1_zalando.json', encoding='utf-8').read())
queries = [TestQuery.model_validate(q) for q in json.load(open('reports/_checkpoint_phase3_zalando.json'))]
tmpl = sc.search_url_template

store: dict = {}
if os.path.exists(CKPT):
    store = json.load(open(CKPT, encoding='utf-8'))
    print(f'resuming: {len(store)} queries already in checkpoint', flush=True)

todo = [q for q in queries if q.query not in store]
print(f'total={len(queries)}  done={len(store)}  todo={len(todo)}', flush=True)

t0 = time.time()
for i, q in enumerate(todo, 1):
    url = tmpl.replace('{}', quote_plus(q.query))
    try:
        results, was_redirected = _fetch_with_mode(url, q.query, MAX_RESULTS, MODE)
    except Exception as e:
        print(f'  [{i}/{len(todo)}] ERROR {q.query[:45]!r}: {e}', flush=True)
        continue

    # transient-zero guard: zalando is authoritative-empty, so one re-fetch
    # distinguishes a genuine zero from a client-render lapse.
    if not was_redirected and not results:
        time.sleep(1.5)
        try:
            retry_results, retry_redirected = _fetch_with_mode(url, q.query, MAX_RESULTS, MODE)
            if not retry_redirected and retry_results:
                print(f'      (recovered {len(retry_results)} on retry)', flush=True)
                results = retry_results
        except Exception as e:
            print(f'      (retry failed: {e})', flush=True)

    if was_redirected:
        results = []

    store[q.query] = [r.model_dump() for r in results]
    json.dump(store, open(CKPT, 'w', encoding='utf-8'), indent=2)   # checkpoint EVERY query

    el = (time.time() - t0) / 60
    top = results[0].title[:50] if results else '(ZERO)'
    flag = ' REDIR' if was_redirected else ''
    print(f'  [{i}/{len(todo)}] {len(results):>2}res{flag} | {el:5.1f}m | {q.category:<20} {q.query[:34]!r} -> {top!r}', flush=True)

print(f'DONE: {len(store)}/{len(queries)} in checkpoint ({(time.time()-t0)/60:.1f} min)', flush=True)
