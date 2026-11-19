# Ordinary shopping search experiment — Imerco, 2026-11-04

## Purpose and limits

Test 30 plausible ordinary Danish shopping searches across five categories (pans, cups, drinking glasses, jugs, vases). Look for repeated shopper obstacles and practical fixes. This replaces the earlier emphasis on difficult measurement/constraint probes for this experiment; those remain useful robustness tests.

No site-search logs or verified frequency weights are available. “Ordinary” means natural retail phrasing grounded in current category inventory, not measured customer demand. Conversion effects require validation after changes. We will report actual findings even if fewer than three problems meet the evidence threshold.

## Registered design (before searches)

Six distinct searches per category: category term, everyday synonym, common subtype, brand-plus-product-type, product-family search, and a named-product lookup. Ground queries and eligible reference products in independently fetched category cards. Use an LLM and separate wording review to reject unnatural queries or invented products. Save the fixed query set before execution; any later diagnostic queries are labelled separately.

Capture the first ten results, their real order, full card text, public search-record product identity/category/brand, and online-stock labels. Assess:

- Top-one/top-three relevance and position of the first suitable result.
- Relevant results versus accessories, wrong categories, and brand/family mismatches.
- Repeated variant concentration for broad queries (not automatically bad for a family-specific query).
- Unavailable-online results and whether relevant available alternatives appear lower down.
- Known-product findability, accepting equivalent unspecified variants rather than demanding one anchor SKU.

Unknowns and ambiguous interpretations remain explicit. Independent review checks relevance judgments; high-impact examples are verified on product pages. Recheck shortlisted problematic queries. No result absence or failure of one obscure query is extrapolated into a commercial uplift claim.

## Pattern thresholds

A recurring problem should have at least three query examples, or multiple examples across independent product families/categories. Repeated queries for the same family are not independent evidence. Top-one mismatches and no-useful-result cases are more actionable than cosmetic reordering. A single strong issue may be reported as an isolated finding, labelled accordingly.

Variant concentration and stock ordering are opportunities requiring merchandising context, not automatic defects. No requirement to manufacture three client-facing problems.

## Workflow

Independent category collection → LLM query drafting → separate wording review → frozen plan → search capture → evidence-based relevance labels → independent judgment review → recurring-pattern grouping → product-page verification/rechecks → recommendations and limitations.

## Completed run

See [results and recommendations](results.md). The run found one recurring availability-ranking opportunity across two categories, one localized variant-concentration opportunity, and one isolated empty phrase. All six shortlisted/control rechecks were stable. Twenty-two model calls cost an estimated $1.09. No search configuration was changed; no conversion effect was measured.

The portable JSON artifacts preserve raw model decisions as well as explicit researcher caveats. In particular, the carafe interpretation and cookware-bundle judgment are not counted as confirmed search failures.

## Expanded follow-up — 5 November

The [fifty-query stock-ranking follow-up](../stock-ranking-imerco-2026-11-05/results.md) found no confirmed unavailable first products in its frozen cohort. Separate historical repeats showed the two glass queries had changed to available first products, while the original broad vase case persisted. The guarded local rule made nine lower-order changes and added two available exact results to the first three slots across the cohort. Treat the earlier stock finding as time-sensitive and narrower than a broad conversion claim.
