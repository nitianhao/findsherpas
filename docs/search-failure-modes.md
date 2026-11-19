# Search failure-mode library

Recorded 2026-11-03. Companion to [Search improvement ideas](search-improvement-ideas.md).

## Scope and status

Working library for ecommerce search evaluation without access to search logs. The aim is broad practical coverage, not a claim to enumerate every possible failure. Shopify plugin work is out of scope.

- **[approved]**: explicitly accepted by the user during brainstorming (30 modes).
- Unmarked: additional candidate modes generated for the library; not individually reviewed by the user.
- **[borderline]**: potentially useful, but needs a scope or evaluation decision. Presented to the user for review.

Some modes overlap intentionally: a symptom may have several causes. Group related findings instead of counting them as independent failures. These are test hypotheses, not automatic verdicts.

## Rules for reliable tests

- Instantiate tests from actual store products, supported capabilities, and independently verified attributes.
- Confirm a qualifying product exists before calling its absence a search failure.
- Record query, market, time, availability, filters, product evidence, and observable result state.
- Mark unknown attributes as unknown; do not infer compliance from vague titles or images.
- Separate site failures from extraction failures, agent mistakes, and legitimate catalog gaps.
- Repeat unstable findings under controlled conditions.
- Label fallback substitutes as alternatives and distinguish them from exact matches.
- Do not infer shopper prevalence, conversion loss, or revenue impact without supporting data.
- For public-storefront tests, distinguish observations from root-cause hypotheses; configuration or catalog access may be needed to confirm the cause.
- Visual, subjective, personalized, shipping, and conversational tests need explicit rubrics and suitable access before scoring.

## Failure modes

### Language and query interpretation

- F001: Synonyms fail: couch misses products found by sofa. [approved]
- F002: Typos fail: runing shoes misses running shoes. [approved]
- F003: Singular, plural, or inflected forms change results incorrectly. [approved]
- F004: Formatting variants fail: USB-C, USB C, and USBC. [approved]
- F005: Abbreviations fail: TV versus television. [approved]
- F006: Regional vocabulary fails: wellies versus wellington boots. [approved]
- F007: Diacritics or special characters prevent matching: cafe versus café. [approved]
- F008: Ambiguous words resolve to the wrong meaning: Apple charger. [approved]
- F009: A valid query is incorrectly corrected into a different word. [approved]
- F010: Word order changes meaning-equivalent results: leather black bag versus black leather bag.
- F011: Extra spaces, capitalization, or harmless punctuation break matching.
- F012: Conversational filler hides intent: looking for a pair of walking boots.
- F013: Compound words and separated forms fail to match in the store’s language.
- F014: Common shortened model or product names fail to resolve to the full name.
- F015: Vocabulary used in product descriptions is not discoverable through search.
- F016: Mixed-language or translated queries fail despite a supported multilingual shopping context. [borderline]

### Intent and requirements

- F018: Explicit requirements are ignored: waterproof jacket returns non-waterproof jackets. [approved]
- F019: Price limits are ignored. [approved]
- F020: Negation or exclusions are ignored: without sleeves returns sleeved dresses. [approved]
- F021: Use-case language misses suitable products: shoes for muddy trails. [approved]
- F022: Combined requirements lose one or more constraints. [approved]
- F023: Unit equivalents fail: 1 litre versus 1000 ml. [approved]
- F024: Compatibility is ignored: a case for one phone model returns incompatible cases. [approved]
- F025: Brand intent is ignored or matching branded products are displaced. [approved]
- F026: Audience is ignored: children’s helmet returns adult helmets. [approved]
- F027: Pack quantity is confused with individual-item quantity. [approved]
- F028: Misleading material matches: leather returns imitation leather as satisfying the requirement. [approved]
- F029: Numeric ranges or comparisons fail: at least 20 litres, between £50 and £100.
- F030: Dimensions are confused: width, height, length, or diameter treated interchangeably.
- F031: Size systems are confused: UK, EU, US, adult, or child sizes.
- F032: Ingredient, allergen, or certification requirements are ignored despite explicit product evidence.
- F033: Similar model generations or editions are treated as interchangeable.
- F034: Product condition is ignored: new, refurbished, or used.
- F035: Bundle versus standalone intent is ignored.
- F036: Alternative requirements are interpreted as requiring both: red or blue.
- F037: Relationships between requirements are lost: a table for six versus six tables.
- F038: Qualitative needs are interpreted poorly: lightweight, quiet, or easy to clean. [borderline]
- F039: Occasion or recipient intent produces poor suggestions: a gift for a beginner gardener. [borderline]
- F040: Vague budget language produces unreasonable suggestions: affordable or premium. [borderline]

### Retrieval and coverage

- F041: An exact product name fails to retrieve a product the store sells. [approved]
- F042: A product code, SKU, or model number fails to retrieve the matching product. [approved]
- F043: Too few matching products appear despite independently verified alternatives. [approved]
- F044: An unavailable exact request has no useful, clearly identified alternatives. [approved]
- F045: Search and equivalent category/filter navigation disagree. [approved]
- F046: Known matching products are absent even though a broader query retrieves them.
- F047: Adding a valid requirement removes verified products satisfying it.
- F048: Removing a requirement unexpectedly loses products that still qualify.
- F049: Products recently added or updated remain missing or stale in search.
- F050: Variants have inconsistent discoverability: parent product appears but the matching variant cannot be found.
- F051: Search retrieves irrelevant pages or editorial content instead of requested products.
- F052: Search matches incidental description text while ignoring the product’s actual purpose.
- F053: Promoted categories are searched while other relevant catalog sections are omitted.
- F054: Exact zero-result requests are silently broadened and presented as exact matches.
- F055: Alternative suggestions violate a hard requirement without explaining the mismatch.

