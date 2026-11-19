# ColourPop query review

65 queries across 26 categories. Review the query wording and rationale before the first fetch.

## Direct Match

- **A Very Mickey Christmas Eyeshadow Palette** — Exact product title from the featured items list tests whether the engine returns this specific palette as the top result.
- **Cloud Whip Blurring Lip Liner** — Exact product title from the featured items list tests precise catalogue lookup for this lip product.
- **Glitter Face Freckle Tattoos** — Exact product title from the featured items list tests whether the engine surfaces this novelty beauty item correctly.
- **Fallen Eyeshadow Palette** — Verbatim title observed on ColourPop's live homepage; tests exact product discovery.
- **Cloud Whip Lip & Cheek Pudding** — Verbatim title observed on ColourPop's live homepage; tests exact product discovery.
- **Dear Santa BFF Crème Gel Liner Kit** — Verbatim title observed on ColourPop's live homepage; tests exact product discovery.

## Synonym

- **eye makeup palette** — Uses a natural alternative for eyeshadow while retaining the real palette product type.
- **shiny lip color** — Uses a shopper's phrase for glossy lip products rather than the site's exact product type.
- **cheek tint** — Tests whether the engine maps 'cheek tint' to the Cloud Whip Lip & Cheek Pudding and related face products in the Face category.

## Typo

- **Fallen Eyeshdow Palette** — Introduces a missing letter in 'Eyeshadow' from the real product 'Fallen Eyeshadow Palette' to test the engine's typo-tolerance and fuzzy matching.
- **ColourPop Paletes** — Transposes/removes a letter in 'Palettes' from the real navigation category to test whether the engine corrects common misspellings.
- **Cloud Whip Lip Liner Blurign** — Introduces a transposition in 'Blurring' from the real product 'Cloud Whip Blurring Lip Liner' to test fuzzy matching on product descriptors.

## Special Character

- **lip & ch*eek pudding** — Injects a special character inside the real product term 'cheek' to test normalization.
- **cr*ème gel liner** — Injects a special character inside the real product term 'crème' to test normalization.
- **eye*shadow palette** — Injects a special character inside the real product term 'eyeshadow' to test normalization.

## Merged Words

- **eyeshadowpalette** — Merges 'eyeshadow' and 'palette' from the site's real product category to test whether the engine can tokenize compound search strings.
- **lipliner** — Merges 'lip' and 'liner' referencing the Cloud Whip Blurring Lip Liner to test token-splitting on a common beauty compound word.
- **colourpoppalettes** — Merges the brand name 'ColourPop' with 'palettes' from the navigation to test whether the engine can split brand and category tokens.

## Brand Search

- **ColourPop** — Searches by brand name alone to test whether the engine prioritizes ColourPop's own catalogue results prominently.
- **ColourPop eyeshadow** — Combines the real brand name with a real product category to test brand-filtered category results for ColourPop's eye products.
- **ColourPop lip liner** — Combines the real brand name with a real product type to test whether the engine surfaces ColourPop lip liner products like the Cloud Whip Blurring Lip Liner.

## Split Word

- **colo urpop** — Splits the single brand word ColourPop at an arbitrary internal position, away from its natural Colour/Pop boundary.
- **eyesh adow** — Splits the single product word 'eyeshadow' at an arbitrary internal position.
- **li ner** — Splits the single product word 'liner' at an arbitrary internal position.

## Natural Language

- **what eyeshadow palettes does colourpop have for the holidays** — Conversational query referencing ColourPop's real holiday palette offerings like A Very Mickey Christmas Eyeshadow Palette to test intent understanding.
- **something shimmery for my eyes that comes in a set** — Describes intent for eye makeup sets referencing ColourPop's Eyes and Palettes categories to test semantic intent parsing.
- **i need a lip product that works as blush too** — Describes the dual-purpose nature of the Cloud Whip Lip & Cheek Pudding to test whether the engine understands multi-use product intent.

## Price Anchored

- **eyeshadow palette under $20** — Combines the real Palettes category with a price constraint to test whether the engine can parse and apply price filters from free text.
- **colourpop lip products under $10** — References ColourPop's real Lips category with a budget constraint to test price-filter extraction from a natural query.

## Negative Intent

- **lip liner not glitter** — References the real Lips category with an exclusion to test whether the engine handles negation and filters out glittery lip liner products.
- **eyeshadow palette not collab** — References the real Palettes category with an exclusion of collaboration products to test negation handling against the Collabs navigation category.

## Unit Variation

- **15 pan eyeshadow palette** — Tests whether a shopper's spaced pan-count format finds the verified 15-pan Fallen Eyeshadow Palette.
- **24-pan eyeshadow palette** — Tests a hyphenated pan-count format against the verified Angel & Villain 24 Pan Eyeshadow Palette.

## Plural Singular

- **eyeshadow palettes** — Uses the plural form of 'palette' referencing the real Palettes navigation category to test whether the engine treats plural and singular equivalently.
- **lip liners** — Uses the plural form referencing the Cloud Whip Blurring Lip Liner and the broader Lips category to test plural-to-singular matching.

