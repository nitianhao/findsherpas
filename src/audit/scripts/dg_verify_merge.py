"""Verify rendered heading/results against stored fetch-derived data.
Input: {"<query>": {"h1":..., "t":N, "f":[titles], "md":...}}
Flags mismatches needing full result re-collection.
"""
import json, sys, pathlib, re
CKPT = pathlib.Path("reports/_checkpoint_phase4_douglas.json")
batch = json.load(open(sys.argv[1], encoding="utf-8"))
store = json.load(open(CKPT, encoding="utf-8"))
suspect = json.loads(pathlib.Path("reports/_dg_suspect.json").read_text(encoding="utf-8")) \
          if pathlib.Path("reports/_dg_suspect.json").exists() else []

def norm(s): return re.sub(r'\W+', '', (s or '')).lower()[:34]

for q, v in batch.items():
    if q not in store: print(f"  !! unknown {q!r}"); continue
    if "Access Denied" in (v.get("h1") or ""): print(f"  SKIP denied: {q[:40]!r}"); continue
    store[q]["heading_rendered"] = v.get("h1","")
    store[q]["did_you_mean"] = v.get("md") or None
    store[q]["tiles_rendered"] = v.get("t")
    store[q]["heading_verified"] = True
    stored_first = [r["title"] for r in store[q]["results"][:3]]
    rend_first = v.get("f", [])
    match = all(norm(a).startswith(norm(b)[:22]) or norm(b).startswith(norm(a)[:22])
                for a, b in zip(stored_first, rend_first)) if rend_first and stored_first else None
    store[q]["grid_matches_rendered"] = match
    exp = min(15, v.get("t") or 0)
    if match is not False and store[q]["n"] < exp and not store[q].get("intermittent"):
        match = False
        print(f"  COUNT MISMATCH {q[:42]!r}: stored n={store[q]['n']} vs rendered tiles={v.get('t')}")
        store[q]["grid_matches_rendered"] = False
    if match is False:
        suspect.append(q)
        print(f"  MISMATCH {q[:45]!r}")
        print(f"     stored : {stored_first[:2]}")
        print(f"     render : {rend_first[:2]}")
    else:
        print(f"  ok {q[:50]!r}  h1={v.get('h1','')[:34]}")
json.dump(store, open(CKPT,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
pathlib.Path("reports/_dg_suspect.json").write_text(json.dumps(sorted(set(suspect)), ensure_ascii=False), encoding="utf-8")
ver = sum(1 for v in store.values() if v.get("heading_verified"))
print(f"\nverified {ver}/77 | suspect grids: {len(set(suspect))}")
