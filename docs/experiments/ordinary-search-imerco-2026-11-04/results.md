# Ordinary-search experiment results — Imerco, 4 November 2026

## Outcome

Completed 30 frozen Danish queries across five categories and six query shapes per category. Twenty-nine returned products; one returned a confirmed empty page. Captured 282 result entries, reviewed relevance with separate model calls, and checked 11 product pages. Six selected queries were repeated: status, hit counts, and first-ten product IDs were identical on both observations.

**One recurring online-shopping opportunity and two localized opportunities are supported.** This does not establish three widespread conversion problems. Query frequency, lost orders, and conversion uplift are unknown.

## 1. Unavailable-online items occupy first place

| Search | First product | First relevant available-online alternative |
|---|---|---|
| `vandglas` | Eva Solo Facet, 43 cl, four-pack — 100353708 | Rank 3: Lyngby Glas Melodia, six-pack — 100431241 |
| `drikkeglas` | Same Eva Solo product | Rank 3: same Lyngby Glas product |
| `vase` | CASA Living Vase — 100465383 | Rank 2: Knabstrup Keramik Vase — 100386969 |

Search cards say unavailable online. Both first-place product pages say **“Giv mig besked / Kommer snart online”**; the alternatives have **“Læg i kurv”** and dispatch information. This is not just an inference from an index boolean. Both first-place items do have store stock, so the recommendation depends on whether the search serves home delivery or store pickup.

Evidence: three queries, two independent products, two categories. The glass synonyms are correlated and must not be presented as three independent product failures. Both glass searches also have an unavailable variant at rank 2.

Suggested experiment: for online-delivery shopping, rank available items ahead of equally relevant unavailable items. Preserve store-stock visibility and explicit unavailable-product lookups. Use a modest availability preference after relevance, rather than hiding all unavailable products or letting weak matches beat exact matches. Confirm the desired omnichannel policy with the merchant.

Regression requirements: the two glass queries should have an available relevant product at rank 1; `vase` likewise. Named unavailable items must remain discoverable; pickup intent must retain appropriate store-stock products. Measure add-to-cart and search exits in a merchant-controlled test before making commercial claims.

## 2. Coffee-cup results spend six slots on one family

`kaffekop` returns 191 products. Ranks 2–7 share parent `P100418556`: RAW by Aida coffee-cup variants in green, pink, black, white, and two brown finishes. Product-page variant selectors corroborate the family relationship. Ten result slots expose five parent families.

All ten results were judged relevant. This is an assortment-discovery opportunity, not a relevance failure. It occurred in one broad query; concentration on explicit family searches was deliberately not flagged.

Suggested experiment: group or limit same-parent variants on broad discovery searches, with a visible colour selector. Keep a more specific colour/size/family query free to show matching variants. Compare useful family exposure and shopper behaviour; do not assume variety always improves conversion.

## 3. One plausible pan phrase has no results

`pande til stegning` returned zero twice. `stegepande` returned 1,220 twice. An independently collected, available product was verified: Eva Trio Stainless Steel Stegepande, ID 100439699.

This proves a retrievable-intent gap for that phrase, not a high-volume problem. Exact root cause was not diagnosed in this experiment.

Suggested experiment: catalog-grounded phrase normalization to `stegepande`, with controls for non-pan uses and competing intent. Preserve the original query and avoid rewriting an already productive search. First expand to related natural phrases across categories to see whether this is a pattern before prioritizing an isolated synonym rule.

## Other observations and exclusions

- `Rosendahl Grand Cru glas` includes a roasting dish, spice grinder, and thermos jug at ranks 7, 8, and 10. Correct glasses lead the results. This is localized lower-page product-type leakage, not evidence of a recurring top-result obstacle.
- A ten-piece cookware set leads `rustfri stegepande`. Its verified contents include two steel frying pans. The query does not specify single-item packaging, so this is not counted as a confirmed relevance failure.
- The draft goal for `karaffel` introduced water/juice intent absent from the literal query. Wine carafes are legitimate carafes; their demotion by both model calls is an evaluator error and is excluded from failure claims. The frozen query and raw labels remain unchanged for auditability.
- Generic jug and cup subtypes have some debatable model distinctions. They do not support headline failure claims. No aggregate relevance percentage is promoted from these labels.
- Most brand and product-family lookups put a relevant product first. Relevant seasonal mugs, packs, and unspecified variants were not automatically treated as defects.

## Automation quality and remaining work

The repeatable pipeline collected independent category inventory, drafted and reviewed queries, froze them before searching, captured results, assigned labels with source quotes, and independently reviewed those labels. Stock and family grouping are deterministic observations from public storefront records/cards. The shortlist was then verified with product pages and repeated searches.

There were 22 model calls, with estimated token cost **$1.088733**, including drafting and review. This is a model-cost estimate, excluding infrastructure and researcher time.

Raw automated labels: 229 exact, 35 substitute, 4 complement, 3 irrelevant, 11 unknown. These are result entries, not unique products, and are not corrected relevance ground truth. Five missing `vandglas` labels stayed unknown; five stoneware thermal-cup labels were disputed by the reviewer and stayed unknown; one crystal-material case lacked clear evidence.

A quote validator initially rejected multiple genuine field quotes when they were on separate lines. Fixed it to validate every quoted segment independently, then recomputed using cached model responses with no additional API calls. Fabricated segments still fail validation. Initial outputs remain in the runtime directory.

Before productization:

1. Validate that generated goals contain no constraints absent from the query; independent review alone missed the carafe problem.
2. Enforce complete pair coverage and add a bounded repair/adjudication stage for missing or disputed labels. Never convert missing output into a store failure.
3. Separate direct product-type evidence from taxonomy quirks and bundle preferences.
4. Expand stock and discovery observations across independently sampled categories and families. The current five-category sample is intentionally small and not representative of all searches.
5. Validate fixes on a controlled search configuration and measure actual shopper outcomes with the merchant. No store configuration was changed in this run.

## Reproduction and artifacts

Run commands from `src/audit`:

```sh
# New live experiment: collect current category inventory first.
PYTHONPATH=. .venv312/bin/python ../../docs/experiments/ordinary-search-imerco-2026-11-04/scripts/collect_category_sources.py
.venv312/bin/python -m src.candidates.ordinary_search --out reports/imerco_dk/ordinary_20261104 --stage plan
.venv312/bin/python -m src.candidates.ordinary_search --out reports/imerco_dk/ordinary_20261104 --stage search
.venv312/bin/python -m src.candidates.ordinary_search --out reports/imerco_dk/ordinary_20261104 --stage evaluate
```

The historical output already exists. **For a fresh live run, change the output directory in the scripts and CLI.** Do not overwrite the frozen plan or mix new inventory with old searches. `search` refuses existing observations. An unchanged `evaluate` reuses cached model calls; `contexts` can regenerate public metadata from local HTML without requests.

Portable artifacts alongside this report include category inventory, frozen queries and review, outcomes, sanitized product contexts, full evaluation and model-call records, verified product-page text and source hashes, repeat observations, and review caveats. Scripts preserve collection/verification/recheck steps. Full compressed HTML remains in the ignored runtime folder `src/audit/reports/imerco_dk/ordinary_20261104/`; copied product text and hashes preserve the portable findings but do not replace the full captures.

Validation: **333 offline tests passed**, including five new tests for ordinary-search plan structure, family-aware concentration, stock ordering, unknown handling, and multiline evidence validation.
