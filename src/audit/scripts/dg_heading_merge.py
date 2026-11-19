"""Merge rendered-page heading data into the Phase 4 checkpoint.

Input JSON: {"<query>": {"h1": "...", "md": "...", "tiles": N, "f": [titles]}, ...}
Replaces the unreliable fetch-derived `heading` with `heading_rendered`,
records `did_you_mean`, `tiles_rendered`, and marks `heading_verified`.
"""
import json, sys, pathlib
CKPT = pathlib.Path("reports/_checkpoint_phase4_douglas.json")

batch = json.load(open(sys.argv[1], encoding="utf-8"))
store = json.load(open(CKPT, encoding="utf-8"))
n = 0
for q, v in batch.items():
    if q not in store:
        print(f"  !! unknown query: {q!r}"); continue
    if "Access Denied" in (v.get("h1") or ""):
        print(f"  SKIP (denied): {q!r}"); continue
    store[q]["heading_rendered"] = v.get("h1", "")
    store[q]["did_you_mean"] = v.get("md", "") or None
    store[q]["tiles_rendered"] = v.get("tiles")
    store[q]["heading_verified"] = True
    store[q]["_spotcheck_first"] = v.get("f", [])
    n += 1
json.dump(store, open(CKPT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
ver = sum(1 for v in store.values() if v.get("heading_verified"))
print(f"merged {n} | headings verified: {ver}/{len(store)}")
