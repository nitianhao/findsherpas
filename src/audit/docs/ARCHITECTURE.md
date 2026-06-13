# Synthetic Search Audit — Architecture & Code Reference

> **Scope:** This is the *engineering reference* for the audit pipeline — how the code is
> built and how to extend it. It is **not** the operating procedure. To *run* an audit,
> follow the `synthetic-search-audit` skill (the gated, phase-by-phase procedure).
>
> Single sources of truth:
> - **How to run an audit** → `synthetic-search-audit` skill (default: gated manual mode)
> - **How the code works** → this document
>
> All facts below are verified against the code as of 2026-06-08
> (`src/orchestrator.py`, `src/github_publisher.py`, `src/sales_materials_generator.py`).

---

## What it does

A search-quality audit for any ecommerce/marketplace site. Given a search-results URL, it
produces: a deep-dive narrative report (Markdown + JSON), a styled HTML report, and three
sales derivative documents (Executive Summary, Forwardable Brief, Cold Email Snippet).
All output lands in `reports/{domain_slug}/`.

## Two run modes

| Mode | How | When |
|------|-----|------|
| **A — gated manual (default)** | Call individual `src.*` phase functions via `python3 -c`, stopping for approval between phases. See the skill. | Default. Quality-first; lets you correct categories/queries before they poison the report. |
| **C — automated orchestrator (fast)** | `python -m src.orchestrator "<search-url>"` runs all phases + publish + sales materials in one shot. | When you trust the inputs and want speed/volume. |

```bash
# Fast mode (orchestrator)
python -m src.orchestrator "https://www.example.com/search?q=shoes"
python -m src.orchestrator "https://www.example.com" --search-url "https://www.example.com/search?q={}"
python -m src.orchestrator "https://www.example.com" --crm-company-id <instantdb-company-id>
python -m src.orchestrator "https://www.example.com" --output-dir my_reports
```

> **Mac only** — `.env` contains a SOCKS proxy (`ALL_PROXY`). Sandboxed shells fail with a
> `socksio` import error. Always run on the Mac terminal.

---

## Pipeline phases (code)

| Phase | Module | What it does |
|-------|--------|--------------|
| 1 | `src/discovery.py` | Scrapes nav categories, brands, featured items, search URL template |
| 2 | `src/category_selector.py` | Picks which `QueryCategory` types to test based on `SiteType` |
| 3 | `src/query_generator.py` | Generates ~20–30 test queries via Claude |
| 4 | `src/fetcher.py` | Fetches search results per query (requests + BeautifulSoup) |
| 5 | `src/scorer.py` | Scores relevance via Voyage AI `rerank-2-5` |
| 6 | `src/judge.py` | Assigns `FailureMode`, `Severity`, `displacement`, `evidence` per query via Claude |
| 7 | `src/report_generator.py` | Builds `AuditReport` with `CapabilityScore` groups + narrative |
| Publish | `src/github_publisher.py` | Uploads HTML + registers report (see below) |
| Post | `src/sales_materials_generator.py` | Generates the 3 sales docs from the completed report |

---

## Output files

Common slug prefix: `{domain_slug}_{YYYYMMDD_HHMMSS}`

| File | Description |
|------|-------------|
| `{slug}_report.md` | Deep-dive narrative (Markdown) |
| `{slug}_data.json` | Complete `AuditReport` as JSON |
| `{slug}_report.html` | Styled HTML report (from `templates/master_report.html`) |
| `{slug}_exec_summary.docx` | 2-page Executive Summary |
| `{slug}_brief.docx` | 1-page Forwardable Brief |
| `{slug}_cold_email.txt` | Cold email opener, 3 versions |
| `{slug}_access.json` | Written by the orchestrator: `company_slug`, `report_url`, `published_at` |
| `findsherpas.com/report/{company}-NNNN/` | Live published report URL (unlisted) |

---

## GitHub publishing (verified vs `github_publisher.py`)

`publish_report(html_content, domain_slug) -> url` does two things, pushing **two files** to
the `nitianhao/findsherpas` repo:

