# Imerco search execution

2026-11-03. Ran the nine reviewed suites: **19 query/control entries, 18 unique search strings**. The duplicate pan baseline was fetched once and reused by both suites.

## Observed outcome

- **13 queries returned products; five showed confirmed zero-result states.** All five empty responses were fetched a second time and remained empty.
- No queries ended blocked, timed out, or unverified in this run. Extraction used the proven static, site-specific path and saved the first ten products at most.
- Refreshed nine anchor/contrast product pages before searching. Product identity checks passed, prior supporting quotations remained present, and each page contained add-to-cart text. No cart action was taken; page text is not a guarantee of complete purchase feasibility.
- A separate rendered Google Chrome check confirmed the vase-height query displayed zero results with no product cards. HTML, visible text, screenshot, and verification metadata are preserved.
- No LLM calls were made during this execution. Result-level attribute satisfaction, precision, severity, and internal root causes have not been adjudicated.

[Full results table](search-execution/results.md) · [Structured observations](search-execution/execution_summary.json) · [Raw top results](search-execution/outcomes.json)

## Empty searches, repeated and unchanged

| Mode | Query | Baseline context |
| --- | --- | --- |
| Height | `vase højde 21 cm` | `vase` returned products. The 21-cm anchor's source evidence refreshed successfully. |
| Pack/capacity baseline | `glas sæt 6 stk` | The baseline itself was empty; the test cannot isolate the effect of adding capacity. |
| Pack/capacity test | `glas sæt 6 stk 38 cl` | Also empty. Treat the incremental capacity experiment as inconclusive pending investigation of the baseline. |
| Solid material | `sofabord massivt egetræ` | `sofabord` returned products, including the verified solid-oak anchor at rank 2. |
| Budget | `stegepande under 500 kr` | `stegepande` returned products. The known public-price pan evidence refreshed successfully. |

These are observable search dead ends, not automatically five distinct root causes or five independent capability failures. In particular, both pack queries may share a wording/retrieval issue. The query library measures synthetic robustness, not real user frequency.

## Other observations worth investigating

- `kande 1,6 L` reported **28** results; `kande 1600 ml` reported **5**. The verified 1.6-L anchor appeared at rank 1 for the first query but not in the five results for the equivalent-unit query. The five extracted titles/cards describe 600, 1800, or 1500 ml. Product-detail verification is still needed before a final constraint verdict; anchor absence alone is not failure.
- `kande` → `kande porcelæn` → `kande porcelæn 1,6 L` narrowed reported counts from **1156 → 147 → 15**. The known porcelain 1.6-L jug appeared at rank 7 in the middle step and rank 1 in the final step. That is an observation of useful narrowing, not a full result-set pass.
- `stegepande rustfrit stål uden belægning` returned two products. Their actual coating/material properties must be checked before judging success; merely getting two products is insufficient.
- Membership/offer wording was preserved separately in `result_card_text.json`, because the existing normalized `SearchResult.price` loses the eligibility label.

## Extraction bug found and fixed

The first extraction incorrectly used an early **price-filter subtotal** as the overall result count. For example, `kande 1,6 L` was reported as three hits despite the actual results header showing 28 and ten real products being extracted.

`src/audit/src/fetcher.py::page_state()` now reads Imerco's scoped `HitsHeader_count` element before generic count parsing. Other hosts retain their previous behavior. The saved original HTML was re-extracted with the fix, without rerunning network searches. Original outcomes and summaries remain in `*_before_count_fix` files; every count correction is recorded in `count_correction.json`. Product ordering and the five confirmed empty outcomes were unchanged.

Two regression tests reproduce the wrong facet-count behavior and verify that an authoritative zero header is not overridden by a positive facet subtotal. Both failed before the fix and passed afterward. The full offline suite passed: **309 tests**.

## Reproduce

From `src/audit/`:

```sh
.venv312/bin/python -m src.candidates.search_run \
  --suites ../../docs/experiments/search-detective-imerco-2026-11-03/query-suites/query_suites.json \
  --candidates ../../docs/experiments/search-detective-imerco-2026-11-03/runs/llm_candidates_live_evidence_v3_20261103 \
  --out reports/imerco_dk/search_execution_new
```

The runner checks that candidate inputs match the reviewed query manifest, refreshes the known product pages, deduplicates searches, checkpoints every outcome, rechecks empty/unverified responses using a proven positive probe, and preserves full card text. It requires a fresh output directory and performs no scoring, publishing, or store writes.

The one-time historical correction is reproducible with `scripts/reparse_search_counts.py` against the original local run directory. It refuses to re-correct an already corrected run.

Portable `search-execution/` contains corrected and original observations, all compressed search-page HTML, browser corroboration, product text and refresh metadata, and SHA-256 hashes. Full refreshed product HTML stays in the local gitignored run folder under `src/audit/reports/imerco_dk/search_execution_20261103/`.

## Next stage

Adjudicate the returned products against each step's requirements, verify unknown attributes on detail pages, and investigate suspicious differences. Separate shared baseline failures, query wording issues, extraction problems, real constraint failures, and ranking effects before recommending changes.
