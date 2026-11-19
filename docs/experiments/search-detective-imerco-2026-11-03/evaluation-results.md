# Imerco search evaluation — 2026-11-04

Evaluated the captured **November 3** searches against their declared requirements. Result ordering and search counts come from that saved execution. All **103 unique result product pages** were successfully identity-checked on November 4; physical attributes were verified from those product details. Empty-search judgments use the product evidence refreshed at the original execution time, including the historical public-price offer.

## Findings

**Four failed cases, three passed cases, one mixed case, one inconclusive case.** These findings apply to the tested queries and captured first ten results, not to every query in a capability or to real customer traffic.

| Test | Finding | Evidence |
| --- | --- | --- |
| Handleless cups | Pass | `kopper uden hank`: 10/10 products explicitly satisfy cup type and no-handle requirements. |
| Equivalent volume units | Fail | `kande 1,6 L`: 10/10 captured products satisfy the need. `kande 1600 ml`: 0/5; capacities are 600, 1800, 1800, 1500 and 1500 ml. A verified 1600-ml jug exists. |
| Height | Fail | `vase højde 21 cm` repeatedly returned zero despite a verified 21-cm-tall vase. The broad baseline worked. |
| Pack size and per-item capacity | Inconclusive | Both the six-glass baseline and capacity-specific query were empty. A suitable pack exists, but this pair cannot isolate what adding capacity does. |
| Solid oak | Fail | `sofabord massivt egetræ` repeatedly returned zero. The broad baseline showed the verified solid-oak table at rank 2. |
| Induction compatibility | Pass | `stegepande induktion`: 10/10 products have explicit induction compatibility. This proves suitable retrieval for the test, not that search distinguishes every incompatible alternative. |
| Steel pan without coating | Pass | Both returned Jamie Oliver by Tefal pans satisfy the material and no-coating requirements. Neither is our original reference pan; qualifying alternatives count. |
| Increasing specificity | Mixed | `kande porcelæn`: 7/10 verified matches, one decorative vase, two unknown classifications. Adding 1.6-L capacity yields 10/10 matching porcelain jugs. |
| Nonmember budget | Fail | `stegepande under 500 kr` repeatedly returned zero, although the execution-time public-price pan cost 299.95 DKK. The member-only bargain was not used as the eligible proof. |

[Per-result comparisons and supporting fact IDs](evaluation-20261104/evaluation.json) · [Compact result table](evaluation-20261104/evaluation.md) · [Audited fact evidence](evaluation-20261104/audited_facts.json)

## What pass, failure, and mixed mean

A step passes findability when at least one verified qualifying product appears in its captured first ten results. Suitable alternatives count. We also retain all known mismatches and unknown attributes; finding one good product does not imply perfect precision.

A suite fails when its baseline passes but a test has no qualifying results, with a trusted fetch and execution-time evidence of a satisfiable need. An empty search is not a failure merely because the scraper returned no objects: all five empty queries were positively marked empty and repeated in the earlier execution.

A suite with successful findability but a known mismatch in a test is labelled **mixed**, not a clean pass. If the baseline fails, the added-constraint comparison is **inconclusive**. Internal engine causes, commercial severity, and revenue effects have not been established.

## Concrete checks

The equivalent-unit query returned:

- Witt Classic Nutri replacement jug: **600 ml**.
- CASA Living Toscana carafe: **1800 ml**.
- CASA Living Daisy carafe: **1800 ml**.
- Two Gefu T-Prep teapots: **1500 ml** each.

All five product pages confirm a volume different from 1600 ml. The replacement jug's broad product-type classification is uncertain, but its wrong capacity is already a decisive mismatch. This finding does not depend on the original anchor's absence.

The porcelain-jug query includes **Lyngby Porcelæn Tura Kandevase** at rank 3. Its page explicitly presents it as a decorative vase in the vase category; it is not established as a serving jug. Two sauce-jug results remain uncertain under the pilot's coarse product-type taxonomy, and one describes its material only as generic ceramic. We did not call those unknowns failures. The first verified full match is rank 4.

## Repeatable evaluation workflow

