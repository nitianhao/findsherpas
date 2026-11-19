import httpx,json,concurrent.futures
from pathlib import Path
from bs4 import BeautifulSoup
base='https://www.imerco.dk'
out=Path('reports/imerco_dk/candidates_20261103');out.mkdir(exist_ok=True)
paths=['/borddaekning/krus-og-kopper/krus-og-kopper-uden-hank','/borddaekning/skaale-og-fade/serverings-og-salatskaale','/borddaekning/kander-og-karafler/serveringskander','/bolig/interioer/vaser','/bolig/moebler/borde','/koekkenudstyr/gryder-og-stegepander/stegepander','/borddaekning/glas/vandglas']
def get(path):
 r=httpx.get(base+path,follow_redirects=True,timeout=40);s=BeautifulSoup(r.text,'html.parser')
 cards=s.select('div[class*="ProductHit_wrapper"]')
 data={'category':path,'status':r.status_code,'cards':[{'text':c.get_text(' ',strip=True),'url':base+a['href'] if a['href'].startswith('/') else a['href']} for c in cards if (a:=c.select_one('a[class*="ProductHit_card"]'))]}
 (out/(path.split('/')[-1]+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2))
 return data
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for d in ex.map(get,paths):
  print('\nCATEGORY',d['category'],d['status'],len(d['cards']))
  for c in d['cards']: print(c['text'][:300],c['url'])
