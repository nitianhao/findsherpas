import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv(override=True)
import json
from urllib.parse import quote_plus
from src.discovery import SiteContext
from src.query_generator import TestQuery
from src.fetcher import _fetch_with_mode, SiteMode, SearchResult
from src.scorer import score_results
from src.models import ScoredResult
from src.judge import _judge_single_query

OLD = 'meind'
NEW_QUERY = 'patago'
NEW_CATEGORY = 'PARTIAL_QUERY'
NEW_RATIONALE = ("Truncates the real brand name 'Patagonia' to a 6-char prefix; tests prefix "
                 "matching / autocomplete-style retrieval. Patagonia is confirmed stocked "
                 "(a full brand search returns 15 Patagonia products), so a zero here is a "
                 "genuine search failure, not a catalog gap.")
MAX_RESULTS = 15

sc = SiteContext.model_validate_json(open('reports/_checkpoint_phase1.json').read())

# 1. Phase 3: swap the query in place (preserve ordering position)
qd = json.load(open('reports/_checkpoint_phase3.json'))
for q in qd:
    if q['query'] == OLD:
        q['query'] = NEW_QUERY
        q['category'] = NEW_CATEGORY
        q['rationale'] = NEW_RATIONALE
json.dump(qd, open('reports/_checkpoint_phase3.json', 'w'))
new_tq = TestQuery(query=NEW_QUERY, category=NEW_CATEGORY, rationale=NEW_RATIONALE)

# 2. Fetch the new query (chromium mode, like the rest of the audit)
url = sc.search_url_template.replace('{}', quote_plus(NEW_QUERY))
results, was_redirected = _fetch_with_mode(url, NEW_QUERY, MAX_RESULTS, SiteMode.PLAYWRIGHT_CHROMIUM)
print(f"FETCH: {NEW_QUERY!r} -> {len(results)} results (redir={was_redirected})", flush=True)

# Patch phase 4
p4 = json.load(open('reports/_checkpoint_phase4.json'))
p4.pop(OLD, None)
p4[NEW_QUERY] = [r.model_dump() for r in results]
json.dump(p4, open('reports/_checkpoint_phase4.json', 'w'))

# 3. Score (skip if zero)
p5 = json.load(open('reports/_checkpoint_phase5.json'))
p5.pop(OLD, None)
if results:
    scored = score_results([new_tq], {NEW_QUERY: results})
    scored_list = scored.get(NEW_QUERY, [])
    p5[NEW_QUERY] = [r.model_dump() for r in scored_list]
else:
    scored_list = []
    p5[NEW_QUERY] = []
json.dump(p5, open('reports/_checkpoint_phase5.json', 'w'))

# 4. Judge
sr = [ScoredResult(**r) for r in p5[NEW_QUERY]]
j = _judge_single_query(new_tq, sr, language=sc.primary_language,
                        site_categories=sc.nav_categories, site_brands=sc.brands)
p6 = json.load(open('reports/_checkpoint_phase6.json'))
p6.pop(OLD, None)
p6[NEW_QUERY] = j.model_dump()
json.dump(p6, open('reports/_checkpoint_phase6.json', 'w'))

sev = j.severity.value if hasattr(j.severity, 'value') else j.severity
fm = j.failure_mode.value if hasattr(j.failure_mode, 'value') else j.failure_mode
print(f"\n=== PARTIAL_QUERY | {NEW_QUERY!r} (replaces {OLD!r}) ===")
print(f"SEVERITY: {sev}")
print(f"FAILURE_MODE: {fm}")
print(f"#results: {len(sr)} | max_rel: {j.max_relevance_score:.2f} | displacement: {j.displacement}")
print(f"\nEVIDENCE:\n{j.evidence}")
print(f"\nRECOMMENDED FIX:\n{j.recommended_fix}")
if sr:
    print("\nRESULTS (rank | rel | title | price):")
    for r in sr[:15]:
        print(f"  {r.original_rank:2d} | {r.relevance_score:.2f} | {r.title[:65]} | {r.price or '-'}")
