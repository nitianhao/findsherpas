"""Resilient, resumable fetch for the synthetic search audit.

Saves the checkpoint after EVERY query (atomic tmp + os.replace, so a kill mid-write
never corrupts it). Each entry is the query's full FetchOutcome: {status, results,
final_url, total_hits, evidence, ...}. On restart, queries whose status is ok or
zero_confirmed are kept; everything else (blocked, timeout, error, zero_unverified,
partial, redirect, and legacy list-only entries with no status) is fetched again.
The site is probed once per run, not once per chunk.

Usage (from src/audit):
    .venv312/bin/python scripts/chunked_fetch.py [phase1.json phase3.json out.json] [--evidence DIR]
"""
import json
import os
import sys

sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)

from src.models import TRUSTED_FETCH_STATUSES, FetchOutcome, SiteContext, TestQuery
from src.fetcher import _outcome_rank, fetch_all_outcomes

MAX_RESULTS = 15
KEEP_STATUSES = set(TRUSTED_FETCH_STATUSES)   # ok, zero_confirmed, partial, redirect

args = [a for a in sys.argv[1:] if not a.startswith("--")]
EVIDENCE_DIR = None
if "--evidence" in sys.argv:
    i = sys.argv.index("--evidence")
    EVIDENCE_DIR = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    if EVIDENCE_DIR in args:
        args.remove(EVIDENCE_DIR)
PHASE1, PHASE3, CKPT = (args + ['reports/_checkpoint_phase1.json', 'reports/_checkpoint_phase3.json',
                                'reports/_checkpoint_phase4.json'][len(args):])[:3]


def log(msg):
    print(msg, flush=True)


def save_atomic(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


with open(PHASE1) as fh:
    ctx = SiteContext.model_validate_json(fh.read())
with open(PHASE3) as fh:
    queries = [TestQuery.model_validate(q) for q in json.load(fh)]

done = {}
if os.path.exists(CKPT):
    with open(CKPT) as fh:
        done = json.load(fh)
    log(f"Resuming: {len(done)} queries in checkpoint")


def _keep(entry) -> bool:
    return isinstance(entry, dict) and entry.get("status") in KEEP_STATUSES


remaining = [q.query for q in queries if not _keep(done.get(q.query))]
log(f"Total queries: {len(queries)} | to fetch: {len(remaining)}")


def on_outcome(outcome: FetchOutcome) -> None:
    previous = done.get(outcome.query)
    if isinstance(previous, dict) and "status" in previous:
        if _outcome_rank(FetchOutcome.model_validate(previous)) > _outcome_rank(outcome):
            log(f"  kept earlier '{outcome.query}' ({previous['status']}) over new {outcome.status}")
            return
    done[outcome.query] = outcome.model_dump(mode="json")
    save_atomic(CKPT, done)
    log(f"  saved '{outcome.query}': {outcome.status}, {len(outcome.results)} results "
        f"({sum(1 for v in done.values() if _keep(v))}/{len(queries)} settled)")


if remaining:
    fetch_all_outcomes(remaining, ctx.search_url_template, max_results=MAX_RESULTS,
                       evidence_dir=EVIDENCE_DIR, on_outcome=on_outcome)

counts = {}
for v in done.values():
    st = v.get("status", "legacy") if isinstance(v, dict) else "legacy"
    counts[st] = counts.get(st, 0) + 1
tot = sum(len(v.get("results", [])) for v in done.values() if isinstance(v, dict))
log(f"FETCH DONE. queries: {len(done)} total_results: {tot} statuses: {counts}")
retry = [k for k, v in done.items() if not _keep(v)]
if retry:
    log(f"NOT SETTLED (re-run to retry): {retry}")
thin = [k for k, v in done.items() if isinstance(v, dict) and len(v.get("results", [])) < MAX_RESULTS]
log(f"FEWER THAN {MAX_RESULTS} RESULTS (review by hand): {thin}")
