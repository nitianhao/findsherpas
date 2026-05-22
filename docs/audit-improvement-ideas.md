# Audit Improvement Ideas

Ideas for adding more value to the search audit while staying inside the current unit of analysis:

> query -> results -> audit

## 1. Result Set Purity

For each query, we already score every returned result for relevance. Today, the audit focuses heavily on where the single best result appears. Result Set Purity would also evaluate how clean the surrounding top results are.

Example metrics:

- Percentage of top 3 results that are relevant
- Percentage of top 5 results that are relevant
- Percentage of top 10 results that are relevant
- Number of irrelevant results above the first good result
- Whether the top results are all on-intent, mixed, or polluted

Why it is valuable:

A query can technically look acceptable because the best result appears at position #2, but if positions #1, #3, #4, and #5 are weak or irrelevant, the shopper experience still feels noisy. This gives us a stronger way to say: search found the right item, but the surrounding result set is polluted.

Potential audit output:

- Query-level purity score
- Capability-level average purity
- Top polluted queries
- Examples where retrieval works but result quality around the best match is poor

## Existing Capability Enhancement: Filters & Constraints

Constraint compliance is already covered by the current Filters & Constraints capability, especially through price-anchored queries, negative intent, multi-attribute queries, facet extraction, and unit variation.

Rather than adding it as a separate capability, we can make the existing capability sharper by adding explicit constraint-level metrics.

Possible enhancements:

- Extract explicit constraints from each query
- Mark each top result as satisfies, violates, or unclear for each constraint
- Report constraint violation rate in top 3, top 5, and top 10
- Break failures down by constraint type: price, negation, age, gender, size, color, material, ingredient, brand, dosage, pack size, availability
- Highlight cases where the product category is correct but the decisive constraint is dropped

Why it is valuable:

This gives clearer evidence for high-intent query failures. Instead of only saying "constraint dropped," the audit can say "8 of the top 10 results violated the stated under 10 euro price constraint" or "the engine matched painkillers, but 6 of the top 10 contained aspirin despite the query saying not aspirin."

## 2. Attribute Drift

Attribute Drift looks at multi-attribute queries and asks which parts of the query the engine preserves versus which parts it silently loses.

Example:

- Query: "women's waterproof trail running shoes"
- Preserved: running shoes
- Partially preserved: women's
- Dropped: waterproof, trail

What we would audit from query -> results:

- Decompose multi-attribute queries into required attributes
- Score each top result by attribute coverage
- Identify which attributes are preserved, partially preserved, dropped, or contradicted
- Report the most commonly dropped attribute types
- Separate "right category, wrong attribute" from "wrong category entirely"

Why it is valuable:

It tells the client how query interpretation breaks, not just that it breaks. Instead of saying "multi-attribute queries fail," the audit can say: "Your engine usually keeps product type and gender, but drops material and weather constraints."

Potential audit output:

- Query-level attribute coverage table
- Most commonly dropped attributes
- Attribute drift examples by capability
- Result-level diagnosis: right category, wrong attribute; right product type, wrong variant; attribute contradicted

## 3. Diversity vs Redundancy

Diversity vs Redundancy evaluates whether broad or exploratory queries return a useful range of options, or whether the top results are clogged with near-duplicates.

Examples:

- Query: "running shoes"
  - Good: different relevant models, genders, brands, use cases, and price points
  - Bad: ten color variants of the same shoe
- Query: "vitamin C"
  - Good: tablets, capsules, powders, children’s options, and different brands
  - Bad: the same supplement repeated across pack sizes only
- Query: "black dress"
  - Good: different styles such as evening, casual, midi, bodycon, plus-size
  - Bad: the same product repeated by size or color variant

Scope note:

This does not apply well to single-brand ecommerce websites where brand diversity is not expected and product families may naturally be narrower. It is more useful for multi-brand retailers, marketplaces, large catalogs, pharmacies, fashion retailers, electronics retailers, and other sites where broad queries should expose meaningful choice.

What we would audit from query -> results:

- Detect near-duplicate titles or product families in top 5 and top 10
- Measure unique product families versus repeated variants
- Judge whether redundancy is appropriate for the query type
- Flag excessive variant flooding
- Report whether broad queries show useful product, brand, category, format, style, or price diversity

Why it is valuable:

This catches a different kind of poor search experience. Results can all be relevant, but still unhelpful if they show the shopper the same option repeatedly. It is especially useful for broad category searches and product discovery queries.

Potential audit output:

- Duplicate / near-duplicate rate in top 10
- Unique product-family count
- Variant flooding examples
- Broad-query diversity score
- Applicability flag: use only when catalog type supports meaningful diversity

## 4. Query Specificity Scaling

Query Specificity Scaling evaluates how search quality changes as the query becomes more specific.

Instead of testing unrelated queries one by one, we create a small query ladder around the same product intent.

Example ladder:

- "shoes"
- "running shoes"
- "women's running shoes"
- "women's waterproof trail running shoes"
- "women's waterproof trail running shoes size 39"

What we would audit from query -> results:

- Whether relevance improves, stays stable, or degrades as intent becomes clearer
- Which added attribute causes the break
- Whether the engine handles head terms but fails long-tail intent
- Whether the engine over-focuses on one token and ignores the full query
- Whether the top result set narrows appropriately as specificity increases

Why it is valuable:

High-specificity queries often come from shoppers who know what they want and are closer to purchase. If the engine gets worse as the shopper gets clearer, that is an easy and commercially strong insight for stakeholders to understand.

Potential audit output:

- Specificity ladder per product area
- Break point detection
- Head / torso / long-tail performance comparison
- Example narrative: search works for "running shoes" but breaks once the shopper adds waterproof and trail

## 5. Top Result Trust

Top Result Trust focuses on the first result shown for each query.

For every query, it asks:

> Is result #1 defensible as the best thing to show a customer?

What we would audit from query -> results:

- Whether result #1 is relevant enough
- Whether result #1 violates any explicit constraint
- Whether result #1 is in the wrong category
- Whether result #1 is a weak partial match while a much better result appears lower
- Whether result #1 is a duplicate, promo, page chrome, or otherwise not a real product

Why it is valuable:

Stakeholders instantly understand the first result. Even if the rest of the result set is mixed, a bad #1 is the clearest evidence that search is failing. This can make reports sharper: "For 42% of tested queries, the first result was not a defensible answer."

Potential audit output:

- Top-result failure rate
- Top-result relevance threshold pass/fail
- Top-result constraint violation count
- Worst #1 results
- Capability breakdown by bad #1 rate
