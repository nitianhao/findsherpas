---
name: synthetic-search-audit
description: "Use when the user wants to run a search quality audit on a website, test site search functionality, or generate a Prism audit report for any URL in any language."
---

# Synthetic Search Audit

Run an 8-phase search quality audit with human review between every phase. Work from `/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/src/audit/`. (The pipeline lives in this project's `src/audit`; checkpoints and per-site report folders live under `src/audit/reports/`. There is no separate `~/Documents/Synthetic Search` project.)

## Two run modes

- **Mode A — gated manual (DEFAULT, this skill).** Call the individual phase functions one at a time and stop for approval between every phase. Use this unless explicitly told otherwise.
- **Mode C — automated orchestrator (fast, opt-in).** `.venv312/bin/python -m src.orchestrator "<search-url>"` runs every phase, renders the report and runs the publish gate, with no human gates. It only publishes with `--publish` (and only if the gate passes). Checkpoints go to `reports/{domain_slug}/run_<timestamp>/`; `--resume <run dir>` skips completed phases. Only use when the user explicitly asks for the fast/one-shot run.

For how the code is built (models, modules, publishing details), see `src/audit/docs/ARCHITECTURE.md`. This skill is the operating procedure; that doc is the code reference. After any code change run the offline tests: `.venv312/bin/python -m unittest discover -s tests -t .`

## Phase Reference

| # | Phase | Function | Module |
|---|-------|----------|--------|
| 1 | Discovery | `discover_from_search_url(url)` | `src.discovery` |
| 2 | Categories | `select_categories(site_context)` | `src.category_selector` |
| 3 | Queries | `generate_queries(site_context, categories)` | `src.query_generator` |
| 4a | First-fetch gate | `fetch_all_outcomes([queries[0].query], search_url_template, evidence_dir=...)` | `src.fetcher` |
| 4 | Fetch | `fetch_all_outcomes([q.query for q in queries], search_url_template, evidence_dir=...)` | `src.fetcher` |
| 4b | Control searches | `_fetch_controls(queries, outcomes, search_url_template, evidence_dir)` | `src.orchestrator` |
| 5 | Score | `score_results(queries, {q: o.results if o.trusted else [] for q, o in outcomes.items()})` | `src.scorer` |
| 6 | Judge | `judge_all_queries(queries, scored, language=..., provenance=..., site_categories=..., site_brands=..., fetch_outcomes=outcomes, control_outcomes=controls)` | `src.judge` |
| 7 | Report | `generate_report(site_context, judgments)` + `save_html_report(...)` | `src.report_generator`, `src.html_renderer` |
| 7b | Publish gate | `check_report(report, html)` / `python -m src.publish_gate <data.json> --html <report.html>` | `src.publish_gate` |
| 8 | Publish | `publish_report_full(html, domain_slug, data_json=..., report_md=...)` | `src.github_publisher` |

## Rules

1. **NEVER proceed to the next step without explicit user approval — no exceptions.** Stop after EVERY step and wait for the user to say go. This applies not just to phase boundaries but to every sub-step within a phase (e.g. junk cleanup, scoring, re-fetching, query swaps, publishing). Do exactly one step, report the result, and wait. **Never chain steps**, and never treat an instruction like "run it" or "let me know when you're done" as blanket approval to run multiple steps — it authorizes only the single step in question. If a background task finishes, report its output and stop; do NOT auto-launch the next step. When in doubt, ask.
2. **Always ask the user for a search results page URL** (e.g. `https://example.com/search?q=shoes`) — not a homepage. Use `discover_from_search_url(url)` exclusively.
3. Save each phase's output in a **per-site run directory** `reports/{domain_slug}/run_<YYYYMMDD_HHMMSS>/` using the orchestrator's helpers, which write atomically and use the same file names as Mode C (so a gated run can later be finished with `--resume`): `from src.orchestrator import _save_checkpoint, _load_checkpoint` → `_save_checkpoint(run_dir, "site_context" | "categories" | "queries" | "fetch" | "controls" | "scored" | "judgments", value)`. **Never** use the old shared `reports/_checkpoint_phaseN.json` names — they collided across sites (a phase-6 file once held 61 Cotswold + 35 Lyko judgments).
4. Every `-c` invocation must start with: `import sys; sys.path.insert(0, '.'); from dotenv import load_dotenv; load_dotenv(override=True)`
5. Run all Python commands from the project directory with the 3.12 venv (system python3.9/LibreSSL fails TLS): `cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/src/audit" && .venv312/bin/python -c "..."`
6. If the user provides corrections at any checkpoint, apply them to the Pydantic object before saving and proceeding.
7. **Per-phase knowledge bases (`src/audit/docs/*_PLAYBOOK.md`).** Each phase has a playbook that is operational memory for that phase: `DISCOVERY_PLAYBOOK` (1), `CATEGORIES_PLAYBOOK` (2), `QUERIES_PLAYBOOK` (3), `FETCHER_PLAYBOOK` (4/4a), `SCORING_PLAYBOOK` (5), `JUDGE_PLAYBOOK` (6), `REPORT_PLAYBOOK` (7), `PUBLISH_PLAYBOOK` (8). **Before running a phase, READ its playbook** and apply any per-site profile / general learning. **After the user gives a correction or expertise at that phase, APPEND it to the playbook** (per-site profile for host-specific facts, general-learnings entry if it generalizes) so the next audit is more fine-tuned. One correction = one entry. Do this every audit — the playbooks are how the pipeline improves over time.

## Phase 0: Pre-flight

Ask the user for a **search results page URL**. This must be a URL that contains a visible query parameter (e.g. `?q=shoes`, `?query=spa`, `?search=guitar`). Do NOT accept a bare homepage like `https://example.com`. Explain why if needed: the pipeline needs to detect the search URL pattern from a real search page.

## Phase 1: Discovery

**FIRST, read `src/audit/docs/DISCOVERY_PLAYBOOK.md`** and apply any per-site profile / general learning. After the user's corrections, **append them to that playbook**.

Run `discover_from_search_url(url)`. Show the user ALL of these fields:

- **site_name**
- **site_type** (PHYSICAL_GOODS / SERVICES_EXPERIENCES / MARKETPLACE_MIXED)
- **search_url_template** (critical — this is what all queries will use)
- **nav_categories** (full list)
- **brands** (full list)
- **featured_items** (full list)
- **primary_language / locale / currency**
- **catalog_sample** (count + first 15 titles — these ground the generated queries in what the store really stocks)
- **provenance** — any key whose value starts with `fallback:` means an LLM step did not run; say so explicitly

Ask: "Does this look correct? You can change site_type, add/remove brands or categories, fix the search_url_template, or add missing featured items."

If the user provides corrections, reconstruct `SiteContext` with changes, re-serialize, and save checkpoint.

## Phase 2: Categories

**FIRST, read `src/audit/docs/CATEGORIES_PLAYBOOK.md`** and apply any per-site / by-site-type learning. After the user's edits, **append them to that playbook**.

Run `select_categories(site_context)`. Show each selected `QueryCategory` name. Show count (10–18, enforced in code).

Ask: "Add or remove any categories?"

If the user changes categories, rebuild as `list[QueryCategory]` from the enum values directly.

## Phase 3: Queries

**FIRST, read `src/audit/docs/QUERIES_PLAYBOOK.md`** and pre-filter known-bad query shapes for this host/locale. After the user's edits, **append them to that playbook**.

Run `generate_queries(site_context, categories)`. Show queries **grouped by category**, each with:
- Query string
- `target_term` (the plain intent term — also used as the control search if the query returns nothing)
- `constraints` where present (price / exclude / attributes)
- Rationale

Show total count.

Ask: "Flag any hallucinated product names, remove bad queries, or request replacements for specific categories."

To remove: filter the list. To top up specific categories: `generate_queries(site_context, [cat], counts={cat: n}, existing=kept_queries, enforce_min=False)` — it returns only the new queries; append them to the kept list.

## Phase 4a: First-fetch verification gate (MANDATORY — do before the full fetch)

**FIRST, read `src/audit/docs/FETCHER_PLAYBOOK.md`** — the fetcher knowledge base. If the target host already has a per-site profile there, you know the fetch mode, the correct results container, and the known traps up front; apply them instead of re-debugging. If the host is new, run the silent-failure checklist below and, once it passes, **append a new per-site profile to the playbook**.

The fetcher is the most silent-failure-prone phase: it tries several extraction strategies and can confidently return junk (nav, cookie banners, footer/policy links) instead of products, or pick the wrong container for this site (e.g. a "you might also like" / mini-cart recommendations carousel). Catch that on **one** query before spending time and API calls on all 60.

**Fetch ONLY the first query:**

```python
from urllib.parse import quote_plus
from src.fetcher import fetch_all_outcomes
q = queries[0].query
o = fetch_all_outcomes([q], site_context.search_url_template, evidence_dir=str(run_dir / "evidence"))[q]
print(f"Query: {q}")
print(f"Live URL to check: {site_context.search_url_template.format(quote_plus(q))}")
print(f"Status: {o.status} | page hit count: {o.total_hits} | strategy: {o.strategy} | attempts: {o.attempts} | {o.evidence}")
for r in o.results:
    print(f"  {r.rank}. {r.title!r}  | price={r.price or '-'}  | url={r.url or 'NO URL'}{'  [SPONSORED]' if r.sponsored else ''}")
print(f"  extracted: {len(o.results)}")
```

Show the user: the query, the **exact live search URL** (so they can open it in a browser), the **status** (`ok`, `zero_confirmed`, `zero_unverified`, `partial`, `redirect`, `blocked`, `timeout`, `error`), the page's own hit count, every fetched result's rank/title/price/url, and the screenshot saved under `run_dir/evidence/`. Anything other than `ok` / `zero_confirmed` / `redirect` on the probe means the fetcher is not observing this site correctly.

Then explicitly ask the user to **eyeball the results against the live site** and run this silent-failure checklist:
- Do the titles look like real products (not "Sign in", "Show more", category names, cookie text)?
- Do URLs point at product pages (not missing, not `#`, not `policies.google.com`/privacy paths)?
- Does the count and ordering roughly match what the real search page shows for this query?
- Did the fetch mode/strategy look sane (e.g. not "blocked", not 0 results when the site clearly has results)?

**STOP and wait for approval.** Do not run the full fetch until the user confirms the fetcher works on this site. If it failed (junk, wrong selectors, blocked, zero results), the fetcher needs a site-specific fix or a different fetch mode **before** proceeding — do not push through a broken fetcher.

## Phases 4+5: Fetch, Clean, and Score

**Before scoring, read `src/audit/docs/SCORING_PLAYBOOK.md`** for host-specific junk titles, poisoned-result patterns, and accurate-low-count quirks. After the user's corrections, **append them to that playbook**.

Only after the Phase 4a gate passes. Run `fetch_all_outcomes([q.query for q in queries], search_url_template, evidence_dir=...)` for the full query set and show the **status counts**. Queries whose status is not trusted (`zero_unverified`, `blocked`, `timeout`, `error`) are never scored as search failures — re-fetch them or accept that they will be excluded. More than 20% untrusted = stop and fix the fetch.

Then run the **control searches** (Phase 4b): `controls = _fetch_controls(queries, outcomes, search_url_template, run_dir / "evidence")`. Each zero-result query is re-searched with its plain `target_term`. Show: query → control status and result count. Control empty too ⇒ catalog gap (excluded from scoring); control has products ⇒ a proven search failure the report may quote.

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

**FIRST, read `src/audit/docs/JUDGE_PLAYBOOK.md`** for severity-calibration rules. After the user's overrides, **append the calibration rule to that playbook**.

Run `judge_all_queries(queries, scored_results, language=site_context.primary_language, provenance={"domain": domain_slug, "url": url, "judged_at": ...}, site_categories=site_context.nav_categories, site_brands=site_context.brands, fetch_outcomes=outcomes, control_outcomes=controls)` — always pass all of these (without them the KB, brand and category guards are silently off). Show:

- **Severity counts**: CRITICAL / MODERATE / MINOR / PASS (scored only)
- **Excluded** queries and why (`excluded_reason`: catalog_gap / fetch_unverified / invalid_test)
- **Fallbacks** (`judge_status == "fallback"`) — must be re-judged or overridden
- **Manual checks** (`from src.judge import needs_manual_check`) — show `internal_notes` for each
- **Failure mode distribution** (count per mode)
- **Every CRITICAL judgment**: query string, failure_mode, evidence (client-facing), internal_notes, recommended_fix

Ask: "Override any judgments or proceed to report generation?"

When you apply an override or confirm a manual check: edit `severity`/`failure_mode`, rewrite `evidence` in plain client language (no scores, no "override" wording — put the reason in `internal_notes`), and set `judge_status = "manual"`. The publish gate blocks any unresolved manual check. After the user has approved the verdicts, promote them into the calibration KB: `.venv312/bin/python scripts/kb_prune.py promote <lang> --domain <domain_slug>` (harvested verdicts sit as `pending` until then).

**Cost-saving rule:** If corrections are needed after judging (e.g. re-fetched/fixed results), only re-judge the **affected queries**, not all queries. `judge_all_queries` makes LLM calls per query — re-judging all 36 queries when only 3 changed is wasteful. Patch the updated judgments into the existing checkpoint.

**Cost tracking:** after judging, show actual token usage: `from src import llm_compat; llm_compat.usage_summary()` (per phase and model, including cache reads). Zero-result, gibberish and untrusted-fetch queries are decided in code and cost nothing. Price at the judge model's rates (Sonnet 4.6: $3/M input, $15/M output; cache reads are 10%). Flag anything above ~$2 for 60 queries.

## Phase 7: Report

**FIRST, read `src/audit/docs/REPORT_PLAYBOOK.md`** for tone/emphasis conventions. After the user's edits, **append the preference to that playbook**.

### Folder + Screenshot

**Step 1 — Create the output folder** (do this immediately, before asking anything):
```bash
mkdir -p "reports/{domain_slug}"
```

**Step 2 — Check for screenshot.** Look for any `.png`, `.jpg`, or `.jpeg` file inside `reports/{domain_slug}/`.

- If a screenshot is found, pass its path as `screenshot_path` to `save_html_report()`. It is re-encoded and embedded in the cover page.
- Otherwise offer the fetcher's first results-page screenshot from `run_dir/evidence/` (`_find_report_screenshot(out_path, run_dir)` does this), or ask the user to save one to `reports/{domain_slug}/`, or 'skip'.
- Do not proceed with HTML generation until the user confirms or skips.

### Generation

Run `generate_report(site_context, judgments)` — the deep dives and roadmap are checked against the data (every quoted query, product title and position must exist) and it raises rather than emitting placeholder text. Show the user the deep dives and roadmap for review; to apply edits, pass the reviewed content back via `generate_report(site_context, judgments, deep_dives=..., roadmap=...)` (it validates instead of regenerating). Then run `save_html_report(report, output_path, screenshot_path=screenshot_path)` from `src.html_renderer`.

Save outputs into the per-website subfolder `reports/{domain_slug}/` using the slug pattern `{domain_slug}_{timestamp}`:
- `reports/{domain_slug}/{slug}_report.md` — write `report.deep_dive_narrative` (the `AuditReport` has no single markdown blob; this is the markdown body the orchestrator persists)
- `reports/{domain_slug}/{slug}_data.json` — `report.model_dump_json(indent=2)`
- `reports/{domain_slug}/{slug}_report.html` — from `save_html_report(...)`

Show the user: file paths, capability score summary (pass rate), and any CRITICAL capabilities. Then run the **publish gate** and show its output:

```bash
.venv312/bin/python -m src.publish_gate reports/{domain_slug}/{slug}_data.json --html reports/{domain_slug}/{slug}_report.html
```

Errors block publishing (untrusted fetches, a scraped no-results widget, judge fallbacks, unresolved manual checks, scores/override wording/model names in client-visible text, missing CTA/logo). Fix them before Phase 8.

After the user approves the report, proceed to Phase 8 — **do not stop at Phase 7.** Every completed audit must be published and registered.

## Phase 8: Publish & Register (MANDATORY — never skip)

**FIRST, read `src/audit/docs/PUBLISH_PLAYBOOK.md`** for slug conventions and verification steps. After any publish issue, **append the cause/fix to that playbook**.

Every finished report MUST end up (a) as a live page on findsherpas.com and (b) listed in the CRM Reports section. Both are accomplished by `publish_report` — do not treat the audit as "done" after Phase 7.

Run from `src.github_publisher`:

Only when the publish gate passes:

```python
from src.github_publisher import publish_report_full
d = 'reports/{domain_slug}/{slug}'
res = publish_report_full(
    open(f'{d}_report.html', encoding='utf-8').read(),
    '{domain_slug}',   # e.g. 'manufactum_de'
    data_json=open(f'{d}_data.json', encoding='utf-8').read(),
    report_md=open(f'{d}_report.md', encoding='utf-8').read(),
)
print(res.company, res.slug, res.url)
```

Always pass `data_json` and `report_md` — they archive the raw audit data to the repo (`audit-data/{report_slug}/`, never web-served) so the judgements survive a local wipe.

What this does (single call, up to FOUR files):
- **findsherpas.com page** — uploads the HTML to the `nitianhao/findsherpas` repo at `public/report/{report_slug}/index.html`, served at `https://findsherpas.com/report/{report_slug}/`. Requires `gh` authed as the repo owner (`gh auth status`).
- **CRM Reports section** — fetches the repo's `reports/report_slugs.json`, merges the local copy (remote wins), adds this report (company key = domain slug minus `www_`/TLD; a second market of the same company gets a domain-qualified key instead of overwriting the first), **pushes it to the repo**, then mirrors it locally. The deployed CRM page `app/crm/(protected)/reports/page.tsx` reads `report_slugs.json` **from the repo**, so a local-only update is NOT enough — the file must be committed to the repo or the report stays invisible in the CRM. The push triggers a Vercel redeploy (~1–2 min) after which the row appears. (`publish_report` handles both files; if you ever update the registry by hand, you must also `gh api PUT` it to `reports/report_slugs.json`.)

Verify before reporting done (check the REPO copy, not just local):
- `gh api -H "Accept: application/vnd.github.object" /repos/nitianhao/findsherpas/contents/reports/report_slugs.json --jq '.content' | base64 -d` contains the `{company}` entry.
- `gh api -H "Accept: application/vnd.github.object" /repos/nitianhao/findsherpas/contents/public/report/{report_slug}/index.html --jq '.size'` matches the local HTML byte size.

Then give the user the live URL and tell them the CRM row appears after the redeploy (~1–2 min).

Phase 8 is the final step — once the report is published and registered, the audit is complete.

> Note: sales-materials generation (formerly Phase 9 — exec summary / forwardable brief / cold email) has been **removed from the workflow**. Do not generate them, and do not treat their absence as an incomplete audit.
