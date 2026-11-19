from pathlib import Path
import json,concurrent.futures
from urllib.parse import parse_qs,urlparse
from src.candidates.collection import fetch,detail_product
from src.candidates.contracts import Link
from src.candidates.runner import save
p=Path('reports/imerco_dk/ordinary_20261104');outs=json.load(open(p/'outcomes.json'));contexts=json.load(open(p/'result_contexts.json'));selected={}
for q in ['vandglas','drikkeglas','vase']:
 rows=outs[q]['results'];choices=[rows[0]]
 for r in rows[1:]:
  pid=parse_qs(urlparse(r['url']).query)['id'][0]
  if contexts[q][pid]['online_stock']=='available_online':choices.append(r);break
 for r in choices:
  pid=parse_qs(urlparse(r['url']).query)['id'][0];selected[pid]=Link(id=pid,url=r['url'],text=r['title'])
# Independently selected known pan to verify the zero-result query is satisfiable.
sources=json.load(open(p/'category_sources.json'));pan=next(c for c in sources['pans']['cards'] if 'stegepande' in c['name'].casefold() and 'på lager online' in c['text'].casefold())
selected[pan['id']]=Link(id=pan['id'],url=pan['url'],text=pan['brand']+' '+pan['name'])
# Verify examples of the concentrated coffee-cup family, without changing the query plan.
for r in outs['kaffekop']['results'][:4]:
 pid=parse_qs(urlparse(r['url']).query)['id'][0];selected[pid]=Link(id=pid,url=r['url'],text=r['title'])
# Explicitly named thermal cup whose functionality was uncertain to one model pass.
for r in outs['termokrus']['results']:
 if r['title'].startswith('RAW'):
  pid=parse_qs(urlparse(r['url']).query)['id'][0];selected[pid]=Link(id=pid,url=r['url'],text=r['title']);break
# The large cookware bundle surfaced by the steel-pan search.
r=outs['rustfri stegepande']['results'][0];pid=parse_qs(urlparse(r['url']).query)['id'][0];selected[pid]=Link(id=pid,url=r['url'],text=r['title'])
def get(link):
 try:
  html,m=fetch(link.url,p/'verification_capture');product=detail_product(link,html,m,'ordinary-search verification')
  return link.id,{'status':'ok','product':product.model_dump()}
 except Exception as e:return link.id,{'status':'error','error_type':type(e).__name__}
verified={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for pid,data in pool.map(get,selected.values()):verified[pid]=data;save(p/'verified_examples.json',verified);print(pid,data['status'],flush=True)
