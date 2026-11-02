"""Inspect, promote and prune the judge calibration knowledge base.

Records are never deleted: pruned/retired entries stay in the file (status flipped) for an
audit trail and are excluded from retrieval. Harvested verdicts land as "pending" and are
only used as calibration anchors after an operator promotes them.

Usage (run from src/audit; <language> is any name or code — German/de/de-CH -> de.jsonl):
    python scripts/kb_prune.py list <language> [--status pending|active|retired|pruned]
    python scripts/kb_prune.py promote <language> <match> [--dry-run]   # pending -> active
    python scripts/kb_prune.py promote <language> --all-pending [--domain bergzeit.de]
    python scripts/kb_prune.py prune <language> <match> [--dry-run]     # active/pending -> pruned
    python scripts/kb_prune.py retire <language> <match> --reason "..."  # -> retired

<match> is an id prefix or a query substring.

Promoting marks the record human_reviewed and stamps the current JUDGE_RULES_VERSION, so it
stays retrievable after a later rules bump only because a human checked it.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

AUDIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUDIT_ROOT))

from src.judge import JUDGE_RULES_VERSION  # noqa: E402
from src.judge_kb import kb_path, normalize_domain, write_records  # noqa: E402

STATUSES = ["pending", "active", "retired", "pruned"]


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


def _matches(rec: dict, match: str | None) -> bool:
    if not match:
        return False
    return rec.get("id", "").startswith(match) or match.lower() in rec.get("query", "").lower()


def cmd_list(args) -> None:
    path = kb_path(args.language)
    shown = 0
    for rec in _load(path):
        if args.status and rec.get("status") != args.status:
            continue
        shown += 1
        print(
            f"{rec.get('id', '')[:8]}  {rec.get('status', ''):7}  {str(rec.get('rules_version', '')):10}  "
            f"{'H' if rec.get('human_reviewed') else ' '}  {rec.get('severity', ''):9}  "
            f"{rec.get('category', ''):18}  {rec.get('failure_mode', ''):26}  "
            f"{(rec.get('domain') or ''):18}  \"{rec.get('query', '')}\""
        )
    print(f"\n{shown} ent(ies) shown — file: {path}")


def _change(args, select, apply, verb: str) -> None:
    path = kb_path(args.language)
    records = _load(path)
    hits = [r for r in records if select(r)]
    if not hits:
        print(f"No entries to {verb}.")
        return
    doing = {"promote": "Promoting", "prune": "Pruning", "retire": "Retiring"}[verb]
    print(f"{'Would ' + verb if args.dry_run else doing} {len(hits)} entr(ies):")
    for rec in hits:
        print(f"  {rec.get('id', '')[:8]}  {rec.get('status', ''):7}  {rec.get('severity', ''):9}  \"{rec.get('query', '')}\"")
    if args.dry_run:
        return
    now = datetime.now().isoformat()
    for rec in hits:
        apply(rec, now)
    write_records(path, records)
    print(f"Done. Updated {path}")


def cmd_promote(args) -> None:
    def select(r):
        if r.get("status") != "pending":
            return False
        if args.domain and normalize_domain(r.get("domain")) != normalize_domain(args.domain):
            return False
        return args.all_pending or _matches(r, args.match)

    def apply(r, now):
        r.update(status="active", human_reviewed=True, reviewed_at=now, rules_version=JUDGE_RULES_VERSION)

    if not args.all_pending and not args.match:
        sys.exit("promote needs <match> or --all-pending")
    _change(args, select, apply, "promote")


def cmd_prune(args) -> None:
    _change(args, lambda r: r.get("status") in ("active", "pending") and _matches(r, args.match),
            lambda r, now: r.update(status="pruned", pruned_at=now), "prune")


def cmd_retire(args) -> None:
    _change(args, lambda r: r.get("status") in ("active", "pending") and _matches(r, args.match),
            lambda r, now: r.update(status="retired", retired_reason=args.reason, retired_at=now), "retire")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect, promote and prune the judge calibration KB.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List KB entries for a language.")
    p.add_argument("language")
    p.add_argument("--status", choices=STATUSES, default=None)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("promote", help="Mark pending entries as reviewed + active.")
    p.add_argument("language")
    p.add_argument("match", nargs="?", default=None, help="ID prefix or query substring.")
    p.add_argument("--all-pending", action="store_true")
    p.add_argument("--domain", default=None, help="Only promote records from this domain.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_promote)

    p = sub.add_parser("prune", help="Mark matching active/pending entries as pruned.")
    p.add_argument("language")
    p.add_argument("match", help="ID prefix or query substring.")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_prune)

    p = sub.add_parser("retire", help="Mark matching entries as retired (superseded rules).")
    p.add_argument("language")
    p.add_argument("match", help="ID prefix or query substring.")
    p.add_argument("--reason", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_retire)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
