# Report Playbook — Phase 7 knowledge base

> **Read this BEFORE running Phase 7 (`generate_report` + `save_html_report`).** It records
> reporting conventions — tone, emphasis, framing — per site and in general, so reports stay
> consistent and on-message across audits. When the user reshapes a report, capture it here.
>
> Companion docs: `ARCHITECTURE.md` and the `synthetic-search-audit` skill. Operational
> memory for the **report** phase.

---

## How to use this file

1. Before Phase 7, read **General learnings** and the **Per-site profile**. Apply known
   tone/emphasis preferences before generating.
2. Create `reports/{domain_slug}/`, handle the screenshot (embed if present, else ask or
   skip), generate, then `save_html_report(..., screenshot_path=...)`.
3. Save `{slug}_report.md` (from `report.deep_dive_narrative`), `{slug}_data.json`
   (`report.model_dump()`), and `{slug}_report.html`.
4. After the user edits the framing, record the preference.

---

## Current contract (Oct 2026 upgrade — read first; supersedes older notes below where they conflict)

- **One stats module.** Every number in the .md AND the .html comes from `src/report_stats.py`
  (`compute_stats`, `formatted_stats`, `capability_rows`, `root_causes`, `whats_working_items`,
  `pick_worst_example`, `benchmark_rows`). Never compute a rate inside a renderer. Avg best
  position is always `#x.y` (`fmt_pos`); "past the first three results" only when avg > 3
  (`position_context`). The md scorecard and the HTML improvement map share one priority rule
  (`capability_rows`: capability severity, then critical/moderate/minor counts).
- **Excluded judgments never count.** `excluded_reason` set ⇒ left out of every rate, listed in
  the "Not scored" appendix (md + html) with the reason in plain words. Persisted
  `capability_scores` keep every judgment but compute severity over scored ones only.
