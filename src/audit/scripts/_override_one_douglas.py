"""Save a manual Phase-6 override for one douglas query. Usage: <idx> <SEVERITY> <FAILURE_MODE> <evidence> <fix>"""
import json, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(override=True)
from src.judge import _compute_stats
from src.models import FailureMode, QueryJudgment, ScoredResult, Severity, TestQuery

CP = "reports/_checkpoint_phase6_douglas.json"
idx, sev, fm, evidence, fix = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
queries = [TestQuery.model_validate(q) for q in json.load(open("reports/_checkpoint_phase3_douglas.json"))]
scored = json.load(open("reports/_checkpoint_phase5_douglas.json"))
tq = queries[idx]
res = [ScoredResult.model_validate(r) for r in scored.get(tq.query, [])]
mx, t3, disp = _compute_stats(res)
j = QueryJudgment(
    test_query=tq, results=res,
    failure_mode=FailureMode[fm], severity=Severity[sev],
    evidence=evidence, recommended_fix=fix,
    displacement=disp, max_relevance_score=mx, top3_original_average=t3,
)
try:
    store = json.load(open(CP))
except FileNotFoundError:
    store = {}
store[tq.query] = j.model_dump(mode="json")
json.dump(store, open(CP, "w"), ensure_ascii=False, indent=2)
print(f"saved [{idx+1}] {tq.query!r} -> {sev}/{fm}  ({len(store)} judged)")
