# Why equivalent-volume searches fail — Imerco, 2026-11-04

## Conclusion

The observed failure has two interacting mechanisms:

1. **Equivalent volumes are not being enforced as the same physical quantity.** The public search records contain capacity, but their text uses mixed representations such as `1.6 L` and `160 cl`. The observed requests pass the shopper's volume as ordinary query text, with no capacity refinement. A litre query and its millilitre equivalent retrieve different records.
2. **Numeric typo matching admits incorrect quantities.** For `kande 1600 ml`, the actual search response highlights `600`, `1800` or `1500` as matches for the query token `1600`. Each wrong-size hit reports two typos. A controlled read-only request disabling numeric typos removes all five wrong hits, returning zero.

This is a retrieval/measurement-handling problem in the observed Imerco Algolia integration. The capacity is present in the public index records; it is not simply missing from product descriptions. We have not inspected private index settings or application source, so we do not attribute it to a particular private configuration line or claim that all measurement queries behave this way.

## Evidence collected

- **18 controlled storefront queries**, derived from the verified 1600-ml need; eight key queries repeated in a different order.
- **All eight repeats were stable** in status, hit count, and returned product IDs.
- **Three read-only Algolia search requests**: a control reproducing the storefront's five wrong matches, numeric typos disabled, and the equivalent litre query with numeric typos disabled.
- Refreshed the reference jug's product page and preserved its identity, description and specifications.
- Inspected the public, query-bound Algolia result records embedded in the search page. This includes capacity fields, matched words, highlights, and ranking metadata. No settings endpoints were used and no store configuration changed.
- No additional LLM calls were needed for this numeric diagnostic; query variants, unit conversion and filtering are deterministic. This is a reusable measurement-specific investigation, not yet a general autonomous root-cause agent.

[Full query matrix](unit-investigation-20261104/results.md) · [Sanitized query evidence](unit-investigation-20261104/query_findings.json) · [Request-level counterfactual](unit-investigation-20261104/numeric_typo_counterfactual.json)

## The strongest comparisons

| Query | Reported hits | What the captured records establish |
| --- | ---: | --- |
| `kande 1,6 L` | 28 | 25 have 1600-ml capacity; two have 1500 ml; one lacks capacity. The known 1.6-L jug ranks first. |
| `kande 1.6 L` | 28 | Same records as the comma version. Decimal punctuation alone is not the main failure here. |
| `kande 1,6 liter` | 27 | 25 capacity-consistent records and two 1500-ml records. |
| `kande 160 cl` | 1 | A valid 160-cl Hübsch Orbit jug, absent from the litre-query result set. |
| `kande 1600 ml` | 5 | All wrong capacity: 600, 1800, 1800, 1500, 1500 ml. |
| `kande 1600ml` | 0 | Removing the unit separator does not recover the 1.6-L products. |
| `kande 1,6L` | 0 | Compact litre formatting is another retrieval weakness; observed once. |
| `kande 1600 milliliter` | 0 | Spelling out the unit does not recover the known products; observed once. |
| `kande 16 dl` | 0 | Another physically equivalent form fails; observed once. |
| `Eva Trio Legio Nova Kande 1,6 L` | 1 | Finds the exact verified jug. |
| `Eva Trio Legio Nova Kande 1600 ml` | 0 | The same named product disappears with equivalent units. Both branded queries were repeated. |

Counts above cover the full first response page for these narrow queries. Other ablation/control queries can have multiple pages; the detailed matrix explicitly measures the captured page, not complete catalog recall. The matrix's reference-match column always compares with 1600 ml, including the separately labelled 1500-ml controls.

The original evaluator inspected the first ten results of the litre baseline, all valid. This investigation expanded to the full 28-record first page and found two additional wrong-capacity products and one accessory without a capacity. That extends the evidence; it does not contradict the earlier top-ten result.

## Public data explains the behavior

The known Eva Trio jug's public index record exposes:

```json
{
  "objectID": "100396731",
  "cust_capacity": "1.6 L",
  "cust_spec_capacity": "1,6"
}
```

