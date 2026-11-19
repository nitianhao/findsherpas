# Search detective experiment: Imerco

Recorded 2026-11-03. Status: bounded LLM candidate builder implemented and exercised. See [implementation results](implementation-results.md) for real API runs, coverage, errors, and limitations. Danish query/control suites have also been generated and reviewed; see [query generation results](query-generation-results.md). Searches have now been executed; see [search execution results](search-execution-results.md). Result evaluation is now complete; see [evaluation results](evaluation-results.md). The original prospective design below is retained as the experiment specification.

## Decision and feasibility assessment

Yes: this can become a repeatable LLM workflow. A bounded program should collect pages, give the LLM evidence to interpret, validate its structured output, and save checkpoints. The LLM chooses useful categories, interprets product facts, matches evidence to failure modes, and later drafts Danish queries. Code controls fetching, provenance, unit conversion, schemas, budgets, and execution.

This session demonstrates that useful evidence can be collected from Imerco without using its search to discover products. It does not demonstrate autonomous API-model performance, cross-store reliability, or search failure rates. Candidate selection and interpretation were performed by the assistant with exploratory Python scripts. No separate LLM API experiment was run for candidate discovery.

The first deliverable should be an autonomous **candidate builder**, ending after verified candidate mappings, before query generation or execution. Benchmark it against this session's evidence. Only then add query generation and investigation.

## Intent and agreed scope

- Eventually productize expert-quality search optimization: discover → prove → diagnose → propose → verify → monitor.
- No access to search logs is expected. Do not infer traffic frequency or revenue loss from synthetic test results.
- Keep Shopify plugin work out of scope.
- Use a failure-mode library for systematic coverage, plus bounded exploration for surprises.
- Discover products independently of search; verify attributes first; construct queries second.
- If evidence is insufficient, skip a test rather than invent a product or requirement.
- User approved the ten difficult failure modes and accepted the displayed candidate list. This is not implementation approval or a reviewed gold dataset.

## Session record

1. Located the established search evaluator in `src/audit/` and the standalone shopper prototype in `src/audit/src/shopper_agent.py`.
2. Recorded five development directions in `docs/search-improvement-ideas.md`: investigate causes; independently establish suitable products; test query relationships; measure shopper effort; test fixes and regressions.
3. Built `docs/search-failure-modes.md`: 120 initial candidates, including 30 explicitly accepted modes. User excluded voice transcription, delivery deadlines, review contradictions, visual style, and conversational memory. There are 115 active candidates; not all were individually approved.
4. Selected Imerco from existing audit evidence and fetcher profiles as a practical starting store.
5. Ran a limited live extraction probe: `Scanpan`, `krus hvid`, and a nonsense query. Saved five results per positive query; reported hit counts were 214 and 238. Nonsense query was positively confirmed empty. Static, site-specific extraction worked.
6. Cross-checked Scanpan's first five results against rendered Google Chrome: titles, order, and displayed prices matched. Bundled Playwright Chromium was unavailable; installed Chrome via `channel='chrome'` worked.
7. Found a price caveat: the extractor preserves the displayed member price but loses its membership condition. This matters for budget tests.
8. User approved ten difficult failure modes, listed below.
9. Discovered products through homepage category links and seven category pages, then fetched 12 selected product pages. Saved descriptions/specifications and mapped candidates to the ten modes. No experimental queries were generated or executed yet.

The extraction probe used search solely to verify the existing extraction machinery. It was not the source of product discovery for the candidate experiment.

## Ten candidate mappings

See `evidence/verified_candidates.md` for product links and `evidence/verified_candidates.json` for structured mappings.

