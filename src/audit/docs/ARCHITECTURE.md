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
> (`src/orchestrator.py`, `src/github_publisher.py`).

---

## What it does

A search-quality audit for any ecommerce/marketplace site. Given a search-results URL, it
produces: a deep-dive narrative report (Markdown + JSON) and a styled HTML report.
All output lands in `reports/{domain_slug}/`.

## Two run modes

| Mode | How | When |
|------|-----|------|
| **A — gated manual (default)** | Call individual `src.*` phase functions via `python3 -c`, stopping for approval between phases. See the skill. | Default. Quality-first; lets you correct categories/queries before they poison the report. |
| **C — automated orchestrator (fast)** | `python -m src.orchestrator "<search-url>"` runs all phases through publish in one shot. | When you trust the inputs and want speed/volume. |

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
| 3 | `src/query_generator.py` | Generates ~20–30 test queries via Claude; validates category fit (rejects miscategorized queries, e.g. a nav-category label filed under `DIRECT_MATCH` — see note below) |
| 4 | `src/fetcher.py` | Fetches search results per query (requests + BeautifulSoup) |
| 5 | `src/scorer.py` | Scores relevance via Voyage AI `rerank-2-5` |
| 6 | `src/judge.py` | Assigns `FailureMode`, `Severity`, `displacement`, `evidence` per query via Claude, then applies a deterministic severity cap for immaterial displacement (see note below). Injects per-language calibration examples from past audits and harvests this run's verdicts back (`src/judge_kb.py`, see note below) |
| 7 | `src/report_generator.py` | Builds `AuditReport` with `CapabilityScore` groups + narrative |
| Publish | `src/github_publisher.py` | Uploads HTML + registers report (see below) |

---

## Output files

Common slug prefix: `{domain_slug}_{YYYYMMDD_HHMMSS}`

| File | Description |
|------|-------------|
| `{slug}_report.md` | Deep-dive narrative (Markdown) |
| `{slug}_data.json` | Complete `AuditReport` as JSON |
| `{slug}_report.html` | Styled HTML report (from `templates/master_report.html`) |
| `{slug}_access.json` | Written by the orchestrator: `company_slug`, `report_url`, `published_at` |
| `findsherpas.com/report/{company}-NNNN/` | Live published report URL (unlisted) |

---

## GitHub publishing (verified vs `github_publisher.py`)

`publish_report(html_content, domain_slug, data_json=None, report_md=None) -> url` pushes up to
**four files** to the `nitianhao/findsherpas` repo (all via the GitHub contents API, which
commits server-side and so bypasses the local `reports/*` gitignore):

1. **`public/report/{slug}/index.html`** → the live findsherpas.com page.
2. **`reports/report_slugs.json`** → the registry the CRM Reports page reads. The registry
   **must** be committed to the repo (not just updated locally) or the report stays invisible
   in the deployed CRM.
3. **`audit-data/{slug}/{slug}_data.json`** and **`{slug}_report.md`** (when `data_json` /
   `report_md` are passed) → a version-controlled archive of the raw audit data so the
   underlying judgements survive a local wipe. Not under `public/` — never web-served. The
   orchestrator and the Phase 8 skill step always pass these; callers re-publishing by hand
   should too.

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

### Materiality cap on ranking severity (`judge.py`)

`displacement` (original rank of the best-scoring result − 1) is **not** a sufficient basis for a `CRITICAL` `POOR_RANKING` call on its own. After the LLM verdict (and in the stats-only fallback), `_ranking_materially_broken()` checks whether reordering by relevance would *materially* change what the shopper sees: if the result the customer saw at original rank #1 is already within `MATERIAL_RANK_GAP` (0.20) of the best available result, the misordering is cosmetic and the severity is capped at `MODERATE`. The judge prompt also surfaces this gap and instructs Claude not to flag immaterial displacement as critical.

This prevents broad/generic queries with tightly clustered, all-relevant results (e.g. a category term where every hit is on-topic) from being over-reported as severe ranking failures. The LLM judge still owns nuance; the cap is a deterministic floor on over-severity.

### Calibration knowledge base (`judge_kb.py`)

A per-language store of past judgements that anchors the judge for **consistency** and lets it reuse strong fix/evidence phrasing. It is **advisory anchoring, not a cache** — every query is still judged fresh against its own results; a past verdict is never reused as this query's verdict (results differ per site).

- **Storage:** `src/audit/kb/{lang}.jsonl`, one record per line, language slugged from `site_context.primary_language` (e.g. `german.jsonl`). Each record holds the query, category, `severity`/`failure_mode`/`evidence`/`recommended_fix`, a Voyage embedding, `provenance` (domain, url, `judged_at`), and `status` (`active`/`pruned`). The `kb/` dir is created on first harvest.
- **Step A — retrieval (before each LLM call):** filter to `active` + same language, prefer same `category` (widen to any-category when <2 matches), Voyage-embed the live query, cosine-rank, take **top 3**. Injected as a "Calibration Examples" section of the judge prompt. Degrades to recency ranking if embeddings are unavailable, and to a silent no-op if the KB file is missing or anything errors — so judging behaves exactly as before when the KB is empty.
- **Step B — harvest (after the whole audit):** appends this run's verdicts to `kb/{lang}.jsonl`. Skips LLM-fallback verdicts (`"LLM analysis failed"` in evidence) and unclassified non-PASS verdicts (`OTHER` failure mode that isn't a PASS); PASS examples are kept as "what good looks like."
- **Wiring & safety:** `judge_all_queries(..., language=None, provenance=None)` — both args optional; with `language=None` the KB is bypassed entirely (existing callers/tests unchanged). The orchestrator passes `site_context.primary_language` + provenance at Phase 6. All KB reads/writes/embeds are wrapped so a KB failure logs a warning and never breaks an audit. Reuses the existing `voyageai` client (embedding model `voyage-3.5`, overridable via `VOYAGE_EMBED_MODEL`); no new dependencies.
- **Pruning:** `scripts/kb_prune.py list <lang>` / `prune <lang> <id-or-query-substring>` flips `status` to `pruned` (kept for audit trail, excluded from retrieval). This plus the Step B noise filter are the drift guards for the auto-harvest model.
- **First-run caveat:** the first audit in a new language writes to an empty KB and gets no calibration benefit; the payoff compounds from audit #2 onward per language.