- **Narratives are structured + grounded.** Deep dives (`generate_deep_dives`) and roadmap
  (`generate_roadmap`) are SEPARATE `structured_call`s (8000 / 3000 tokens). Static rules live
  in the cached system prompt; site data (incl. `site_context.currency`) in the user turn; ids
  index `failing_judgments()`. No other client's examples or budgets in the prompt.
  `grounding_violations` checks every quoted string (must be a tested query, or a title/target
  term/proof from that search's results, a nav category or brand; single plain words allowed),
  every `#N` (must be a real `original_rank` of that search) and every carry/stock claim (needs
  `proof_of_stock`). Violations ⇒ one regeneration with the problems fed back ⇒ `GroundingError`.
  `LLMResponseError` propagates. **No placeholder text can be rendered** — the old
  "Roadmap section was not generated…" path, the regex roadmap parser and the title-rewrite
  hack (which turned item 6 into a copy of item 1) are gone; item #1's concrete framing is a
  prompt rule plus a soft retry check.
- **Accepted narratives are stored on the report** in `run_metadata["report_content"]`
  (`{"deep_dives": [{capability, capability_name, intro, examples:[{query, narrative}]}],
  "roadmap": [{title, description, impact, effort, owner, queries}]}`), query-keyed. The HTML
  renders the same reviewed deep-dive text as the .md, and roadmap items show "Fixes N tested
  searches (K critical)" from `queries`. To re-use a reviewed version, pass these lists back as
  `generate_report(..., deep_dives=, roadmap=)` — they are validated, never regenerated.
  **Callers must merge into `run_metadata`, never overwrite it**; `render_html_report` raises
  if the structured roadmap is missing (a legacy `_data.json` must be regenerated first).
- **"The store carries X" only with proof:** a control search for `target_term` that returned
  products (judge evidence: `searching '<term>' returns products such as '<title>'`) or a title
  from another tested query's results (Unicode-aware token match). A category claim in the
  "most severe example" also requires the category to be a real `nav_categories` entry.
- **Client text is sanitised.** `sanitize_client_text` strips score parentheticals, workflow
  markers ("User override:", "[Override: …]", "per calibration", "[MANUAL VERIFICATION
  REQUIRED]", "[Severity escalated…]") and any sentence still mentioning scores/thresholds/tools.
  `internal_notes` is never rendered. Score bars are gone from risk cases; "Should have come
  first" lists only appear for ordering failures with a clearly on-topic better match
  (`show_better_matches`).
- **Headline = share of tested searches that fail the shopper**, with the sample size and the
  adversarial-sample note (`SAMPLE_NOTE`) — never "% revenue risk". No revenue numbers unless
  from an explicit, labelled model. "Products returned, but the wrong ones or in the wrong
  order" is the ONE found-but-wrong metric in both outputs (replaces the HTML-only "Right
  products found, ranked too low", which was a bare POOR_RANKING count). The "returned nothing
  usable" figure is footnoted (`ZERO_RESULT_FOOTNOTE`) against the smaller failure-mode row.
- **No unverifiable citations.** The Baymard/Econsultancy/"55–60% of clicks" callouts are
  removed. The comparison table shows Find Sherpas working targets (labelled as ours) and an
  optional `peer_benchmark` column (`{"label", "sample_size", "values": {stat_key: float}}`,
  passed to `generate_report`/`render_html_report` or stored in `run_metadata`).
- **Language cap.** `_limit_language_mentions` never edits inside quotes/backticks, removes only
  adjectival uses ("German synonym mapping"), keeps noun uses ("in German"), and re-capitalises
  only a sentence it edited (the old version corrupted text after closing `**`).
- **HTML safety + presentation.** Jinja autoescape is ON; only the logo SVG is `Markup`.
  Queries/titles carry `lang` (site locale) + `dir="auto"`; document `lang` stays `en` (the
  prose is English). `<details>` expand in print (CSS + `beforeprint`). Cover shows the scope
  line (N searches tested · date · locale · desktop). Each tested query links to the live
  search (`search_url`, `rel="noopener nofollow"`). Markdown tables escape `|` (`md_cell`).
- **Size.** The cover screenshot is re-encoded (`encode_cover_screenshot`: ≤1400px, JPEG q80,
  stepping down to stay ≤350KB). Reports land at ~160–280KB; `html_size_bytes()` vs
  `HTML_SIZE_BUDGET` (900KB) is what the publish gate should check.
- **Root causes.** `root_causes()` groups failing searches by (failure mode, category family) so
  one mechanism ("Price limits in the query are ignored") is shown once with its N searches —
  rendered in both outputs and fed to the roadmap prompt for consolidation.
- **Advanced diagnostics.** Substitutions count only wrong-KIND modes (no POOR_RANKING /
  DUPLICATE_FLOODING); the ordering example names "the better X" only when it is clearly on-topic
  and the verdict is POOR_RANKING; constraint buckets (honoured/violated/empty/other) sum to the
  total; the specificity sentence follows the sign of the change.
- `templates/report.html` is legacy and unused (kept, not deleted).

## General learnings (apply to every site)

- **Audience determines emphasis.** Internal/monobrand recipients care about customer
  bounces, not ranking nuance — deprioritize reordering findings (cf. the
  `monobrand-search-audit` skill). External/prospect reports can carry more ranking detail.
- **Lead with customer impact**, evidence-backed. Each CRITICAL should state what a real
  shopper experiences and the recommended fix.
- **Don't inflate.** Pass rate and CRITICAL count must match the Phase 5/6 data exactly —
  no rounding the story up or down.
- **A cover screenshot is a standard Phase 7 step — do NOT skip it.** Capture the live search
  page (e.g. `search?q=<seed>`) with the browser, **dismiss the cookie banner first** (click
  Accept) or it covers the shot, save it into `reports/{slug}/` (e.g. `avoca_cover.png`), and
  pass `screenshot_path=` to `save_html_report` — it embeds as base64 (`.cover-screenshot`,
  adds ~230KB). Verify it renders by loading the report over `http://localhost` (file:// is
  blocked in the headless browser) and screenshotting `.cover-screenshot`.
  - **Rerenders auto-recover the cover; don't rely on remembering the arg.** `save_html_report`
    now calls `find_cover_screenshot(output_dir)` when `screenshot_path` is None — it picks up
    any `*_cover.png` / `*screenshot*` already in the report folder — and prints a stderr
    WARNING if the saved HTML ends up with no `cover-screenshot`. **Always re-save through
    `save_html_report`, not a bare `render_html_report(report)`** (which has no directory to
    auto-detect from), and heed the warning. This is why ad-hoc rerenders previously dropped the
    cover silently.
- **Executive Summary leads with retrieval health, not ranking.** The position metrics
  (avg best position, % best-not-in-top-3) are computed ONLY over queries that returned
  results — they silently drop zero-result queries and misframe a retrieval-failure site as
  a ranking problem. `build_executive_summary` now leads with metrics over ALL queries:
  `pct_no_relevant_first` (no usable results OR off-topic #1) and `pct_zero_result`
  (`zero_result_count`/total), names the causes (phrasing/category/typo/exclusion), and only
  then reports position metrics as "among queries that did return results". The worst example
  prefers a CRITICAL zero-result on a provably-stocked item (`worst_zero_query`) over a
  displacement example — never describe a zero/constraint failure as "scroll to position #N".
  *(Oct 2026: the md and html now both use `pick_worst_example`; the causes sentence is derived
  from the zero-result failure-mode counts, not four hard-coded causes.)*
- **Report is unbranded.** `PIPELINE_NAME` is empty — no "Prism" (or other tool name) in
  section headers, methodology, or appendix. Client reports carry the site's name, not ours.
- **Test Results Summary — Key Metrics.** Lead with retrieval health, parallel to the exec
  summary: (1) "No usable results returned" = **zero-result FAILURES only** (`zero_result_count`
  excludes correctly-empty catalog-gap PASSes — don't count a correct empty as a problem);
  (2) "Results returned but mis-ranked or wrong" = **all non-pass verdicts that DID return
  results** (poor ranking + partial keyword + dropped constraint + brand bleed + facet + flooding),
  not POOR_RANKING alone — POOR_RANKING-only badly understates it; (3) position metrics labelled
  "among queries that returned results". Severity + failure-mode tables are per-query (unaffected
  by the capability ease-up rule).
- **Advanced Diagnostics must respect the calibrated judgments.** Purity / Top-Result-Trust /
  Attribute-Drift recompute relevance from raw Voyage scores, which re-introduces the
  brand-not-in-title blind spot (brand-correct PASSes score ~0.3 → falsely flagged as noise /
  weak #1), contradicting the verdict tables. Gating via `_is_pass(j)`: a PASS query's result
  set counts as **clean / trustworthy** (kept in the denominator so aggregates stay honest, e.g.
  Purity 77% not 13%), but is **never cited as a failure** in counts or evidence. Non-PASS
  queries still use the score threshold. (Avoca: removed false flags on Barbour jaket, Amercan
  Vintage, Never Fully Dressed, HK Living, Craie-Studio.)
- **Deep Dives — failures only, retrieval-aware.** (1) Only NON-PASS judgments are fed to the
  Sonnet prompt — never let it pad a thin capability with passing queries reframed as problems
  (e.g. a PASS partial-match query shown as "ranked poorly"). Show fewer than 5 if there are
  fewer failures. (2) Match the narrative to the failure type: RETRIEVAL failures (zero/semantic/
  category-mapping/fuzzy) → "returned nothing" (+ "even though…" ONLY with proof of stock, Oct 2026), NO fabricated
  "Should have seen" product list, NO "position #X"; CONSTRAINT_DROPPED → lead with the violation
  across the set; only POOR_RANKING/PARTIAL (results exist) use before/after + displacement.
- **What's Working surfaces strengths at the QUERY-CATEGORY grain, not capability grain.**
  Capability-level passes (worst-severity-wins) hide real strengths — a capability with one
  failing query reads as "not passing" even when several of its query types passed 100%.
  `build_whats_working_markdown` lists query categories where EVERY test passed (≥2 queries),
  with an example each. (Avoca: surfaces Synonym, Brand search, Special character,
  Plural/singular, Partial query, Multi-attribute — vs the old output that showed only the one
  fully-passing capability, "Brand & Model Search".) Keeps the partial-wins fallback when no
  category passes cleanly. *(Oct 2026: every fallback statement is now verified against data —
  the old "relevant results found in {POOR_RANKING count} of {total}" and unconditional
  "correctly interprets typos" lines stated false facts; if nothing holds, the section is omitted.)*
- **Roadmap — consolidate the product-type/head-noun fix.** The "product type / head noun
  under-weighted vs a modifier" defect (outerwear→throws, woollen throws→sweaters, throws
  grey→socks, winter coat sale→socks, grey accessories→t-shirts) is ONE fix — the prompt now
  forces it into a single item (requirement + ranking boost), not split into "require head
  noun" and "boost product type". Roadmap item #1 must still name concrete signals, never
  abstract "relevance/ranking". Likewise consolidate ALL category-mapping failures
  (occasion/colloquial/category terms → taxonomy) into ONE item — don't split out "stationery"
  or any single term, whether it maps to an exact category page or spans multiple nodes.
  No standalone "fix ranking / relevance order / surface highest-scoring first" item either —
  all ordering-of-retrieved-results cases are the product-type/head-noun fix and fold into it
  (the model repeatedly tries to manufacture a 7th item by re-splitting this defect).
- *(Oct 2026: external citations removed — see Current contract. The all-search vs
  with-results distinction below still holds.)*
- **Benchmarks lead with the dead-end comparison, all-search metrics honest.** The table's
  headline row is the **dead-end rate** (`pct_no_relevant_first`) vs Baymard's ~31% industry
  average / <10% target — the one metric with a directly comparable published number, and where
  the zero-result findings actually land. "Relevant in top 3" uses the **all-search** figure
  (`pct_top3_relevant_all`, counts zero-results as no-relevant), not the with-results-only number
  that inflates it (39% not 53% for Avoca). Position/irrelevant-#1 rows are labelled "when
  results returned". Don't present with-results-only percentages as if they cover all searches.
- **Methodology Phase 6 wording is retrieval-inclusive.** Describe severity as based on
  customer impact (returned nothing / wrong products / poorly ordered), not "how far the best
  result was buried" — the displacement-only phrasing misdescribes a retrieval-dominated audit.
- **"Search risk at a glance" / short version — the "first fix to ship" line is the roadmap
  item-1 TITLE only**, not title + full description (`_build_short_version_fix`). It must be one
  short, scannable, actionable sentence; the detail lives in the Prioritized Roadmap section.
- **"Most severe example" (`pick_worst_example` → `stats["worst_example"]`) must be a TRUE,
  genuine failure.** (1) Skip PASS judgments — never feature a catalog-gap zero (e.g. "American
  Vintage top black", which the store simply doesn't carry). (2) The "you carry it" claim must
  be VERIFIABLE: a zero-result that judging mapped to a real site category ("cosy loungewear" →
  you have a "Sleep & Loungewear" category) or a constraint the engine ignored ("not wool" → N
  wool results). Do NOT use the old token-match proof-of-stock that cited an unrelated product
  ("Vintage … Joggers" supposedly proving a "black top" is stocked) — a top and joggers are not
  the same; that produced false claims. Prefer category-mapping dead-ends, then constraint
  drops, then plain dead-ends, then ranking.
- **Coverage map (per-category) — stable rows show no diagnostic question or "Next tuning
  move".** A row with zero issues shouldn't pose "Does search …?" or suggest a tuning move
  (nothing to tune). `_build_coverage_summary` sets `has_issue`; the template gates both
  `item.meaning` (question) and the `coverage-remedy` block on it. Stable rows show only the
  status + "N probes reviewed: N stable results."
- **Coverage signal note states the failing-probe COUNT, not "at least one…".** `_coverage_signal_note`
  takes `total` and reads e.g. "3 of 4 probes returned shopper-visible misses" / "1 of 3 probes
  surfaced relevant products but not cleanly" — varies per row, not robotic. (Watch article/plural:
  "a shopper-visible miss" singular vs "shopper-visible misses" plural.)
- **Result Set Purity communicates the impact, not a bare "0/5".** A list of identical
  "0/5 relevant" reads like a broken metric. Lead the result with the count of searches whose
  ENTIRE top 5 was off-topic (`fully_offtopic_count`) — "On N searches the entire top 5 was
  off-topic — a full page to discard" — and frame the average (e.g. 77%) as "most pages clean,
  but the misses are total". Evidence lines (`_purity_evidence_line`) say "not one of the 5
  visible results matched…" / "only N of 5 were relevant", never "0/5".
- *(Oct 2026: largely resolved — both renderers read `src/report_stats.py`, and the HTML renders
  the stored reviewed narratives. Still true: layout lives in two places — md builders in
  `report_generator.py`, `_build_*` + `master_report.html` for HTML.)*
- **The HTML deliverable is a PARALLEL renderer — tune both paths.** `report_generator.py`
  markdown builders feed the `.md` file; `src/html_renderer.py` + `templates/master_report.html`
  render the HTML independently. Shared (fixes propagate automatically): `compute_aggregate_stats`,
  `build_capability_scores`, `build_advanced_diagnostics_sections`, and the roadmap (parsed from
  `roadmap_narrative`). NOT shared — the HTML has its own `_build_*` (must port fixes there too):
  executive/risk (`_build_short_version`/`_build_risk_cases`), Test-Results metrics, **benchmarks
  (`_build_benchmarks`)**, **What's Working (`_build_whats_working`)**, **deep dives
  (`_build_deep_dives`)**, methodology (template block). New stats keys must be added to
  `_build_stats` (the HTML's transformed stats dict), not just `compute_aggregate_stats`. Active
  template is `master_report.html` (`report.html` is legacy; it still has `{{ pipeline_name }}`).
  `generate_report(..., deep_dives_md=, roadmap_md=)` accepts reviewed narratives so the final
  report uses the approved versions rather than a fresh (re-splitting) LLM call.
- **Advanced Diagnostics was rebuilt on judged data, not reranker scores (replaces the old
  five).** The previous metrics (Result Set Purity, Top Result Trust, Attribute Drift, Diversity,
  Specificity Scaling) all re-derived relevance from the raw Voyage score — opaque to the client,
  duplicated the judge, and had to be `_is_pass`-muzzled to stop contradicting the verdicts. They
  are RETIRED. The section now has four plain-language analyses built on judge verdicts /
  failure_mode / displacement / titles / price (`advanced_diagnostics.py`): **(1) "Did the best
  match come first?"** — ordering quality from `displacement` (non-PASS, ≥2 results); **(2) "The
  specificity cliff"** — pass rate by query word-count tier (1/2/3+ words); **(3) "When it misses,
  what shows up instead"** — wrong-product substitution table from the wrong-#1 failure modes;
  **(4) "Did it respect the filters?"** — constraint-obedience rate over PRICE_ANCHORED /
  NEGATIVE_INTENT / MULTI_ATTRIBUTE / FACET_EXTRACTION / UNIT_VARIATION, violations from
  CONSTRAINT_DROPPED/FACET_NOT_EXTRACTED. **Sections self-suppress** when not applicable: the
  cliff needs ≥2 word-tiers with ≥`SPECIFICITY_MIN_PER_TIER` (3) queries each; constraints/
  substitutions need at least one qualifying query — no "N/A" tiles. Don't reintroduce the old
  score-threshold metrics. Section dicts now carry a `type` (`rate_list`/`bars`/`table`) the
  template (`master_report.html` advanced-diagnostics block) and markdown builder both switch on;
  the common envelope is `title/question/headline/headline_label/headline_class/narrative`.
- **Never show a result position for a zero-result query.** `best_position` is derived as
  `displacement + 1`, but `displacement` is meaningless when nothing was returned — it produced
  a self-contradicting card ("No results returned" alongside "Best result at position #16"). The
  deterministic renderers now guard on empty results: deep dives carry a `no_results` flag
  (`_build_deep_dives`) and the template gates both the topline position and the "buried at #N"
  note on it; the HTML appendix (`_build_appendix`) and markdown appendix (`report_generator`)
  emit an em dash for the position of a zero-result row. The LLM deep-dive prompt already forbids
  "buried at position #X" for retrieval failures — keep the deterministic paths consistent with it.
- **Capability severity ease-up (Part 1 scoring).** `build_capability_scores` is
  worst-severity-wins, which overstates a capability where most queries actually pass. Rule:
  **downgrade CRITICAL → MODERATE when more than half the capability's queries passed**
  (`pass_count > total/2`). Keeps a single critical query from branding an otherwise-healthy
  capability as critical. (Avoca: Typo Tolerance 8/10 pass and Filters & Constraints 6/11 pass
  downgrade to MODERATE; Shopping Context, Language Understanding, Product Discovery stay
  CRITICAL as the majority of their queries fail.)

---

## Per-site profiles

### baechli-bergsport.ch (Bächli Bergsport)
- **User asked for LOCAL HTML ONLY for this audit — skip Phase 8 publish entirely.** Generated `_report.md`/`_data.json`/`_report.html` into `reports/baechli_bergsport_ch/` and stopped there; did NOT run `publish_report` (no findsherpas.com page, no CRM registry entry for this run). This is a per-request override of the normally-mandatory Phase 8 — only do this when the user explicitly says "local only" / "don't publish"; otherwise Phase 8 stays mandatory per the skill.
- **`Severity` enum requires the FULL canonical string, not a paraphrase.** When manually constructing `QueryJudgment` dicts for zero-result queries (bypassing the LLM judge), using shorthand severity text like `"Critical — Search fails outright. High customer impact."` fails Pydantic validation — the enum only accepts the exact four strings from `src.models.Severity` (e.g. `"Critical — Customers searching this way see irrelevant results. This directly loses sales."`). Always pull the literal enum value, never write a severity string from memory.

---

---

## When you learn something new

After every Phase 7 edit, append a per-site profile (tone/emphasis for this host or
recipient) or a General-learnings entry if it generalizes.
