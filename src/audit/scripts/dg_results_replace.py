"""Replace stale results with rendered-page results, preserving verified heading fields."""
import json, sys, pathlib
CKPT = pathlib.Path("reports/_checkpoint_phase4_douglas.json")
batch = json.load(open(sys.argv[1], encoding="utf-8"))
store = json.load(open(CKPT, encoding="utf-8"))
for q, rows in batch.items():
    if q not in store: print(f"  !! unknown: {q!r}"); continue
    results = [{"rank": r[0], "title": r[1], "price": (r[2] or None),
                "url": f"https://www.douglas.de/de/p/{r[3]}", "sponsored": bool(r[4])} for r in rows]
    store[q]["results"] = results
    store[q]["n"] = len(results)
    store[q]["results_source"] = "rendered"
    store[q]["heading"] = store[q].get("heading_rendered", store[q].get("heading"))
    print(f"  replaced {q[:50]!r}: n={len(results)}")
json.dump(store, open(CKPT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
rem = [q for q in json.loads(pathlib.Path('reports/_dg_stale.json').read_text(encoding='utf-8'))
       if store[q].get("results_source") != "rendered"]
pathlib.Path('reports/_dg_stale.json').write_text(json.dumps(rem, ensure_ascii=False), encoding='utf-8')
print(f"stale remaining: {len(rem)}")
