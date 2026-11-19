# Shopify search evaluation: research and product plan

**Status (2026-10-19):** planning paused while the owner adds more audits. This document is the product brief for resumption, not an instruction to start implementation now. See [build handoff](WHEN_READY.md). Re-inventory audit counts and revisit cohort size when the owner is ready.

## Goal

Build a Shopify app for store owners who do **not** know search terminology or have technical help. It should answer three questions: **Can shoppers find what I sell? What is going wrong? What should I do next?** A useful free check should show concrete examples and a practical next step; paid plans should provide broader coverage, scheduled monitoring, guided fixes, and optional search-provider integrations. The app should use deterministic, catalog-grounded checks wherever possible and spend on AI only when a case genuinely needs interpretation.

**Non-negotiable product requirement:** after a merchant installs and configures any optional connector, the app runs without Find Sherpas involvement. It must discover the catalog and active search surface, select and run tests, validate evidence, publish understandable findings, handle uncertainty, and repeat on schedule. No audit may depend on the founder reviewing queries, correcting verdicts, operating scripts, or approving a report. Expert review in this plan is temporary **research and prelaunch validation**, not a production workflow.

**Non-negotiable experience requirement:** installation and the first useful result must require no search expertise, query writing, data export, or consultation. The merchant should understand each finding and its next action without learning terms such as *relevance*, *facet*, *recall*, *reranker*, or *severity*. A report that is technically accurate but leaves the merchant unable to act does not meet the product goal.

The originally proposed 50 additional stores are a **research program**, not a target number of reports to accumulate. Reassess how many more stores are needed after the owner's new audits are inventoried. The output is a verified benchmark, a library of reusable checks, and evidence about which diagnoses merchants value.

## Starting point

- Fourteen completed audits are represented by published report pages, covering approximately 854 tested queries according to their report titles. Eight of those audits also retain full local raw JSON with 480 query judgments; the other six currently have published HTML but no local raw JSON. Douglas and Zalando have partial audit checkpoints and are not counted as completed audits.
- The existing audit pipeline discovers a site, generates queries, fetches results, reranks them, judges failures, and writes a report. It has useful query categories, failure modes, and a substantial calibration playbook.
- The current calibration knowledge base has 119 entries. It retrieves examples for the AI judge; it is not a verdict cache or a deterministic rule engine. Entries are harvested from audits without mandatory expert approval. It should **not** be copied directly into the customer-facing app as ground truth.
- Past calibrations identify recurring errors: a zero-result query when the item was never stocked, attributes invisible in titles, misleading relevance scores, wrong result extraction, and an apparently good first result masking a mostly irrelevant page.

## What we are building

Keep three assets separate:

| Asset | Purpose | Admission rule |
| --- | --- | --- |
| **Gold benchmark** | Measure whether the app makes correct claims | Expert verifies the query, catalog evidence, actual displayed results, and verdict |
| **Rule library** | Power cheap, repeatable merchant-facing checks | Rule has explicit preconditions, evidence requirements, and tests against gold cases |
| **Research examples** | Discover new failure patterns and calibrate optional AI analysis | May be machine generated; never treated as verified labels |

Every benchmark case should record: store and locale; retail category; catalog snapshot/date; search provider and surface tested (search page or autocomplete); query and test type; exact returned product IDs, order, and visible attributes; evidence that the expected item is actually available; expert verdict and rationale; confidence; and whether the case is suitable for a customer-facing claim. Keep snapshots because catalogs and rankings change.

Store-level splits matter. Cases from a store used to design a rule cannot also serve as the final proof that the rule generalizes.

## Research program: staged expansion, up to 50 additional stores

### Phase 0 — Reuse what we have

1. Inventory all 14 completed audits. Map the eight available raw JSON reports into one benchmark schema, then assess what case-level evidence can be recovered from the six HTML-only reports. Keep partial Douglas and Zalando checkpoints separate.
2. Have the search expert review the strongest examples and known corrections first. Label cases **verified**, **uncertain**, or **rejected**.
3. Write the first 10–15 narrow checks from repeated patterns in the playbooks. Define for each check what evidence is required and when the app must say “cannot verify.”
4. Record the current cost and time per audit phase. Establish a per-store run budget before starting the new cohort.

**Exit gate:** a small verified seed set, a repeatable annotation process, and a cost dashboard. Do not count the existing raw or published judgments as gold labels automatically.

### Phase 1 — 10 deliberately varied Shopify stores

