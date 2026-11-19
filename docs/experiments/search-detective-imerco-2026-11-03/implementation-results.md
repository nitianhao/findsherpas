# Candidate-builder implementation results

2026-11-03. The approved candidate-discovery milestone is implemented in `src/audit/src/candidates/`. No experimental queries have been generated or executed. No report was published and no store configuration was changed.

## Outcome

A real API model can perform the candidate-building work outside this chat. In fresh category-first collection it selected seven categories and 35 products without fixed product IDs or using store search. The initial live validation accepted eight modes. After fixing extraction/review issues, a replay of those same autonomously collected product sources accepted nine modes. The final run did not make new storefront requests or substitute manually selected products.

The curated 12-product replay ultimately covered all ten modes. That is evidence for extraction/matching on supplied products, not autonomous discovery. Neither result establishes general reliability across stores.

See [accepted model-selected candidates and source quotes](model-selected-candidates.md), [machine-readable run summary](run-summary.json), and [implementation guide](../../../src/audit/src/candidates/README.md).

## What was built

- Imerco-only category-first collection: observed homepage links → model-selected categories → model-selected product cards → saved product detail pages.
- Structured fact extraction with product identity, short source quotations, typed attributes, numeric normalization, and original source metadata.
- Deterministic reference/quote validation; separate dimension axes, pack counts and per-item capacity; member versus public pricing; explicit proof required for no-coating claims.
- Ten explicit mode contracts and independent model-call review. Source presence alone cannot approve a claim. Reasons are generated before the approval boolean.
- One bounded re-extraction pass for absent/non-contiguous quotations. Failed claims remain in the evidence; no repeated “try until approved” loop.
- Call/currency budgets, source and prompt hashes, usage estimates, resumable checkpoints, and refusal to silently reuse incompatible runs or edited product checkpoints.
- Replay and fresh-collection CLI modes using the existing LLM adapter, with no dependencies added.

Public promotional prices count as public prices when unrestricted; they do not have to be full list prices. Danish `kr`/`DKK` units normalize to DKK in this store-specific adapter. Unknown or unsupported conditions remain unaccepted.

## Real API trials

All trials used `claude-sonnet-4-6` through the existing API client. These are successive engineering iterations, **not** a repeatability study with an unchanged configuration.

| Trial | Input/discovery | Accepted modes | API requests | Estimated USD |
| --- | --- | --- | --- | --- |
| Curated replay 1 | 12 earlier manually selected products | 9/10 | 6 | 0.168414 |
| Curated replay 2 | Same 12 products, stronger checks | 8/10 | 7 | 0.176226 |
| Curated replay 3 | Same 12 products, clarified review instructions | 10/10 | 7 | 0.172344 |
| Live discovery 1 | Six categories, 30 model-selected products | 7/10 | 19 | 0.518523 |
| Live discovery 2 | Seven categories, 35 model-selected products | 8/10 | 18 | 0.538173 |
| Final live-evidence replay | The same 35 autonomously selected products, final checks | 9/10 | 15 | 0.414438 |

