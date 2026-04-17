---
name: synthetic-search-audit
description: >
  Run or extend the Synthetic Search Audit pipeline. Use when the user wants to
  audit a site's search quality, understand the pipeline phases, add new output
  types, or work on the sales materials generation (exec summary, brief, cold email).
---

# Synthetic Search Audit — Pipeline Reference

## What It Does

Fully automated 7-phase search quality audit for any ecommerce or marketplace site.
Given a URL, it generates: a deep-dive narrative report (Markdown + JSON), and three
sales derivative documents (Executive Summary, Forwardable Brief, Cold Email Snippet).

All output lands in `reports/{domain_slug}/` alongside each other.

---

## How to Run

```bash
# Preferred: pass a search results page URL directly
python -m src.orchestrator "https://www.example.com/search?q=shoes"

# Homepage URL (auto-detects search form; less reliable)
python -m src.orchestrator "https://www.example.com"

# Override the search URL template manually
python -m src.orchestrator "https://www.example.com" \
  --search-url "https://www.example.com/search?q={}"

# Custom output directory
python -m src.orchestrator "https://www.example.com" --output-dir my_reports
```

> **Mac only** — the `.env` contains a SOCKS proxy (`ALL_PROXY`). Running in a
> sandboxed environment (e.g. Cowork shell) will fail with a `socksio` import error.
> Always run on the Mac terminal.

---

## Output Files

All files share a common slug prefix: `{domain_slug}_{YYYYMMDD_HHMMSS}`

| File | Description |
|------|-------------|
| `{slug}_report.md` | Full deep-dive narrative (Markdown) |
| `{slug}_data.json` | Complete AuditReport as JSON (all judgments, scores, raw data) |
| `{slug}_exec_summary.docx` | 2-page Executive Summary for prospects |
| `{slug}_brief.docx` | 1-page Forwardable Brief (VP/CMO-ready) |
| `{slug}_cold_email.txt` | Cold email opener, 3 versions (plain text) |

---

## Pipeline Phases

| Phase | Module | What it does |
|-------|--------|--------------|
| 1 | `src/discovery.py` | Scrapes the site: nav categories, brands, featured items, search URL template |
| 2 | `src/category_selector.py` | Picks which `QueryCategory` types to test based on `SiteType` |
| 3 | `src/query_generator.py` | Generates ~20–30 test queries via Claude |
| 4 | `src/fetcher.py` | Fetches search results for every query (requests + BeautifulSoup) |
| 5 | `src/scorer.py` | Scores relevance of each result via Voyage AI `rerank-2-5` |
| 6 | `src/judge.py` | Assigns `FailureMode`, `Severity`, `displacement`, `evidence` per query via Claude |
| 7 | `src/report_generator.py` | Builds `AuditReport` with `CapabilityScore` groups + narrative via Claude |
| Post | `src/sales_materials_generator.py` | Generates 3 sales docs from the completed report |

---

## Sales Materials Generation

### Entry Point

```python
from src.sales_materials_generator import generate_sales_materials

generate_sales_materials(report, out_dir, slug)
```

Called automatically at the end of `run_audit()` in `orchestrator.py`. Takes the same
`AuditReport` object returned by `generate_report()`.

### Three Outputs

**Executive Summary** (`_exec_summary.docx`)
- 2 pages, 4 sections: What We Found / The Findings That Matter / The Revenue Picture / Next Step
- Opens with pass rate and average best-result position
- Each finding section (`###` sub-heading) names a specific query, what the customer saw, and the best-result position number
- Soft CTA: 30-minute walkthrough of top 3 fixes ranked by effort-to-impact

**Forwardable Brief** (`_brief.docx`)
- 1 page, memo format (`TO: / FROM: / RE: / DATE:`)
- 4 short paragraphs: headline stat → concrete example → pattern + fix → call to action
- Designed to be forwarded from a mid-level contact to their VP or CMO
- Readable in 90 seconds

**Cold Email Snippet** (`_cold_email.txt`)
- 3 versions (A, B, C), 2–4 sentences each
- Version A and B: each uses a different specific audit finding
- Version C: uses aggregate stats (pass rate, avg position, ranking failure rate)
- No intro, no sign-off — starts mid-thought, names something verifiable

### Branding

- Font: Calibri throughout
- Primary color: teal `#009BA3` (Find Sherpas brand)
- Branded header: `Find Sherpas | {doc_type} | {site_name}` with teal rule
- Footer: `findsherpas.com` (centered, muted)
- `FROM:` line in brief reads `[Name], Find Sherpas` — update `AGENCY_SENDER_NAME` in `.env` to auto-populate (not yet wired)

### Key Internal Logic

**Data extraction** (`_extract_sales_context`)

