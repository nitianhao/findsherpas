import sys, json; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv(override=True)
import os; os.environ['AUDIT_MODEL_FETCHER']='claude-sonnet-5'
from src.models import TestQuery
from src.fetcher import fetch_all_results

tmpl = "https://www.douglas.de/de/search?q={}"
target = sys.argv[1] if len(sys.argv) > 1 else 'lippenstift rot'
allq = [TestQuery.model_validate(x) for x in json.load(open('reports/_checkpoint_phase3_douglas.json',encoding='utf-8'))]
probe = [q for q in allq if q.query == target]
print("PROBE QUERY:", probe[0].query)
print("LIVE URL   :", tmpl.format(probe[0].query.replace(' ','%20')))
res = fetch_all_results(tmpl, probe)
for k, v in res.items():
    print(f"\n--- {k}: {len(v)} results ---")
    for r in v:
        print(f"  {r.rank}. {r.title!r} | price={r.price or '-'} | url={r.url or 'NO URL'}")
out = f"reports/_probe4a_douglas_{target.replace(' ','_')}.json"
json.dump({k:[r.model_dump() for r in v] for k,v in res.items()},
          open(out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print("\nsaved:", out)
