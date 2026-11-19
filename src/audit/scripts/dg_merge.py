"""Merge a Douglas fetch batch into the Phase 4 checkpoint.

Usage: dg_merge.py <batch.json>

Batch format (compact, produced by the in-browser runner):
  {"<query>": {"n":15,"h":"<heading>","rd":0,
               "r":[[rank,title,price,product_id,sponsored], ...]}, ...}

Writes/updates reports/_checkpoint_phase4_douglas.json, keyed by query, storing
full SearchResult-shaped dicts plus the heading (Douglas's claimed result count,
which we need because it can contradict what is displayed).
"""
import json, sys, pathlib

CKPT = pathlib.Path("reports/_checkpoint_phase4_douglas.json")

def main(batch_path):
    batch = json.load(open(batch_path, encoding="utf-8"))
    store = json.load(open(CKPT, encoding="utf-8")) if CKPT.exists() else {}

    added, skipped = [], []
    for q, v in batch.items():
        if "e" in v:
            skipped.append((q, v["e"]))
            continue
        heading = v.get("h", "")
        if "Access Denied" in heading:
            skipped.append((q, "Access Denied"))
            continue
        results = [
            {"rank": r[0], "title": r[1], "price": (r[2] or None),
             "url": f"https://www.douglas.de/de/p/{r[3]}", "sponsored": bool(r[4])}
            for r in v.get("r", [])
        ]
        store[q] = {"heading": heading, "redirect": bool(v.get("rd")),
                    "n": v.get("n", len(results)), "results": results}
        added.append(q)

    CKPT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(store, open(CKPT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"merged {len(added)} | skipped {len(skipped)} | checkpoint now holds {len(store)}/77")
    for q, why in skipped:
        print(f"  SKIP {q!r}: {why}")

if __name__ == "__main__":
    main(sys.argv[1])
