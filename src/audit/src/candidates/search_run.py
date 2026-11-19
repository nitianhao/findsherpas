"""Execute reviewed Imerco query suites and preserve observations, not quality verdicts."""
from __future__ import annotations
import argparse
import gzip
import json
import logging
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
from .collection import fetch, detail_product
from .contracts import Link
from .runner import digest, save, stamp
from .validation import norm
from src.fetcher import fetch_all_outcomes


def product_id(url: str) -> str:
    return parse_qs(urlparse(url).query).get('id',[''])[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suites',type=Path,required=True)
    parser.add_argument('--candidates',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    suites=json.loads(args.suites.read_text())
    if suites['status']!='complete' or not suites['cases'] or any(c['status']!='wording_review_accepted' for c in suites['cases']):
        parser.error('Only complete wording-reviewed query suites can run')
    if args.out.exists() and any(args.out.iterdir()):parser.error('Use a new output directory; existing observations are immutable')
    source=json.loads((args.candidates/'report.json').read_text())
    products={p['id']:p for p in json.loads((args.candidates/'products.json').read_text())}
    facts={f['id']:f for f in source['facts']}
    query_manifest=json.loads((args.suites.parent/'manifest.json').read_text())
    for name in ['report.json','products.json']:
        if query_manifest['config']['inputs'][name]!=digest((args.candidates/name).read_text()):
            parser.error('Candidate source does not match reviewed query input')
    queries=list(dict.fromkeys(s['query'] for c in suites['cases'] for s in c['steps']))
    save(args.out/'manifest.json',{'started_at':stamp(),'suites_sha256':digest(args.suites.read_text()),
        'candidate_report_sha256':digest((args.candidates/'report.json').read_text()),
        'query_entries':sum(len(c['steps']) for c in suites['cases']),'unique_queries':len(queries),
        'search_url_template':'https://www.imerco.dk/search?query={}', 'top_k':10,
        'llm_calls':0,'note':'Read-only execution and source refresh; no relevance or search-quality judgments.'})
    referenced={c['anchor_product_id'] for c in suites['cases']}
    referenced.update(pid for c in suites['cases'] for pid in c['known_ineligible_product_ids'])
    refreshed={}
    for pid in sorted(referenced):
        original=products[pid]
        try:
            html,metadata=fetch(original['url'],args.out/'product_refresh')
            p=detail_product(Link(id=pid,url=original['url'],text=original['name']),html,metadata,'known anchor/contrast')
            relevant=[f for c in suites['cases'] for fid in c['supporting_fact_ids']
                      if (f:=facts[fid])['product_id']==pid]
            missing=sorted({f['id'] for f in relevant if norm(f['quote']) not in norm(p.text)})
            refreshed[pid]={'status':'refreshed','product':p.model_dump(),'missing_prior_quotes':missing,
                'add_to_cart_text_present':'læg i kurv' in norm(p.text),
                'note':'Page identity and text refreshed; purchase feasibility/semantic fact changes require review.'}
        except Exception as exc:refreshed[pid]={'status':'error','error_type':type(exc).__name__}
        save(args.out/'refreshed_products.json',refreshed)
        print('Refreshed product',pid,refreshed[pid]['status'],flush=True)
    history={q:[] for q in queries}
    def checkpoint(o):
        history[o.query].append({'observed_at':stamp(),'outcome':o.model_dump(mode='json')})
        save(args.out/'outcome_history.json',history)
    logging.basicConfig(level=logging.INFO)
    fetch_all_outcomes(queries,'https://www.imerco.dk/search?query={}',max_results=10,
                       evidence_dir=str(args.out/'evidence'/'first'),on_outcome=checkpoint,light=True)
    suspects=[q for q in queries if history[q][-1]['outcome']['status'] in {'zero_confirmed','zero_unverified','timeout','error'}]
    positive=next((q for q in queries if history[q][-1]['outcome']['status']=='ok' and len(history[q][-1]['outcome']['results'])==10),None)
    if suspects and positive:
        # Re-establish the successful static transport before rechecking thin/empty queries.
        fetch_all_outcomes([positive]+suspects,'https://www.imerco.dk/search?query={}',max_results=10,
                           evidence_dir=str(args.out/'evidence'/'recheck'),on_outcome=checkpoint,light=True)
    final={q:items[-1]['outcome'] for q,items in history.items()}
    save(args.out/'outcomes.json',final)
    # Preserve full visible card wording, including offer/member conditions discarded by SearchResult.price.
    card_text={}
    for q,items in history.items():
        item=items[-1]['outcome']; cards={}
        for path in (args.out/'evidence').rglob('*.html.gz'):
            # Evidence paths include a query slug and digest; use the exact recorded path.
            if str(path) not in item.get('evidence',''):continue
            soup=BeautifulSoup(gzip.decompress(path.read_bytes()).decode(),'html.parser')
            for card in soup.select('div[class*="ProductHit_wrapper"]'):
                a=card.select_one('a[class*="ProductHit_card"]')
                if a:cards[product_id(a['href'])]=card.get_text(' ',strip=True)
        card_text[q]=[{'rank':r['rank'],'product_id':product_id(r['url'] or ''),'card_text':cards.get(product_id(r['url'] or ''),'')}
                      for r in item['results']]
    save(args.out/'result_card_text.json',card_text)
    cases=[]
    for c in suites['cases']:
        steps=[]
        for s in c['steps']:
            o=final[s['query']]
            steps.append({'role':s['role'],'query':s['query'],'status':o['status'],'total_hits':o['total_hits'],
                'extracted':len(o['results']),'anchor_rank':next((r['rank'] for r in o['results'] if product_id(r['url'] or '')==c['anchor_product_id']),None),
                'observations':len(history[s['query']]),'trusted_fetch':o['status'] in {'ok','partial','redirect','zero_confirmed'}})
        cases.append({'mode':c['mode'],'anchor_product_id':c['anchor_product_id'],'steps':steps})
    summary={'status':'complete','completed_at':stamp(),'searches_executed':True,'unique_queries':len(queries),
        'query_entries':sum(len(c['steps']) for c in cases),'status_counts':dict(Counter(o['status'] for o in final.values())),
        'cases':cases,'refreshed_products':len(refreshed),'product_refresh_errors':sum(p['status']=='error' for p in refreshed.values()),
        'quality_judgments_performed':False,'llm_calls':0,
        'note':'Counts/anchor visibility are observations. Result-level eligibility and root causes have not been judged.'}
    save(args.out/'execution_summary.json',summary)
    lines=['# Imerco search execution\n','All rows are observations, not search-quality verdicts. Only the first ten results were extracted. Anchor absence does not establish failure.\n',
           '| Mode | Role | Query | Status | Reported hits | Anchor rank in top 10 |','| --- | --- | --- | --- | ---: | ---: |']
    for c in cases:
        for s in c['steps']:lines.append(f'| {c["mode"]} | {s["role"]} | {s["query"]} | {s["status"]} | {s["total_hits"]} | {s["anchor_rank"] or "—"} |')
    (args.out/'results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