Implemented in:

- `src/audit/src/candidates/evaluation_sources.py`: collect the distinct returned product pages with identity checks, snapshots and a checkpoint cache; never reruns queries.
- `src/audit/src/candidates/evaluate_results.py`: request needed facts from the LLM, independently audit them, compare accepted facts with requirements in code, and aggregate step/suite findings.

The run extracted **178 grounded facts**. Independent source review accepted **177** and rejected one unsupported cup classification: an air-fryer ramekin had been called a cup. That fact is excluded from judgments. The baseline cup search therefore has eight verified matching products and two unknowns; the constrained handleless-cup search has ten verified matches.

Numeric comparisons, unit equivalence, known categorical aliases, and nonmember eligibility are deterministic. A decisive wrong capacity can establish a mismatch even when another attribute is unknown. Missing evidence and coarse `other` classifications remain unknown rather than automatically becoming negatives. No title-only topical relevance scores or reranking were used.

The model was `claude-sonnet-4-6`, with separate extraction and audit calls. Total: **35 API requests**, estimated **$0.964851**, using the previously documented November 3 rates and recorded token usage. A final unchanged `--resume` made **zero new API requests**. Extraction and review use the same model, so errors can still be correlated; this is evidence-backed pilot evaluation rather than a human gold benchmark.

## Evaluator corrections made during this experiment

- The evidence validator initially rejected `liter` when its exact source quote used `L`. Equivalent source-unit aliases now normalize correctly; a wrong magnitude/unit still fails validation. Four valid capacity facts were recovered and independently audited.
- The LLM sometimes returned Danish material values (`Porcelæn`, `Keramik`) despite the canonical English vocabulary. Code now maps known aliases; generic ceramic does not prove or disprove porcelain.
- The coarse product type `other` does not by itself prove a product is outside the requested type. This protects ambiguous sauce jugs and bundles from unsupported negative judgments.
- A suite that finds qualifying products but also returns a known mismatch now reports `mixed_results`, preserving the distinction between findability and result cleanliness.

Old intermediate evaluations are retained in files explicitly named `*_before_*_fix.json`; they are debugging records, not approved findings. Code revalidation preserves prior manifests and reuses only request-identical cached API responses. The initial broad review used 34 requests; one additional audit checked recovered unit facts. Later deterministic corrections required no further API calls.

All **322 offline tests** passed, including new tests for unit aliases, categorical normalization, unknowns, decisive violations, mixed result sets, baseline attribution, rejected audit facts, and nonmember prices.

## Reproduce

From `src/audit/`:

```sh
# Collect product details into a fresh evaluation folder.
.venv312/bin/python -m src.candidates.evaluation_sources \
  --execution ../../docs/experiments/search-detective-imerco-2026-11-03/search-execution \
  --out reports/imerco_dk/evaluation_new

# Extract, audit and evaluate the saved searches.
.venv312/bin/python -m src.candidates.evaluate_results \
  --experiment ../../docs/experiments/search-detective-imerco-2026-11-03 \
  --out reports/imerco_dk/evaluation_new
```

Use an identical command with `--resume` for cached completion. Explicit `--revalidate` recomputes after code changes only when source inputs are unchanged, preserving the old manifest. Budget: at most 50 model requests / $5 for this evaluation stage. No store settings are changed and nothing is published.

Portable `evaluation-20261104/` includes product text/identity/capture metadata, exact model prompts and responses, fact audits, every result comparison, intermediate correction records, and a SHA-256 manifest. Raw detail HTML remains in the local gitignored `src/audit/reports/imerco_dk/evaluation_20261104/detail_capture/` directory. Source paths inside product records are relative to that detail-capture root.

## Next investigation

The strongest next case is equivalent units: the source need is identical, the baseline works, and every returned alternative has a provably wrong capacity. Investigate controlled query variations and retrieval evidence to identify why it happens before proposing a platform fix. Height, solid-material and price dead ends also warrant that investigation. Repair the pack baseline before treating it as a capacity-understanding test.

The unit-conversion investigation has now been completed: see [findings and tested local fix](unit-investigation-results.md).