Total estimated API spend across these trials: **$1.988118**. The successful seven-category collection plus final evidence re-evaluation cost about **$0.95** together. This is a two-pass development result, not a measured price for one cold run of the final pipeline. Costs use recorded token usage, including cache writes/reads, and the checked [Sonnet 4.6 API rates](https://platform.claude.com/docs/en/models/sonnet-4-6/overview); they are estimates rather than invoices. Every trial had its own $3 budget and a 30-request cap.

## What the trials exposed

1. **Quote presence is insufficient.** The model quoted a real steel-pan description but used it to claim no coating. Review rejected it. An explicit-negative guard now rejects that claim earlier; PFAS-free also does not prove uncoated.
2. **The reviewer can falsely reject correct evidence.** It treated a SuperPris offer as ineligible just because it was promotional, and overlooked an explicit solid-oak phrase elsewhere in the source. Review instructions now distinguish eligibility from promotion and inspect the full product source.
3. **Collection truncation can masquerade as a catalog gap.** The initial 220-link navigation cutoff omitted furniture. The adapter now retains the full observed navigation up to a bounded 400 links, then stops explicitly rather than silently losing later sections. The corrected live run selected tables independently.
4. **Formatting errors should not become invented facts.** The live model combined separated solid-oak passages using an ellipsis; exact matching rejected them. The prompt now demands contiguous quotations, and one bounded format-repair pass is available.
5. **Store-specific normalization matters.** Some price facts used `kr`, others `DKK`, and a few omitted a unit entirely. Known Danish currency aliases normalize; missing units remain rejected. Composite capacities such as a two-bowl set's `1,4/2,5` are not collapsed into a single guessed capacity.
6. **A final representation error remains.** The either/or mapping identified valid glass and porcelain bowls, but duplicated them as both positive and contrast examples. Validation rejected it, leaving final accepted coverage at nine. We did not manually force a pass. A bounded proposal-correction stage is a possible next improvement.

These are workflow errors and limitations, not findings about Imerco search. The system kept rejected and uncovered cases visible instead of reporting them as search failures.

## Verification

- 18 new focused offline tests passed: quote/reference rejection, numeric/unit normalization, explicit negative evidence, observed-link restrictions, product identity, budgets, cached calls, failures, independent review rejection, navigation coverage, edited checkpoint rejection, bounded quote repair, and provenance retention.
- Full audit offline suite: **299 tests passed**.
- Syntax and tracked whitespace checks passed.
- Actual final-run `--resume` replay completed with the same 15 journaled API requests and identical cost estimate: **zero new API requests**.
- A completed candidate run can legitimately have incomplete mode coverage. No search-quality verdicts were produced.

## Reproduce

From `src/audit/`, with the existing environment/API credentials:

```sh
# New autonomous discovery; current code may select different valid products.
.venv312/bin/python -m src.candidates \
  --live --out reports/imerco_dk/candidates_new --max-usd 3

# Curated evidence replay: model work, no storefront collection.
.venv312/bin/python -m src.candidates \
  --replay ../../docs/experiments/search-detective-imerco-2026-11-03/evidence/products.json \
  --out reports/imerco_dk/candidates_replay_new --max-usd 3

# Resume the exact same run/configuration without repeating completed calls.
.venv312/bin/python -m src.candidates \
  --live --out reports/imerco_dk/candidates_new --max-usd 3 --resume
```

The final recorded run was a replay of `reports/imerco_dk/llm_candidates_live_v2_20261103/products.json`, saved to `reports/imerco_dk/llm_candidates_live_evidence_v3_20261103/`. Its unchanged command was resumed successfully.

Portable copies of manifests, product texts, facts, proposals, reports, and exact model requests/responses live under `runs/`; `run-evidence-manifest.json` hashes those copied files. Full live HTML snapshots remain in the local gitignored report folders. Portable product captures retain source URLs and hashes, but do not include every original HTML file. Historical intermediate implementations were revised during the experiment; their exact prompts/replies are preserved, while their code fingerprints should not be mistaken for committed reproducible revisions.

## Remaining limits and next milestone

- Imerco static HTML adapter only; no cross-store reliability established.
- Same model makes extraction and independent review calls, so their errors can be correlated. `verified_candidate` means accepted by these checks, not independent human gold.
- Review still needs calibration. We have not run three unchanged independent trials or a held-out store/product benchmark.
- No active coverage top-up or semantic conflict-resolution loop. This pilot stops with explicit gaps.
- The initial design's six reserved planning/exploration calls were replaced by an explicit first-pass allocation: up to eight category planning/selection requests, then extraction/matching/review within the total cap. No uncovered-mode exploration is implemented yet.
- Source state is time-sensitive; refresh price/availability evidence before testing queries.

The next product milestone is **Danish query construction from accepted candidate facts**, with baseline controls and explicit success rules. Do not score “anchor missing” as a failure when other suitable products are found. Search execution and root-cause investigation follow that stage.

## Follow-up

The query-construction milestone was subsequently completed and independently wording-reviewed. See [query generation results](query-generation-results.md). Search execution remains pending.

Subsequent search execution is documented in [search execution results](search-execution-results.md). Result-level quality adjudication remains pending.
