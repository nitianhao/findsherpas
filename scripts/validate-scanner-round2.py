#!/usr/bin/env python3
"""Run the round-two headed cohort in isolated scanner processes (no writes to services)."""
import argparse
import csv
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--stores', type=Path, default=ROOT/'docs/scanner-validation/stores-round2.csv')
p.add_argument('--output', type=Path, default=ROOT/'scanner_output/round2')
p.add_argument('--env-file', required=True)
p.add_argument('--workers', type=int, default=3)
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(args.stores.open()))
start = time.time()

def scan(row):
    domain = urlparse(row['domain']).netloc
    directory = args.output/domain
    existing = list(directory.glob('*_20*.json')) if directory.exists() else []
    if existing:
        previous = json.loads(existing[-1].read_text())
        if previous.get('overall_score') != 'error':
            return previous
    with (args.output/f'{domain}.log').open('w') as log:
        completed = subprocess.run([str(ROOT/'scripts/scan-search'),row['domain'],
            '--headed','--country',row['country'],'--vertical',row['vertical'],
            '--env-file',args.env_file,'--output-dir',str(args.output)],stdout=log,stderr=log)
    files = list(directory.glob('*_20*.json'))
    if not files:
        return {'site':row,'overall_score':'error','error_message':f'Process exited {completed.returncode} without result'}
    return json.loads(files[-1].read_text())

results = []
with ThreadPoolExecutor(max_workers=args.workers) as pool:
    for future in as_completed([pool.submit(scan,row) for row in rows]):
        result = future.result()
        results.append(result)
        print(f"{len(results)}/{len(rows)} {result['site']['domain']}: {result['overall_score']}",flush=True)
        (args.output/'batch_results.json').write_text(json.dumps({'results':results,
            'wall_seconds':time.time()-start,'total_llm_cost_usd':sum(r.get('llm_cost_usd',0) for r in results)},indent=2))
