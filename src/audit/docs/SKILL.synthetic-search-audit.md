<!--
  ╔══════════════════════════════════════════════════════════════════════╗
  ║  VERSION-CONTROLLED MIRROR — NOT THE WORKING SKILL                      ║
  ╠══════════════════════════════════════════════════════════════════════╣
  ║  This is a read-only backup of the audit operating procedure.          ║
  ║                                                                        ║
  ║  The LIVE skill that Claude loads lives at:                            ║
  ║      ~/.claude/skills/synthetic-search-audit/SKILL.md                  ║
  ║                                                                        ║
  ║  To change the procedure: edit the LIVE skill there, then re-copy it   ║
  ║  here to keep this mirror in sync. Do NOT treat this file as the       ║
  ║  source of truth, and do NOT place it under any .claude/skills/ path   ║
  ║  (that would make it load as a second, competing skill).               ║
  ║                                                                        ║
  ║  Last synced: 2026-06-13                                               ║
  ╚══════════════════════════════════════════════════════════════════════╝
-->

---
name: synthetic-search-audit
description: "Use when the user wants to run a search quality audit on a website, test site search functionality, or generate a Prism audit report for any URL in any language."
---

# Synthetic Search Audit

Run an 8-phase search quality audit with human review between every phase. Work from `/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/src/audit/`. (The pipeline lives in this project's `src/audit`; checkpoints and per-site report folders live under `src/audit/reports/`. There is no separate `~/Documents/Synthetic Search` project.)

## Two run modes

- **Mode A — gated manual (DEFAULT, this skill).** Call the individual phase functions one at a time and stop for approval between every phase. Use this unless explicitly told otherwise.
- **Mode C — automated orchestrator (fast, opt-in).** `python -m src.orchestrator "<search-url>"` runs every phase + publish + sales materials in one shot, with no gates. Only use when the user explicitly asks for the fast/one-shot run.

For how the code is built (models, modules, sales-materials internals, publishing details), see `src/audit/docs/ARCHITECTURE.md`. This skill is the operating procedure; that doc is the code reference.

## Phase Reference

| # | Phase | Function | Module |
|---|-------|----------|--------|
| 1 | Discovery | `discover_from_search_url(url)` | `src.discovery` |
| 2 | Categories | `select_categories(site_context)` | `src.category_selector` |
| 3 | Queries | `generate_queries(site_context, categories)` | `src.query_generator` |
| 4a | First-fetch gate | `fetch_all_results(search_url_template, queries[:1])` | `src.fetcher` |
| 4 | Fetch | `fetch_all_results(search_url_template, queries)` | `src.fetcher` |
| 5 | Score | `score_results(queries, scraped_results)` | `src.scorer` |
| 6 | Judge | `judge_all_queries(queries, scored_results)` | `src.judge` |
| 7 | Report | `generate_report(site_context, judgments)` | `src.report_generator` |
| 8 | Publish | `publish_report(html_content, domain_slug)` | `src.github_publisher` |
| 9 | Sales materials | `generate_sales_materials(report, out_dir, slug)` | `src.sales_materials_generator` |

## Rules

1. **NEVER proceed to the next step without explicit user approval — no exceptions.** Stop after EVERY step and wait for the user to say go. This applies not just to phase boundaries but to every sub-step within a phase (e.g. junk cleanup, scoring, re-fetching, query swaps, publishing). Do exactly one step, report the result, and wait. **Never chain steps**, and never treat an instruction like "run it" or "let me know when you're done" as blanket approval to run multiple steps — it authorizes only the single step in question. If a background task finishes, report its output and stop; do NOT auto-launch the next step. When in doubt, ask.
2. **Always ask the user for a search results page URL** (e.g. `https://example.com/search?q=shoes`) — not a homepage. Use `discover_from_search_url(url)` exclusively.
3. Save each phase's output as JSON in `reports/_checkpoint_phaseN.json`. Use `.model_dump_json()` for Pydantic objects, `json.dumps()` for dicts/lists of Pydantic objects. Reconstruct with `Model.model_validate_json()` or `Model.model_validate()`.
4. Every `python3 -c` invocation must start with: `import sys; sys.path.insert(0, '.'); from dotenv import load_dotenv; load_dotenv(override=True)`
5. Run all Python commands from the project directory: `cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/src/audit" && python3 -c "..."`
6. If the user provides corrections at any checkpoint, apply them to the Pydantic object before saving and proceeding.

## Phase 0: Pre-flight

Ask the user for a **search results page URL**. This must be a URL that contains a visible query parameter (e.g. `?q=shoes`, `?query=spa`, `?search=guitar`). Do NOT accept a bare homepage like `https://example.com`. Explain why if needed: the pipeline needs to detect the search URL pattern from a real search page.

## Phase 1: Discovery

Run `discover_from_search_url(url)`. Show the user ALL of these fields:

- **site_name**
- **site_type** (PHYSICAL_GOODS / SERVICES_EXPERIENCES / MARKETPLACE_MIXED)
- **search_url_template** (critical — this is what all queries will use)
- **nav_categories** (full list)
- **brands** (full list)
- **featured_items** (full list)

Ask: "Does this look correct? You can change site_type, add/remove brands or categories, fix the search_url_template, or add missing featured items."

If the user provides corrections, reconstruct `SiteContext` with changes, re-serialize, and save checkpoint.

## Phase 2: Categories

Run `select_categories(site_context)`. Show each selected `QueryCategory` name. Show count (target: 12-16).

Ask: "Add or remove any categories?"

If the user changes categories, rebuild as `list[QueryCategory]` from the enum values directly.

## Phase 3: Queries

Run `generate_queries(site_context, categories)`. Show queries **grouped by category**, each with:
- Query string
- Rationale

Show total count.

Ask: "Flag any hallucinated product names, remove bad queries, or request replacements for specific categories."

To remove: filter the list. To regenerate for specific categories: re-run `generate_queries` with only those categories, then merge with the kept queries.

## Phase 4a: First-fetch verification gate (MANDATORY — do before the full fetch)

The fetcher is the most silent-failure-prone phase: it tries several extraction strategies and can confidently return junk (nav, cookie banners, footer/policy links) instead of products, or pick the wrong container for this site. Catch that on **one** query before spending time and API calls on all ~30.

**Fetch ONLY the first query:**

```python
results = fetch_all_results(search_url_template, queries[:1])
q = queries[0].query
print(f"Query: {q}")
print(f"Live URL to check: {search_url_template.format(q)}")
for r in results[q]:
    print(f"  {r.rank}. {r.title!r}  | price={r.price or '-'}  | url={r.url or 'NO URL'}")
print(f"  total results: {len(results[q])}")
```

Show the user: the query, the **exact live search URL** (so they can open it in a browser), every fetched result's rank/title/price/url, and the total count. Also surface the fetcher's stdout — the **fetch mode** it settled on (static / playwright / blocked) and which **extraction strategy** matched (the fetcher logs these); these are the diagnostic signals for a silent failure.

Then explicitly ask the user to **eyeball the results against the live site** and run this silent-failure checklist:
- Do the titles look like real products (not "Sign in", "Show more", category names, cookie text)?
- Do URLs point at product pages (not missing, not `#`, not `policies.google.com`/privacy paths)?
- Does the count and ordering roughly match what the real search page shows for this query?
- Did the fetch mode/strategy look sane (e.g. not "blocked", not 0 results when the site clearly has results)?

**STOP and wait for approval.** Do not run the full fetch until the user confirms the fetcher works on this site. If it failed (junk, wrong selectors, blocked, zero results), the fetcher needs a site-specific fix or a different fetch mode **before** proceeding — do not push through a broken fetcher.

## Phases 4+5: Fetch, Clean, and Score

Only after the Phase 4a gate passes. Run `fetch_all_results(search_url_template, queries)` for the full query set.

**Before scoring, run a junk cleanup pass.** The fetcher often scrapes UI elements (buttons, modals, cookie banners) as if they were search results. Remove any result where:
- Title matches known junk: `"+ Zobrazit více"`, `"Zobrazit více"`, `"Porovnání produktů"`, `"Podobné fráze"`, `"Zapomněli jste heslo?"`, `"Povolit vše"`, `"Smazat vše"`, `"Přejít do košíku"`, `"Kategorie"`, `"Značky"`, `"Přihlásit se"`, `"Registrovat se"`, `"Show more"`, `"Compare products"`, `"Sign in"`, `"Accept all"`, `"Clear all"`
- URL is missing (`None` or empty string)
- URL starts with `#` (anchor/modal link, not a product page)

After removing junk, re-index ranks (1-based) within each query's result list. Save the cleaned data back to both the phase 4 and phase 5 checkpoint files. Report how many junk entries were removed.

Then run `score_results(queries, scraped_results)` on the **cleaned** data.

Show:
- Total results fetched (before and after cleanup)
- Junk entries removed count
- Queries with **0 results** (list them by name)
- Average relevance score per category
- Queries where **top result relevance < 0.3** (list them)

Ask: "Remove zero-result queries from further analysis, re-fetch any specific queries, or proceed?"

### Handling poisoned results

Some fetcher extractions fail silently — instead of product results, the fetcher scrapes footer/cookie/privacy policy elements (e.g. "Zásady ochrany osobních údajů", links to `policies.google.com/privacy`). After the junk cleanup pass, scan for remaining poisoned results:
- Any result with a URL containing `policies.google.com`, `business.safety.google`, or site privacy policy paths
- Any query where ALL results are non-product pages

For each poisoned query:
1. Verify on the live site (via Playwright) whether real product results exist
2. If real results exist: manually extract them from `.product-list` or equivalent selector, rebuild `SearchResult` objects, and update checkpoints
3. If no real results exist: set the query's results to `[]` (genuine zero results)
4. Re-score only the fixed queries, then patch into the phase 5 checkpoint

## Phase 6: Judge

Run `judge_all_queries(queries, scored_results)`. Show:

- **Severity counts**: CRITICAL / MODERATE / MINOR / PASS
- **Failure mode distribution** (count per mode)
- **Every CRITICAL judgment**: query string, failure_mode, evidence, recommended_fix

Ask: "Override any judgments or proceed to report generation?"

**Cost-saving rule:** If corrections are needed after judging (e.g. re-fetched/fixed results), only re-judge the **affected queries**, not all queries. `judge_all_queries` makes LLM calls per query — re-judging all 36 queries when only 3 changed is wasteful. Patch the updated judgments into the existing checkpoint.

**Cost tracking:** After judging, estimate and show the LLM cost for this phase. The judge calls `_call_sonnet` (Claude Sonnet) once per query with `max_tokens=800`. To estimate cost:
1. Count the number of queries judged (N)
2. Use the Anthropic API to check actual usage, or estimate: ~1500 input tokens + ~500 output tokens per query (typical for the judge prompt + response)
3. Show: `Estimated Phase 6 cost: N queries x ~2000 tokens ≈ $X.XX` using current Sonnet pricing ($3/M input, $15/M output)
4. If the cost seems abnormally high (e.g. >$1 for <50 queries), flag it as a potential issue.

## Phase 7: Report

### Folder + Screenshot

**Step 1 — Create the output folder** (do this immediately, before asking anything):
```bash
mkdir -p "reports/{domain_slug}"
```

**Step 2 — Check for screenshot.** Look for any `.png`, `.jpg`, or `.jpeg` file inside `reports/{domain_slug}/`.

- If a screenshot is found, pass its path as `screenshot_path` to `save_html_report()`. It will be embedded in the cover page below the date/Prism badge.
- **If no screenshot is found, ask the user:** "Please save a screenshot of the website to `reports/{domain_slug}/` (any .png/.jpg file) and confirm, or say 'skip' to generate the report without one."
- Do not proceed with HTML generation until the user confirms or skips.

### Generation

Run `generate_report(site_context, judgments)`. Then run `save_html_report(report, output_path, screenshot_path=screenshot_path)` from `src.html_renderer`.

Save outputs into the per-website subfolder `reports/{domain_slug}/` using the slug pattern `{domain_slug}_{timestamp}`:
- `reports/{domain_slug}/{slug}_report.md` — write `report.deep_dive_narrative` (the `AuditReport` has no single markdown blob; this is the markdown body the orchestrator persists)
- `reports/{domain_slug}/{slug}_data.json` — `report.model_dump()`
- `reports/{domain_slug}/{slug}_report.html` — from `save_html_report(...)`

Show the user: file paths, capability score summary (pass rate), and any CRITICAL capabilities.

After the user approves the report, proceed to Phase 8 — **do not stop at Phase 7.** Every completed audit must be published and registered.

## Phase 8: Publish & Register (MANDATORY — never skip)

Every finished report MUST end up (a) as a live page on findsherpas.com and (b) listed in the CRM Reports section. Both are accomplished by `publish_report` — do not treat the audit as "done" after Phase 7.

Run from `src.github_publisher`:

```python
from src.github_publisher import publish_report
html = open('reports/{domain_slug}/{slug}_report.html', encoding='utf-8').read()
url = publish_report(html, '{domain_slug}')   # e.g. 'manufactum_de'
print(url)
```

What this does (single call covers BOTH deliverables — it pushes TWO files to the repo):
- **findsherpas.com page** — uploads the HTML to the `nitianhao/findsherpas` repo at `public/report/{report_slug}/index.html`, served at `https://findsherpas.com/report/{report_slug}/`. Requires `gh` authed as the repo owner (`gh auth status`).
- **CRM Reports section** — updates the local `find-sherpas/reports/report_slugs.json` (company key = domain slug minus `www_`/TLD) **and pushes that file to the repo**. The deployed CRM page `app/crm/(protected)/reports/page.tsx` reads `report_slugs.json` **from the repo**, so a local-only update is NOT enough — the file must be committed to the repo or the report stays invisible in the CRM. The push triggers a Vercel redeploy (~1–2 min) after which the row appears. (`publish_report` handles both files; if you ever update the registry by hand, you must also `gh api PUT` it to `reports/report_slugs.json`.)

Verify before reporting done (check the REPO copy, not just local):
- `gh api /repos/nitianhao/findsherpas/contents/reports/report_slugs.json --jq '.content' | base64 -d` contains the `{company}` entry.
- `gh api /repos/nitianhao/findsherpas/contents/public/report/{report_slug}/index.html --jq '.size'` matches the local HTML byte size.

Then give the user the live URL and tell them the CRM row appears after the redeploy (~1–2 min).

## Phase 9: Sales materials (do not skip)

After publishing, generate the three sales deliverables from the completed report — these are part of every audit, not optional extras. Run:

```python
from src.sales_materials_generator import generate_sales_materials
generate_sales_materials(report, out_path, slug)   # report = the AuditReport from Phase 7
```

This writes into `reports/{domain_slug}/`:
- `{slug}_exec_summary.docx` — 2-page Executive Summary
- `{slug}_brief.docx` — 1-page Forwardable Brief
- `{slug}_cold_email.txt` — cold email opener, 3 versions

Show the user the file paths. For prompt copy, branding, and internal logic, see `src/audit/docs/ARCHITECTURE.md`. (In Mode C the orchestrator runs this automatically at the end of `run_audit()`.)