1. **`public/report/{slug}/index.html`** → the live findsherpas.com page.
2. **`reports/report_slugs.json`** → the registry the CRM Reports page reads. The registry
   **must** be committed to the repo (not just updated locally) or the report stays invisible
   in the deployed CRM. `publish_report` pushes both.

- **Slug format:** `{company}-{4-digit}` (e.g. `huckberry-6746`). TLD suffixes stripped:
  `huckberry_com` → `huckberry`, `www_zalando_de` → `zalando`. Stored in `report_slugs.json`
  as `{company: {slug, url}}`; re-publishes reuse the existing slug.
- **No password gate.** The HTML is unlisted (non-guessable slug) and `noindex`. There is no
  password generation and no `passwords.json` — that system was removed. (Any stray
  `passwords.json` on disk is a relic.)
- **Requires** `gh` CLI authenticated as the repo owner (`gh auth status`).

```python
# Re-publish an existing report
from pathlib import Path
from src.github_publisher import publish_report
html = Path("reports/huckberry_com/huckberry_com_20260506_report.html").read_text()
url = publish_report(html, "huckberry_com")
print(url)
```

**Verify a publish (check the REPO copy, not just local):**
- `gh api /repos/nitianhao/findsherpas/contents/reports/report_slugs.json --jq '.content' | base64 -d` contains the `{company}` entry.
- `gh api /repos/nitianhao/findsherpas/contents/public/report/{slug}/index.html --jq '.size'` matches the local HTML byte size.

The CRM row appears after the Vercel redeploy (~1–2 min).

---

## CRM writeback (email sequence variables)

If the audited company exists in the CRM, pass its InstantDB id so the report URL and audit
personalization variables are written immediately:

```bash
python3 src/audit/src/orchestrator.py "https://example.com/search?q=shoes" \
  --crm-company-id <instantdb-company-id>
```

For an existing report artifact, write the same fields manually:

```bash
npx tsx --tsconfig tsconfig.json src/enrichment/scripts/writeAuditToCRM.ts \
  --company-id <instantdb-company-id> \
  --report reports/example/example_YYYYMMDD_HHMMSS_data.json \
  --report-url https://findsherpas.com/report/example/
```

CRM email sequences use company-level audit variables from this writeback: `{{score}}`,
`{{query_count}}`, `{{top_3_rate}}`, `{{outside_3_rate}}`, `{{worst_query}}`, `{{worst_pos}}`,
`{{wrong_product}}`, `{{search_platform_sentence}}`, `{{report_url}}`. `{{query_count}}` is
derived from the actual number of query judgments. `{{search_platform_sentence}}` is
intentionally cautious and currently renders `Looks fixable without replatforming.`

---

## Report presentation rules (client-facing HTML)

- Reusable template: `src/audit/templates/master_report.html`.
- Reports **must** show the Find Sherpas logo/wordmark on the cover. Keep the cover logo block
  in the template and the SVG at `src/audit/assets/logo.svg`; do not ship without it.
- Cover = boutique agency presentation: large logo/wordmark, clean client name line, separate
  `Prepared by` block (`Name`, `Agency`, `Contact`).
- Do **not** put `findsherpas.com` inside the logo lockup — put it in the `Prepared by` block.
- Do **not** include a methodology/process section, or expose automation/scoring/scraper/LLM
  details in the rendered report.
- Keep: short-version summary, revenue-risk hero, tier cards, coverage heatmap, revenue-risk
  failure cards, deep dives, appendix, scope/boundaries section, final CTA.
- Final CTA links to `https://findsherpas.com/book-a-call`.

---

## Sales materials generation

```python
from src.sales_materials_generator import generate_sales_materials
generate_sales_materials(report, out_dir, slug)
```

Called automatically at the end of `run_audit()`. Takes the `AuditReport` from `generate_report()`.

**Executive Summary** (`_exec_summary.docx`) — 2 pages, 4 sections (What We Found / The
Findings That Matter / The Revenue Picture / Next Step). Opens with pass rate + avg best
position. Soft CTA: 30-minute walkthrough of top 3 fixes by effort-to-impact.