Choose stores across catalog size, vertical, language, native Shopify search versus third-party search, and simple versus variant-heavy products. Prefer consenting pilot merchants for catalog access and feedback. Public storefronts can reveal patterns but may not let us prove whether a product was stocked or available.

Run a common set of about 25–30 tests per store: known product, brand, SKU, category, typo, prefix, synonym, and simple visible-attribute constraints. Add store-specific tests only when grounded in its catalog. Review all proposed critical findings, all zero-result cases, and ambiguous cases; sample passes too, so we can find missed failures.

**Exit gate:** confirm the app is testing the search experience shoppers actually see. Shopify's storefront `search` and `predictiveSearch` APIs provide native search results, but a merchant's custom or third-party storefront search may require a separate connector or direct storefront observation. Do not report a native API result as a finding about a different search widget. [Shopify search API](https://shopify.dev/docs/api/storefront/latest/queries/search), [predictive search API](https://shopify.dev/docs/api/storefront/latest/queries/predictiveSearch).

### Phase 2 — 20 expansion stores

Use the pilot's error analysis to pick stores that challenge the current rules, rather than simply choosing convenient stores. Increase language and category diversity. Add provider-specific cases only when the app can read that provider's real result surface. Run the same core suite and targeted edge cases.

For each new pattern, either add a deterministic check with clear evidence or mark it as requiring selective automated AI analysis. Track false positives and false negatives by check and by store type. Maintain a small permanent regression set whenever an expert corrects a finding during research.

**Exit gate:** recurring failure patterns are covered; checks work on stores that did not inspire them; cost per store is falling; and the pipeline can complete an audit end to end without an operator.

### Phase 3 — 20 validation stores

Reserve at least 10 of these stores as a true store-level holdout. Freeze the rules and thresholds before running them. Let the app produce its reports entirely automatically, then have the expert assess every critical claim and a sample of passes and lower-severity claims **afterward**, without intervening in the runs. Record performance by category, language, catalog size, and search provider.

**Exit gate:** for the held-out stores, target at least 95% precision on claims labeled “critical”; publish per-check coverage and abstention rates alongside precision. If a check misses this bar, narrow its preconditions or keep it out of the app. Treat this as a proposed launch criterion, not a result we have already achieved.

## Product milestones alongside the research

| Milestone | Merchant experience | How the benchmark helps |
| --- | --- | --- |
| **Free preview** | Install, scan, and see a plain-language summary with roughly 12–20 catalog-backed checks; up to 2–3 complete findings, each with a suggested action | Use only high-confidence deterministic checks; no routine AI judging; show an honest good result if no problem is verified |
| **Paid core** | More checks, a short prioritized to-do list, guided fixes, scheduled reruns, and progress over time | Expand only with checks proven on held-out stores; automated AI analysis handles selected ambiguous cases within a fixed budget |
| **Provider connectors** | A simple connection flow where needed, followed by the same merchant-friendly report | Build a separate adapter and validation set for each provider; do not assume native-search findings transfer |

The initial product should **diagnose and guide the fix**, without silently changing merchant search settings. Where Shopify allows it, take the merchant to the relevant product or search setting; otherwise provide short provider-specific instructions. A later version can offer one-click fixes when they are safe, reversible, and measurable. Merchant feedback on “useful / wrong / already known” findings becomes research input, but never changes gold labels without review.

### Merchant-facing experience

- **First screen:** “We checked whether shoppers can find your products.” Show the number of checks completed, the number of confirmed problems, and the single most useful next action. If no issue is confirmed, say so plainly and show what was checked. Never invent a problem to encourage an upgrade.
- **Finding card:** show the shopper's words, what products the store actually sells, what the shopper saw, why this matters, and one action the owner can take. Use a storefront example or product image where available. Keep technical evidence behind “See details.”
- **Example:** “Shoppers searching for ‘waterproof hiking boots’ see jackets first, even though you sell waterproof boots. Check the boots' product titles and search settings.” The actual action must be tailored to the diagnosed cause; do not give generic advice when the evidence points elsewhere.
- **Priority:** order findings by confidence, affected products, and (when available) actual search demand. Do not claim lost revenue without a defensible calculation. A useful label is “Start here,” not an unexplained numerical search score.
- **Upgrade path:** free users see complete evidence and the action for their visible findings. Paid value is broader coverage, recurring checks, trend tracking, and deeper guidance, not unlocking the explanation of a problem already shown.
- **Language and accessibility:** use the store's language when supported, clear merchant vocabulary, accessible Shopify admin patterns, and a design that works on mobile. If a language cannot be assessed reliably, state the coverage limit.

Shopify's own guidance emphasizes quick onboarding, immediately actionable App Home content, and plain language. [Onboarding](https://shopify.dev/docs/apps/design/user-experience/onboarding), [App Home](https://shopify.dev/docs/apps/design/user-experience/app-home-page), [content](https://shopify.dev/docs/apps/design/content).

### Required automatic workflow

1. **Install:** request only needed Shopify access, identify the catalog and locale, detect the search experience in use, and explain any optional connector setup in a short guided flow. Native Shopify stores should reach the first scan without copying credentials or selecting query types. A connected third-party provider must be tested through its own results; unsupported surfaces are identified clearly.
2. **Generate tests:** select representative in-stock products, brands, categories, and attributes from current catalog data. Produce valid test queries from controlled templates. Avoid invented products and impossible constraints.
3. **Run and verify:** fetch the search results shoppers actually see, match them to catalog records, and run deterministic checks first. Use bounded AI analysis only for paid cases that cannot be resolved reliably by rules.
4. **Decide automatically:** publish a finding only when its required evidence is present and confidence clears its threshold. Otherwise retry transient errors, label the test inconclusive, or omit it. Never route a routine case to Find Sherpas for a decision.
5. **Report and repeat:** translate the query, observed results, and catalog evidence into a plain-language finding with one prioritized next action and an optional technical detail view. Schedule reruns after catalog changes or at the plan's cadence; show whether a merchant action improved the result, and alert on newly confirmed issues.
6. **Learn safely:** collect merchant feedback and anonymous quality metrics for future rule releases. Human review may improve the global product offline, but no individual store's report waits for it.

**Product launch gate:** a merchant can install the app, understand the initial result, take its suggested action, and receive scheduled updates without contacting us. An unsupported search setup must yield an honest, actionable setup or coverage message rather than a misleading audit. An AI outage or exhausted cost budget must degrade to deterministic findings and inconclusive tests, not block the report. Before launch, test the flow with nontechnical Shopify merchants: they should be able to explain the top finding and complete or confidently delegate its suggested action without us coaching them.

## Cost and quality controls

- Cap requests, products inspected, AI calls, and runtime per store. Log actual vendor spend per audit and per accepted finding before setting prices.
- Generate queries from the store's catalog and verified taxonomy. Run cheap checks first. Escalate to reranking or an AI judge only when a paid analysis needs it and a deterministic decision is unavailable.
- Cache immutable catalog snapshots and result evidence for review; rerun live checks when reporting current status.
- Measure the production funnel automatically: generated tests → valid tests → verifiable results → published findings → merchant-rated useful findings. Separately, measure expert-confirmed accuracy on research and holdout stores; expert confirmation is never a production prerequisite.
- Measure merchant value as well as model quality: installs reaching a first useful result, findings understood in usability tests, actions started/completed, repeat scans, and merchants who say the report changed what they did. Treat support requests about basic interpretation as a product defect to fix.
- Track **precision, false-positive rate, coverage, abstention rate, and cost per confirmed finding**. A high score is not useful if it comes from making too few claims, or from judging the wrong search surface.
- Do not ingest customer personal data into the benchmark. If merchant search logs later improve query selection, design access, retention, and privacy handling separately.

## Roles and decisions

**Search expert (you):** during development, select representative stores, define what constitutes a real failure, adjudicate disputed benchmark cases, prioritize merchant-facing fixes, and assess the fully automatic reports. Once the app launches, your involvement is optional product improvement, not store-by-store operations.

**Engineering (Codex):** build the benchmark importer and research review workflow, Shopify integration, automatic test generation and scheduling, deterministic checks, bounded AI fallback, provider adapters, cost telemetry, regression harness, and app UI. The expert should review product decisions, not operate scripts for every store.

Decisions after the first 10 stores: which store segments to target first; which checks are compelling in the free tier; whether a provider connector is demanded enough to justify maintenance; how much AI analysis merits a paid plan; and whether the next 40 stores still produce genuinely new knowledge.

## First actions when work resumes

1. Recount the newly expanded audit collection; convert available full raw reports into a provisional dataset and inventory HTML-only reports for recoverable evidence, without modifying the audit pipeline.
2. Build a lightweight expert-review screen or spreadsheet export for accepting, correcting, and rejecting cases.
3. Define the first deterministic check set and its evidence requirements.
4. Select the first 10 Shopify pilot stores from the expanded audits where possible, and classify their actual search setup.
5. Run the pilot, review errors and costs, then commit to the next 20 stores.

This plan deliberately leaves price points and calendar estimates open until the pilot produces measured unit costs and review time.