### Category-fit validation (`query_generator.py`)

`_category_mismatch_reason()` rejects queries that definitionally don't fit their category before they enter the audit. The high-precision check in place: a `DIRECT_MATCH` query (which must reference a *specific product the shopper already knows by name*) whose text exactly equals one of the site's real navigation-category labels is rejected — the generation loop then regenerates to refill that category's target count. This stops generic category terms (e.g. "parfym") from producing misleading "direct match buried at #N" findings.

### Evidence snippet trimming (`html_renderer.py`)

`_trim_evidence()` shortens free-text `evidence` for compact callouts (e.g. the pattern-calibration example). It ends on the fullest natural boundary that fits — sentence breaks preferred, clause breaks as fallback — so a snippet never reads as cut off mid-sentence. Note: decimal figures like `0.621` are not treated as sentence boundaries (a boundary requires a trailing space).

### Advanced diagnostics — zero-result exclusion & non-ASCII tokenization (`advanced_diagnostics.py`)

These diagnostics assess the quality of the *visible* result set, so queries that returned **no results** are excluded from them entirely — `Result Set Purity`, `Top Result Trust`, and `Attribute Drift` all skip zero-result queries. A dead-end query has no #1 result to trust and no products to inspect for attribute coverage; counting it here inflates failure rates and emits nonsensical evidence (`#1 was "No results"`, or "every term dropped"). Dead ends are captured separately by the `ZERO_RESULTS_OR_GARBAGE` failure mode and reflected in the purity denominator. Failure rates are therefore computed over *evaluated* (result-bearing) queries, not all queries. (See also the `feedback_zero_result_stats` rule for executive-summary position stats.)

Tokenization (`_query_terms`) and family-key extraction (`_family_key`) are **Unicode-aware** (`[^\W_]+` / `[^\w\s-]`), not ASCII-only. An ASCII-only regex shreds non-English query words (e.g. Swedish "kläder" → "kl","der"), which then never match product titles and surface as falsely "dropped" attributes. This matters for any non-English site. Note that `Attribute Drift` matches query terms against result **titles** by substring, so attributes expressed only in facets/variants (color, size) or as compound/plural forms ("väskor" vs "axelväska") can legitimately read as low coverage — it is a directional title-coverage signal, not a semantic relevance measure.

**`Attribute Drift` only assesses title-observable terms.** Title-substring matching cannot see attributes carried in facet metadata — colour, size, gender, generic category words almost never appear in product titles — so naively treating them as "dropped" produced a false failure for nearly every multi-attribute query (the original bug). The diagnostic now classifies each query term against the actual result set:

- **preserved** — the term appears in a TOP-5 result title;
- **dropped** — the term appears *somewhere* in the returned result titles but **not** in the top 5 (matching products exist yet are ranked below — genuine, observable ranking drift);
- **unverifiable** — the term appears in **no** returned title (a facet/metadata attribute, or the engine returned nothing matching — indistinguishable from titles, so we don't guess).

A query is reported as drift **only** when it has both a *preserved* anchor and a *dropped* observable attribute. Total misses (no preserved anchor) and zero-result queries are left to the failure-mode analysis. When a catalog expresses its attributes only in facets (common for non-fashion retail — e.g. Åhléns), the section honestly reports "no title-observable drift" and counts the `unverifiable` queries rather than inventing dropped attributes. `common_dropped` counts only observable dropped terms from reported rows.

---

## Dependencies

```
anthropic          # Claude API
beautifulsoup4     # HTML scraping
jinja2             # Templating (report generation)
pydantic           # Data models
python-dotenv      # .env loading
requests           # HTTP fetching
voyageai           # Relevance scoring (rerank-2-5)
```

Install: `pip install -r requirements.txt`

---

## Brand voice (when editing prompts)

- Short sentences. Direct assertions. No hedging.
- Forbidden: "leverage," "synergy," "optimize," "robust," "exciting," "deep dive,"
  "fascinating," "powerful," "unique"
- Tone: peer-to-peer, consultative — the reader is smart and has seen plenty of agency pitches
- Do not name the site's own language repeatedly. The reader is a native speaker, so qualifying every fix as "[Language] …" reads as templated. The narrative prompt forbids it, and `_limit_language_mentions()` in `report_generator.py` deterministically enforces a cap of one mention across deep dives + roadmap combined (using `site_context.primary_language`), stripping the rest. Let the quoted query examples convey the language instead.