| Mode | Product anchor | Evidence |
| --- | --- | --- |
| Negation | Eva Trio Legio Nova cup, 100347058 | Explicitly classified as a cup without a handle; 25 cl, porcelain. |
| Either/or materials | Eva Trio Legio Nova bowls, 100353730; Bjørn Wiinblad Guirlande bowls, 100408047 | Porcelain versus glass; both are serving bowls. |
| Unit conversion | Stelton EM77 jug, 100437750 | 1.5 L equals 150 cl or 1500 ml. The observed listing uses litres, so reverse the original illustrative conversion. |
| Dimension distinction | CASA Living vase, 100465402 | Height 20 cm, diameter 15.5 cm. |
| Pack versus capacity | Georg Jensen Bernadotte glasses, 100404522 | Six glasses, capacity 25 cl each = 250 ml each. |
| Solid wood versus veneer | FDB Møbler D102, 100455702; Hübsch Skak, 100478281 | Explicit solid oak versus MDF/oak veneer. |
| Induction compatibility | Eva Trio Stainless Steel pan, 100456331 | Description explicitly includes induction. |
| Combined exclusions | Eva Trio Multi 5-ply pan, 100468229 | Stainless steel; description explicitly states no coating. PFAS-free alone would not prove uncoated. |
| Adding valid detail | Stelton EM77 jug, 100437750 | Capacity 1.5 L and ABS plastic support a controlled specificity ladder. |
| Conditional price | Scanpan Fusion 5, 100414744 | 499.95 DKK members, 969.95 DKK nonmembers. Negative example under a nonmember 500-DKK budget. Eva Trio Multi 5-ply at unconditional 499.95 DKK is a positive contrast at capture. |

Prices and availability must be refreshed before execution. A search showing a member price is not automatically defective: judge whether eligibility is clear. Missing membership labels in our own extraction are an extraction defect, not proof of a store defect.

## Proposed LLM workflow

### 1. Plan independent coverage

Input: store URL, locale, selected versioned failure-mode definitions, explicit fetch/model budgets.

Fetch homepage navigation. Give the LLM only observed links and ask it to select categories likely to expose the needed attributes. Output category IDs/URLs and their intended modes. Reject invented URLs and search endpoints. Category filters/pagination are allowed; search-generated product discovery is not part of this baseline.

### 2. Collect a bounded product pool

Code fetches selected category pages, extracts product links, deduplicates by product/variant identity, and saves page snapshots. The LLM ranks candidates for detail-page inspection from the observed cards. Do not download the entire catalog or let the model browse indefinitely.

For the first pilot, proposed configurable ceilings are seven category pages, 40 detail pages, and 30 model calls, with an operator-configured currency cap. Stop with explicit uncovered modes when a ceiling is reached. These are starting limits, not measured optimal settings.

The model-call cap is authoritative: batch up to five product fragments per extraction or verification call, reserve six of the 30 calls for planning and uncovered-mode exploration, and stop with abstentions if the remaining calls cannot complete verification. Each call also has bounded input/output tokens; enforce the configured currency cap before dispatch. Failed calls and retries count toward the cap.

### 3. Extract facts with evidence

Parse structured specifications/JSON-LD where possible, then ask the LLM to extract only supported facts from the product page. Each fact must reference a saved source fragment and exact source quote. Retain original Danish text and normalized values.

Validate that quotes occur in the saved fragment and refer to this product, not recommendations, variants, or brand-wide marketing. Quote existence checks grounding but does not prove correct interpretation; contradictions go to review or abstention. Store content is untrusted data, never instructions to the model.

### 4. Match facts to test requirements

Give the LLM the verified product pool and explicit requirements for each mode. It proposes positive examples, contrasting negatives, and unknowns. Deterministic checks enforce numeric equivalence and required evidence fields.

Reject unsupported negatives: no mention of coating is not evidence of no coating. Preserve capacity-per-item separately from pack quantity; height separately from width; solid material separately from veneer; offer price separately from eligibility.

### 5. Challenge the proposed candidates

Run a separate verification pass against source evidence, without treating the first model's conclusion as truth. Ask whether every required attribute is established, whether the product is currently obtainable, and whether a contrasting product really violates the intended requirement. An independent pass can still share model biases; human-reviewed calibration remains necessary.