The observed search state has a price-refinement container but no capacity refinement. For the failing query, matched-word metadata in `cust_synopsis` pairs the query term `1600` with highlighted `600`, `1800`, and `1500`; the same records have `_rankingInfo.nbTypos = 2`. Algolia documents this ranking field as the number of typos in a match. [Algolia ranking metadata](https://www.algolia.com/doc/api-reference/api-parameters/getRankingInfo)

This supports text/typo matching rather than physical-unit equivalence in these requests. The generic `unit` and `cust_messurementUnit` fields are not safe substitutes for capacity units: in this record they contain pack/dimension-related values, including `cm`. The prototype normalizes the self-contained `cust_capacity` value instead.

## Causal counterfactual: disable numeric typos for one request

Using the same public index and storefront visibility filters:

| Read-only request | Hits | Interpretation |
| --- | ---: | --- |
| Original `kande 1600 ml` request, control | 5 | Reproduces the same wrong products. |
| Same query, `allowTyposOnNumericTokens=false` | 0 | Numeric typo handling caused the five bad matches; disabling it alone does not retrieve equivalent litre records. |
| `kande 1,6 L`, numeric typos disabled | 28 | The known jug is recovered, but two 1500-ml records and an unclassified accessory still remain in the full page. Literal rewriting alone does not enforce capacity. |

Only a query-level option was varied; index settings were not written. Diagnostic API requests disabled analytics/click analytics. The public client credential was used only in memory for these normal search requests; its value is absent from saved portable evidence and logs. The script stops on unavailable or mismatched controls rather than trying other indexes or credentials.

Algolia supports disabling numeric typo tolerance; its documentation warns that numeric typos can introduce irrelevant matches. This is distinct from converting physical units. [Numeric typo handling](https://www.algolia.com/doc/api-reference/api-parameters/allowTyposOnNumericTokens)

## Fix tested locally

A limited prototype:

1. Parse one explicit, exact volume and normalize it with decimal arithmetic to millilitres.
2. Retrieve the relevant litre, centilitre, millilitre and decilitre representations.
3. Merge by product ID.
4. Normalize each returned record's capacity and keep exact numeric matches; retain unknown-capacity records separately for review.

For 1600 ml, this local replay merged **33 distinct captured candidates**, kept **26 capacity-consistent candidates**, and excluded **seven wrong-size candidates**. None of those 33 had unknown capacity. The original 1600-ml query had zero capacity-consistent candidates.

A litre-only expansion kept 25 candidates and missed the centilitre-only Orbit jug. This is why a blanket rewrite of everything into litres is insufficient when the catalog stores mixed units.

A second, 1500-ml control merged 44 captured candidates: 27 capacity-consistent, 11 wrong-size, six unknown. Unknowns are preserved, not fabricated as matches or silently counted as violations. This is a limited second-volume control, not a cross-store validation.

[Local replay details](unit-investigation-20261104/local_fix_replay.json)

These counts check capacity consistency against exposed index metadata. They are not 26 independently re-audited complete shopping recommendations, and they do not measure total catalog recall or a deployed conversion improvement.

## Recommended production change

Normalize product capacity during ingestion into a numeric field such as `capacity_ml`, preserving the original display value and product variant identity. Parse explicit volume intent in the query, remove the quantity phrase from the text portion, and apply an exact numeric filter while retaining existing storefront filters and ranking context.

Conceptual request, after that field has been populated and enabled for filtering:

```json
{
  "query": "kande",
  "numericFilters": ["capacity_ml = 1600"]
}
```

Algolia supports exact comparisons on numeric attributes. [Numeric filtering](https://www.algolia.com/doc/api-reference/api-parameters/numericFilters)

Keep typo tolerance for ordinary words. For recognized measurement requests, avoid fuzzy matching of the numeric requirement. Disabling numeric typos can suppress false positives, but it must accompany unit-aware retrieval to avoid replacing wrong results with zero results.

Before adoption, verify indexing coverage, missing/ambiguous capacity values, variant identities, other units, and interactions with existing filters. Comparisons/ranges require their own parser and tests. The prototype deliberately abstains on ambiguous multi-volume expressions, inequalities, ranges and non-volume tokens rather than treating them as exact volume requests. No production field or setting was changed in this experiment.

## Reproduce and evidence quality

From `src/audit/`:

```sh
# New storefront investigation from the accepted unit test.
.venv312/bin/python -m src.candidates.unit_investigation \
  --experiment ../../docs/experiments/search-detective-imerco-2026-11-03 \
  --out reports/imerco_dk/unit_investigation_new

# Re-analyze an existing capture without making network requests.
.venv312/bin/python -m src.candidates.unit_investigation \
  --experiment ../../docs/experiments/search-detective-imerco-2026-11-03 \
  --out reports/imerco_dk/unit_investigation_20261104 --analyze-only
```

The one-off read-only API counterfactual is preserved in `scripts/probe_numeric_typos_20261104.py`. Run it from `src/audit/` with `PYTHONPATH=.`; it reads the existing public page capture and never stores credential values.

The new public-data parser initially selected a recommendation feed that appeared before the actual search feed. It now scopes to `product-list` and verifies that the embedded query matches the observed query. All 26 captures satisfy that check. Incorrect preliminary analyses are retained only in clearly named `*_before_feed_fix.json` debugging files. They are not benchmark data.

Six targeted tests cover exact unit conversions, ambiguous/non-volume expressions, query planning, query-bound feed selection, credential-value exclusion from sanitized outputs, and preserving centilitre-only candidates during expansion. The full offline suite passed **328 tests**. The latest small guards were additionally exercised by offline re-analysis.

Portable evidence in `unit-investigation-20261104/` contains the query plan, timestamped outcomes, sanitized public-index records, the request-level counterfactual, local replay results, anchor text, and SHA-256 manifests. Full raw search HTML remains local under `src/audit/reports/imerco_dk/unit_investigation_20261104/evidence/`; hashes are portable. The backend metadata is evidence from normal public search responses, not private settings inspection.