## Abbreviation

- **CP eyeshadow** — Uses 'CP' as a common abbreviation for ColourPop to test whether the engine expands the abbreviation and surfaces relevant eye products.
- **BFF liner kit** — Uses 'BFF' as it appears in the real product 'Dear Santa BFF Crème Gel Liner Kit' to test whether the engine matches on acronym tokens.

## Locale Variation

- **colourful eyeshadow** — Tests the British spelling 'colourful' on this US-English store.
- **colourpop blusher** — Uses the British term 'blusher' instead of 'blush' referencing ColourPop's Face category to test regional terminology normalization.

## Sku Model Number

- **EyePalette-Fallen** — Exact SKU published in structured product data on the Fallen Eyeshadow Palette product page.
- **CloudWhipLipLiner-TrueAutumn** — Exact SKU published in structured product data on the True Autumn Cloud Whip Lip Liner product page.

## Subjective Attribute

- **glam eyeshadow palette** — Applies the subjective qualifier 'glam' to the real Palettes category to test whether the engine understands qualitative descriptors for eye products.
- **budget friendly colourpop lip set** — Applies the subjective qualifier 'budget friendly' to ColourPop's real Lips and Value Sets categories to test qualitative intent matching.

## Occasion

- **gift for makeup lover** — Describes a gifting occasion relevant to ColourPop's Value Sets and Collabs categories to test whether the engine infers appropriate products from context.
- **stocking stuffer beauty set** — Describes a holiday gifting occasion referencing ColourPop's Value Sets and seasonal products to test occasion-based product inference.

## Seasonal Occasion

- **christmas makeup collection** — References the seasonal context of the real product 'A Very Mickey Christmas Eyeshadow Palette' to test seasonal relevance surfacing.
- **holiday value sets colourpop** — References ColourPop's real Value Sets category in a holiday seasonal context to test whether the engine surfaces seasonally relevant results.

## Multi Attribute

- **glitter eyeshadow palette** — Combines the real Palettes category with a single attribute 'glitter' referencing the Glitter Face Freckle Tattoos context to test compound constraint handling.
- **pink lip liner** — Uses one product type and one color constraint; omits the redundant house-brand term.

## Stop Word Heavy

- **what is the best eyeshadow palette to get from colourpop** — Pads the real Palettes category and brand name with stop words to test whether the engine extracts meaningful terms despite noise.
- **i am looking for a good lip and cheek product from colourpop** — Pads the real product type 'Lip & Cheek' referencing the Cloud Whip Lip & Cheek Pudding with stop words to test stop-word filtering.

## Partial Query

- **fallen eye** — Truncates the real product name 'Fallen Eyeshadow Palette' to test prefix matching and autocomplete-like behaviour.
- **cloud wh** — Truncates the real product name 'Cloud Whip Blurring Lip Liner' to test partial prefix matching on product names.

## Long Verbose Query

- **i am trying to find a really nice eyeshadow palette from colourpop that would be perfect as a christmas gift for someone who loves sparkly and festive holiday makeup looks** — Over-specified query referencing ColourPop's real Palettes category and holiday products like A Very Mickey Christmas Eyeshadow Palette to test core intent extraction.
- **looking for a colourpop lip product that can also be used on the cheeks as a blush or tint and comes in a creamy pudding or balm formula that is not too expensive** — Verbose query describing the real product 'Cloud Whip Lip & Cheek Pudding' with extra qualifiers to test whether the engine extracts the core product intent.

## Semantic Meaning

- **something to make my eyes pop for a night out** — Describes a conceptual outcome referencing ColourPop's Eyes and Palettes categories to test semantic search beyond keyword matching.
- **products to add a fun sparkle to my face** — Describes a conceptual desire referencing the real 'Glitter Face Freckle Tattoos' and glitter products in the Face category to test meaning-based retrieval.

## Category Mapping

- **makeup brushes** — Uses the colloquial term 'makeup brushes' to map to the site's real navigation category 'Brushes & Tools' to test taxonomy mapping.
- **face makeup** — Uses the colloquial term 'face makeup' to map to the site's real 'Face' navigation category to test whether the engine maps user language to internal taxonomy.

## Facet Extraction

- **red lip liner** — Combines the colour facet 'red' with the real product type lip liner from ColourPop's Lips category to test whether the engine parses colour as a filter.
- **matte eyeshadow palette** — Combines the finish facet 'matte' with the real Palettes category to test whether the engine extracts finish type as a filterable attribute.

## Gibberish

- **xkvbnmqwertzasdfg** — Pure keyboard mash with no product term; the expected behavior is zero results.
- **zzzqqqxxxyyy** — Pure repeated-letter mash with no product term; the expected behavior is zero results.
- **qwertyuiop** — Pure keyboard-row mash; the expected behavior is zero results.
- **sfjhdshdssjhdfdsshsdhgsddgshdghshdksghskgdhgshkhkghkskhksdnsidssi** — Long pure keyboard mash; the expected behavior is zero results.
