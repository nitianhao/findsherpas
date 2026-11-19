"""Re-extract saved pages after the Imerco authoritative hit-header fix; no network calls.
Run from src/audit/: .venv312/bin/python ../../docs/experiments/search-detective-imerco-2026-11-03/scripts/reparse_search_counts.py <run-directory>
"""
import gzip
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import quote_plus,parse_qs,urlparse
from src.fetcher import _analyse_page
from src.candidates.runner import save,stamp

p=Path(sys.argv[1])
if (p/'count_correction.json').exists():raise SystemExit('Already corrected; preserve immutable original observations')
for name in ['outcome_history.json','outcomes.json','execution_summary.json','results.md']:
    shutil.copyfile(p/name,p/(Path(name).stem+'_before_count_fix'+Path(name).suffix))
history=json.loads((p/'outcome_history.json').read_text())
changes=[]
for query,items in history.items():
    for item in items:
        original=item['outcome']
        capture=next(f for f in (p/'evidence').rglob('*.html.gz') if str(f) in original['evidence'])
        html=gzip.decompress(capture.read_bytes()).decode()
        outcome=_analyse_page(html=html,url='https://www.imerco.dk/search?query='+quote_plus(query),query=query,max_results=10,
                              final_url=original['final_url'],http_status=original['http_status'],allow_llm=False)
        outcome.attempts=original['attempts']
        outcome.evidence=(outcome.evidence or '')+f' [evidence: {capture}]'
        if outcome.total_hits!=original['total_hits']:
            changes.append({'query':query,'observed_at':item['observed_at'],'before':original['total_hits'],'after':outcome.total_hits})
        item['outcome']=outcome.model_dump(mode='json')
        item['reparsed_at']=stamp()
final={q:items[-1]['outcome'] for q,items in history.items()}
save(p/'outcome_history.json',history);save(p/'outcomes.json',final)
summary=json.loads((p/'execution_summary.json').read_text())
for case in summary['cases']:
    for step in case['steps']:
        o=final[step['query']]
        step['total_hits']=o['total_hits'];step['extracted']=len(o['results']);step['status']=o['status']
        step['trusted_fetch']=o['status'] in {'ok','partial','redirect','zero_confirmed'}
        step['anchor_rank']=next((r['rank'] for r in o['results'] if parse_qs(urlparse(r['url'] or '').query).get('id',[''])[0]==case['anchor_product_id']),None)
summary['count_correction']='Re-extracted from original saved HTML with scoped HitsHeader_count; original data preserved in *_before_count_fix files.'
save(p/'execution_summary.json',summary)
lines=['# Imerco search execution\n','Observed results, not quality verdicts. Counts use the authoritative results header, excluding facet subtotals.\n','| Mode | Role | Query | Status | Reported hits | Anchor rank in top 10 |','| --- | --- | --- | --- | ---: | ---: |']
for c in summary['cases']:
    for s in c['steps']:lines.append(f'| {c["mode"]} | {s["role"]} | {s["query"]} | {s["status"]} | {s["total_hits"]} | {s["anchor_rank"] or "—"} |')
(p/'results.md').write_text('\n'.join(lines)+'\n')
save(p/'count_correction.json',{'corrected_at':stamp(),'source':'saved original HTML; no network requests','changes':changes})
print(json.dumps(changes,ensure_ascii=False,indent=2))
