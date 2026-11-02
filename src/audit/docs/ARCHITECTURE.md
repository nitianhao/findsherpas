# Synthetic Search Audit — Architecture & Code Reference

> **Scope:** This is the *engineering reference* for the audit pipeline — how the code is
> built and how to extend it. It is **not** the operating procedure. To *run* an audit,
> follow the `synthetic-search-audit` skill (the gated, phase-by-phase procedure).
>
> Single sources of truth:
> - **How to run an audit** → `synthetic-search-audit` skill (default: gated manual mode)
> - **How the code works** → this document
> - **Per-phase lessons and site profiles** → `docs/<PHASE>_PLAYBOOK.md`
> - **Product roadmap ideas** → `docs/IMPROVEMENT_PROPOSALS.md`
>
> Verified against the code as of 2026-10-30 (judge rules version `2026-10-30`).

---

## What it does

A search-quality audit for any ecommerce/marketplace site. Given a search-results URL, it
produces a deep-dive narrative report (Markdown + JSON) and a styled HTML report. Output lands
in `src/audit/reports/{domain_slug}/`, with per-phase checkpoints in a `run_<timestamp>/`
subfolder.

Two principles run through the whole pipeline:

1. **Never score what was not observed.** A page the fetcher could not see (bot wall, timeout,
   error) carries a `FetchStatus` and is excluded from scoring. An empty result list is only a
   "zero results" finding when the page itself showed a no-results state.
2. **Never fail silently.** LLM calls go through `src/llm_compat.py`, which raises on refused,
   truncated or empty output. Any fallback a phase still takes is recorded (`SiteContext.provenance`,
   `QueryJudgment.judge_status`), and the publish gate blocks reports that contain one.

## Two run modes

| Mode | How | When |
|------|-----|------|
| **A — gated manual (default)** | Call individual `src.*` phase functions, stopping for approval between phases. See the skill. | Default. Quality-first; lets you correct categories/queries before they poison the report. |
| **C — automated orchestrator (fast)** | `python -m src.orchestrator "<search-url>"` runs every phase, renders the report and runs the publish gate. Publishing is opt-in (`--publish`). | When you trust the inputs and want speed/volume. |

Run from `src/audit/` with the 3.12 venv (system python 3.9/LibreSSL fails TLS on modern sites):

```bash
.venv312/bin/python -m src.orchestrator "https://www.example.com/search?q=shoes"
.venv312/bin/python -m src.orchestrator "https://www.example.com" --search-url "https://www.example.com/search?q={}"
.venv312/bin/python -m src.orchestrator "<url>" --resume reports/example_com/run_20261030_120000   # skip completed phases
.venv312/bin/python -m src.orchestrator "<url>" --publish --crm-company-id <instantdb-company-id>
```

Flags: `--allow-unverified` (continue when >20% of pages could not be observed; those queries
are excluded), `--no-controls` (skip control searches), `--output-dir`.

Run the offline test suite (no network, no paid calls) after any change:

```bash
.venv312/bin/python -m unittest discover -s tests -t .
```

---

## Pipeline phases (code)

