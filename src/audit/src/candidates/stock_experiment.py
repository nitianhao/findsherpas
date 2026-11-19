"""Catalog-grounded 50-query availability study and conservative offline reranking."""
from __future__ import annotations
import argparse, concurrent.futures, gzip, json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs,urlparse,urljoin
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from .collection import fetch,nav_links,detail_product
from .contracts import Strict,Link
from .runner import Calls,save,stamp,digest
from .ordinary_search import (ShoppingCase,PlanReview,SYSTEM,PLAN_REVIEW,JUDGE,JUDGE_REVIEW,
    Labels,LabelReviews,evidence_matches,metrics,records_from_html,run_searches)
from .validation import norm
from src.fetcher import fetch_all_outcomes

CATEGORIES={
 'pans':'/koekkenudstyr/gryder-og-stegepander/stegepander',
 'cups':'/borddaekning/krus-og-kopper',
 'glasses':'/borddaekning/glas/vandglas',
 'jugs':'/borddaekning/kander-og-karafler/serveringskander',
 'vases':'/bolig/interioer/vaser',
 'plates':'/borddaekning/tallerkener/middagstallerkener',
 'bowls':'/borddaekning/skaale-og-fade/serverings-og-salatskaale',
 'pots':'/koekkenudstyr/gryder-og-stegepander/gryder',
 'knives':'/koekkenudstyr/koekkenknive-og-sakse/koekkenknive',
 'cutlery':'/borddaekning/bestik/bestiksaet'}
SHAPES=['category','subtype','brand','family','named_product']
class Case(ShoppingCase):
    category:str
class Plan(Strict):
    cases:list[Case]


