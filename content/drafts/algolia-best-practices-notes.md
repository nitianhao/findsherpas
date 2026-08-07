# Algolia best practices — interview notes

Working notes for the first article. Not for publication.

## Why this article

Target cluster: `algolia best practices` (single term, no variants in cluster).

| | |
|---|---|
| SERP weakness | **0.845 — highest of all 195 clusters** |
| US volume | 50/mo |
| Top-of-page bid | none |
| Track | vendor |

**Page one, fetched 2026-08-01:**

```
vendor-docs  algolia.com/doc/guides/security/security-best-practices
vendor-blog  academy.algolia.com/collections/best-practices
vendor-docs  algolia.com/doc/guides/security/security-best-practices/in-depth/shared-re…
forum        youtube.com/watch?v=d5GpPTk_E2w
forum        youtube.com/watch?v=UZe7sOxujpk
forum        youtube.com/watch?v=ep-md_RRfJQ
forum        youtube.com/watch?v=Y9-uFjz3QzI
forum        youtube.com/watch?v=23UUyUQv2Iw
forum        youtube.com/watch?v=gzijs2U4z98
forum        youtube.com/watch?v=T8rbaz-PeUo
```

Two things make this the opening:

1. **Seven of ten slots are YouTube.** Google fills a page with video when no
   written article competes. There is no written incumbent to displace.
2. **Algolia's own top result is about security**, not relevance. Even the
   vendor has not written "how to configure Algolia's relevance well."

Volume is small (50/mo), so this is a precision play, not a traffic play. It is
being written because the gap and the author's expertise overlap here, which is
not true of the higher-scoring procurement terms.

## Positioning constraint

The author optimises search relevance. They do **not** do tool selection,
procurement, or integration. Nothing in this article should require knowledge of
pricing, contracts, or migration effort.

---

## Q1 — What teams consistently get wrong in Algolia's ranking setup

**Headline: it is almost never the ranking config. It is the data underneath it.**
If the right signals are not in the index, nothing can find or rank anything —
no amount of attribute tuning recovers from missing signal.

### The order of operations

1. **Fix the data first.** Title and price are not enough. Feed also:
   - a short description (can be AI-summarised)
   - as much structured data as possible, extracted from whatever exists —
     attached documents, long descriptions, FAQs, **customer reviews**
2. **Then** order `searchableAttributes` correctly, and decide per attribute
   whether it is `ordered` or `unordered`. Both matter; they are separate
   decisions and both have to be made deliberately.
3. **Then** validate before real users ever see it (see below).

### Relevance beats merchandising

Promoting products because the business asked **hurts overall conversion**.
This is the contrarian spine of the piece: the merchandising lever feels like
control and reads as revenue, but measured across the whole funnel it costs
more than it earns.

Corollary nobody does: **A/B test what sponsored positions actually do to
conversion.** Sponsored placement is usually assumed to be free money; the
author's position is that it should have to prove itself like any other change.

### Validate before shipping — the part that is genuinely differentiated

Do NOT dump a large volume of new structured data straight onto live users.
First:

- **Re-run the variation through a relevance-scoring LLM** (Cohere or Voyage
  rerankers) to score the new ranking offline
- **Run simulations with synthetic personas** across thousands of searches and
  watch for *emerging patterns* — behaviour that only appears at volume, not in
  a handful of spot checks

This mirrors the author's own audit pipeline (`src/audit/`, which uses Voyage
embeddings and an LLM judge), so it is lived methodology rather than theory.

### Notes for drafting

- Author said "voyager"; the product is **Voyage AI**. Use the correct name.
- The Algolia-specific mechanics (attribute ordering, ordered vs unordered) are
  currently asserted but not explained — Q2 goes there, because without the
  mechanism this reads as generic search advice with an Algolia label.
- "Promoting products hurts conversion" is a strong claim. It needs either a
  number, a mechanism, or explicit framing as the author's position. Flagged for
  a later question.

## Q2 — searchableAttributes ordering and ordered/unordered

**The rule:**

| attribute | setting | why |
|---|---|---|
| title | **ordered** | titles are written most-important-first; that convention is free signal |
| short description / summary | **unordered** | prose has no positional convention |
| structured attributes | **ordered** | short, and word order is meaningful |
| brand, category | high in the list | but *how* high is genuinely context-dependent per catalogue |

