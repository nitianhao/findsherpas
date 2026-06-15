import sys, json
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv(override=True)
from collections import Counter
from src.query_generator import TestQuery
from src.scorer import ScoredResult
from src.judge import judge_all_queries

all_q = [TestQuery.model_validate(q) for q in json.load(open('reports/_checkpoint_phase3.json'))]
screen = json.load(open('reports/_redirect_screen.json'))
keep_set = {s for _, s in screen['keep']}
queries = [q for q in all_q if q.query in keep_set]

raw = json.load(open('reports/_checkpoint_phase5.json'))
scored = {q: [ScoredResult.model_validate(r) for r in rows] for q, rows in raw.items()}

judgments = judge_all_queries(queries, scored)

json.dump([j.model_dump() for j in judgments], open('reports/_checkpoint_phase6.json', 'w'), ensure_ascii=False)

sev = Counter(str(getattr(j.severity, 'value', j.severity)) for j in judgments)
fm = Counter(str(getattr(j.failure_mode, 'value', j.failure_mode)) for j in judgments)

print('=== Severity counts ===', flush=True)
for s in ['CRITICAL', 'MODERATE', 'MINOR', 'PASS']:
    hit = next((k for k in sev if s in k.upper()), None)
    print(f'  {s:9} {sev.get(hit,0) if hit else 0}', flush=True)
print('  (raw:', dict(sev), ')', flush=True)

print('\n=== Failure mode distribution ===', flush=True)
for k, v in fm.most_common():
    print(f'  {k:28} {v}', flush=True)

print('\n=== CRITICAL judgments ===', flush=True)
crits = [j for j in judgments if 'CRITICAL' in str(getattr(j.severity,'value',j.severity)).upper()]
if not crits:
    print('  (none)', flush=True)
for j in crits:
    print(f'\n  QUERY: {j.query}', flush=True)
    print(f'  failure_mode: {getattr(j.failure_mode,"value",j.failure_mode)}', flush=True)
    print(f'  evidence: {j.evidence}', flush=True)
    print(f'  fix: {j.recommended_fix}', flush=True)

print(f'\nTotal judged: {len(judgments)}', flush=True)