Computes from `AuditReport`:
- `capabilities_passed` / `total_capabilities` — how many `CapabilityScore` groups have severity = PASS
- `avg_best_position` — mean of `(displacement + 1)` across all `QueryJudgment`s
- `pct_in_top3` — % of queries where `displacement <= 2`
- `ranking_failures` — count of `failure_mode == "POOR_RANKING"`
- `critical_caps` — list of capability group names with severity = CRITICAL
- `top_findings` — top 4 non-pass judgments, sorted by severity then effective displacement

**Egregious failure mode handling**

`NO_FUZZY_MATCHING` and `ZERO_RESULTS_OR_GARBAGE` have `displacement = 0` in the data
because the garbage result sits at position #1. But their actual severity is worse than
a typical ranking miss. To sort them correctly, `_effective_displacement()` maps those
modes to `9999` so they float to the top of the findings list.

```python
_EGREGIOUS_MODES = {"NO_FUZZY_MATCHING", "ZERO_RESULTS_OR_GARBAGE"}

def _effective_displacement(j) -> int:
    return 9999 if j.failure_mode in _EGREGIOUS_MODES else j.displacement
```

**Docx rendering** (`_write_docx`)

Parses Claude's Markdown-structured output line by line:
- `## heading` → teal, bold, 12pt
- `### heading` → dark, bold, 11pt (used for named findings)
- `TO:/FROM:/RE:/DATE:` → bold label + normal value (memo header)
- everything else → body paragraph, 10pt

---

## Key Models (`src/models.py`)

```
AuditReport
  ├── site_context: SiteContext (url, site_name, site_type, nav_categories, brands, ...)
  ├── selected_categories: list[QueryCategory]
  ├── queries: list[TestQuery]
  ├── capability_scores: list[CapabilityScore]
  │     ├── capability: CapabilityGroup
  │     ├── severity: Severity
  │     ├── summary: str
  │     └── judgments: list[QueryJudgment]
  │           ├── test_query: TestQuery (category, query, rationale)
  │           ├── results: list[ScoredResult] (title, price, relevance_score, original_rank)
  │           ├── failure_mode: FailureMode
  │           ├── severity: Severity
  │           ├── evidence: str
  │           ├── displacement: int  (0 = best result at #1)
  │           ├── max_relevance_score: float
  │           └── top3_original_average: float
  ├── deep_dive_narrative: str
  └── roadmap_narrative: str
```

**Severity enum values** (full string, used for comparison):
- `"Critical — Customers searching this way see irrelevant results. This directly loses sales."`
- `"Moderate — Results are partially relevant but the experience is degraded. Customers may bounce."`
- `"Minor — Niche edge case. Low search volume, but still a gap."`
- `"Pass — Search handles this well."`

---

## Dependencies

```
anthropic          # Claude API (sonnet-4-20250514)
beautifulsoup4     # HTML scraping
jinja2             # Templating (report generation)
pydantic           # Data models
python-docx        # .docx file writing (exec summary + brief)
python-dotenv      # .env loading
requests           # HTTP fetching
voyageai           # Relevance scoring (rerank-2-5)
```

Install: `pip install -r requirements.txt`

---

## Common Tasks

### Add a new sales output type

1. Add a new prompt builder function `_new_prompt(ctx: dict) -> str` in `sales_materials_generator.py`
2. Call `_call_claude(_new_prompt(ctx))` in `generate_sales_materials()`
3. Write the output with `_write_docx()` or `Path.write_text()` depending on format

### Modify prompt copy

All three prompts are fully parameterized — no hardcoded site names or examples.
Edit `_exec_summary_prompt()`, `_brief_prompt()`, or `_cold_email_prompt()` in
`src/sales_materials_generator.py`. The `ctx` dict keys available are:

```python
ctx = {
    "site_name", "site_url",
    "capabilities_passed", "total_capabilities", "total_queries",
    "avg_best_position", "pct_in_top3", "pct_outside_top3",
    "ranking_failures", "pct_ranking_failure",
    "critical_caps",       # list[str] — capability group names
    "top_findings",        # list[dict] — see _extract_sales_context()
}
```

Each finding in `top_findings`:
```python
{
    "query", "severity", "best_position", "displacement",
    "failure_mode", "evidence",
    "customer_saw",   # list[str] — "#1 Title (price)" format
    "best_match",     # str — highest-relevance-scored result
}
```

### Re-run sales materials on an existing data.json

```python
import json
from pathlib import Path
from src.models import AuditReport
from src.sales_materials_generator import generate_sales_materials

data = json.loads(Path("reports/example_com/example_com_20260410_data.json").read_text())
report = AuditReport.model_validate(data)
generate_sales_materials(report, Path("reports/example_com"), "example_com_20260410_rerun")
```

---

## Brand Voice Reminders

When editing prompts, preserve these rules:
- Short sentences. Direct assertions. No hedging.
- Forbidden words: "leverage," "synergy," "optimize," "robust," "exciting," "deep dive," "fascinating," "powerful," "unique"
- No methodology section in exec summary
- Cold email: starts mid-thought, no "hope this finds you well," no sign-off
- Tone: peer-to-peer, consultative — assume the reader is smart and has seen plenty of agency pitches