### Ranking and result-set usefulness

- F056: Accessories outrank the requested main product. [approved]
- F057: The exact or clearly stronger match is buried beneath weaker products. [approved]
- F058: Near-duplicate variants flood the first page. [approved]
- F059: Unavailable requested variants appear as usable matches. [approved]
- F060: Out-of-stock or discontinued products displace suitable available products.
- F061: Related but incompatible substitutes displace exact matches.
- F062: Promoted or sponsored items crowd out suitable organic matches.
- F063: Broad searches expose a narrow slice of the assortment despite verified relevant variety.
- F064: Cheaper-looking results use misleading from-prices for variants that do not satisfy the query.
- F065: Price sorting orders products incorrectly for the matching variant or selected market.
- F066: Popularity, discount, or merchandising boosts overwhelm explicit query relevance.
- F067: Small equivalent query changes cause unstable rankings that materially hide relevant products.
- F068: Visually different products with similar titles are incorrectly collapsed into one family.
- F069: Visually similar products with different functions are treated as interchangeable.
- F070: Product imagery conflicts with the requested variant even when the title matches.
- F071: Good matches appear only below obstructive banners, content blocks, or excessive sponsored rows.
- F072: Product ordering ignores implicit value tradeoffs: durability versus price, for example. [borderline]

### Autocomplete and search entry

- F073: Autocomplete suggestions lead to empty or irrelevant results. [approved]
- F074: Autocomplete cannot find exact products or brands that full search can retrieve.
- F075: Autocomplete truncates or rewrites a meaningful part of the query.
- F076: Suggestion labels promise one category or product but link to another.
- F077: Selecting a suggestion applies hidden constraints or redirects away from the intended search.
- F078: Keyboard submission and clicking search produce different queries or results.
- F079: Typed query text is lost during submission, navigation, or suggestion selection.
- F080: Search input cannot handle pasted model codes or product names correctly.
- F081: Mobile search is inaccessible, obscured, or requires excessive steps to use.
- F082: Autocomplete fails to surface useful exploratory suggestions for vague needs. [borderline]

### Filters, sorting, and navigation

- F083: A visible filter does not change results or includes products that violate it.
- F084: Combining filters produces false zero results despite known matching products.
- F085: Filter options omit values present in the matching product set.
- F086: Filter counts disagree materially with the products reachable through them.
- F087: Filters reset unexpectedly during reformulation, sorting, pagination, or back navigation.
- F088: Previous filters silently persist and make a new search appear broken.
- F089: An active filter or sorting choice is not visible to the shopper.
- F090: Removing a filter fails to restore qualifying results.
- F091: Pagination or load-more repeats products or skips known matching products.
- F092: Product links lead to the wrong item, broken pages, or the wrong variant.
- F093: Back navigation loses the query, filters, or result position.
- F094: Sort changes reset or ignore the query’s requirements.
- F095: Relevant facets are unavailable even though catalog data supports them.
- F096: Category redirects lead to an irrelevant or overbroad destination.
- F097: Search suggestions or redirects create loops rather than reaching products.

### Product verification and shopping feasibility

- F098: Result cards hide decisive information that is available on the product page.
- F099: Search claims an attribute that product details contradict.
- F100: Search price differs from the currently purchasable matching variant.
- F101: Search availability differs from product-page availability.
- F102: A matching product cannot be purchased in the displayed market or currency.
- F103: The advertised matching size, color, or configuration is not selectable.
- F104: Product comparison is obstructed by missing or inconsistent key specifications.
- F106: Excluding shipping or minimum-order requirements makes budget matches misleading. [borderline]

### Recovery, context, and reliability

- F109: Zero-result pages provide no useful recovery path despite known matching alternatives.
- F110: Search shows stale results after a query change.
- F111: An error, timeout, or loading state is presented as zero results.
- F112: Results fail to load or become interactive on mobile or desktop.
- F113: The same controlled query intermittently loses qualifying products.
- F114: Locale or currency changes silently alter or invalidate the search.
- F115: Search URLs do not preserve enough state to reproduce a finding.
- F116: Result counts promise products that are not reachable through pagination or filters.
- F117: Query highlighting misrepresents why a product matches.
- F118: Personalization or session history makes useful products disappear. [borderline]
- F120: Complex multi-item needs fail: assemble a compatible camping kit within a total budget. [borderline]

## Excluded by user (2026-11-03)

These modes are out of scope. Their IDs are reserved to keep existing references stable.

- F017: Voice transcription errors prevent recovery of otherwise clear intent. [excluded]
- F105: Delivery location or deadline makes apparently suitable results unusable. [excluded]
- F107: Reviews contradict a claimed suitability or compatibility attribute. [excluded]
- F108: Product images are needed to establish a visual style that text search misses. [excluded]
- F119: Reformulations lose conversational context in an explicitly conversational search interface. [excluded]

## Next step

Review borderline modes, then choose a small first set to turn into store-grounded test templates. No tests or implementation have been run as part of generating this library.
