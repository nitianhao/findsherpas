# Availability-ranking results — Imerco, 5 November 2026

Completed **50 frozen queries across ten categories**. Fetch outcomes: `{'ok': 49, 'zero_confirmed': 1}`. Captured 418 result entries. Forty query strings were new to the earlier cohort. Queries are plausible retail searches, not measured demand.

**The earlier first-place stock problem does not reproduce broadly in this cohort: 0 confirmed candidates.** Initial top-one stock metadata: `{'available_online': 48, 'unknown': 1}`. The unknown case is discussed below; an empty search has no top-one product.

## Observed scope

| Category | Queries | Unavailable exact top-one with available exact alternative | Orders changed locally | First products changed |
|---|---:|---:|---:|---:|
| cups | 5 | 0 | 1 | 0 |
| glasses | 5 | 0 | 1 | 0 |
| jugs | 5 | 0 | 1 | 0 |
| pans | 5 | 0 | 0 | 0 |
| vases | 5 | 0 | 2 | 0 |
| bowls | 5 | 0 | 1 | 0 |
| cutlery | 5 | 0 | 1 | 0 |
| knives | 5 | 0 | 0 | 0 |
| plates | 5 | 0 | 0 | 0 |
| pots | 5 | 0 | 2 | 0 |

This sample does not establish site-wide customer-search prevalence. Ten repeated query strings and related families are correlated observations. The broader cohort is not a random sample of search traffic.

## Temporal check of yesterday’s examples

| Search | First product on 4 November | First product on current repeat | Current online stock |
|---|---|---|---|
| vandglas | Eva Solo Facet Vandglas  /  4 stk. (100353708) | Lyngby Glas Melodia Vandglas  /  6 stk. (100431241) | available_online |
| drikkeglas | Eva Solo Facet Vandglas  /  4 stk. (100353708) | Lyngby Glas Melodia Vandglas  /  6 stk. (100431241) | available_online |
| vase | CASA Living Vase (100465383) | CASA Living Vase (100465383) | not_available_online |

A separate current PDP check confirms the historical broad-vase contrast: CASA Living 100465383 cannot be ordered online, while rank-two CASA Living 100465690 can. Those two pages are saved in `historical_vase_verified.json` and are additional to the 18 cohort verification pages.

These are temporal observations, not changes made by this experiment. The historical probes outside the frozen fifty are diagnostic controls and do not change its denominator. Why the live order changed was not established.

## Local before/after

The conservative simulation changes **9 result orders** and **0 first-place products**. Available exact products in the first three slots increase from **125 to 127** across the fifty queries. This is unweighted offline availability exposure, not conversion uplift. Product counts and the candidate pool do not change.

All 10 named-product orders remain unchanged. Same product sets: **True**. Same relevance-label sequence: **True**. Relevance is an input to the simulator; these invariants do not independently prove production relevance quality. Unknown/weaker labels, unknown stock, and named lookups prevent movement. Only the captured first ten candidates participate.

| Query | First changed position | Product before → after at that position | Selected moved-pair PDP contrast confirmed |
|---|---:|---|---|
| termokop | 8 | Stanley The Quencher H2.0 Flowstate Tumbler → Stanley The Quencher H2.0 Flowstate Tumbler | True |
| vandglas | 2 | Eva Solo Facet Vandglas  /  4 stk. → Lyngby Glas Zero Vandglas  /  6 stk. | True |
| vandfilterkande | 4 | BWT Vida Vandfilterkande → Brita Style Vandfilterkande | True |
| vase stentøj | 5 | Kähler Hammershøi Sommer Vase → CASA Living Vase | True |
| Kähler vase | 6 | Kähler Hammershøi Sommer Vase → Kähler Hammershøi Jul Vase | True |
| salat skål hvid | 5 | Villeroy & Boch Afina Salatskål → Aida Relief Salatskål | True |
| Georg Jensen bestik | 9 | Georg Jensen Bernadotte Sauceske → Georg Jensen Bernadotte Bestiksæt  /  16 dele | True |
| støbejern gryde | 5 | Orrefors Jernverk Støbejernsgryde → Orrefors Jernverk Støbejernsgryde | True |
| Le Creuset gryde | 3 | Le Creuset Signature Gryde → Le Creuset Signature Gryde | True |

## Verification and limitations

Fetched 18 unique product pages for original/promoted first products, selected moved stock contrasts, and unknown first-product stock: **9 changed-query contrasts** were confirmed from the purchase area, with **0 fetch/identity errors**. One pair per lower-order changed query is checked; this is not a complete PDP audit of every moved SKU. A lack of confirmation is not a confirmed opportunity; inspect `verification_summary.json` for unknown/conflicting statuses.

Repeated 6 queries: stock candidates, three named controls and historical probes. Of 4 repeats inside the frozen cohort, 4 retained the same first-ten URLs. `recheck_summary.json` retains status, counts and stock drift. Repeats are not independent prevalence examples.

Automated reviewed relevance labels: `{'exact': 341, 'complement': 7, 'substitute': 49, 'irrelevant': 4, 'unknown': 17}`. Rejected, missing and unsupported labels stay unknown and cannot trigger reordering. Product pages verify stock/identity, not a second independent full relevance gold set.

The `glasvase` search returned normal product cards but its embedded public index query did not bind to the requested query. That metadata was withheld; its relevance/family labels stay unknown. The visible first card says available online, and its PDP is captured in `verified_examples.json`. This coverage gap is an evaluator limitation, not a store failure.

The empty query is preserved in `outcomes.json`; no synonym diagnosis or claim about query demand is made in this stock experiment. Some low-yield named queries return fewer than ten products, which is not inherently a defect.

Model journal: 56 requests, estimated token cost **$1.8898**, excluding infrastructure and researcher time. Two batches run concurrently with fixed disjoint budgets. Failed calls retain reserves.

Online availability differs from store availability. Pickup stock and named unavailable-product discovery may justify existing merchant policy. No store configuration changed. No traffic frequencies, lost sales, conversion uplift, or production ranking performance were measured.

## Reproduction and handoff

The registered design, amendments and CLI commands are in [README.md](README.md). Implementation: `src/audit/src/candidates/stock_experiment.py`. Portable JSON includes the frozen reviewed plan, sanitized result metadata, labels/reviews, simulation orders, product-page text/hashes, repeats and model-call journals. Full HTML stays in the ignored runtime directory `src/audit/reports/imerco_dk/stock_20261105/`.

The fifty-query test does not justify prioritizing a broad stock-ranking overhaul based on yesterday’s first-place examples alone. Treat the local replay as a demonstration of a guarded merchandising rule. A merchant trial needs online-versus-pickup policy, an independently validated relevance gate, live stock and actual behavioural measurements.

Validation: **342 offline tests passed**. Workflow source hashes and the validation record are saved alongside the artifacts.
