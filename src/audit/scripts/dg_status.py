"""Show Phase 4 fetch progress and emit the remaining queries as JSON."""
import json, pathlib
store = json.loads(pathlib.Path("reports/_checkpoint_phase4_douglas.json").read_text(encoding="utf-8")) \
        if pathlib.Path("reports/_checkpoint_phase4_douglas.json").exists() else {}
qs = [q["query"] for q in json.loads(pathlib.Path("reports/_checkpoint_phase3_douglas.json").read_text(encoding="utf-8"))]
todo = [q for q in qs if q not in store]
print(f"done {len(store)}/{len(qs)} | remaining {len(todo)}")
pathlib.Path("reports/_dg_todo.json").write_text(json.dumps(todo, ensure_ascii=False), encoding="utf-8")
print("remaining written to reports/_dg_todo.json")