def collect(out:Path):
    html,_=fetch('https://www.imerco.dk',out/'navigation_capture')
    nav=nav_links(html);save(out/'navigation.json',[x.model_dump() for x in nav])
    observed={urlparse(x.url).path for x in nav}
    if any(path not in observed for path in CATEGORIES.values()):raise ValueError('Category not observed in navigation')
    def one(item):
        category,path=item;html,metadata=fetch('https://www.imerco.dk'+path,out/'category_capture')
        soup=BeautifulSoup(html,'html.parser');cards=[]
        for card in soup.select('div[class*="ProductHit_wrapper"]')[:40]:
            a=card.select_one('a[class*="ProductHit_card"]')
            if not a:continue
            url=urljoin('https://www.imerco.dk',a['href']);pid=parse_qs(urlparse(url).query).get('id',[''])[0]
            brand=card.select_one('[class*="NewProductCard_brand"]');name=card.select_one('[class*="NewProductCard_name"]')
            if not pid or not brand or not name:continue
            cards.append({'id':pid,'brand':brand.get_text(' ',strip=True),'name':name.get_text(' ',strip=True),'url':url,'text':card.get_text(' ',strip=True)[:600]})
        sample=[];seen=set()
        for card in cards:
            key=(card['brand'],card['name'])
            if key not in seen:seen.add(key);sample.append(card)
            if len(sample)==12:break
        if not sample:raise ValueError('No category cards: '+category)
        return category,{'url':'https://www.imerco.dk'+path,'source':metadata,'cards':cards,'sample':sample}
    sources={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for k,v in pool.map(one,CATEGORIES.items()):
            sources[k]=v;save(out/'category_sources.json',sources);print('Collected',k,len(v['cards']),flush=True)
    return sources


def validate_plan(plan:Plan,sources:dict)->list[str]:
    errors=[]
    if len(plan.cases)!=5*len(CATEGORIES):errors.append('Expected exactly 50 cases')
    if len({norm(c.query) for c in plan.cases})!=len(plan.cases):errors.append('Duplicate queries')
    for cat in CATEGORIES:
        if Counter(c.shape for c in plan.cases if c.category==cat)!=Counter(SHAPES):errors.append('Wrong shapes: '+cat)
    for c in plan.cases:
        cards={v['id']:v for v in sources.get(c.category,{}).get('cards',[])}
        if c.id!=c.category+'_'+c.shape:errors.append('Wrong ID: '+c.id)
        if not c.anchor_ids or any(pid not in cards for pid in c.anchor_ids):errors.append('Ungrounded anchor: '+c.id)
        if c.required_brand and norm(c.required_brand) not in norm(c.query):errors.append('Hidden brand: '+c.id)
        if c.required_family and norm(c.required_family) not in norm(c.query):errors.append('Hidden family: '+c.id)
        if not 2<=len(c.query)<=100:errors.append('Invalid query length: '+c.id)
    return errors


def draft(out:Path,calls:Calls):
    sources=json.loads((out/'category_sources.json').read_text());all_cases=[];all_reviews=[]
    for start in [0,5]:
        selected=list(CATEGORIES)[start:start+5]
        inventory={k:{'url':sources[k]['url'],'products':sources[k]['sample']} for k in selected}
        instruction='''Draft exactly 25 DISTINCT short natural Danish shopping searches, FIVE for each supplied category.
Shapes exactly category, subtype, brand, family, named_product, one each per category. IDs category_shape.
Ground anchor_ids in supplied cards. Use ordinary product, material or subtype words. No artificial typos,
measurements, deadlines, negations or elaborate constraints. No stock requirement in query. Named_product
must identify a real observed brand + named series/product, accepting unspecified sizes, colors and packs.
Family and named_product should use different series where inventory supports it. Brand and family fields
must be explicit substrings of query, not implied. No invented products or shopper demand claims.
Goal must equal query VERBATIM: do not interpret broad terms as secretly narrower shopping needs.
Do not choose queries based on suspected stock problems. Cards include availability as evidence, not a
selection objective. Diverse queries must be grounded in the independently observed inventory.'''
        plan=calls.call('stock_plan_'+str(start),inventory,Plan,instruction,max_tokens=6500)
        for attempt in range(2):
            # Canonical query-only goal prevents extra inferred constraints from entering result judging.
            for c in plan.cases:c.goal=c.query
            review=calls.call(f'stock_plan_review_{start}_{attempt}',{'inventory':inventory,'plan':plan.model_dump()},PlanReview,
                PLAN_REVIEW.replace('all 30','all 25').replace('six shapes','five shapes')+'''\nRequired shapes: category, subtype, brand, family, named_product. Goal is the literal query.
Reject unnatural wording and constraints not stated by the query. Never narrow karaffel to water-only,
krus to handled-only, or stegepande to single-item packaging without explicit query evidence.''')
            errs=[]
            if len(plan.cases)!=25:errs.append('Expected 25 cases')
            for cat in selected:
                if Counter(c.shape for c in plan.cases if c.category==cat)!=Counter(SHAPES):errs.append('Wrong shapes '+cat)
            for c in plan.cases:
                cards={v['id'] for v in sources.get(c.category,{}).get('cards',[])}
                if c.category not in selected or not c.anchor_ids or any(pid not in cards for pid in c.anchor_ids):errs.append('Ungrounded '+c.id)
                ds=[d for d in review.decisions if d.case_id==c.id]
                if len(ds)!=1 or not ds[0].approved:errs.append(c.id+': '+str([d.reason for d in ds]))
                if c.required_brand and norm(c.required_brand) not in norm(c.query):errs.append('Hidden brand '+c.id)
                if c.required_family and norm(c.required_family) not in norm(c.query):errs.append('Hidden family '+c.id)
            if not errs:break
            save(out/f'plan_rejections_{start}_{attempt}.json',{'plan':plan.model_dump(),'errors':errs})
            if attempt:raise ValueError(str(errs))
            plan=calls.call('stock_plan_repair_'+str(start),{'inventory':inventory,'plan':plan.model_dump(),'errors':errs},Plan,instruction,max_tokens=6500)
        all_cases.extend(plan.cases);all_reviews.extend(d.model_dump() for d in review.decisions)
    plan=Plan(cases=all_cases);errors=validate_plan(plan,sources)
    if errors:raise ValueError(str(errors))
    save(out/'frozen_plan.json',{'created_at':stamp(),'cases':plan.model_dump()['cases'],'review':all_reviews,'inventory_hash':digest(sources),'scope':'Fifty natural queries, not measured demand; frozen before search capture.'})


def evaluate(out:Path,calls:Calls):
    plan=Plan.model_validate({'cases':json.loads((out/'frozen_plan.json').read_text())['cases']})
    outcomes=json.loads((out/'outcomes.json').read_text());contexts=json.loads((out/'result_contexts.json').read_text())
    final=[];audit=[]
    def batch_run(start):
        # Disjoint journals and fixed quotas bound aggregate concurrency to 70 calls / $8.
        batch_index=start//2
        calls=Calls(out/"calls"/f"batch_{batch_index:02d}",max_calls=3 if batch_index<10 else 2,max_usd=.28,system=SYSTEM)
        batch_final=[]
        batch=plan.cases[start:start+2];payload=[];pairs={}
        for c in batch:
            products=[]
            for r in outcomes[c.query]['results']:
                pid=parse_qs(urlparse(r['url']).query).get('id',[''])[0]
                ctx=contexts[c.query].get(pid,{}).get('context','')
                if ctx:products.append({'product_id':pid,'context':ctx});pairs[(c.id,pid)]=ctx
            payload.append({'case':c.model_dump(),'products':products})
        instruction=JUDGE+'''\nThe query is the entire shopper requirement. Do not impose narrower beverage, handle,
packaging or material requirements than it states. Merchant labels termokrus may include stoneware.
A matching product name is positive type evidence. Exactly one label for every listed pair; do not skip
pairs that repeat across queries. Source quotes may be separate exact field lines; every line must exist.'''
        labels=calls.call('stock_labels_'+str(start),{'cases':payload},Labels,instruction,max_tokens=6000)
        expected=set(pairs)
        counts=Counter((x.case_id,x.product_id) for x in labels.labels)
        missing=[key for key in expected if counts[key]!=1]
        if missing and batch_index<10:
            repair_payload=[{'case':next(c.model_dump() for c in batch if c.id==cid),'product_id':pid,'context':pairs[(cid,pid)]} for cid,pid in sorted(missing)]
            repaired=calls.call('stock_missing_'+str(start),{'pairs':repair_payload},Labels,instruction,max_tokens=4500)
            labels=Labels(labels=[x for x in labels.labels if (x.case_id,x.product_id) not in missing]+repaired.labels)
        review=calls.call('stock_review_'+str(start),{'cases':payload,'labels':labels.model_dump()},LabelReviews,
            JUDGE_REVIEW+'\nLiteral query controls: no hidden requirements from category scope. Do not require single-item packaging or handles unless stated. Missing/duplicate judgments remain unknown.',max_tokens=5000)
        batch_audit={'start':start,'labels':labels.model_dump(),'review':review.model_dump()}
        for c in batch:
            rows=[]
            for r in outcomes[c.query]['results']:
                pid=parse_qs(urlparse(r['url']).query).get('id',[''])[0];rec=contexts[c.query].get(pid,{})
                ls=[x for x in labels.labels if x.case_id==c.id and x.product_id==pid];rs=[x for x in review.decisions if x.case_id==c.id and x.product_id==pid]
                okay=len(ls)==1 and len(rs)==1 and rs[0].approved and evidence_matches(pairs.get((c.id,pid),''),ls[0].evidence)
                label=ls[0].label if okay else 'unknown'
                if label=='exact' and c.required_brand and norm(rec.get('fields',{}).get('brand',''))!=norm(c.required_brand):label='unknown';okay=False
                rows.append({'rank':r['rank'],'product_id':pid,'title':r['title'],'url':r['url'],'label':label,'review_accepted':okay,
                    'reason':ls[0].reason if len(ls)==1 else 'Missing/duplicate label','evidence':ls[0].evidence if len(ls)==1 else '',
                    'review_reasons':[x.reason for x in rs],'online_stock':rec.get('online_stock','unknown'),'family_id':rec.get('family_id')})
            batch_final.append({'case':c.model_dump(),'fetch_status':outcomes[c.query]['status'],'total_hits':outcomes[c.query]['total_hits'],'rows':rows,'metrics':metrics(c.model_dump(),rows)})
        return batch_final,batch_audit
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for batch_final,batch_audit in pool.map(batch_run,range(0,len(plan.cases),2)):
            final.extend(batch_final);audit.append(batch_audit)
            save(out/'labels_and_reviews.json',audit);save(out/'evaluated_cases.json',final)
            print('Evaluated',len(final),'/ 50',flush=True)
    records=[json.loads(f.read_text()) for f in (out/'calls').rglob('*.json')]
    cost=calls.summary();cost.update(requests=len(records),estimated_usd=round(sum(r.get('estimated_usd',r['reserved_usd']) for r in records),6),reserved_usd=round(sum(r['reserved_usd'] for r in records),6))
    save(out/'evaluation.json',{'completed_at':stamp(),'cases':final,'cost':cost})


def rerank(case:dict,rows:list[dict])->list[dict]:
    """Stable availability preference inside reviewed-exact, known-stock blocks only.

    Named lookups are pinned. Ambiguous, weaker, unreviewed and unknown-stock rows
    are barriers; no candidate crosses them. This uses offline judged labels, not a
    production-ready relevance classifier, and never introduces a new product.
    """
    if case['shape']=='named_product':return list(rows)
    result=[];block=[]
    def flush():
        result.extend(r for r in block if r['online_stock']=='available_online')
        result.extend(r for r in block if r['online_stock']=='not_available_online')
        block.clear()
    for r in rows:
        if r['label']=='exact' and r.get('review_accepted') is True and r['online_stock'] in {'available_online','not_available_online'}:block.append(r)
        else:flush();result.append(r)
    flush();return result


def simulate(out:Path):
    evaluation=json.loads((out/'evaluation.json').read_text());cases=[]
    for c in evaluation['cases']:
        before=c['rows'];after=rerank(c['case'],before)
        after_ranked=[dict(r,rank=i+1,original_rank=r['rank']) for i,r in enumerate(after)]
        cases.append({'case':c['case'],'before':before,'after':after_ranked,'before_metrics':metrics(c['case'],before),'after_metrics':metrics(c['case'],after_ranked),
            'available_exact_top3_before':sum(r['label']=='exact' and r['online_stock']=='available_online' for r in before[:3]),
            'available_exact_top3_after':sum(r['label']=='exact' and r['online_stock']=='available_online' for r in after[:3]),
            'changed': [r['product_id'] for r in before]!=[r['product_id'] for r in after],
            'top1_changed':bool(before and before[0]['product_id']!=after[0]['product_id']),
            'relevance_sequence_preserved':[r['label'] for r in before]==[r['label'] for r in after],
            'same_products':Counter(r['product_id'] for r in before)==Counter(r['product_id'] for r in after)})
    summary={'completed_at':stamp(),'queries':len(cases),'fetch_status':dict(Counter(c['fetch_status'] for c in evaluation['cases'])),
        'stock_ordering_before':sum(c['before_metrics']['stock_ordering_flag'] for c in cases),
        'stock_ordering_after':sum(c['after_metrics']['stock_ordering_flag'] for c in cases),
        'available_exact_top3_before':sum(c['available_exact_top3_before'] for c in cases),
        'available_exact_top3_after':sum(c['available_exact_top3_after'] for c in cases),
        'ranking_changed':sum(c['changed'] for c in cases),'top1_changed':sum(c['top1_changed'] for c in cases),
        'relevance_sequence_preserved':all(c['relevance_sequence_preserved'] for c in cases),'same_products':all(c['same_products'] for c in cases),
        'named_lookups':sum(c['case']['shape']=='named_product' for c in cases),
        'named_lookups_changed':sum(c['changed'] for c in cases if c['case']['shape']=='named_product'),
        'raw_top1_unavailable':sum(bool(c['before']) and c['before'][0]['online_stock']=='not_available_online' for c in cases),
        'label_counts':dict(Counter(r['label'] for c in cases for r in c['before'])),
        'model_cost':evaluation['cost'],'scope':'Offline replay of first ten, judged relevance used as an input; not an independent relevance uplift test. No conversion impact measured.'}
    save(out/'simulation.json',{'summary':summary,'cases':cases});print(json.dumps(summary,ensure_ascii=False,indent=2))



def purchase_stock(purchase_text:str)->str:
    """Classify only explicit online purchase-area status; store stock is separate."""
    n=norm(purchase_text)
    if any(x in n for x in ['kommer snart online','udgået online','ikke på lager online','udsolgt online']):return 'not_available_online'
    if 'læg i kurv' in n and 'afsendes' in n:return 'available_online'
    return 'unknown'


def verify(out:Path):
    simulation=json.loads((out/'simulation.json').read_text());selected={}
    # Verify every top-one contrast, plus one moved stock contrast for lower-order changes.
    for c in simulation['cases']:
        chosen=[]
        if c['top1_changed']:chosen=[c['before'][0],c['after'][0]]
        elif c['changed']:
            before_rank={r['product_id']:r['rank'] for r in c['before']}
            promoted=next((r for r in c['after'] if r['original_rank']>r['rank'] and r['online_stock']=='available_online'),None)
            demoted=next((r for r in c['after'] if r['original_rank']<r['rank'] and r['online_stock']=='not_available_online'),None)
            if promoted and demoted:chosen=[demoted,promoted]
        if c['before'] and c['before'][0]['online_stock']=='unknown':chosen.append(c['before'][0])
        for row in chosen:selected[row['product_id']]=Link(id=row['product_id'],url=row['url'],text=row['title'])
    def one(link):
        try:
            html,metadata=fetch(link.url,out/'verification_capture');p=detail_product(link,html,metadata,'stock ranking verification')
            # Limit status to the purchase area, before description/recommendations.
            purchase=p.text.split('Beskrivelse')[0]
            status=purchase_stock(purchase)
            return link.id,{'status':'ok','product':p.model_dump(),'online_stock':status,'purchase_text':purchase}
        except Exception as e:return link.id,{'status':'error','error_type':type(e).__name__}
    verified={};save(out/'verified_examples.json',verified)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for pid,v in pool.map(one,selected.values()):verified[pid]=v;save(out/'verified_examples.json',verified);print('Verified',pid,v['status'],v.get('online_stock'),flush=True)
    queries=[c['case']['query'] for c in simulation['cases'] if c['before_metrics']['stock_ordering_flag']]
    # Also repeat three named controls, chosen deterministically, regardless of stock.
    queries+= [c['case']['query'] for c in simulation['cases'] if c['case']['shape']=='named_product'][:3]
    # Historical diagnostics are separate from the frozen fifty-query prevalence cohort.
    queries=list(dict.fromkeys(queries+['vandglas','drikkeglas','vase']))
    history={}
    def emit(o):history[o.query]={'observed_at':stamp(),'outcome':o.model_dump(mode='json')};save(out/'rechecks.json',history)
    fetch_all_outcomes(queries,'https://www.imerco.dk/search?query={}',max_results=10,evidence_dir=str(out/'evidence/recheck'),on_outcome=emit,light=True)


def main():
    load_dotenv(Path(__file__).resolve().parents[2]/'.env',override=True)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--stage',choices=['collect','plan','search','evaluate','simulate','verify'],required=True);a=p.parse_args();out=a.out;out.mkdir(exist_ok=True,parents=True)
    calls=Calls(out/'calls',max_calls=10,max_usd=1,system=SYSTEM)
    if a.stage=='collect':collect(out)
    elif a.stage=='plan':
        if (out/'outcomes.json').exists():raise ValueError('Cannot change plan after search')
        draft(out,calls)
    elif a.stage=='search':
        if (out/'outcomes.json').exists():raise ValueError('Existing observations; use a new experiment')
        run_searches(Plan.model_validate({'cases':json.loads((out/'frozen_plan.json').read_text())['cases']}),out)
    elif a.stage=='evaluate':evaluate(out,calls)
    elif a.stage=='simulate':simulate(out)
    else:verify(out)

if __name__=='__main__':main()
