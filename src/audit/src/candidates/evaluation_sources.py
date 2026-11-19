"""Collect identity-checked detail pages for saved search results, without rerunning queries."""
from __future__ import annotations
import argparse
import concurrent.futures
import json
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from .collection import fetch,detail_product
from .contracts import Link
from .runner import save,stamp,digest


def collect(execution: Path,out: Path) -> dict:
    outcomes=json.loads((execution/'outcomes.json').read_text())
    links={}
    for data in outcomes.values():
        for result in data['results']:
            pid=parse_qs(urlparse(result['url']).query)['id'][0]
            links[pid]=Link(id=pid,url=result['url'],text=result['title'])
    if len(links)>200:raise ValueError('Evaluation source budget: at most 200 distinct detail pages')
    cache=out/'product_sources.json'
    manifest=out/'collection_manifest.json'
    input_hash=digest((execution/'outcomes.json').read_text())
    if manifest.exists() and json.loads(manifest.read_text())['input_sha256']!=input_hash:
        raise ValueError('Source collection belongs to different search observations')
    records=json.loads(cache.read_text()) if cache.exists() else {}
    if set(records)-set(links):raise ValueError('Unreferenced products in source cache')
    def get(link):
        try:
            html,metadata=fetch(link.url,out/'detail_capture')
            product=detail_product(link,html,metadata,'observed search result')
            return link.id,{'status':'ok','product':product.model_dump()}
        except Exception as exc:return link.id,{'status':'error','error_type':type(exc).__name__,'url':link.url}
    missing=[link for pid,link in links.items() if pid not in records]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for pid,result in pool.map(get,missing):
            records[pid]=result;save(cache,records)
            print(f'Product {len(records)}/{len(links)} {pid}: {result["status"]}',flush=True)
    save(manifest,{'completed_at':stamp(),'unique_products':len(links),'input_sha256':input_hash,
        'errors':sum(d['status']!='ok' for d in records.values()),
        'note':'Search ordering preserved; detail sources have their own capture timestamps. No searches rerun.'})
    return records


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();collect(args.execution,args.out)


if __name__=='__main__':main()
