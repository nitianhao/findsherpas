import sys, json, os
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
from src.models import TestQuery, SearchResult
from src.fetcher import fetch_all_results

TMPL = 'https://lyko.com/sv/sok?q={}'
CKPT = 'reports/_checkpoint_phase4.json'

queries = [TestQuery.model_validate(q) for q in json.loads(open('reports/_checkpoint_phase3.json').read())]

# Resume: load existing checkpoint
done = {}
if os.path.exists(CKPT):
    raw = json.loads(open(CKPT).read())
    for qstr, rs in raw.items():
        done[qstr] = [SearchResult.model_validate(r) for r in rs]

remaining = [q for q in queries if q.query not in done]
print(f'total={len(queries)} done={len(done)} remaining={len(remaining)}', flush=True)

def save():
    out = {qstr: [r.model_dump() for r in rs] for qstr, rs in done.items()}
    open(CKPT, 'w').write(json.dumps(out, indent=2, ensure_ascii=False))

BATCH = 10
for i in range(0, len(remaining), BATCH):
    batch = remaining[i:i+BATCH]
    res = fetch_all_results(TMPL, batch, max_results=15)
    for q in batch:
        done[q.query] = res.get(q.query, [])
    save()
    print(f'batch {i//BATCH+1}: saved {len(done)}/{len(queries)}', flush=True)

print('DONE', flush=True)
# Summary of thin/zero
for q in queries:
    rs = done.get(q.query, [])
    if len(rs) < 15:
        print(f'  THIN/ZERO [{q.category.value if hasattr(q.category,"value") else q.category}] {q.query!r}: {len(rs)}', flush=True)
