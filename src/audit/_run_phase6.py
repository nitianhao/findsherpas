import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', stream=sys.stdout)
for n in ('urllib3','httpx','anthropic'): logging.getLogger(n).setLevel(logging.WARNING)

from src.models import SiteContext, TestQuery, ScoredResult
from src.judge import judge_all_queries

ctx = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())
qdata = json.load(open('reports/_checkpoint_phase3.json'))
queries = [TestQuery.model_validate(q) for q in qdata]
scored_raw = json.load(open('reports/_checkpoint_phase5_huckberry.json'))
scored = {q: [ScoredResult.model_validate(r) for r in rs] for q, rs in scored_raw.items()}

judgments = judge_all_queries(
    queries, scored,
    language='en',
    site_categories=ctx.nav_categories,
    site_brands=ctx.brands,
)
json.dump([j.model_dump() for j in judgments], open('reports/_checkpoint_phase6_huckberry.json','w'), default=str)
print('=== JUDGE COMPLETE ===', flush=True)
print('judgments:', len(judgments))
