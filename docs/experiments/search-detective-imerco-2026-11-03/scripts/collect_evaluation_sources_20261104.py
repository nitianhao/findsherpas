from pathlib import Path
import json,concurrent.futures
from urllib.parse import parse_qs,urlparse
from src.candidates.collection import fetch,detail_product
from src.candidates.contracts import Link
from src.candidates.runner import save,stamp,digest
exp=Path('../../docs/experiments/search-detective-imerco-2026-11-03')
out=Path('reports/imerco_dk/evaluation_20261104');out.mkdir(exist_ok=True)
results=json.loads((exp/'search-execution/outcomes.json').read_text())
links={}
for data in results.values():
 for r in data['results']:
  pid=parse_qs(urlparse(r['url']).query)['id'][0]
  links[pid]=Link(id=pid,url=r['url'],text=r['title'])
def get(link):
 try:
  html,meta=fetch(link.url,out/'detail_capture')
  p=detail_product(link,html,meta,'observed search result')
  return link.id,{'status':'ok','product':p.model_dump()}
 except Exception as e:return link.id,{'status':'error','error_type':type(e).__name__,'url':link.url}
collected={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for pid,result in pool.map(get,links.values()):
  collected[pid]=result;save(out/'product_sources.json',collected)
  print(f'Product {len(collected)}/{len(links)} {pid}: {result["status"]}',flush=True)
save(out/'collection_manifest.json',{'completed_at':stamp(),'unique_products':len(links),'input_sha256':digest((exp/'search-execution/outcomes.json').read_text()),'errors':sum(d['status']!='ok' for d in collected.values()),'note':'Nov 3 saved search ordering; product details verified Nov 4. No searches rerun.'})
