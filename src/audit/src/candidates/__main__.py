"""Run from src/audit/: .venv312/bin/python -m src.candidates --help."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from .runner import Calls, build_candidates, digest, replay_products, save, stamp


def main():
    load_dotenv(Path(__file__).resolve().parents[2]/'.env',override=True)
    p=argparse.ArgumentParser(description='Experimental product-first candidate discovery; no search queries executed.')
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--replay',type=Path,help='Captured product text JSON; no network collection.')
    mode.add_argument('--live',action='store_true',help='Category-first Imerco discovery with no fixed product IDs.')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--model',default=os.environ.get('AUDIT_MODEL_CANDIDATES','claude-sonnet-4-6'))
    p.add_argument('--max-usd',type=float,default=5)
    p.add_argument('--max-calls',type=int,default=30)
    p.add_argument('--input-rate',type=float,default=3,help='USD per million input tokens; default Sonnet 4.6.')
    p.add_argument('--output-rate',type=float,default=15,help='USD per million output tokens; default Sonnet 4.6.')
    a=p.parse_args()
    if not 1<=a.max_calls<=30 or min(a.max_usd,a.input_rate,a.output_rate)<=0:
        p.error('Positive currency/rate values and 1..30 calls required')
    if a.model!='claude-sonnet-4-6' and not ('--input-rate' in __import__('sys').argv and '--output-rate' in __import__('sys').argv):
        p.error('A different model requires explicit input/output rate arguments')
    code_files=sorted(Path(__file__).parent.glob('*.py'))+[Path(__file__).parents[1]/'llm_compat.py']
    library=Path(__file__).resolve().parents[4]/'docs/search-failure-modes.md'
    config={'failure_library_sha256':digest(library.read_text()),'mode':'live' if a.live else 'replay','input_sha256':digest(a.replay.read_text()) if a.replay else None,
            'model':a.model,'max_usd':a.max_usd,'max_calls':a.max_calls,
            'input_rate':a.input_rate,'output_rate':a.output_rate,
            'code_sha256':digest({f.name:digest(f.read_text()) for f in code_files})}
    manifest=a.out/'manifest.json'
    if a.out.exists() and any(a.out.iterdir()):
        if not a.resume: p.error('Output exists; use --resume or a new directory')
        if not manifest.exists() or json.loads(manifest.read_text())['config']!=config:
            p.error('Resume inputs, code, model, or budgets differ; use a new directory')
    else:
        if a.resume:p.error('Nothing to resume')
        try:revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
        except Exception:revision='unknown'
        save(manifest,{'started_at':stamp(),'config':config,'git_revision':revision,
                       'note':'Code hash includes uncommitted implementation; no queries generated/executed.'})
    calls=Calls(a.out/'calls',model=a.model,max_usd=a.max_usd,max_calls=a.max_calls,
                input_rate=a.input_rate,output_rate=a.output_rate)
    products_file=a.out/'products.json'
    try:
        if products_file.exists():
            stored=json.loads(manifest.read_text())
            if stored.get('products_sha256')!=digest(products_file.read_text()):
                raise ValueError('Product checkpoint changed; use a new run')
            from .contracts import Product
            products=[Product.model_validate(d) for d in json.loads(products_file.read_text())]
        elif a.replay:
            products=replay_products(a.replay)
            save(products_file,[v.model_dump() for v in products])
        else:
            from .collection import collect
            products=collect(calls,a.out)
            save(products_file,[v.model_dump() for v in products])
        stored=json.loads(manifest.read_text())
        stored['products_sha256']=digest(products_file.read_text())
        save(manifest,stored)
        report=build_candidates(products,calls,a.out)
    except Exception as exc:
        save(a.out/'collection_failure.json',{'error_type':type(exc).__name__,'budget':calls.summary(),'at':stamp()})
        print(f'Collection did not complete: {type(exc).__name__}; inspect checkpoints.')
        raise SystemExit(1)
    print(json.dumps({'status':report['status'],'products':len(products),'covered_modes':report['covered_modes'],
                      'cost':report['cost'],'report':str(a.out/'report.json')},indent=2))
    if report['status']!='complete':raise SystemExit(1)


if __name__=='__main__':main()
