# Keyword research pipeline

Replaces Ahrefs with free sources. Each stage writes a CSV the next one reads,
so any stage can be inspected or hand-edited before the next runs.

Design spec: `docs/superpowers/specs/2026-07-31-content-keyword-program-design.md`

## What works today

Stages 1, 2 and 4 are runnable end to end. Stages 3, 5 and 6 exist as tested
logic but have **no runner script and no live data source yet** — see
[Not built yet](#not-built-yet).

```bash
npm run kw:expand          # Stage 1: autocomplete expansion (~8 min, ~950 requests)
npm run kw:filter          # Stage 2: contamination filter — THEN READ THE REJECTS
npm run kw:planner-emit    # Stage 4a: write batch files for Keyword Planner
# ... manual: paste each batch into Keyword Planner, download CSVs into data/planner/
npm run kw:planner-merge   # Stage 4b: merge volume and bid back in
```

Those four are the only `kw:` scripts that exist. There is deliberately no
`kw:serp`, `kw:gsc`, `kw:cluster` or `kw:score`.

## Stages

| Stage | Module | Status | What it does |
|---|---|---|---|
| 0 | `config/seeds.ts` | ✅ | 28 hand-curated seeds tagged by track |
| 1 | `expand/autocomplete.ts` | ✅ runnable | Google autocomplete, alphabet soup + intent modifiers |
| 2 | `filter/contamination.ts` | ✅ runnable | Strips operator / jobs / corporate / registry noise |
| 3 | `serp/ownerClassifier.ts`, `serp/serpRecon.ts` | ⚠️ logic only | Classifies who owns page one, scores winnability |
| 4 | `planner/keywordPlanner.ts` | ✅ runnable | Keyword Planner batch emit and CSV merge |
| 5 | `gsc/gscJoin.ts` | ⚠️ logic only | Search Console join, striking-distance report |
| 6 | `cluster/prefilter.ts`, `cluster/serpOverlap.ts`, `score/scoring.ts` | ⚠️ logic only | Groups by SERP overlap, scores, builds backlog |

Shared: `types/index.ts`, `io/csv.ts` (hand-rolled CSV, handles CRLF and quoted
fields containing commas and newlines — real Google exports need both).

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

## Three things that will bite you

### 1. Always read the rejects. This is not optional.

`data/stage2-rejected.csv` is where the filter's mistakes hide, and the
histogram above will look perfectly healthy while it quietly deletes your best
keywords. This is not hypothetical — it happened twice during the build, and
both times the histogram gave no hint:

- A bare `operator` token was killing **`elasticsearch operator`** and
  **`opensearch operator`**. Those are Kubernetes operators — among the most
  valuable practitioner keywords in the whole set. The token was written to
  catch Google's `site:` search operator.
- Bare `support` and `dashboard` were killing **`opensearch extended support`**
  (a real version-lifecycle policy) and **`elasticsearch grafana dashboard`**
  (a real devops topic).

Both were found only by reading the actual rejected terms. Between them they
were destroying ~28 legitimate keywords. When you add a seed, its contamination
patterns are new — re-read the rejects.

### 2. Bid matters more than volume here, and that assumption is unverified.

On a zero-spend Google Ads account, Keyword Planner returns bucketed ranges like
`10 – 100` (note: an EN DASH, not a hyphen). At this niche's scale that carries
almost no information, so `score/scoring.ts` weights **top-of-page bid** above
volume.

That is the single most load-bearing and least verified assumption in the model.
`kw:planner-merge` prints what fraction of terms carry a non-zero bid. **If that
fraction is low, the assumption has failed for this niche** — move weight from
`bid` to `weakness` in `WEIGHTS`.

### 3. Locales are deliberately just `us`.

The plan originally expanded across `us`, `gb` and `de`. A measured run showed
all three return an identical 5,155-term set; the union was 5,157, so `gb` and
`de` contributed 2 terms, both German grammar fragments.

Root cause: `buildSuggestUrl` sends `hl=en`. For this endpoint the **host
language** dominates and the geo parameter `gl` barely moves results. To target
DACH properly you must vary `hl` (`hl=de&gl=de`), not add entries to `LOCALES` —
and expect to write German articles to match.

## Manual inputs

Two stages take CSV exports rather than API calls, deliberately — neither is
worth an OAuth build:

- **Stage 4**: Keyword Planner → Discover new keywords → Download
  → `data/planner/planner-results-*.csv`. Exports carry preamble lines before
  the real header; `stripPlannerPreamble` handles this.
- **Stage 5**: Search Console → Performance → Queries → Export
  → `data/gsc-queries.csv`

Both parsers tolerate inconsistent whitespace in header names. **Neither
tolerates non-English column names** — a localised export produces an empty
merge with no error, and `kw:planner-merge`'s low-bid warning will then
misattribute it to a bid-signal problem. Export in English.

## Not built yet

- **The live SERP fetcher.** Stage 3 classifies and scores a SERP but nothing
  fetches one. Wiring it is the next real piece of work, and it needs a decision
  first: 4,286 keywords is far too many to fetch individually, so clustering
  must run on a scored subset.
- **Runner scripts for stages 3, 5 and 6.** They depend on the fetcher.
- **Two-level autocomplete recursion.** Level one already yields thousands of
  terms; add depth only if the backlog proves thin.

## Known limitations

- `cluster/prefilter.ts` normalisation drops stopwords and sorts tokens, so
  `search for products` and `product search` collapse together. Harmless **only
  if** Stage 3 fetches a SERP per distinct term and lets `serpOverlap` re-decide.
  If you wire Stage 3 to fetch one SERP per prefilter group, this becomes a real
  over-merge — the discarded term never gets a chance to be re-separated.
- Aggregator domains (G2, Capterra, TrustRadius) place multiple pages across
  unrelated vendor queries and could produce 3 coincidental URL overlaps,
  chaining unrelated terms into one cluster via transitivity. Consider an
  aggregator denylist or a top-5 overlap window once you see real SERP data.
- `WEIGHTS` in `score/scoring.ts` is provisional — set before any real run. It is
  the tuning surface, not a tuned result.
- A cluster with no keyword or SERP data scores ~0.25, which is mid-table rather
  than bottom, and looks identical in the output to a genuinely researched thin
  topic. Watch for data-join gaps outranking real signal.
