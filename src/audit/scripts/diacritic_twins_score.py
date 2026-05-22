"""Junk-clean and score the stripped-diacritic twins. Step 2 of 3."""
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
from src.scorer import score_results

JUNK_TITLES = {
    "+ Zobrazit více", "Zobrazit více", "Porovnání produktů", "Podobné fráze",
    "Zapomněli jste heslo?", "Povolit vše", "Smazat vše", "Přejít do košíku",
    "Kategorie", "Značky", "Přihlásit se", "Registrovat se",
    "Show more", "Compare products", "Sign in", "Accept all", "Clear all",
}


def is_junk(r):
    if r.get("title", "") in JUNK_TITLES:
        return True
    url = r.get("url") or ""
    if not url or url.startswith("#"):
        return True
    if "policies.google.com" in url or "business.safety.google" in url:
        return True
    return False


def main():
    fetch_ckpt = ROOT / "reports" / "_checkpoint_diacritic_twins_fetch.json"
    raw = json.loads(fetch_ckpt.read_text())

    cleaned = {}
    removed = 0
    for q, results in raw.items():
        keep = [r for r in results if not is_junk(r)]
        removed += len(results) - len(keep)
        for i, r in enumerate(keep, 1):
            r["original_rank"] = i
        cleaned[q] = keep

    print(f"Junk removed: {removed}")
    for q, res in cleaned.items():
        print(f"  {q}: {len(res)} clean results")

    TWINS = list(raw.keys())
    queries = [TestQuery(category="SPECIAL_CHARACTER", query=q, rationale="Diacritic-stripped twin.") for q in TWINS]
    scraped = {q: [SearchResult.model_validate(r) for r in cleaned[q]] for q in TWINS}

    print("\nScoring...")
    scored = score_results(queries, scraped)

    scored_serial = {q: [r.model_dump() for r in res] for q, res in scored.items()}
    out = ROOT / "reports" / "_checkpoint_diacritic_twins_scored.json"
    out.write_text(json.dumps(scored_serial, ensure_ascii=False, indent=2))

    # Show top-1 relevance per twin
    print("\nTop-1 relevance per twin:")
    for q, res in scored.items():
        if not res:
            print(f"  {q}: (no results)")
            continue
        by_rank = sorted(res, key=lambda r: r.original_rank)
        print(f"  {q}: top1={by_rank[0].relevance_score:.2f}")

    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
