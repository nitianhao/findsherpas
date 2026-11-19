# Copied evaluation knowledge

Snapshot date: 2026-10-19. `MANIFEST.json` records every copied file, its source path in the main project, and a checksum. This is a duplicate, not a move or a live link.

| Folder | Contents | Use |
| --- | --- | --- |
| `playbooks/` | Six per-phase operational playbooks | Read before the corresponding research step; record new corrections here |
| `calibration/` | 119 German and Swedish JSONL prompt examples | Advisory examples for the existing AI judge; not a verified benchmark |
| `archive/raw/` | Eight full audit JSON files, 480 query judgments | Provisional case-level research data |
| `archive/html/` | 14 published report snapshots, titles totaling 854 tested queries | Historical reports; six have no local raw JSON |

The six HTML-only audits are Lyko, Miinto, Nordic Nest, Sportamore, The Reformation, and Woodie's. HTML may omit product IDs, exact result order, or other information needed to verify a case. The raw audits also contain machine judgments that require expert review before being called gold labels.

The copied playbooks contain original `src/audit/...` path references because the files are exact snapshots. In this subproject, read and update the copies under `evaluation/knowledge/playbooks/`. Only sync a learning back to the main project intentionally after review. New run outputs belong under `evaluation/runs/`; new auto-harvested examples stay in each run's `proposed_calibration/` until vetted.
