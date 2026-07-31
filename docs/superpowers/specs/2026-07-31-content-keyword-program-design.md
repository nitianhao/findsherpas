# Content & Keyword Program — Design

Date: 2026-07-31
Status: Approved (design), pending implementation plan

## Problem

findsherpas.com has effectively no organic traffic. Google Search Console, 2026-05-01 to 2026-07-30:

| Metric | Value |
|---|---|
| Impressions | 128 |
| Clicks | **0** |
| Indexed pages with impressions | 8 |
| Avg position (home) | 9.5 |

Content inventory is two framework pages, one placeholder blog post, and one placeholder
case study. The domain is new and carries no authority.

Ahrefs is unavailable. The program must run on free and near-free data sources.

### Diagnostic finding: the site attracts the wrong audience

`/frameworks/query-interpretation` is the #2 page by impressions (24). The queries hitting it
are Google Quality Rater Guidelines phrasings:

- "a query can have no more than three common interpretations"
- "some queries do not have a dominant interpretation"
- "queries with a user location can have just one interpretation"

That audience is search quality raters and SEO students, not ecommerce search owners with
budget. The one page that ranks, ranks for the wrong people. The article program must
deliberately correct for this.

## Goals

1. Build a repeatable keyword research pipeline that replaces Ahrefs with free sources.
2. Produce a scored article backlog, one row per article rather than per keyword.
3. Ship articles on a sustainable loop that uses the owner's first-party expertise.

## Non-goals

- Paid acquisition, link building outreach, or technical SEO beyond what is noted below.
- Automating article writing end to end. Drafts are interview-driven by design.
- Ranking for head terms in the near term. See phasing.

---

## Part 1 — Keyword research pipeline

Location: `scripts/keyword-research/`. Six stages, CSV between each, so any stage can be
inspected and manually overridden before the next runs.

### Stage 0 — Seeds

~40 hand-curated seeds, tagged by track:

- **Vendor**: algolia, coveo, bloomreach, constructor.io, klevu, searchspring, elasticsearch,
  opensearch, typesense, luigi's box, meilisearch, attraqt, lucidworks, nosto
- **Buyer**: ecommerce search, product discovery, zero results, search conversion,
  merchandising, search audit
- **Practitioner**: search relevance, query understanding, ranking, vector search,
  semantic search, search analytics, synonyms, faceted search

### Stage 1 — Autocomplete expansion

`https://suggestqueries.google.com/complete/search?client=firefox&hl=&gl=&q=` — unauthenticated,
no API key, verified working during design.

- Alphabet soup: `seed + a..z`
- Intent modifiers: `vs`, `how`, `why`, `best`, `for`, `alternatives`, `pricing`
- Two levels deep (re-expand top suggestions)
- Locales: `gl=us`, `gl=gb`, `gl=de`

### Stage 2 — Contamination filter

**This stage is the main justification for building a script rather than doing this by hand.**

Evidence from the design run: seed `site search` produced 256 suggestions, the majority of
which were the Google `site:` operator (`site search command google`, `site search google dork`)
or job boards (`best site to search jobs in india`, `job site search engines`). A naive expander
hands that back as a top cluster.

Filter rules:

- Blocklist: careers/jobs, login/dashboard, stock/valuation/revenue/CEO/employees/funding,
  logo/icon/png/svg, meaning/pronunciation, unrelated-industry hijacks
- Require at least one topic token from a controlled vocabulary
- Drop navigational brand queries (`algolia login`, `algolia status`)

Expected reduction on the design-run data: ~620 raw suggestions to ~150 usable.

### Stage 3 — SERP recon

Via Firecrawl (available in this environment). For each shortlisted term:

- Top 10 URLs
- Owner classification: vendor blog / vendor docs / listicle / forum / independent
- Page depth (word count)
- People Also Ask questions

Produces a **SERP weakness score**. A page one owned entirely by vendors marking their own
homework is winnable by an independent voice; a page one with strong independent incumbents
is not.

### Stage 4 — Keyword Planner merge

Semi-manual. Google Ads API automation requires a developer token with Basic access
(~1–3 day approval) and is not worth blocking on.