| Phase | Module | What it does |
|-------|--------|--------------|
| 1 | `src/discovery.py` | Nav categories, brands, featured items, search URL template, language + BCP-47 `locale`, `currency`, and a `catalog_sample` of ~150 real titles (homepage + 5–8 seed searches from the nav). LLM refinement via structured output; hallucinated items dropped; fallbacks recorded in `provenance`. |
| 2 | `src/category_selector.py` | Picks 10–18 `QueryCategory` types for the `SiteType` (structured output; bounds enforced in code). |
| 3 | `src/query_generator.py` | 60 test queries. DIRECT_MATCH, GIBBERISH and SKU queries are built deterministically from real titles/codes; the rest via structured output, each with a `target_term` and (for constraint categories) `constraints`. Deterministic validators reject typo collisions, invented items and base-word reuse. |
| 4 | `src/fetcher.py` | `fetch_all_outcomes()` → one `FetchOutcome` per query with a `FetchStatus` (ok, zero_confirmed, zero_unverified, partial, redirect, blocked, timeout, error), the page's own hit count, and optional HTML/screenshot evidence. Playwright-first; per-site extractors plus generic strategies. |
| 4b | `src/orchestrator.py` | **Control searches**: every trusted zero-result query is re-searched with its plain `target_term`. Control also empty → `catalog_gap` (not scored). Control has products → the zero result is a proven search failure, and evidence may say the store carries the item. |
| 5 | `src/scorer.py` | Voyage `rerank-2.5` relevance per result (titles cleaned of badges/prefixes; price not in the document). Retries only transient errors; resumable. |
| 6 | `src/judge.py` | One structured verdict per query on the judge model, then deterministic guards (ranking materiality cap, multilingual constraint checks, price parsing, flooding rule, DIRECT_MATCH tolerance). Zero-result, gibberish and untrusted-fetch cases are decided in code. Client-facing `evidence` is kept separate from `internal_notes`. |
| 7 | `src/report_generator.py`, `src/report_stats.py`, `src/html_renderer.py` | Capability groups, stats from one module, deep dives + roadmap as structured output checked against the data (grounding validator). HTML via `templates/master_report.html` with autoescape on. |
| Gate | `src/publish_gate.py` | Blocks publishing on untrusted fetches, scraped fallback widgets, judge fallbacks, unresolved manual checks, stale rules version, and internal details in client-visible text. CLI: `python -m src.publish_gate <data.json> --html <report.html>`. |
| Publish | `src/github_publisher.py` | Uploads HTML + registry + raw data archive (see below). |

### LLM plumbing (`src/llm_compat.py`)

- `structured_call(model, system, user, schema, max_tokens, phase)` uses `messages.parse` with a
  Pydantic schema, sends the static rules as a cached system block, records token usage per
  phase (`usage_summary()` → `run_metadata.llm_usage`), and raises `LLMResponseError` on refusal,
  truncation or invalid output.
- `response_text()` joins all text blocks and raises instead of returning `""`.
- `AUDIT_STRICT_LLM=1` (default) makes discovery/category/query phases raise instead of falling back.
- Models are env-overridable per phase (`AUDIT_MODEL_DISCOVERY`, `_CATEGORIES`, `_QUERIES`,
  `_FETCHER`, `_JUDGE`, `_REPORT`). Defaults: Haiku 4.5 for discovery/categories/fetcher,
  Sonnet 4.6 for queries/judge/report.
- `temperature` is sent only to 4-series models. **Before upgrading the Anthropic SDK to 1.x**
  (API version `2026-10-21` rejects sampling params on every model), make
  `supports_temperature()` return False.

### Run directory and reproducibility

`reports/<site>/run_<timestamp>/` holds `01_site_context.json`, `02_categories.json`,
`03_queries.json`, `04_fetch.json`, `04b_controls.json`, `05_scored.json`, `06_judgments.json`
(atomic writes) and `evidence/`. `--resume` skips completed phases and re-fetches only queries
whose fetch was not trusted. `AuditReport.run_metadata` records source revision, model per
phase, `judge_rules_version`, fetch status counts, control count and token usage.

---

## Output files

Common slug prefix: `{domain_slug}_{YYYYMMDD_HHMMSS}`

| File | Description |
|------|-------------|
| `{slug}_report.md` | Deep-dive narrative (Markdown) |
| `{slug}_data.json` | Complete `AuditReport` as JSON (incl. `run_metadata`, accepted narratives) |
| `{slug}_report.html` | Styled HTML report (from `templates/master_report.html`), target < 900 KB |
| `{slug}_access.json` | Written after a publish: `company_slug`, `report_slug`, `report_url`, `published_at` |
| `findsherpas.com/report/{company}-NNNN/` | Live published report URL (unlisted) |

---

## GitHub publishing (verified vs `github_publisher.py`)

`publish_report_full(html_content, domain_slug, data_json=None, report_md=None) -> PublishResult`
(`publish_report` returns just the URL) pushes up to **four files** to the
`nitianhao/findsherpas` repo via the GitHub contents API:

1. **`public/report/{slug}/index.html`** → the live findsherpas.com page.
2. **`reports/report_slugs.json`** → the registry the CRM Reports page reads. The remote
   registry is fetched and merged with the local one first (remote wins), pushed, and only
   then mirrored locally — a stale local copy can no longer clobber repo-only entries.
3. **`audit-data/{slug}/{slug}_data.json`** and **`{slug}_report.md`** (when passed) → archive
   of the raw audit data. Not under `public/`, never web-served. Check that the repo is private.