**Governing heuristic: the longer the field, the further down the list.** A long
description matches almost any query eventually, so a match there is weak
evidence; a title match is strong evidence. Ordering by field length is roughly
ordering by what a match is worth.

## Q3 — the merchandising claim, refined

Author could not substantiate the blanket "promoting hurts conversion" claim,
and instead supplied a better distinction:

- **sponsored product that would have ranked anyway, just lower** — reordering a
  set of reasonable answers; close to harmless
- **sponsored product that doesn't match the query, or barely** — not reordering
  but *injecting*; a slot that would have held a relevant answer now doesn't

These get discussed as one thing, which is how the second case survives.

Test to run: A/B sponsored placement, **split by whether the sponsored product
would have appeared organically**. Expectation (explicitly the author's
position, not a measured finding): the two cases separate clearly, and the
usual aggregate number averages across them and hides the damage.

Drafted as a stated position with the reasoning shown, not as a finding. No
fabricated numbers.

## Q4 — war story, docs, and numbers

**War story (now the article's opening).** A catalogue had a correctly populated
brand field that was simply not in `searchableAttributes`. Any product not
repeating its brand inside the title was **invisible** to a brand search — not
ranked low, absent. Reads from outside as a ranking failure; the ranking was
fine. Perfect demonstration of the thesis, and a severity failure rather than a
nuance, which is why it earns the lede. It also pays off a second time in the
attribute-order section.

**On Algolia's docs.** Author explicitly declined the "docs mislead" framing.
Their position: the docs don't mislead, they *under-educate* — they tell you
what each control does, not what value to give it for your catalogue. Expert
calibration is the gap. This is fairer and more defensible, and it reinforces
the opening observation that the whole SERP is "which toggles exist" content.

**Sponsored numbers.**
- Top 3 positions take ~80% of clicks; sharper on mobile, where 3 results is
  most of a screen
- Replacing those with irrelevant sponsored listings: ~20–30% conversion hit on
  the affected queries

Framed in the draft as a practitioner estimate, explicitly not a published
figure. The mechanism (click concentration means the top 3 are effectively the
whole result set) carries the argument even if a reader discounts the number.

## Q5 — the brand fix outcome, and how simulation actually runs

**Brand fix cost: 7–10% of purchases.** Now the second line of the article.
One line of configuration, 7–10% of purchases. That is the whole thesis in a
number, and it is the strongest sentence in the piece.

**Simulation methodology:**
- **5 personas**, developed in fine detail *including internal monologues* —
  the thing being modelled is how someone decides a result is wrong and what
  they do next, which a demographic sketch cannot represent
- **Queries come from the real query log**, not invented. Invented queries test
  the search you imagine you have; logs test the one you actually have,
  misspellings and all
- **Emerging patterns = shifting behaviour across configurations**
- Canonical example of a question only simulation answers: is it better to make
  only colour/size/price searchable, or to push every attribute into
  `searchableAttributes`? More signal sounds strictly better; dilution is real;
  nobody can reason their way to the answer for a specific catalogue
- **The core value: you can run dozens of configurations against synthetic users
  and cannot against real ones** — most candidate configurations are bad, and
  testing them live means charging real customers to discover that. Simulation
  narrows a large space to the two or three worth an A/B test.
- Framing used: *"Simulation doesn't replace the A/B test. It earns you the
  right to run a good one."*

**Tension this surfaced, and its resolution.** The article says "feed as much
structured data as possible" while the simulation question asks whether dumping
everything into searchable attributes helps. These only conflict if indexing and
searchability are conflated. Added an explicit distinction in the data section:
index everything (near-free, usable for faceting/filtering/ranking); which
fields enter `searchableAttributes` is a separate decision with real cost, and
is answered by simulation later in the piece. This also sets up the payoff.

## Still open (optional)

- Nothing on zero-results handling, which is a named diagnostic pattern on the
  site's own homepage but absent here.
- No mention of query understanding / synonyms, also a homepage theme.
- Neither is required; the piece is coherent as it stands.
