"""Inspect and prune the judge calibration knowledge base.

Pruned entries are kept in the file (status flipped to "pruned") for an audit trail and
excluded from retrieval — they are never used as calibration anchors again.

Usage (run from src/audit):
    python scripts/kb_prune.py list <language>
    python scripts/kb_prune.py list <language> --status active
    python scripts/kb_prune.py prune <language> <match>   # id prefix or query substring
    python scripts/kb_prune.py prune <language> <match> --dry-run

Examples:
    python scripts/kb_prune.py list german
    python scripts/kb_prune.py prune german "laufschuhe ohne"
    python scripts/kb_prune.py prune german 3f2a1b
"""

import argparse
import json
import sys
from pathlib import Path

AUDIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUDIT_ROOT))

from src.judge_kb import kb_path  # noqa: E402


def _load(path: Path) -> list[dict]:
    if not path.exists():
        print(f"No KB file at {path}")
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _write(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _matches(rec: dict, match: str) -> bool:
    return rec.get("id", "").startswith(match) or match.lower() in rec.get("query", "").lower()


def cmd_list(args) -> None:
    path = kb_path(args.language)
    records = _load(path)
    shown = 0
    for rec in records:
        if args.status and rec.get("status") != args.status:
            continue
        shown += 1
        print(
            f"{rec.get('id', '')[:8]}  {rec.get('status', ''):7}  "
            f"{rec.get('severity', ''):9}  {rec.get('category', ''):18}  "
            f"{rec.get('failure_mode', ''):26}  \"{rec.get('query', '')}\""
        )
    print(f"\n{shown} ent(ies) shown — file: {path}")


def cmd_prune(args) -> None:
    path = kb_path(args.language)
    records = _load(path)
    hits = [r for r in records if r.get("status") == "active" and _matches(r, args.match)]

    if not hits:
        print(f"No active entries match '{args.match}'.")
        return

    print(f"{'Would prune' if args.dry_run else 'Pruning'} {len(hits)} entr(ies):")
    for rec in hits:
        print(f"  {rec.get('id', '')[:8]}  \"{rec.get('query', '')}\"")

    if args.dry_run:
        return

    for rec in hits:
        rec["status"] = "pruned"
    _write(path, records)
    print(f"Done. Updated {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and prune the judge calibration KB.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List KB entries for a language.")
    p_list.add_argument("language")
    p_list.add_argument("--status", choices=["active", "pruned"], default=None)
    p_list.set_defaults(func=cmd_list)

    p_prune = sub.add_parser("prune", help="Mark matching active entries as pruned.")
    p_prune.add_argument("language")
    p_prune.add_argument("match", help="ID prefix or query substring to match.")
    p_prune.add_argument("--dry-run", action="store_true")
    p_prune.set_defaults(func=cmd_prune)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
