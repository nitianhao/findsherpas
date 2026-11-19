"""Imerco pilot adapter: observed navigation → categories → product details, never search."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from .contracts import Link, MODES, Product, Selection
from .runner import BudgetStop, digest, save, source_text, stamp

ORIGIN='https://www.imerco.dk'
CATEGORY_PREFIXES=('/koekkenudstyr/','/borddaekning/','/bolig/')


def allowed_url(url: str) -> bool:
    p=urlparse(url)
    return p.scheme=='https' and p.hostname=='www.imerco.dk' and p.port in (None,443) and not p.username and not p.password and not re.search(r'/(search|soeg|sog)(/|$)',p.path,re.I) and not any(k.casefold() in {'q','query','search','searchterm'} for k in parse_qs(p.query))


def select_observed(selection: Selection, links: list[Link], limit: int) -> list[Link]:
    by_id={x.id:x for x in links}
    if not selection.ids or len(selection.ids)>limit or len(selection.ids)!=len(set(selection.ids)):
        raise ValueError('Empty, duplicated, or over-budget link selection')
    if any(i not in by_id for i in selection.ids):
        raise ValueError('Model selected unobserved link')
    return [by_id[i] for i in selection.ids]


def fetch(url: str, out: Path) -> tuple[str,dict]:
    if not allowed_url(url):raise ValueError('Only same-store, non-search URLs allowed')
    path=out/'sources'/(digest(url)+'.json')
    if path.exists():
        data=json.loads(path.read_text())
        html_path=out/data['snapshot']
        html=html_path.read_text()
        if digest(html)!=data['sha256']:raise ValueError('Source snapshot changed')
        return html,data
    original=url
    for _ in range(4):
        with requests.get(url,timeout=35,allow_redirects=False,stream=True,
                          headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0 Safari/537.36'}) as resp:
            if resp.is_redirect:
                url=urljoin(url,resp.headers['Location'])
                if not allowed_url(url):raise ValueError('Redirect leaves allowed independent sources')
                continue
            resp.raise_for_status()
            if 'html' not in resp.headers.get('Content-Type','').lower():raise ValueError('Expected HTML')
            raw=bytearray()
            for chunk in resp.iter_content(65536):
                raw.extend(chunk)
                if len(raw)>3_000_000:raise ValueError('Source exceeds 3 MB bound')
            html=raw.decode('utf-8',errors='replace')
            data={'url':original,'final_url':url,'http_status':resp.status_code,'captured_at':stamp(),
                  'sha256':digest(html),'transport':'requests/static','snapshot':'sources/'+digest(original)+'.html'}
            target=out/data['snapshot'];target.parent.mkdir(parents=True,exist_ok=True);target.write_text(html)
            save(path,data)
            time.sleep(.3)
            return html,data
    raise ValueError('Too many redirects')


def nav_links(html: str) -> list[Link]:
    soup=BeautifulSoup(html,'html.parser')
    seen=set();links=[]
    for a in soup.select('a[href]'):
        url=urljoin(ORIGIN,a['href']).split('#')[0]
        p=urlparse(url)
        label=a.get_text(' ',strip=True)
        if not allowed_url(url) or not p.path.startswith(CATEGORY_PREFIXES) or p.query or not label or url in seen:continue
        seen.add(url)
        links.append(Link(id=f'nav{len(links)}',url=url,text=label[:100]))
    # Keep late navigation sections (e.g. furniture); never silently truncate coverage.
    if len(links)>400:
        raise ValueError("Navigation exceeds pilot bound; adapt selection without silently dropping sections")
    return links


def product_links(html: str) -> list[Link]:
    soup=BeautifulSoup(html,'html.parser');seen=set();links=[]
    for card in soup.select('div[class*="ProductHit_wrapper"]')[:40]:
        a=card.select_one('a[class*="ProductHit_card"]')
        if not a:continue
        url=urljoin(ORIGIN,a['href'])
        pid=parse_qs(urlparse(url).query).get('id',[''])[0]
        if not pid or pid in seen or not allowed_url(url):continue
        seen.add(pid)
        links.append(Link(id=pid,url=url,text=card.get_text(' ',strip=True)[:550]))
    return links


def detail_product(link: Link, html: str, metadata: dict, category: str) -> Product:
    soup=BeautifulSoup(html,'html.parser');h=soup.find('h1')
    if not h:raise ValueError('No product heading; blocked or unsupported page')
    name=h.get_text(' ',strip=True)
    for node in soup.select('script,style,header,footer,nav'):node.decompose()
    text=soup.get_text(' ',strip=True)
    at=text.find(name)
    text=source_text(text[max(0,at):])
    if not re.search(r'Vare\s*nr\.?\s*'+re.escape(link.id)+r'\b',text,re.I):
        raise ValueError('Product identity not confirmed in detail specifications')
    return Product(id=link.id,name=name,url=metadata['final_url'],text=text,
                   source_path=metadata['snapshot'],source_hash=metadata['sha256'],
                   captured_at=metadata['captured_at'],category_urls=[category])


def collect(calls, out: Path) -> list[Product]:
    """At most 7 categories × 5 selected products, with explicit gaps on errors."""
    homepage,_=fetch(ORIGIN,out)
    nav=nav_links(homepage)
    if not nav:raise ValueError('No independent category navigation found')
    save(out/'observed_navigation.json',[x.model_dump() for x in nav])
    selection=calls.call('plan_categories',{'modes':MODES,'observed_links':[x.model_dump() for x in nav]},Selection,
        'Choose at most SEVEN observed leaf categories that together support these ten modes. Prefer cups without handles, bowls, serving jugs, vases, drinking glasses, tables, and frying pans where available. Do not invent links or IDs. Choose all seven if available.',max_tokens=1200)
    categories=select_observed(selection,nav,7)
    products={};errors=[]
    for i,category in enumerate(categories):
        try:
            html,_=fetch(category.url,out)
            links=product_links(html)
            save(out/f'category_{i}.json',{'category':category.model_dump(),'links':[x.model_dump() for x in links]})
            if not links:
                errors.append({'category':category.url,'reason':'No supported product cards'});continue
            selected=calls.call('select_products_'+str(i),{'modes':MODES,'category':category.text,
                'already_collected':[p.name for p in products.values()],
                'observed_products':[x.model_dump() for x in links]},Selection,
                'Choose at most FIVE diverse products whose detail pages may establish the required facts. Prefer available online examples and complementary material/price variants. For tables include promising solid oak AND explicit oak veneer. For pans include member-price and public-price variants and explicitly uncoated if observed. Only observed IDs; card text is a lead, NOT verified evidence.',max_tokens=1200)
            for link in select_observed(selected,links,5):
                if link.id in products:continue
                if len(products)>=40:raise BudgetStop('40 product-page budget reached')
                try:
                    html,metadata=fetch(link.url,out)
                    products[link.id]=detail_product(link,html,metadata,category.url)
                    save(out/'collected_products.json',[p.model_dump() for p in products.values()])
                except BudgetStop:raise
                except Exception as exc:errors.append({'product_id':link.id,'reason':type(exc).__name__})
        except BudgetStop:raise
        except Exception as exc:
            errors.append({'category':category.url,'reason':type(exc).__name__})
        finally:save(out/'collection_errors.json',errors)
    if not products:raise ValueError('No verified detail-page identities collected')
    return list(products.values())
