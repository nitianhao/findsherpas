"""Controlled volume-query diagnosis using public storefront responses; no store writes."""
from __future__ import annotations
import argparse
import gzip
import json
import logging
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from bs4 import BeautifulSoup
from .runner import save,stamp,digest
from .collection import fetch,detail_product
from .contracts import Link
from src.fetcher import fetch_all_outcomes

VOLUME=re.compile(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(milliliter|millilitre|centiliter|deciliter|litre|liter|ml|cl|dl|l)(?![\w])',re.I)
FACTORS={'l':1000,'liter':1000,'litre':1000,'dl':100,'deciliter':100,'cl':10,'centiliter':10,'ml':1,'milliliter':1,'millilitre':1}


def parse_volume(text: str) -> Decimal | None:
    if re.search(r'\d\s*[/–-]\s*\d',text) or re.search(r'[<>≤≥]|\b(?:under|over|mindst|højst|minimum|maximum|at least|at most|less than|more than|up to)\b',text,re.I):return None
    matches=list(VOLUME.finditer(text))
    if len(matches)!=1:return None
    value=Decimal(matches[0].group(1).replace(',','.'))*FACTORS[matches[0].group(2).lower()]
    return value if value.is_finite() and value>0 else None


def plain(value: Decimal,comma=False) -> str:
    text=format(value.normalize(),'f')
    return text.replace('.',',') if comma else text


def plan_variants(base: str,ml: Decimal,brand_name: str) -> list[dict]:
    liters=ml/1000
    variants=[
        ('comma_symbol',f'{base} {plain(liters,True)} L','equivalent_volume'),
        ('dot_symbol',f'{base} {plain(liters)} L','equivalent_volume'),
        ('comma_word',f'{base} {plain(liters,True)} liter','equivalent_volume'),
        ('dot_word',f'{base} {plain(liters)} liter','equivalent_volume'),
        ('compact_liter',f'{base} {plain(liters,True)}L','equivalent_volume'),
        ('centiliters',f'{base} {plain(ml/10)} cl','equivalent_volume'),
        ('milliliters',f'{base} {plain(ml)} ml','equivalent_volume'),
        ('compact_ml',f'{base} {plain(ml)}ml','equivalent_volume'),
        ('milliliter_word',f'{base} {plain(ml)} milliliter','equivalent_volume'),
        ('deciliters',f'{base} {plain(ml/100)} dl','equivalent_volume'),
        ('integer_only',f'{base} {plain(ml)}','token_ablation'),
        ('decimal_only',f'{base} {plain(liters,True)}','token_ablation'),
        ('unit_only',f'{base} ml','token_ablation'),
        ('nearby_ml',f'{base} {plain(ml-100)} ml','nearby_volume_control'),
        ('nearby_l',f'{base} {plain((ml-100)/1000,True)} L','nearby_volume_control'),
        ('brand_only',brand_name,'brand_control'),
        ('brand_l',f'{brand_name} {plain(liters,True)} L','brand_control'),
        ('brand_ml',f'{brand_name} {plain(ml)} ml','brand_control'),
    ]
    rows=[];seen=set()
    for identifier,query,family in variants:
        if query not in seen:
            seen.add(query);rows.append({'id':identifier,'query':query,'family':family})
    return rows


def extract_public_search(html: str,expected_query: str | None = None) -> dict:
    soup=BeautifulSoup(html,'html.parser');node=soup.select_one('script#__NEXT_DATA__')
    if not node:return {'available':False,'reason':'No public Next.js search state'}
    data=json.loads(node.string or node.get_text())
    blocks=data.get('props',{}).get('pageProps',{}).get('page',{}).get('data',{}).get('plpResult',{}).get('serverState',{}).get('initialResults',{})
    block=blocks.get('product-list')
    if not isinstance(block,dict) or not block.get('results') or 'hits' not in block['results'][0]:
        return {'available':False,'reason':'No scoped product-list query response'}
    raw=block['results'][0]
    if expected_query is not None and ' '.join(raw.get('query','').casefold().split())!=' '.join(expected_query.casefold().split()):
        return {'available':False,'reason':'Public result query does not match the observed search'}
    records=[]
    for hit in raw['hits']:
        volume=parse_volume(str(hit.get('cust_capacity','')))
        highlights=[]
        for key,value in hit.get('_highlightResult',{}).items():
            if not isinstance(value,dict) or not value.get('matchedWords'):continue
            if key not in {'cust_synopsis','name','pageTitle','cust_webSearchWords'}:continue
            content=value.get('value','')
            snippets=[content[max(0,m.start()-25):m.end()+35] for m in re.finditer(r'<em>.*?</em>',content)][:6]
            highlights.append({'field':key,'matched_words':value['matchedWords'],'snippets':snippets})
        records.append({'product_id':str(hit.get('objectID','')),'name':hit.get('name'),
            'capacity_text':hit.get('cust_capacity'),'capacity_spec_text':hit.get('cust_spec_capacity'),
            'capacity_ml':plain(volume) if volume is not None else None,'url':hit.get('url'),
            'nb_typos':hit.get('_rankingInfo',{}).get('nbTypos'),'highlights':highlights})
    params=parse_qs(raw.get('params',''))
    return {'available':True,'algolia_config_present':any(k.startswith('NEXT_PUBLIC_ALGOLIA_') for k in data.get('runtimeConfig',{})),
        'query':raw.get('query'),'parsed_query':raw.get('parsedQuery'),'total_hits':raw.get('nbHits'),
        'complete_returned_page':len(records)>=(raw.get('nbHits') or 0),
        'numeric_refinements':block.get('state',{}).get('numericRefinements',{}),
        'query_parameters':{k:params[k] for k in ['query','numericFilters','typoTolerance','allowTyposOnNumericTokens','queryType','removeWordsIfNoResults'] if k in params},
        'records':records}


def parse_saved(out: Path,history: dict,plan: list[dict],ml: Decimal,anchor: str) -> list:
    rows=[]
    for variant in plan:
        q=variant['query'];observations=[]
        for observed in history[q]:
            o=observed['outcome']
            capture=next((f for f in (out/'evidence').rglob('*.html.gz') if str(f) in o.get('evidence','')),None)
            public=extract_public_search(gzip.decompress(capture.read_bytes()).decode(),expected_query=q) if capture else {'available':False}
            if public.get('available'):
                records=public['records'];qual=[h for h in records if h['capacity_ml'] is not None and Decimal(h['capacity_ml'])==ml]
                wrong=[h for h in records if h['capacity_ml'] is not None and Decimal(h['capacity_ml'])!=ml]
                stats={'matching_capacity':len(qual),'wrong_capacity':len(wrong),'unknown_capacity':sum(h['capacity_ml'] is None for h in records),
                       'anchor_rank':next((i for i,h in enumerate(records,1) if h['product_id']==anchor),None)}
            else:stats={}
            observations.append({'observed_at':observed['observed_at'],'fetch_status':o['status'],'public_search':public,**stats})
        rows.append({**variant,'observations':observations})
    return rows


def replay_fix(rows: list,ml: Decimal,original_id: str,expanded_id: str,extra_ids: tuple[str,...]=()) -> dict:
    by_id={row['id']:row for row in rows};original=by_id[original_id]['observations'][-1]['public_search'];expanded=by_id[expanded_id]['observations'][-1]['public_search']
    union={}
    retrievals=[original,expanded]+[by_id[key]['observations'][-1]['public_search'] for key in extra_ids]
    for source in retrievals:
        for record in source.get('records',[]):union.setdefault(record['product_id'],record)
    matches=[r for r in union.values() if r['capacity_ml'] is not None and Decimal(r['capacity_ml'])==ml]
    unknown=[r for r in union.values() if r['capacity_ml'] is None]
    return {'target_capacity_ml':plain(ml),'original_query':original.get('query'),'expanded_query':expanded.get('query'),'retrieval_queries':[r.get('query') for r in retrievals],
        'input_records':len(union),'eligible_records':matches,'unknown_records':unknown,
        'rejected_wrong_capacity':len(union)-len(matches)-len(unknown),
        'scope':'Local replay of captured candidate records, not a production change or complete catalog recall measurement.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--experiment',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--analyze-only',action='store_true')
    args=parser.parse_args();exp=args.experiment;out=args.out
    if out.exists() and any(out.iterdir()) and not args.analyze_only:parser.error('Use a new output directory or --analyze-only')
    suites=json.loads((exp/'query-suites/query_suites.json').read_text())
    case=next(c for c in suites['cases'] if c['mode']=='unit_conversion')
    candidates=json.loads((exp/'runs/llm_candidates_live_evidence_v3_20261103/products.json').read_text())
    product=next(p for p in candidates if p['id']==case['anchor_product_id'])
    ml=parse_volume(case['steps'][0]['query'])
    if ml is None or ml!=parse_volume(case['steps'][1]['query']):parser.error('Source case does not establish equivalent volumes')
    base=VOLUME.sub('',case['steps'][0]['query']).strip()
    plan=plan_variants(base,ml,product['name'])
    if args.analyze_only:
        manifest=json.loads((out/'manifest.json').read_text())
        if manifest['source_suite_sha256']!=digest((exp/'query-suites/query_suites.json').read_text()):parser.error('Source suite changed')
        if digest(json.loads((out/'query_plan.json').read_text()))!=digest(plan):parser.error('Query plan changed; use a new run')
        from .contracts import Product
        anchor=Product.model_validate(json.loads((out/'anchor.json').read_text()))
        history=json.loads((out/'outcome_history.json').read_text())
        retry=[]
    else:
        save(out/'query_plan.json',plan)
        html,meta=fetch(product['url'],out/'anchor_refresh')
        anchor=detail_product(Link(id=product['id'],url=product['url'],text=product['name']),html,meta,'unit diagnostic anchor')
        save(out/'anchor.json',anchor.model_dump())
        save(out/'manifest.json',{'created_at':stamp(),'source_suite_sha256':digest((exp/'query-suites/query_suites.json').read_text()),
            'target_ml':plain(ml),'anchor_id':anchor.id,'queries':len(plan),'scope':'Read-only storefront queries; no private settings fetched and no store changes.'})
        history={r['query']:[] for r in plan}
        def emit(o):
            history[o.query].append({'observed_at':stamp(),'outcome':o.model_dump(mode='json')});save(out/'outcome_history.json',history)
        logging.basicConfig(level=logging.INFO)
        fetch_all_outcomes(list(history),'https://www.imerco.dk/search?query={}',max_results=10,
                           evidence_dir=str(out/'evidence/first'),on_outcome=emit,light=True)
        repeated={'comma_symbol','dot_symbol','comma_word','centiliters','milliliters','compact_ml','brand_l','brand_ml'}
        retry=[r['query'] for r in reversed(plan) if r['id'] in repeated]
        retry=[plan[0]['query']]+[q for q in retry if q!=plan[0]['query']]
        if any(items and items[-1]['outcome']['status']=='blocked' for items in history.values()):retry=[]
        if retry:
            fetch_all_outcomes(retry,'https://www.imerco.dk/search?query={}',max_results=10,
                               evidence_dir=str(out/'evidence/recheck'),on_outcome=emit,light=True)
    rows=parse_saved(out,history,plan,ml,anchor.id);save(out/'query_findings.json',rows)
    fixes=[replay_fix(rows,ml,'milliliters','comma_word'),replay_fix(rows,ml,'milliliters','comma_word',('centiliters','deciliters')),replay_fix(rows,ml-100,'nearby_ml','nearby_l')]
    save(out/'local_fix_replay.json',fixes)
    lines=['# Controlled unit-query investigation\n','Whole first response page inspected from public Algolia hit records; this is not necessarily the full catalog.\n',
           f'| Query | Hits | {plain(ml)}-ml reference matches | Other known volumes | Unknown | Anchor rank | Observations |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in rows:
        obs=row['observations'][-1];lines.append(f'| {row["query"]} | {obs["public_search"].get("total_hits")} | {obs.get("matching_capacity")} | {obs.get("wrong_capacity")} | {obs.get("unknown_capacity")} | {obs.get("anchor_rank") or "—"} | {len(row["observations"])} |')
    (out/'results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'queries':len(plan),'rechecked':len(retry),'target_ml':plain(ml),'local_replay':[{'target_ml':r['target_capacity_ml'],'input_records':r['input_records'],'eligible':len(r['eligible_records']),'rejected':r['rejected_wrong_capacity'],'unknown':len(r['unknown_records'])} for r in fixes]},indent=2))

if __name__=='__main__':main()