Outputs: verified, rejected, needs_review, or unsupported. A mode without enough evidence remains uncovered. Model self-confidence is not a reliability metric.

### 6. Construct queries only after candidate verification

Ask the LLM for natural Danish queries, baseline controls, and one controlled variation per targeted behavior, citing the fact IDs that justify expectations. Preserve shopper context such as nonmember pricing. Validate language, units, contradictions, and accidental extra requirements before execution.

The selected anchor is evidence that the need is satisfiable, not the only acceptable answer. Missing it alone is not necessarily a failure if equivalent qualifying products are readily found. For an either/or query, either material can satisfy an individual result; not displaying both types is not itself proof of failure. Compare controlled queries and known coverage before making a broader claim.

### 7. Execute and investigate (later stage)

Reuse fetch outcomes and evidence capture. Check whether returned products satisfy the verified need; fetch result details where cards are insufficient. Repeat suspicious failures, compare controls, and classify: confirmed observable failure, suspected failure, inconclusive, catalog/stock change, or extraction/agent failure.

Keep separate findings for observable behavior and hypothesized internal causes. A public storefront usually cannot prove a configuration-level cause. The browser shopper can investigate friction, but its own mistakes must not become site failures.

## Required evidence for the ten pilot modes

| Mode | Minimum acceptance rule |
| --- | --- |
| Negation | Explicit handleless classification; absence of a handle mention is insufficient. A handled contrast requires explicit evidence too. |
| Either/or | At least one verified bowl for each material branch; preserve the OR relation. No negative example is mandatory. |
| Unit conversion | Explicit capacity and unit on the identified product; conversion computed in code. |
| Dimensions | Explicit height and a distinct diameter or width, retaining axis labels. |
| Pack/capacity | Explicit pack count and capacity per item; unresolved aggregate capacity means abstain. |
| Material | Explicit solid-oak claim for positive and explicit veneer/MDF evidence for contrast. Plain “oak” does not establish solid wood. |
| Compatibility | Explicit induction suitability; no negative contrast may be inferred merely from missing compatibility text. |
| Combined exclusions | Explicit stainless-steel surface/material and explicit absence of coating; PFAS-free does not suffice. |
| Added detail | At least two verified attributes belonging to the same product variant; define one changed attribute per step. |
| Conditional price | Both member and nonmember offers, eligibility, currency, capture time, and a verified unconditional under-budget contrast. Refresh before executing. |

Current historical captures have session-date rather than exact per-page fetch times; the future pilot must populate those timestamps on fresh collection.

## Minimum checkpoint contracts

- `run`: ID, timestamps/timezone, store/locale, library version/hash, prompts and hashes, model IDs, sampling settings, code revision, budgets, usage, errors.
- `source`: ID, original/final URL, fetched timestamp, HTTP status, transport, snapshot path/hash, product/variant identity, extraction strategy.
- `product`: stable ID, URL, category-source IDs, variant, availability, offers and eligibility, fact IDs.
- `fact`: ID, attribute, raw value/unit, normalized value/unit, source ID, source-fragment locator, exact quote, verification status and contradiction notes.
- `candidate`: mode ID, positive product IDs, contrast IDs, required fact IDs, rationale, limitations, status and uncovered reason.
- `test`: candidate ID, Danish query, baseline/control, changed requirement, expected eligibility rule, evidence IDs, customer context.

Save stages independently as JSON. Resume without silently overwriting reviewed facts or paying for completed model calls. Include skipped modes and failed fetches in the final coverage manifest.

## Existing code: reuse and gaps