1. Script emits `seeds-for-planner.txt` in batches of ≤1000 terms (Keyword Planner's paste limit)
2. Operator runs Discover-new-keywords, downloads CSV
3. Script joins CSV back on the keyword column

**Use top-of-page bid as the primary signal, not volume.** On a zero-spend Ads account the
volume column returns bucketed ranges (`10–100`) that carry little information at this scale.
Bid is a much better proxy for commercial intent: `algolia alternatives` carries a real CPC,
`algolia pronunciation` does not.

### Stage 5 — GSC join

Pull findsherpas.com queries and pages via the Search Console MCP. Flag striking-distance
terms (position 5–20 with impressions). Near-empty today. Expected to become the
highest-signal input in the pipeline by month three, at which point it should drive more
decisions than the autocomplete data.

### Stage 6 — Cluster and score

Clustering approach, decided:

| | Approach | Trade-off |
|---|---|---|
| **A** (chosen) | SERP-overlap: keywords sharing 3+ top-10 URLs are one article | Matches how Google actually groups intent. Costs one SERP fetch per keyword. |
| B | String/embedding similarity | Free, but wrong: splits `algolia cost` from `algolia kosten`, merges terms Google treats separately. |
| C | Manual | Best judgment, does not scale past ~100 terms. |

**Implementation: run B as a cheap pre-filter to reduce the candidate set, then A on the
survivors.** Correct grouping without paying for ~600 SERP fetches.

Score inputs: commercial intent (bid), SERP weakness, volume band, topical fit to positioning.

Output `backlog.csv`, one row per article: title, keyword cluster, primary target, PAA
questions to answer, track, score.

---

## Part 2 — Article program

### Phasing

Sequencing matters more than ratio. With zero authority, attacking `algolia vs elasticsearch`
first wastes months.

**Phase 1 (articles 1–6) — fast wins.** Long-tail vendor-implementation and buyer-intent terms
where page one is currently vendor docs and forum threads. Realistic to rank in weeks.

| Article | Cluster (verified autocomplete terms) | Rationale |
|---|---|---|
| What Algolia actually costs at scale | `algolia units`, `algolia pricing`, `algolia cost`, `algolia free tier`, `algolia kosten` | Pricing confusion is universal; the vendor structurally cannot write this honestly |
| Query rules: when they quietly break relevance | `algolia query rules`, `algolia merchandising`, `algolia optional filters`, `algolia virtual replica` | Docs rank but never say "when this is a bad idea" |
| What a healthy zero-results rate looks like | `zero results rate`, `zero results page` | Benchmark content earns links; direct buyer intent |
| Typo tolerance and the misspelling tax | `algolia typo tolerance`, `algolia did you mean` | Concrete, measurable, underwritten |
| Measuring search relevance without a labelled set | `search relevance metrics`, `ecommerce search relevance` | Core first-party expertise; practitioner link bait |
| The search audit nobody runs | buyer-intent tail | Routes to `/search-check` |

**Phase 2 (7–14) — the comparison ladder,** once Phase 1 has built internal link equity.
Hub-and-spoke, attacked in ascending difficulty:

1. `algolia alternatives`, `best algolia alternatives`, `algolia open source alternative`
2. `algolia vs typesense`, `algolia vs meilisearch` — dev audience, easier SERPs
3. `algolia vs coveo`, `algolia vs bloomreach`, `algolia vs constructor` — enterprise, closest to buyer
4. `algolia vs elasticsearch` — head term, attacked last with everything else linking into it

Stage 6 SERP-overlap determines which `vs` pairs are genuinely one page versus separate.

**Phase 3** — head terms (`ecommerce search`, `site search engine`) only once the domain can
carry them.

Net ratio lands near **50% vendor / 25% buyer-intent / 25% practitioner**, front-loaded toward
whatever ranks fastest.

### Per-article loop

1. Pull next row from `backlog.csv`
2. Ask the owner 3–5 sharp questions: real numbers, the war story, the contrarian take
3. Owner answers in bullets
4. Draft to `content/blog/<slug>.mdx`
5. Owner red-pens
6. Revise

Cadence is gated on interview time. One per week is realistic. One credible piece beats four
generic ones — generic content actively harms the vendor-neutrality position.

### Content pipeline (existing, no build work needed)

`lib/content.ts` reads MDX from `content/blog/`. Frontmatter schema:

```yaml
title, excerpt, date, tags[], featured, seoTitle, seoDescription
```

`app/(site)/blog/page.tsx` renders the index; `app/(site)/blog/[slug]/page.tsx` renders posts.

### Structural fixes, folded in

1. **`/blog/welcome-to-find-sherpas` is live, indexed, and ranking at position 3.5.** The
   case study publishes the literal sentence "This is a placeholder case study. Replace the
   details once you're ready." Credibility-negative to anyone who lands on it. Rewrite or
   unpublish before driving traffic.
2. **`/frameworks` has no index page.** The two framework pages are orphans with no hub.
   A hub page is free internal link equity and a natural practitioner-track target.
3. **Every article needs a soft route to `/search-check` or `/book-a-call`.** Soft is the
   operative word — see risk 2.

### Measurement

Re-run the pipeline monthly. The Stage 5 GSC join produces a striking-distance report that
governs what to *update*, separate from the backlog that governs what to *write*.

---

## Risks

1. **Zero domain authority.** `algolia vs elasticsearch` is realistically 6–12 months out.
   The program is phased so buyer-intent quick wins fund patience on the slow head terms.
2. **The vendor wedge only works if the content stays genuinely honest.** The audience
   searching `algolia alternatives` detects a sales pitch instantly, and it is precisely the
   audience least affordable to lose. This constrains how hard any article may sell.
3. **Contamination.** Demonstrated with `site search`. Mitigated by Stage 2, but the blocklist
   needs review each run — new contamination patterns will appear with new seeds.
4. **Keyword Planner volume is bucketed** on zero-spend accounts. Mitigated by scoring on bid
   rather than volume.
5. **Wrong-audience drift.** The QRG incident shows the house writing style attracts
   practitioners and students over buyers. Each Phase 1 article should be checked against
   "would an ecommerce search owner with budget search this?"

## Open decisions deferred to implementation

- Exact scoring weights in Stage 6 — tune against the first real run rather than guessing now.
- Whether Firecrawl or a lighter SERP fetch is used in Stage 3, depending on rate limits
  observed on the first full run.
