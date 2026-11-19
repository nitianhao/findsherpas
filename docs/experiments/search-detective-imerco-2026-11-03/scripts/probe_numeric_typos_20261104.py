"""Read-only query-level counterfactual using the storefront's own public search context.
No settings endpoints are used. Client-token/header values are never printed or saved.
"""
from pathlib import Path
from urllib.parse import parse_qs,urlencode,quote
import gzip,json,requests
from bs4 import BeautifulSoup
from src.candidates.runner import save,stamp
from src.candidates.unit_investigation import extract_public_search
p=Path('reports/imerco_dk/unit_investigation_20261104')
f=next((p/'evidence/first').glob('kande-1600-ml-*.html.gz'))
d=json.loads(BeautifulSoup(gzip.decompress(f.read_bytes()),'html.parser').select_one('script#__NEXT_DATA__').string)
config=d['runtimeConfig'];block=d['props']['pageProps']['page']['data']['plpResult']['serverState']['initialResults']['product-list'];raw=block['results'][0]
app=config['NEXT_PUBLIC_ALGOLIA_APP'];token=config['NEXT_PUBLIC_ALGOLIA_TOKEN'];index=block['state']['index']
if not isinstance(app,str) or not app.isalnum():raise SystemExit('Unexpected public app identifier format')
endpoint='https://'+app+'-dsn.algolia.net/1/indexes/'+quote(index,safe='')+'/query'
base=parse_qs(raw['params'])
for k in ['userToken','authenticatedUserToken','analyticsTags','queryID']:base.pop(k,None)
results=[]
for label,q,override in [('public_query_control','kande 1600 ml',None),('numeric_typos_disabled','kande 1600 ml',False),('canonical_units_numeric_typos_disabled','kande 1,6 L',False)]:
 params={**base,'query':[q],'page':['0'],'hitsPerPage':['40'],'getRankingInfo':['true'],'analytics':['false'],'clickAnalytics':['false']}
 if override is not None:params['allowTyposOnNumericTokens']=['false']
 response=requests.post(endpoint,headers={'X-Algolia-Application-Id':app,'X-Algolia-API-Key':token,'Content-Type':'application/json'},json={'params':urlencode(params,doseq=True)},timeout=25,allow_redirects=False)
 if response.status_code!=200:
  results.append({'label':label,'query':q,'http_status':response.status_code,'status':'unavailable'});break
 data=response.json()
 wrapper={'runtimeConfig':{'NEXT_PUBLIC_ALGOLIA_APP':True},'props':{'pageProps':{'page':{'data':{'plpResult':{'serverState':{'initialResults':{'product-list':{'state':{'numericRefinements':{}},'results':[data]}}}}}}}}}
 sanitized=extract_public_search('<script id="__NEXT_DATA__" type="application/json">'+json.dumps(wrapper)+'</script>')
 results.append({'label':label,'query':q,'request_allow_numeric_typos':override,'observed_at':stamp(),'http_status':200,'search':sanitized})
 print(label,'hits',sanitized['total_hits'],'capacities',[r['capacity_text'] for r in sanitized['records'][:5]],flush=True)
 if label=='public_query_control' and sanitized['total_hits']!=raw['nbHits']:
  results[-1]['control_mismatch']=True;break
save(p/'numeric_typo_counterfactual.json',{'method':'Read-only searches using the same public index/visibility filters; no settings read or written. Analytics disabled for these diagnostic requests.','results':results})