**Forwardable Brief** (`_brief.docx`) — 1 page memo (`TO/FROM/RE/DATE`), 4 short paragraphs
(headline stat → example → pattern + fix → CTA). Readable in 90 seconds.

**Cold Email Snippet** (`_cold_email.txt`) — 3 versions (A/B/C), 2–4 sentences. A and B each
use a specific finding; C uses aggregate stats. No intro, no sign-off.

**Branding:** Calibri; teal `#009BA3`; header `Find Sherpas | {doc_type} | {site_name}`;
footer `findsherpas.com`. `FROM:` reads `[Name], Find Sherpas` — set `AGENCY_SENDER_NAME` in
`.env` (not yet wired).

### Internal logic

`_extract_sales_context(report)` computes: `capabilities_passed`/`total_capabilities`,
`avg_best_position` (mean of `displacement + 1`), `pct_in_top3` (`displacement <= 2`),
`ranking_failures` (`failure_mode == "POOR_RANKING"`), `critical_caps`, `top_findings`
(top 4 non-pass judgments by severity then effective displacement).

`NO_FUZZY_MATCHING` and `ZERO_RESULTS_OR_GARBAGE` have `displacement = 0` (garbage sits at #1)
but are worse than a ranking miss, so `_effective_displacement()` maps them to `9999` to float
them to the top:

```python
_EGREGIOUS_MODES = {"NO_FUZZY_MATCHING", "ZERO_RESULTS_OR_GARBAGE"}
def _effective_displacement(j) -> int:
    return 9999 if j.failure_mode in _EGREGIOUS_MODES else j.displacement
```

`_write_docx()` parses Claude's Markdown output line by line: `## heading` → teal bold 12pt;
`### heading` → dark bold 11pt (named findings); `TO:/FROM:/RE:/DATE:` → bold label + value;
else → body 10pt.

---

## Key models (`src/models.py`)

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

**Severity enum values** (full strings, used for comparison):
- `"Critical — Customers searching this way see irrelevant results. This directly loses sales."`
- `"Moderate — Results are partially relevant but the experience is degraded. Customers may bounce."`
- `"Minor — Niche edge case. Low search volume, but still a gap."`
- `"Pass — Search handles this well."`

---

## Dependencies

```
anthropic          # Claude API
beautifulsoup4     # HTML scraping
jinja2             # Templating (report generation)
pydantic           # Data models
python-docx        # .docx writing (exec summary + brief)
python-dotenv      # .env loading
requests           # HTTP fetching
voyageai           # Relevance scoring (rerank-2-5)
```

Install: `pip install -r requirements.txt`

---

## Common tasks

### Add a new sales output type
1. Add a prompt builder `_new_prompt(ctx: dict) -> str` in `sales_materials_generator.py`
2. Call `_call_claude(_new_prompt(ctx))` in `generate_sales_materials()`
3. Write output with `_write_docx()` or `Path.write_text()`

### Modify prompt copy
All three prompts are fully parameterized — no hardcoded site names. Edit
`_exec_summary_prompt()`, `_brief_prompt()`, or `_cold_email_prompt()`. Available `ctx` keys:

```python
ctx = {
    "site_name", "site_url",
    "capabilities_passed", "total_capabilities", "total_queries",
    "avg_best_position", "pct_in_top3", "pct_outside_top3",
    "ranking_failures", "pct_ranking_failure",
    "critical_caps",   # list[str]
    "top_findings",    # list[dict]: query, severity, best_position, displacement,
                       #             failure_mode, evidence, customer_saw, best_match
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

## Brand voice (when editing prompts)

- Short sentences. Direct assertions. No hedging.
- Forbidden: "leverage," "synergy," "optimize," "robust," "exciting," "deep dive,"
  "fascinating," "powerful," "unique"
- No methodology section in exec summary
- Cold email: starts mid-thought, no "hope this finds you well," no sign-off
- Tone: peer-to-peer, consultative — the reader is smart and has seen plenty of agency pitches
