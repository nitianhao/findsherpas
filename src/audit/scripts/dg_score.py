import sys, json, pathlib; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv(override=True)
from src.models import TestQuery, SearchResult
from src.scorer import score_results

qs = [TestQuery.model_validate(x) for x in json.loads(
    pathlib.Path('reports/_checkpoint_phase3_douglas.json').read_text(encoding='utf-8'))]
raw = json.loads(pathlib.Path('reports/_checkpoint_phase4_douglas_clean.json').read_text(encoding='utf-8'))
scraped = {q: [SearchResult.model_validate(r) for r in v] for q, v in raw.items()}
qs = [q for q in qs if scraped.get(q.query)]
print(f"scoring {len(qs)} queries...")
scored = score_results(qs, scraped)
out = {q: [r.model_dump() for r in v] for q, v in scored.items()}
pathlib.Path('reports/_checkpoint_phase5_douglas.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"scored {len(scored)} queries -> reports/_checkpoint_phase5_douglas.json")