- **Slug format:** `{company}-{4-digit}` (e.g. `huckberry-6746`). TLD suffixes stripped
  (`co_uk`, `com_au`, ccTLDs), hyphens normalised to underscores. Registry entries record the
  `domain` they were published for; a second market of the same company (`zalando_ie` after
  `zalando_de`) gets a domain-qualified key instead of overwriting the first market's page.
- GETs use the `object` media type, so re-publishing reports over 1 MB gets the file `sha`.
- **No password gate.** The HTML is unlisted and `noindex`. 4-digit suffixes are enumerable —
  see IMPROVEMENT_PROPOSALS if that matters.
- **Requires** `gh` CLI authenticated as the repo owner (`gh auth status`).

```python
# Re-publish an existing report (run the publish gate first)
from pathlib import Path
from src.github_publisher import publish_report_full
d = Path("reports/huckberry_com")
res = publish_report_full(
    (d / "huckberry_com_20260622_154614_report.html").read_text(),
    "huckberry_com",
    data_json=(d / "huckberry_com_20260622_154614_data.json").read_text(),
    report_md=(d / "huckberry_com_20260622_154614_report.md").read_text(),
)
print(res.url)
```

**Verify a publish (check the REPO copy, not just local):**
- `gh api -H "Accept: application/vnd.github.object" /repos/nitianhao/findsherpas/contents/reports/report_slugs.json --jq '.content' | base64 -d` contains the entry.
- `gh api -H "Accept: application/vnd.github.object" /repos/nitianhao/findsherpas/contents/public/report/{slug}/index.html --jq '.size'` matches the local HTML byte size.

The CRM row appears after the Vercel redeploy (~1–2 min).

---

## CRM writeback (email sequence variables)

If the audited company exists in the CRM, pass its InstantDB id so the report URL and audit
personalization variables are written immediately:

```bash
cd src/audit && .venv312/bin/python -m src.orchestrator "https://example.com/search?q=shoes" \
  --publish --crm-company-id <instantdb-company-id>
```

For an existing report artifact, write the same fields manually:

```bash
npx tsx --tsconfig tsconfig.json src/enrichment/scripts/writeAuditToCRM.ts \
  --company-id <instantdb-company-id> \
  --report reports/example/example_YYYYMMDD_HHMMSS_data.json \
  --report-url https://findsherpas.com/report/example-1234/
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

`displacement` (original rank of the best-scoring result − 1) is **not** a sufficient basis for a `CRITICAL` `POOR_RANKING` call on its own. `_apply_guards()` runs after every verdict — LLM *and* fallback:

- A reorder is **cosmetic** only when the gap between the customer's #1 and the best result is < `MATERIAL_RANK_GAP` (0.20) **and** #1 is on-topic (≥ `ON_TOPIC_TOP1_FLOOR`, 0.30) **and** the set is not weak (best ≥ 0.25). A weak, off-topic set is never eased.
- `POOR_RANKING` may be CRITICAL only when the customer's first result is off-topic (top1 < 0.30).
- Any label: a CRITICAL with an on-topic #1, no deterministic violation, outside NEGATIVE_INTENT / DIRECT_MATCH / BRAND_SEARCH, and no off-topic title cited in the top 3 is capped at MODERATE.
- `CONSTRAINT_DROPPED` needs a violating title (cited by the judge or found by the price/exclusion/colour checks); otherwise the verdict carries a `MANUAL CHECK:` note in `internal_notes`, which the publish gate blocks until the operator resolves it (`judge_status="manual"`).
- Sponsored tiles are excluded from every ranking statistic.

### Calibration knowledge base (`judge_kb.py`)

A per-language store of past judgements that anchors the judge for **consistency** and lets it reuse strong fix/evidence phrasing. It is **advisory anchoring, not a cache** — every query is still judged fresh against its own results; a past verdict is never reused as this query's verdict (results differ per site).

- **Storage:** `src/audit/kb/{iso}.jsonl` — language normalised to ISO-639-1 (`German`/`de`/`Deutsch` → `de.jsonl`, Swedish → `sv.jsonl`). Each record holds query, category, verdict fields, a Voyage embedding, `domain`, `model`, `rules_version`, `human_reviewed`, a result digest (top1, max, n_results, 3 titles) and `status` (`active` / `pending` / `retired` / `pruned`). Pre-migration originals are kept as `*.jsonl.pre-migration`.
- **Step A — retrieval (before each LLM call):** only records that are `active`, match the current `JUDGE_RULES_VERSION` (or are `human_reviewed`), and come from a *different* domain than the one being audited. Prefer same category, cosine-rank, top 3, scores stripped. Injected at the end of the user message, after the per-query data.
- **Step B — harvest (after the whole audit):** new verdicts land as `pending` — never retrieved until an operator promotes them, so the judge cannot feed its own mistakes back. Skips fallback, deterministic and excluded verdicts; dedups on (domain, query); refuses to harvest when the judge model is not the default.
- **Curation:** `scripts/kb_prune.py list <lang>`, `promote <lang> <match> | --all-pending | --domain d`, `retire <lang> <match> --reason "…"`, `prune`. Promote after the operator has reviewed (and corrected) a run's verdicts.
- **First-run caveat:** the first audit in a new language writes to an empty KB and gets no calibration benefit; the payoff compounds from audit #2 onward per language.

### Category-fit validation (`query_generator.py`)

`_category_mismatch_reason()` rejects queries that definitionally don't fit their category before they enter the audit. The high-precision check in place: a `DIRECT_MATCH` query (which must reference a *specific product the shopper already knows by name*) whose text exactly equals one of the site's real navigation-category labels is rejected — the generation loop then regenerates to refill that category's target count. This stops generic category terms (e.g. "parfym") from producing misleading "direct match buried at #N" findings.

### Evidence snippet trimming (`html_renderer.py`)

`_trim_evidence()` shortens free-text `evidence` for compact callouts (e.g. the pattern-calibration example). It ends on the fullest natural boundary that fits — sentence breaks preferred, clause breaks as fallback — so a snippet never reads as cut off mid-sentence. Note: decimal figures like `0.621` are not treated as sentence boundaries (a boundary requires a trailing space).

### Advanced diagnostics — zero-result exclusion & non-ASCII tokenization (`advanced_diagnostics.py`)

These diagnostics assess the quality of the *visible* result set, so queries that returned **no results** are excluded from them entirely — `Result Set Purity`, `Top Result Trust`, and `Attribute Drift` all skip zero-result queries. A dead-end query has no #1 result to trust and no products to inspect for attribute coverage; counting it here inflates failure rates and emits nonsensical evidence (`#1 was "No results"`, or "every term dropped"). Dead ends are captured separately by the `ZERO_RESULTS_OR_GARBAGE` failure mode and reflected in the purity denominator. Failure rates are therefore computed over *evaluated* (result-bearing) queries, not all queries. (See also the `feedback_zero_result_stats` rule for executive-summary position stats.)

Tokenization (`_query_terms`) is **Unicode-aware** (`[^\W_]+` / `[^\w\s-]`), not ASCII-only. An ASCII-only regex shreds non-English query words (e.g. Swedish "kläder" → "kl","der"), which then never match product titles and surface as falsely "dropped" attributes. This matters for any non-English site. Note that `Attribute Drift` matches query terms against result **titles** by substring, so attributes expressed only in facets/variants (color, size) or as compound/plural forms ("väskor" vs "axelväska") can legitimately read as low coverage — it is a directional title-coverage signal, not a semantic relevance measure.

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
voyageai           # Relevance scoring (rerank-2.5) + KB embeddings (voyage-3.5)
markupsafe         # Escaping trusted fragments in the HTML template
pillow             # Re-encodes the embedded cover screenshot
playwright         # Default fetch path for most sites (+ playwright-stealth)
```

Install: `.venv312/bin/pip install -r requirements.txt && .venv312/bin/python -m playwright install chromium`

---

## Brand voice (when editing prompts)

- Short sentences. Direct assertions. No hedging.
- Forbidden: "leverage," "synergy," "optimize," "robust," "exciting," "deep dive,"
  "fascinating," "powerful," "unique"
- Tone: peer-to-peer, consultative — the reader is smart and has seen plenty of agency pitches
- Do not name the site's own language repeatedly. The reader is a native speaker, so qualifying every fix as "[Language] …" reads as templated. The narrative prompt forbids it, and `_limit_language_mentions()` in `report_generator.py` deterministically enforces a cap of one mention across deep dives + roadmap combined (using `site_context.primary_language`), stripping the rest. Let the quoted query examples convey the language instead.
