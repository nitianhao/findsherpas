# Grounded Danish query generation

2026-11-03. Implemented as `src/audit/src/candidates/query_cases.py`, using the existing budgeted LLM-call machinery with a stage-specific system prompt. This is a repeatable workflow, not a manually written query list.

## Outcome

- Input: the nine accepted candidate modes from the final re-evaluation of the 35 autonomously discovered Imerco products.
- Output: **nine reviewed suites, 19 query/control entries, 18 unique search strings**. Specificity has a three-step ladder; the other suites have two steps. The generic pan baseline is intentionally reused across two suites.
- One model call drafted the wording; three independent calls checked it against facts, source text, and the compiled requirements.
- All nine suites passed wording review; no draft was manually substituted or accepted by override. The previously rejected either/or candidate was not used.
- Four API requests, estimated **$0.122982** using recorded usage and the same documented Sonnet 4.6 rates as candidate discovery.
- An actual `--resume` run reused all four requests with **zero new API requests**.
- No storefront search was executed; no search quality result or store defect is claimed.

[Read the Danish queries and anchor products](query-suites/queries.md). [Structured suites and requirements](query-suites/query_suites.json). [Exact model-call evidence](query-suites/calls/).

## How expectations are grounded

The model selects a verified anchor and writes the Danish text. Code derives ordered requirements from the source facts and the approved test policy. It does not let the model invent the expected capacity, pack count, height, material, compatibility, price eligibility, or budget.

- Volume stays equivalent: e.g. 1.6 L and 1600 ml share the same canonical 1600-ml requirement.
- Dimensions retain their axis: the vase test requires height 21 cm, not diameter 21 cm.
- Pack count and volume per glass stay separate: six glasses, 38 cl each.
- Specificity adds material first, then capacity; it does not change the shopping need halfway through.
- Conditional pricing uses a nonmember context and the public-price pan as the eligible anchor. The member-only bargain is the ineligible contrast, reversing the candidate-discovery roles appropriately. Budget is strictly below 500 DKK.
- Source quotes, canonical numeric values, fact IDs, the changed requirement, and contextual eligibility remain available for later execution.

Draft validation rejects unaccepted modes, unknown/ineligible anchors, duplicate or missing steps, unsupported numeric requirements, and unit-conversion queries that do not use the required original/converted units. Independent review checks natural Danish and semantics that string checks cannot establish. Both generation and review use the same model in separate calls, so this is not independent human validation.

## Rules for the future search experiment

These are evaluation rules, not results from this stage:

1. Refresh the source product's identity, stock, and any price-sensitive facts before execution. Old evidence cannot prove a present search defect.
2. Compare each test with its baseline. If the baseline also fails, do not attribute the failure specifically to the added constraint or conversion.
3. Inspect the first ten results and verify decisive attributes on product pages when result cards are insufficient. Record first suitable rank, qualifying count, violations, unknowns, and whether the anchor appears.
4. At least one verified qualifying result in the first ten demonstrates findability for that step. Suitable alternatives count; the chosen anchor need not appear or rank first. Irrelevant surrounding results remain a separate contamination observation.
5. No qualifying result is a failure candidate only with a trusted page/fetch state and a currently verified satisfiable need. Unknown result attributes, stale stock/prices, or unreliable extraction make the outcome inconclusive until investigated.
6. Height is not diameter; per-item volume is not pack volume; a clearly labelled member-only offer is not automatically a defect. Use actual nonmember eligibility for the budget test.
7. Do not require strict result-set nesting or stable rankings when adding a constraint. Test eligibility and findability rather than invented monotonic ranking guarantees.
8. A compatibility pass does not prove that the engine understood compatibility if every plausible result is compatible. Verified incompatible contrasts or further investigation are needed to establish discrimination.

The structured suites contain the exact per-step predicates, source references, measurement fields, and refresh requirements. These rules define the intended execution policy; a search-result adjudicator has not been implemented in this stage.

## Reproduce

Run from `src/audit/`:

```sh
.venv312/bin/python -m src.candidates.query_cases \
  --input ../../docs/experiments/search-detective-imerco-2026-11-03/runs/llm_candidates_live_evidence_v3_20261103 \
  --out reports/imerco_dk/query_suites_new
```

Add `--resume` to the same command to reuse completed calls. Input or code changes require a new output directory. This pilot uses Sonnet 4.6, a 12-call maximum and a $2 planning budget. Calls retain existing request journaling, failure reservations, and conservative cost estimates. `query-suites/evidence-manifest.json` hashes the portable copied outputs and exact calls.

## Verification and limits

Eight additional offline tests cover equivalents, invented numeric requirements, controlled specificity steps, nonmember roles, rejected/tampered source inputs, independent wording-review rejection, preserved dimension axes, and system-prompt cache isolation. Together with candidate-builder tests: 26 focused tests passed. The full audit offline suite passed: **307 tests**. Portable output hashes and accepted-suite contracts were also checked.

The source candidate stage remains a pilot with known limitations. This stage does not refresh storefront evidence, find new products, fix rejected candidate mappings, or prove general reliability of generated tests. No inference about real user frequency, conversion, or revenue is justified without further data.

Next milestone: execute these suites on Imerco, verify result-level attributes, and investigate suspicious differences before calling them search failures.

Subsequent search execution is documented in [search execution results](search-execution-results.md). Result-level quality adjudication remains pending.
