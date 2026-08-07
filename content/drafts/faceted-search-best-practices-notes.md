# Faceted search best practices — interview notes

Working notes for the second article. Not for publication.

## Why this article

Target cluster: `faceted search best practices`.

| | |
|---|---|
| SERP weakness | 0.66 |
| Score | 0.392 |
| Track | vendor (domain-adjacent, actually practitioner) |

**Page one, fetched:**

```
vendor-blog  coveo.com/blog/faceted-search/
unknown      brokenrubik.com/blog/faceted-search-best-practices
unknown      fact-finder.com/blog/faceted-search/
unknown      rush-analytics.com/learn-seo/faceted-search-and-filters
unknown      searchengineland.com/guide/faceted-navigation
vendor-blog  algolia.com/blog/ux/faceted-search-an-overview
unknown      doofinder.com/en/blog/faceted-search
unknown      numberanalytics.com/blog/mastering-faceted-search
vendor-blog  coveo.com/en/resources/ebooks/faceted-search-best-practices
forum        medium.com/design-bootcamp/faceted-search-filters-best-practices...
```

Two vendor blogs, generic SEO/UX content, one content-farm "mastering X" piece,
one Medium post. No practitioner-written piece diagnosing facets that are
already live and already broken. Same shape as the Algolia piece: the gap is
real, and it's the author's actual domain — this is relevance/UX work, not tool
selection.

Ruled out ahead of this: `elasticsearch/opensearch best practices` (infra/ops,
deploy-manage/scaling — wrong domain) and `bloomreach best practices` (mostly
their marketing-automation "Engagement" product, not Discovery/search).

## Positioning constraint

Same as the Algolia piece — relevance and search UX, not procurement or
integration. This topic is squarely in that lane; no vendor-neutrality
constraint needed since facets are a UX/architecture pattern, not a specific
product.

---

## Q1 — What goes wrong with facets once they're already shipped

**Headline reframe, and it's the whole article: facets are primarily a UX
problem, not a data problem.** This inverts the interviewer's framing (which
assumed data-quality issues would lead) — the author corrected it immediately,
and the correction is the piece's spine.

### 1. Discoverability comes first — mobile is where it's actually lost

Teams build and review on a laptop, where filters are typically visible in a
sidebar by default. Most traffic is mobile, where filters are **not visible by
default** — they live behind a button. If that button isn't obviously present
and labeled, the entire faceting system might as well not exist for most
visitors.

Concrete fix pattern: a clearly labeled filters button, or a floating/sticky
button pinned to the bottom of the screen so it survives scroll.

This is the "camera never lies" problem — a stakeholder reviewing the desktop
experience sees the filters and moves on, while the majority of real sessions
never discover them.

### 2. Ordering by actual usage, not intuition

Once discovered, facet **order** is the next lever. Rule: order by
importance/usage, not by how the schema was written or how the merchandising
team assumes people shop.

**Diagnostic method, concrete and repeatable:** look at facet-usage data and
find filters with high usage that are NOT positioned near the top. That
mismatch is the finding — it's a specific, checkable diagnostic, not a vague
"reorder your filters" suggestion.

Stated default: **price is the primary filter on most ecommerce sites.**

### 3. "Metafilters" — a named category the author says most teams skip

In *search results* specifically (as opposed to category browse), results cut
across many categories, so filtering needs a category facet — the search-results
context makes this non-obvious in a way it isn't on a category page.

Alongside a genuine category facet, a **metafilter** group:
- new
- on sale
- best sellers
- in stock / out of stock

These complement sorting rather than substitute for it, and the author frames
this as a commonly-missed group, not just "add more filters."

### 4. Data normalization inside facet values

"Nothing kills conversion" like bloated filter value lists that are really the
same value spelled differently — duplicate/near-duplicate strings clogging a
facet.

Colour is the named example, and it has a specific two-level structure:
**group by primary colour first** (e.g. "Red"), with shades available as a
secondary breakdown falling out of the primary group ("Bright Red", "Maroon"
nested under "Red"), rather than every shade sitting flat as its own top-level
option.

### 5. Never let a filter combination silently zero out

Filters must make the space of valid combinations visible before commitment:
- It should not be possible to combine filters and land on zero results
- On mobile specifically — where the filter panel is a modal — the result
  count should be visible *before* the user applies/closes the filter, since
  the modal hides the result grid while it's open

### 6. Dynamic filters — the one genuinely search-specific idea

This is flagged by the author as unique to *search results* rather than
category browse, and it's the most novel point in the interview.

For a given query's result set, there should be additional filter options
generated from what's actually IN that specific set of results — facets that
represent the group returned, not the static global facet list.

