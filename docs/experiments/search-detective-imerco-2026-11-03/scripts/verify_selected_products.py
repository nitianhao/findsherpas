import httpx,json,concurrent.futures,re
from pathlib import Path
from bs4 import BeautifulSoup
p=Path('reports/imerco_dk/candidates_20261103')
ids=['100347058','100353730','100408047','100437750','100465402','100404522','100434157','100455702','100478281','100456331','100414744','100468229']
cards=[c for f in p.glob('*.json') if f.name!='products.json' for c in json.loads(f.read_text()).get('cards',[])]
def get(pid):
 c=next(c for c in cards if 'id='+pid in c['url'])
 r=httpx.get(c['url'],follow_redirects=True,timeout=35);s=BeautifulSoup(r.text,'html.parser')
 for e in s.select('script,style,header,footer,nav'):e.decompose()
 text=s.get_text(' ',strip=True)
 h=s.find('h1'); start=text.find(h.get_text(' ',strip=True)) if h else 0
 text=text[max(0,start):]
 d={'id':pid,'url':str(r.url),'category_card':c['text'],'text':text}
 (p/('product_'+pid+'.txt')).write_text(text)
 return d
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 data=list(ex.map(get,ids))
(p/'products.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
for d in data:
 print('\nID',d['id'],d['url'])
 print(d['text'][:5000])
