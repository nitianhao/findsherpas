# Expanded availability-ranking experiment — Imerco, 5 November 2026

## Registered design

Authorized scope: run fifty ordinary searches across more categories, assess repeated availability ordering, simulate an improvement locally, and check relevance and named-product preservation. No merchant configuration changes or publication.

Ten independently observed category pages: frying pans, cups, drinking glasses, serving jugs, vases, dinner plates, serving/salad bowls, pots, kitchen knives, and cutlery sets. Five natural Danish queries per category: category, common subtype, brand plus type, family plus type, and named product. This is an expansion to fifty total queries in a fresh cohort, not fifty demand-weighted observations. Some queries may overlap the earlier cohort; distinguish old versus new categories in results.

Category selection is fixed before collecting search outcomes and includes five new categories. Select cards by document order and distinct brand/name, not stock risk. LLM drafting plus separate review ground queries in this independent inventory. Query text is the entire requirement: goals are forced to equal the literal query, avoiding the previous hidden water-only carafe requirement. Freeze and hash the plan before executing searches. No post-result query substitutions.

Capture ten results per query with public product fields, stock-card labels and family IDs. Independently review relevance judgments with exact field quotes; repair missing pairs once, otherwise abstain. Unknowns are not search failures. All fifty named/family/category shapes are analyzed, including healthy results.

## Predefined local ranking change

Stable availability preference inside contiguous blocks of independently reviewed exact results with known stock. Unknown or weaker relevance and unknown stock form barriers. Named-product lookups retain their entire original order, including unavailable items. No products are added or removed; equal-stock order is preserved. Family/brand queries accept unspecified variants, but not wrong product types or brands.

The simulator uses judged relevance as an input. Preserving its relevance-label sequence is a design property, not independent proof of relevance improvement or production safety. This is an offline feasibility demonstration, not a drop-in ranker. A production implementation needs a validated relevance gate and current fulfillment stock. Conservative barriers may leave some opportunities unresolved.

Measure: queries with relevant unavailable top-one and available exact alternative; independent categories/families; before/after first relevant available position; changed rankings; top-one changes; relevance-label sequence; product-set preservation; named-product order. Distinguish raw unavailable top-one from verified actionable opportunity, especially for explicit named intent. Report uncertainty and failure counts without demanding a positive result.

Verify original/promoted top-one product pages for every simulated top-one change. Recheck all stock-ordering query candidates and three deterministically selected named controls. Repeats are stability checks, not independent prevalence observations. Compare live repeats with the initial capture and retain drift. Availability applies to online delivery: in-store availability may make the existing policy intentional.

No logs, representative traffic weights, conversion measurements, or revenue-loss estimates. Generalization requires more stores/categories and actual merchant traffic validation.

## Reproduction

From `src/audit`, use a new output directory:

```sh
.venv312/bin/python -m src.candidates.stock_experiment --out reports/imerco_dk/stock_NEW --stage collect
.venv312/bin/python -m src.candidates.stock_experiment --out reports/imerco_dk/stock_NEW --stage plan
.venv312/bin/python -m src.candidates.stock_experiment --out reports/imerco_dk/stock_NEW --stage search
.venv312/bin/python -m src.candidates.stock_experiment --out reports/imerco_dk/stock_NEW --stage evaluate
.venv312/bin/python -m src.candidates.stock_experiment --out reports/imerco_dk/stock_NEW --stage simulate
.venv312/bin/python -m src.candidates.stock_experiment --out reports/imerco_dk/stock_NEW --stage verify
```

Bounded model journal: at most 70 requests and $8 estimated model budget; unchanged completed requests are cached, failed/pending requests are not automatically rebilled. Raw source HTML stays in ignored runtime captures. Portable sanitized data, model calls, product-page text/hashes, result report and regression cases will accompany this record.

### Execution details

Relevance batches run with two concurrent requests using disjoint journals. The planning stage has a ten-call/$1 allowance; 25 result batches each have $0.28, with two normal calls each and one reserved missing-pair repair for the first ten batches. This totals at most 70 requests/$8; batches beyond that repair allowance abstain on missing pairs. No automatic rebilling of failed calls. This allocation is an execution limit, not a reason to call missing output a store failure.

The first query review rejected a floor-vase subtype unsupported by its small-vase anchors, and an ungrounded glass anchor ID. Those drafts were repaired before any search execution; rejected drafts are retained.

The final plan contains 50 reviewed queries, including 40 query strings absent from the previous 30-query cohort. Some category-level searches include ordinary material modifiers; they are not all bare category names. Ten queries reuse earlier wording as fresh observations. All goals equal the literal query. The final freeze timestamp is recorded in `frozen_plan.json` before the first search capture.

### Diagnostic amendment during capture, before relevance review/simulation

The fresh `vandglas` capture places the previously rank-three available glass first; yesterday's unavailable glass is now second and still unavailable. Record this temporal ranking drift rather than assuming yesterday's first-place issue persists. Repeat the three historical broad probes (`vandglas`, `drikkeglas`, `vase`) as separate diagnostics; only `vandglas` belongs to the frozen fifty unless another exact query overlaps. These probes do not change the cohort denominator.

Also count available exact products in the first three positions before/after. If first place is already available, a lower-order stock preference may still improve availability exposure without improving first-available rank. This is an offline count, not measured conversion uplift. For changes below first place, verify one promoted available / demoted unavailable product-page pair per changed query in addition to all changed top-one pairs. This amendment does not change query strings or the reranking rule.

One captured `glasvase` page has a public search-record query mismatch. The guard correctly withholds that metadata rather than combining an unbound index response with visible cards. The captured first card itself says available online; the first product will also be checked on its PDP. Relevance/parent grouping for unbound records remains unknown, and this query cannot trigger simulated movement. Treat this as an extractor/metadata coverage limitation, not a search defect.

Product-page verification exposed another explicit status phrase, `Midlertidligt udsolgt online` (temporarily sold out online). The initial PDP parser abstained on it. Added that negative online-stock marker, tested that store stock cannot override it, and recomputed status from the same saved purchase-area text without new requests. The pre-fix verification output remains in the runtime folder. This parser correction changes verification coverage, not the frozen queries, labels, or local ranking rule.

## Completed results

See [results.md](results.md) and `summary.json`. Fifty frozen queries returned 49 nonempty searches and one confirmed zero. No confirmed unavailable first-product stock cases appeared in this cohort. The guarded replay changed nine lower result orders, increased available exact top-three slots from 125 to 127, and retained all ten named-product orders. All nine selected changed-query product-page contrasts were verified, using 18 unique product pages. Four within-cohort repeats retained their first-ten order.

Separate historical diagnostics are essential context: the glass examples changed to available first products, while broad `vase` still shows an unavailable first product. Broad `vase` was not in this fifty-query cohort (the category-level vase query was `vase stentøj`), so do not mix it into the fifty-query denominator or claim the original issue disappeared entirely. Its current first/second products receive a separate PDP check in `historical_vase_verified.json`.

Review coverage limitations: ten `glasvase` rows were withheld for unbound public metadata (its first product was separately confirmed available on its PDP); five cutlery rows lacked model labels; two set-versus-single-item judgments were disputed. These 17 rows remain unknown. Missing outputs and reviewer over-restriction need stronger automated adjudication before productization; they are not store failures.

The simulation uses relevance labels as input and preserves them by construction. No independent production relevance test or conversion experiment has occurred. Model cost estimate: $1.889841 across 56 calls. **342 offline tests passed**, including nine stock-experiment tests. No store settings or external publication were changed.
