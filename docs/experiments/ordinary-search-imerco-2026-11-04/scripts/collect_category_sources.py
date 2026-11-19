from pathlib import Path
import concurrent.futures,json
from bs4 import BeautifulSoup
from src.candidates.collection import fetch
from src.candidates.runner import save,stamp
base='https://www.imerco.dk';out=Path('reports/imerco_dk/ordinary_20261104');out.mkdir(exist_ok=True)
categories={'pans':'/koekkenudstyr/gryder-og-stegepander/stegepander','cups':'/borddaekning/krus-og-kopper','glasses':'/borddaekning/glas/vandglas','jugs':'/borddaekning/kander-og-karafler/serveringskander','vases':'/bolig/interioer/vaser'}
def get(item):
 category,path=item;html,meta=fetch(base+path,out/'category_capture');soup=BeautifulSoup(html,'html.parser');cards=[]
 for c in soup.select('div[class*="ProductHit_wrapper"]')[:40]:
  a=c.select_one('a[class*="ProductHit_card"]');brand=c.select_one('[class*="NewProductCard_brand"]');name=c.select_one('[class*="NewProductCard_name"]')
  if not a:continue
  from urllib.parse import parse_qs,urlparse,urljoin
  url=urljoin(base,a['href']);pid=parse_qs(urlparse(url).query).get('id',[''])[0]
  cards.append({'id':pid,'brand':brand.get_text(' ',strip=True) if brand else '', 'name':name.get_text(' ',strip=True) if name else '', 'url':url,'text':c.get_text(' ',strip=True)[:450]})
 # Deterministically sample distinct brand/name pairs; no search outcomes used.
 sample=[];seen=set()
 for c in cards:
  key=(c['brand'],c['name'])
  if key not in seen:seen.add(key);sample.append(c)
  if len(sample)==12:break
 return category,{'url':base+path,'source':meta,'cards':cards,'sample':sample}
data={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for category,value in pool.map(get,categories.items()):data[category]=value;save(out/'category_sources.json',data);print(category,len(value['cards']),len(value['sample']),flush=True)
save(out/'collection.json',{'completed_at':stamp(),'categories':5,'scope':'Independent category inventory, not site-search logs or demand estimates.'})
