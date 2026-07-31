# Judge Calibration Knowledge Base — Design

**Date:** 2026-06-16
**Status:** Approved (design); pending implementation plan
**Component:** `src/audit` (synthetic search audit pipeline)

## Problem

The LLM judge (`src/audit/src/judge.py`) grades every test query with an independent,
stateless Sonnet call. It has no memory of how it graded similar queries earlier in the
same audit, or in any past audit. This causes two issues:

1. **Inconsistency / drift** — the severity bar (CRITICAL vs MODERATE) and failure-mode
   labeling can vary between runs and between similar queries.
2. **Lost quality** — strong `recommended_fix` / `evidence` phrasing written in one audit
   is never reused; every report reinvents it.

Judgements *are* persisted today (each audit writes `{slug}_data.json` with all
`QueryJudgment` objects) but nothing reads them back. There is no cross-audit index.

## Goal

A per-language knowledge base of past judgements that the judge consults at runtime to
(a) grade **consistently** and (b) reuse strong fix/evidence phrasing. It is **advisory
anchoring, not a cache** — the judge still judges every query fresh against that query's
own results; KB examples only calibrate severity/labeling and supply reference phrasing.

### Explicit non-goals
- **Not a result cache.** A past verdict is tied to a specific site's results and does not
  transfer as a verdict to a different site. We never skip a judge call based on the KB.
- **No DB, no schema, no UI.** Local files in the repo only.
- **No human approval gate on capture.** Capture is automatic (auto-harvest, then prune).

## How it works inside the pipeline

The site's primary language is already detected in Phase 1 (`discovery.py`
`_detect_primary_language` → `site_context.primary_language`), e.g. `de`. That selects the
KB file `kb/de.jsonl` for the whole run.

Two hooks attach to the existing Phase 6 judging loop:

### Step A — before judging each query (read the notebook)
Inside `_judge_single_query`, before the Sonnet call:
1. Load `kb/{lang}.jsonl`, keep entries with `status:"active"` AND the **same category**.
2. Voyage-embed the current query, cosine-rank the candidates, take **top 3**.
3. Fallback: if fewer than 2 same-category matches exist, widen to same-language /
   any-category. If the file is missing or empty, inject nothing (behaves like today).
4. Render the 3 picks into a "Calibration Examples" section of the prompt.

### Step B — after the audit (write the notebook)
After `judge_all_queries` completes, append each fresh verdict as a new line to
`kb/{lang}.jsonl`. **Skip noise:** LLM-fallback verdicts (evidence contains
`"LLM analysis failed"`) and `OTHER` / empty-evidence verdicts never become anchors.

The payoff compounds: audit #1 in a new language writes to an empty notebook and gets no
calibration benefit; audit #2 onward in that language does.

## Storage

`src/audit/kb/{lang}.jsonl` — one file per language, one JSON record per line:

```json
{
  "id": "uuid",
  "query": "laufschuhe ohne nike",
  "category": "NEGATIVE_INTENT",
  "language": "de",
  "severity": "MODERATE",
  "failure_mode": "CONSTRAINT_DROPPED",
  "evidence": "...",
  "recommended_fix": "...",
  "embedding": [0.01, -0.02, "..."],
  "provenance": { "audit_slug": "...", "domain": "...", "judged_at": "ISO-8601" },
  "status": "active",
  "source": "harvested"
}
```

Embedding is computed once at harvest (Voyage `embed`) and stored inline, so retrieval
never re-embeds the bank — only the single live query is embedded per judge call.

## Injection (prompt section)

Added after the severity criteria in `_build_prompt`:

> Here is how similar queries were graded in past audits, for consistency. Use them to
> calibrate severity and failure-mode labeling. Do NOT copy them — the products differ;
> judge this query on its own results.

Followed by up to 3 compact lines:
`query → SEVERITY / FAILURE_MODE — one-line evidence gist`, plus the `recommended_fix`
text so the model can echo good phrasing.

## Pruning

`src/audit/scripts/kb_prune.py` — list/grep entries and flip `status` to `"pruned"`
(kept for audit trail, not deleted). Pruned entries are excluded from retrieval. This is
the drift guard for the auto-harvest model, alongside the Step B noise filter.

## Wiring & safety

- `judge.py` gains `_load_kb(lang, category, query)` (retrieval) and
  `_harvest(judgments, lang, provenance)` (capture).
- `judge_all_queries` takes new **optional** `language` and `provenance` args; defaults
  make the whole feature a no-op, so existing callers and tests keep working unchanged.
- `orchestrator.py` passes `site_context.primary_language` and a provenance dict
  (`audit_slug`, `domain`, timestamp) into `judge_all_queries`.
- All KB reads/writes/embeds are wrapped in try/except → a KB failure logs a warning and
  never breaks an audit.
- Dependencies: reuses existing `voyageai` client; no new packages.

## Defaults (decided)

- **Top-K = 3** calibration examples per query.
- **Per-language file split** (`kb/{lang}.jsonl`), not one file with a language column.

## Testing

- `_load_kb` returns `[]` when file missing → judge behaves exactly as today (no-op proof).
- Category filter + same-language fallback select expected records from a fixture KB.
- Noise filter excludes fallback / `OTHER` / empty-evidence verdicts on harvest.
- Harvest appends well-formed JSONL lines with provenance + embedding.
- Pruned entries are excluded from retrieval.
- Judge call still succeeds when Voyage embedding fails (caught, empty examples).
