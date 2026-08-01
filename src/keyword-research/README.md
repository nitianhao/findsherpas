# Keyword research pipeline

Replaces Ahrefs with free sources. Each stage writes a file the next one reads,
so any stage can be inspected or hand-edited before the next runs.

Design spec: `docs/superpowers/specs/2026-07-31-content-keyword-program-design.md`

## What works today

```bash
npm run kw:expand          # Stage 1: autocomplete expansion (~3 min, ~950 requests)
npm run kw:filter          # Stage 2: contamination filter — THEN READ THE REJECTS
npm run kw:serp            # Stage 3: DuckDuckGo SERPs (headful browser, resumable)
npm run kw:reclassify      # Stage 3: recompute owners/weakness offline, no refetch
npm run kw:planner-emit    # Stage 4a: write batch files for Keyword Planner
# ... manual: paste each batch into Keyword Planner, download CSVs into data/planner/
npm run kw:planner-merge   # Stage 4b: merge volume and bid back in
```

Those six are the only `kw:` scripts. Stages 5 and 6 have tested logic but no
runner — see [Not built yet](#not-built-yet).

`kw:serp` accepts `--limit=N` (or `--limit N`). It opens a **visible browser
window**; headless is blocked. It is resumable — re-running skips terms already
fetched.

## Stages

| Stage | Module | Status | What it does |
|---|---|---|---|
| 0 | `config/seeds.ts` | ✅ | 28 hand-curated seeds tagged by track |
| 1 | `expand/autocomplete.ts` | ✅ runnable | Google autocomplete, alphabet soup + intent modifiers |
| 2 | `filter/contamination.ts` | ✅ runnable | Strips operator / jobs / corporate / registry noise |
| 3 | `serp/duckduckgoSerp.ts`, `serp/ownerClassifier.ts`, `serp/serpRecon.ts` | ✅ runnable | Fetches SERPs, classifies who owns page one, scores winnability |
| 4 | `planner/keywordPlanner.ts` | ✅ runnable | Keyword Planner batch emit and CSV merge |
| 5 | `gsc/gscJoin.ts` | ⚠️ logic only, no runner | Search Console join, striking-distance report |
| 6 | `cluster/serpOverlap.ts`, `score/scoring.ts` | ⚠️ logic only, no runner | Groups by SERP overlap, scores, builds backlog |

Shared: `types/index.ts`, `io/csv.ts` (hand-rolled, handles CRLF and quoted
fields containing commas and newlines), `io/columns.ts` (matches Google's
inconsistent column names), `io/keywordRows.ts` (**the only correct way to read
a keyword CSV** — see below).

## Results from the first real run

Stage 1 produced **15,480 raw rows**. Stage 2 cut them to **4,286 kept / 871
rejected**:

| Reason | Count |
|---|---|
| NO_TOPIC_TOKEN | 443 |
| TRIVIA | 96 |
| CORPORATE | 94 |
| NAVIGATIONAL | 92 |
| JOBS | 91 |
| BRAND_ASSET | 44 |
| REGISTRY | 8 |
| SEARCH_OPERATOR | 3 |

Stage 3 targets only the **351 commercial-intent terms** of those 4,286 (those
carrying `vs`, `alternatives`, `pricing`, `cost`, `review`, `compare`, `best`,
`competitor`). **84 are fetched; 267 remain.**

Across 820 results from the first 82 SERPs, **not one came from a credible
independent authority**: 45.7% unknown (content farms, small blogs), 28.9%
review aggregators, 17.6% vendor blogs, 6.1% forums, 1.7% vendor docs.

## Four things that will bite you

### 1. Always read the rejects.

`data/stage2-rejected.csv` is where the filter's mistakes hide, and the
histogram looks healthy while it deletes your best keywords. This happened
twice during the build, and the histogram gave no hint either time:

- A bare `operator` token was killing **`elasticsearch operator`** and
  **`opensearch operator`** — Kubernetes operators, among the most valuable
  practitioner keywords in the set. The token was written to catch Google's
  `site:` operator.
- Bare `support` and `dashboard` were killing **`opensearch extended support`**
  (a version-lifecycle policy) and **`elasticsearch grafana dashboard`**.

`kw:filter` now refuses to run if any seed's own term would be rejected, which
closes the worst case. It cannot catch a wrongly-rejected expansion. Read them.

### 2. Re-run `kw:reclassify` after touching the classifier.

`ownerType` and `weakness` are computed at fetch time and frozen into
`stage3-serps.json`, and `kw:serp` skips terms already present. A classifier
change therefore does **not** reach cached data, and re-running the fetcher
prints "Nothing to do" and exits 0. This already happened once: a fix corrected
64.5% of stored classifications in code while the cache kept the old values.

The cache now carries a `classifierVersion` and `kw:serp` throws on a mismatch.
`kw:reclassify` recomputes offline — no network, no browser.

### 3. Never cast a CSV row to `Keyword`.

`readCsv` returns `Record<string, string>`. Casting that to `Keyword[]`
type-checks and lies: `avgMonthlySearches` is a string, so `volume +=` performs
string concatenation. Summing two rows of 100 produced `"0100100"`, which
`normalizeVolume` then coerced to 100100 and pinned at its cap, silently.

Use `readKeywords()` from `io/keywordRows.ts`.

### 4. Export from Google in English.

Both Google parsers tolerate inconsistent whitespace in header names. Neither
tolerates **localised column names** — a French export naming the column
`Mot clé` now throws rather than producing an all-zero merge whose own
diagnostic then advised moving scoring weight off bid.

Cell formats are handled: `parseMoney` reads EU comma-decimals correctly
(`1,23` is 1.23, not 123 — the latter exceeded `BID_CAP` and turned the model's
heaviest weight into a constant).

## Scoring notes

`WEIGHTS` in `score/scoring.ts` is **provisional** — set before any real run.
Bid is weighted above volume because zero-spend Ads accounts return bucketed
volume ranges that carry little information. `kw:planner-merge` prints what
fraction of terms have a non-zero bid; if that is low, move weight from `bid` to
`weakness`.

`serpWeakness` is nominally 0..1 but occupies 0.52–0.85 on real data, so
`normalizeWeakness` rescales it against those measured bounds. Without that,
weakness contributed under 0.1 of score spread against bid's 0.35 — making the
most actionable signal the weakest discriminator. **Re-derive those bounds when
the SERP set grows.**

`ScoredArticle.hasData` is false when a row rests on defaults rather than real
lookups. Such rows still score mid-table, so filter on this column before
trusting a ranking.

## Manual inputs

- **Stage 4**: Keyword Planner → Discover new keywords → Download
  → `data/planner/planner-results-*.csv`. Exports carry preamble lines before
  the header; `stripPlannerPreamble` handles them and throws if it finds none.
- **Stage 5**: Search Console → Performance → Queries → Export
  → `data/gsc-queries.csv`

## Not built yet

- **Runners for stages 5 and 6.** The logic is tested; nothing wires
  clustering → scoring → `backlog.csv`.
- **267 of 351 SERPs.** Run `npm run kw:serp` to continue.
- **Two-level autocomplete recursion.** Level one already yields thousands of
  terms; add depth only if the backlog proves thin.

## Known limitations

- **These are DuckDuckGo results, not Google's.** A sound proxy for whether page
  one is owned by vendors grading their own homework; not a proxy for rank
  position. Brave and Bing were both measured and rejected — Brave burns a paid
  quota shared with the enrichment pipeline, Bing returns an empty shell even
  headful.
- **`peopleAlsoAsk` is always empty.** DuckDuckGo has no PAA equivalent, so
  `Cluster.peopleAlsoAsk` and `ScoredArticle.peopleAlsoAsk` are dead columns.
  The design spec lists PAA as a Stage 3 deliverable; it is not delivered.
- **The SERP extractor takes every anchor** and filters DuckDuckGo's own hosts,
  rather than depending on a class name that would break silently. A layout
  change could still promote non-organic URLs into result positions.
  `selectOrganicResults` is pure and tested; the browser call around it is not.
- **Aggregator domains** (G2, Capterra, Gartner) appear across unrelated vendor
  queries and could in principle chain unrelated terms into one cluster. Checked
  against the first 82 SERPs: 17 of 99 overlap edges touch listicles, and
  removing them entirely only splits 47 clusters into 52. Not occurring — recheck
  as the set grows.
