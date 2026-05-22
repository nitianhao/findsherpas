"""Judge the 11 stripped twins and merge into phase 6 checkpoint. Step 3 of 3."""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))
from dotenv import load_dotenv
load_dotenv(override=True)

from src.models import TestQuery, ScoredResult
from src.judge import judge_all_queries


def main():
    scored_path = ROOT / "reports" / "_checkpoint_diacritic_twins_scored.json"
    scored_raw = json.loads(scored_path.read_text())

    TWINS = list(scored_raw.keys())
    queries = [TestQuery(category="SPECIAL_CHARACTER", query=q, rationale="Diacritic-stripped twin.") for q in TWINS]
    scored = {q: [ScoredResult.model_validate(r) for r in scored_raw[q]] for q in TWINS}

    print(f"Judging {len(queries)} diacritic twins...")
    judgments = judge_all_queries(queries, scored)

    # Merge into phase 6
    phase6_path = ROOT / "reports" / "_checkpoint_phase6.json"
    existing = json.loads(phase6_path.read_text())
    existing_queries = {j["test_query"]["query"] for j in existing}

    new_entries = []
    for j in judgments:
        q = j.test_query.query
        if q in existing_queries:
            print(f"  Skipping duplicate: {q}")
            continue
        new_entries.append(json.loads(j.model_dump_json()))

    merged = existing + new_entries
    phase6_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    print(f"Added {len(new_entries)} judgments. Total: {len(merged)}")


if __name__ == "__main__":
    main()
