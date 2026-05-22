"""Fetch stripped-diacritic twins for the UA CZ audit. Step 1 of 3."""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))
from dotenv import load_dotenv
load_dotenv(override=True)

from src.models import TestQuery, SearchResult
from src.fetcher import fetch_all_results

SITE_CTX = json.loads((ROOT / "reports" / "_checkpoint_phase1.json").read_text())
SEARCH_URL = SITE_CTX["search_url_template"]

TWINS = [
    ("bezecke boty", "Diacritic-stripped twin of 'běžecké boty' — mobile default."),
    ("sportovni podprsenka", "Diacritic-stripped twin of 'sportovní podprsenka'."),
    ("tilko", "Diacritic-stripped twin of 'tílko'."),
    ("kratasy", "Diacritic-stripped twin of 'kraťasy'."),
    ("panske bezecke boty", "Diacritic-stripped twin of 'pánské běžecké boty'."),
    ("damska sportovni podprsenka", "Diacritic-stripped twin of 'dámská sportovní podprsenka'."),
    ("detske outlet tenisky", "Diacritic-stripped twin of 'dětské outlet tenisky'."),
    ("ponozka", "Diacritic-stripped twin of 'ponožka'."),
    ("muzi", "Diacritic-stripped twin of 'muži'."),
    ("deti", "Diacritic-stripped twin of 'děti'."),
    ("trenink", "Diacritic-stripped twin of 'trénink'."),
]

queries = [TestQuery(category="SPECIAL_CHARACTER", query=q, rationale=r) for q, r in TWINS]

print(f"Fetching {len(queries)} diacritic twins via {SEARCH_URL}")
results = fetch_all_results(SEARCH_URL, queries)

out = ROOT / "reports" / "_checkpoint_diacritic_twins_fetch.json"
serial = {q: [r.model_dump() for r in res] for q, res in results.items()}
out.write_text(json.dumps(serial, ensure_ascii=False, indent=2))

for q, res in results.items():
    print(f"  {q}: {len(res)} results")
print(f"Saved: {out}")