- `src/audit/src/llm_compat.py`: existing client, structured Pydantic responses, failure handling, and usage accounting. Reuse rather than introducing a separate model integration. Model choice must be configurable; do not assume a provider/model label establishes capability.
- `src/audit/src/fetcher.py`: existing transport, site-specific extraction, status classification, and evidence capture. Reuse for executing later queries. Candidate crawling needs generic source capture and product-detail parsing, not only SERP extraction.
- `src/audit/src/discovery.py`: navigation discovery is useful. Its `build_catalog_sample()` uses seed searches, so it is unsuitable as the independent candidate baseline without a separate category-first path.
- `src/audit/src/query_generator.py`: existing constraints and validation can help, but title sampling is insufficient for evidence-linked tests. Extend with an explicit verified-candidate input rather than silently replacing ordinary audits.
- `src/audit/src/shopper_agent.py`: optional later investigator; not required for the candidate-builder milestone.

Keep the experiment separate from report generation/publishing and the ordinary orchestrator until validated. Build in Python to fit this existing Python subsystem.

## How to establish reliability

Proposed pilot acceptance criteria, not achieved results:

1. Replay saved source snapshots: every accepted required fact has a resolvable source and matching quote; no unsupported decisive attributes or price conditions in human review.
2. Preserve identity, units, dimension axes, pack/per-item quantities, material distinctions, and offer eligibility on all accepted pilot mappings.
3. Resolve all ten modes as covered with valid evidence or explicitly unsupported; never force coverage. The ten current mappings are a starting benchmark, not a required exact product list.
4. On fresh collection, cover at least eight modes within the declared budget; review whether missed modes reflect catalog changes or workflow limitations. This threshold is provisional.
5. Run candidate creation three times against the same snapshots and compare valid mode coverage, unsupported assertions, and cost. Different valid products are acceptable.
6. Evaluate on additional independently chosen products and at least one other store before any general reliability claim. Avoid tuning only to these 12 products.
7. Log runtime, fetched pages, token usage, actual/estimated cost with pricing source/date, human corrections, abstentions, and discovery provenance. No cost prediction is established by this session.

## Evidence and reproducibility

The `evidence/` directory contains copied category listings, 12 product-page text captures, candidate mappings, live extraction outcomes, and the browser cross-check. A hash manifest records these captured files.

Original run folders remain under `src/audit/reports/imerco_dk/{candidates_20261103,extraction_check_20261103}/`, including the extraction screenshot and gzipped search HTML. That reports tree is gitignored, so core evidence was copied here for a portable handoff. These new documentation files are not committed yet.

Collection scripts are preserved in `scripts/`. They are historical exploratory scripts with hardcoded categories, IDs, and output paths, not the proposed autonomous workflow. Run from `src/audit/` with `.venv312/bin/python`; category collection precedes product verification. Re-running live may change the results. Product evidence retained here is extracted text, not original product HTML; the original collection did not record precise per-page timestamps or hashes at fetch time. The manifest hashes preserved files now and does not retroactively establish capture-time integrity.

## Next action

The candidate-builder milestone has been implemented. See [implementation results](implementation-results.md) and `src/audit/src/candidates/README.md` for execution details. Danish query construction is now complete for the nine accepted modes; see [query generation results](query-generation-results.md). Search execution is complete; see [search execution results](search-execution-results.md). Result evaluation is complete; see [evaluation results](evaluation-results.md). Root-cause investigation is the next stage.

## Document review

A separate builder review found no factual discrepancies in the preserved product records. Its clarifications are incorporated: candidate-only first milestone, explicit per-mode evidence requirements, and batched calls under an authoritative budget. Offline extraction/matching replay and fresh autonomous category discovery are separate evaluations.

## Unit-conversion investigation completed

The first root-cause investigation is documented in [unit investigation results](unit-investigation-results.md): 18 controlled queries, eight stable repeats, read-only request counterfactuals, and a tested local normalization/filtering prototype. No production configuration changed.

## Commercial-relevance follow-up — 2026-11-04

The user challenged prioritizing an uncommon unit-conversion issue. We completed a separate [ordinary-shopping cohort of 30 frozen searches](../ordinary-search-imerco-2026-11-04/results.md), covering five categories and recording availability, relevance, and variant concentration. That report supersedes any plan to treat difficult synthetic cases as evidence of frequent conversion loss.