**Practical de-scoping hint from the author, important for making this
achievable rather than aspirational:** this does not require real-time
automation. It can be **hardcoded per query for the top 100–200 queries** —
i.e., manually curate the dynamic-filter set for your highest-volume searches
rather than building a system that infers it live for every query.

### 7. Facet vocabulary must match the customer's mental model, not the data model

**Distinct from point 4 (normalization).** Normalization is about deduplicating
messy values that mean the same thing. This is about values that are each
individually correct and clean, but meaningless to the person using them.

**Real story — online pharmacy client.** An important category exposed filters
built on the underlying technical/regulatory data as it existed in the source
system — ISO codes and similarly technical classification values. Each value
was accurate. None of them were comprehensible to an ordinary shopper. Nobody
except a domain expert could read the filter and know what they'd get by
selecting it. Net effect: confusion, not narrowing — the facet made the page
look more sophisticated while making it harder to use.

This becomes the concrete anchor for the article, filling the "no story yet"
gap. Likely candidate for the opening, playing the same role the brand-field
story played in the Algolia piece — used as an addition/expansion by the
author's own note, not just a supporting example.

## Numbers

**Filter usage correlates with conversion: users who use filters are 19% more
likely to convert.** Confirmed: this is the **author's own observation**, not a
cited external study. Draft and attribute it as a practitioner's own finding —
same framing convention as the sponsored-placement number in the Algolia piece
("in my experience", not "research shows"). It is a correlation between filter
usage and conversion, not a causal claim that fixing filters produces a 19%
lift — the rest of the article makes the causal argument (undiscoverable or
unusable filters mean this uplift never gets captured).

**Facet reordering by usage: a small but positive effect, 1–2% conversion.**
Author is explicit this is not a silver bullet — framed as "won't solve
everything, but helps." Keep that honesty in the draft rather than inflating
it; it's a real, modest, checkable number and should read as one.

## Point 6 detail — dynamic filters, concrete example

Confirmed: this is NOT a default-on-every-query behavior. The rule is
query-specific relevance — a facet gets added only when it's meaningful for
that particular search's category.

**Example given:** searching "shoes" on a fashion site should surface a **shoe
size** filter, which would not make sense as a global/default facet across all
search results (most result sets aren't shoes). This is the concrete
illustration of the "hardcode for your top 100–200 queries" method from Q1 —
size-for-shoes is exactly the kind of query-category mapping that gets
hand-built rather than inferred live.

## Point 5 detail — zero-result combinations, the actual mechanism

This is a **principle**, not tied to one incident — but the author sharpened
the mechanism significantly beyond "show the count first":

**The real fix: every remaining facet's displayed options must be constrained
to only the values still reachable given filters already applied.** Not just
surfacing a result count before commit — the available *options in every other
facet* should already be pruned to whatever intersects with the current
selection. If a value in another facet would produce zero results in
combination with what's already selected, it should not be offered at all (or
should be visibly disabled), rather than being clickable and then failing.

**Consequence stated plainly: people stop using filters when this happens.**
This is the cost of getting it wrong — not just a bad single interaction, but
abandonment of the whole filtering feature going forward. Strong candidate for
how this section closes.

## Notes for drafting

- The reframe ("UX before data") should probably be the opening hook, mirroring
  how the Algolia piece opened on "wrong layer." Same rhetorical move: most
  advice targets the wrong thing first.
- Seven distinct, concrete sub-topics now — likely seven sections, similar
  structure to the Algolia piece's numbered list close.
- "Dynamic filters" is the most differentiated/shareable idea and the one
  competitors are least likely to have written about. Consider whether it
  deserves to lead rather than close, or whether it works better as the payoff
  after the more foundational points.
- Opening candidate: 19% conversion-correlation number + pharmacy ISO-code
  story, in that order or reversed — need to decide which lands first when
  drafting, same way the Algolia piece opened on the story before the number.
- Pharmacy story could double as evidence for the discoverability argument too
  (a confusing filter is arguably worse than an undiscoverable one) — but it's
  really about vocabulary mismatch (point 7), keep it there rather than
  stretching it to cover point 1 as well.

## Open threads (remaining, optional)

- A concrete diagnostic example: real usage data showing a high-usage facet
  buried low, and what moving it did (point 2).
- Whether "metafilters" is the author's own term or a term of art worth
  double-checking before publishing.
- Have not yet asked about points 3 (metafilters) or 4 (value normalization
  beyond colour) in follow-up depth — both were given fully formed in Q1 and
  may not need more, but worth a pass if time allows.

## Status: enough to draft

All seven points now have mechanism + at least one of {story, number,
concrete example}. Two real numbers (19% correlation, 1-2% reorder lift), one
full anonymized story (pharmacy), one concrete worked example (shoe size).
Sufficient to write a full draft; remaining open threads are enrichment, not
blockers.
