"""Single-window snapshot collector store for Douglas."""
import json, sys, pathlib, datetime
SNAP = pathlib.Path("reports/_snapshot_douglas.json")

def load(): return json.loads(SNAP.read_text(encoding="utf-8")) if SNAP.exists() else {}

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "init":
        SNAP.write_text(json.dumps({"_meta":{"started":datetime.datetime.now().isoformat(timespec='seconds'),
            "method":"rendered page, navigate + 5s wait, real browser sessions",
            "note":"single continuous window to keep the snapshot internally consistent"}}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("initialised")
    elif cmd == "merge":
        s = load(); b = json.load(open(sys.argv[2], encoding="utf-8"))
        for q, v in b.items():
            if "Access Denied" in (v.get("h1") or ""): print(f"  DENIED {q[:40]!r}"); continue
            s[q] = {"heading": v.get("h1",""), "did_you_mean": v.get("md") or None,
                    "n": len(v.get("r",[])),
                    "results":[{"rank":r[0],"title":r[1],"price":r[2] or None,
                                "url":f"https://www.douglas.de/de/p/{r[3]}","sponsored":bool(r[4])} for r in v.get("r",[])],
                    "captured": datetime.datetime.now().isoformat(timespec='seconds')}
            print(f"  + {q[:46]:<48} n={s[q]['n']:<3} {v.get('h1','')[:34]}")
        SNAP.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        done = len([k for k in s if k != "_meta"])
        print(f"snapshot: {done}/77")
    elif cmd == "todo":
        s = load()
        qs = [q["query"] for q in json.loads(pathlib.Path("reports/_checkpoint_phase3_douglas.json").read_text(encoding="utf-8"))]
        todo = [q for q in qs if q not in s]
        print(f"remaining {len(todo)}")
        import urllib.parse
        for q in todo[:int(sys.argv[2]) if len(sys.argv)>2 else 3]:
            print(urllib.parse.quote(q))
