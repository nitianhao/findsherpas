# Keyword Research Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a re-runnable keyword research pipeline for findsherpas.com that replaces Ahrefs with free data sources and outputs a scored article backlog.

**Architecture:** Six stages, each writing a CSV that the next stage reads, so any stage can be inspected or hand-edited before the next runs. Every stage separates **pure logic** (filtering, classification, clustering, scoring — unit tested) from **network I/O** (fetching — thin, mockable wrappers). Stages 4 and 5 are semi-manual by design: they ingest CSV exports from Google Keyword Planner and Search Console rather than building OAuth flows.

**Tech Stack:** TypeScript, `tsx` for script execution, `vitest` for tests, `node:fs` for CSV. No new runtime dependencies.

## Global Constraints

- Location is `src/keyword-research/`, mirroring `src/enrichment/`. **This deviates from the spec's `scripts/keyword-research/` (Python)** — justified because `src/enrichment/` is a structurally identical TypeScript data pipeline, vitest is already configured for `src/**/*.test.ts`, and TypeScript is the project default. The Python in `src/audit/` is a separate legacy subsystem.
- Module naming: `camelCase.ts`, colocated `camelCase.test.ts`. Follow `src/enrichment/` conventions.
- Test runner: `npx vitest run <path>`. Vitest `include` is already `['src/**/*.test.ts', 'lib/**/*.test.ts']` — no config change needed.
- No new npm dependencies. CSV parse/serialize is hand-rolled in Task 1 (the data is simple; a dependency is not warranted).
- All intermediate data lands in `src/keyword-research/data/`, which must be git-ignored **except** the final `backlog.csv`.
- `.gitignore` currently has a blanket `*.csv` rule that would silently swallow every pipeline output. Task 1 fixes this. Do not skip it.
- Network calls must be rate-limited with a delay between requests (50ms for autocomplete, 1000ms for SERP fetches). Never parallelise these — the endpoints are undocumented and unthrottled requests will get the IP blocked.
- Scoring weights in Task 8 are **explicitly provisional**, to be tuned against the first real run. The code is complete; the constants are the tuning surface.

---

### Task 1: Types, CSV I/O, and gitignore fix

**Files:**
- Create: `src/keyword-research/types/index.ts`
- Create: `src/keyword-research/io/csv.ts`
- Test: `src/keyword-research/io/csv.test.ts`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `Keyword`, `SerpResult`, `SerpOwnerType`, `Cluster`, `ScoredArticle` types; `toCsv(rows: Record<string, unknown>[]): string`, `fromCsv(text: string): Record<string, string>[]`, `writeCsv(path: string, rows: Record<string, unknown>[]): void`, `readCsv(path: string): Record<string, string>[]`

- [ ] **Step 1: Write the failing test**

Create `src/keyword-research/io/csv.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { toCsv, fromCsv } from './csv';

describe('toCsv', () => {
  it('writes a header row from the first object keys', () => {
    expect(toCsv([{ term: 'algolia pricing', source: 'autocomplete' }]))
      .toBe('term,source\nalgolia pricing,autocomplete');
  });

  it('quotes fields containing commas', () => {
    expect(toCsv([{ term: 'algolia, coveo' }])).toBe('term\n"algolia, coveo"');
  });

  it('escapes embedded double quotes by doubling them', () => {
    expect(toCsv([{ term: 'the "best" search' }])).toBe('term\n"the ""best"" search"');
  });

  it('renders null and undefined as empty fields', () => {
    expect(toCsv([{ a: null, b: undefined }])).toBe('a,b\n,');
  });

  it('returns an empty string for no rows', () => {
    expect(toCsv([])).toBe('');
  });
});

describe('fromCsv', () => {
  it('parses a simple table', () => {
    expect(fromCsv('term,source\nalgolia pricing,autocomplete'))
      .toEqual([{ term: 'algolia pricing', source: 'autocomplete' }]);
  });

  it('parses quoted fields containing commas', () => {
    expect(fromCsv('term\n"algolia, coveo"')).toEqual([{ term: 'algolia, coveo' }]);
  });

  it('parses doubled quotes back into a single quote', () => {
    expect(fromCsv('term\n"the ""best"" search"')).toEqual([{ term: 'the "best" search' }]);
  });

  it('returns an empty array for an empty string', () => {
    expect(fromCsv('')).toEqual([]);
  });

  it('round-trips through toCsv', () => {
    const rows = [{ term: 'a,b', note: 'say "hi"' }];
    expect(fromCsv(toCsv(rows))).toEqual(rows);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/io/csv.test.ts`
Expected: FAIL — `Failed to resolve import "./csv"`

- [ ] **Step 3: Write the types**

Create `src/keyword-research/types/index.ts`:

```typescript
// ---------------------------------------------------------------------------
// Keyword research pipeline types
// ---------------------------------------------------------------------------

export type Track = 'vendor' | 'buyer' | 'practitioner';

/** A single keyword as it moves through the pipeline. */
export interface Keyword {
  term: string;
  seed: string;
  track: Track;
  locale: string;
  /** Set by Stage 4 (Keyword Planner CSV merge). */
  avgMonthlySearches?: number;
  /** Top-of-page bid, high range, in account currency. Stage 4. */
  topOfPageBid?: number;
  /** Set by Stage 5 (GSC join). Current position for findsherpas.com. */
  gscPosition?: number;
  gscImpressions?: number;
}

export type SerpOwnerType =
  | 'vendor-blog'
  | 'vendor-docs'
  | 'listicle'
  | 'forum'
  | 'independent'
  | 'unknown';

export interface SerpResult {
  url: string;
  title: string;
  ownerType: SerpOwnerType;
  wordCount: number;
}

export interface SerpSnapshot {
  term: string;
  results: SerpResult[];
  peopleAlsoAsk: string[];
  /** 0..1. Higher means the SERP is more winnable by an independent voice. */
  weakness: number;
}

export interface Cluster {
  id: string;
  primaryTerm: string;
  terms: string[];
  peopleAlsoAsk: string[];
}

export interface ScoredArticle {
  clusterId: string;
  primaryTerm: string;
  terms: string;
  track: Track;
  score: number;
  avgMonthlySearches: number;
  topOfPageBid: number;
  serpWeakness: number;
  peopleAlsoAsk: string;
}
```

- [ ] **Step 4: Write the CSV implementation**

Create `src/keyword-research/io/csv.ts`:

```typescript
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

function escapeField(value: unknown): string {
  if (value === null || value === undefined) return '';
  const s = String(value);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return '';
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(',')];
  for (const row of rows) {
    lines.push(headers.map((h) => escapeField(row[h])).join(','));
  }
  return lines.join('\n');
}

/** Splits one CSV line, honouring quoted fields and doubled quotes. */
function parseLine(line: string): string[] {
  const out: string[] = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQuotes) {
      if (c === '"') {
        if (line[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') { out.push(field); field = ''; }
    else field += c;
  }
  out.push(field);
  return out;
}

export function fromCsv(text: string): Record<string, string>[] {
  const trimmed = text.trim();
  if (trimmed === '') return [];
  const lines = trimmed.split('\n');
  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseLine(line);
    return Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ''])) as Record<string, string>;
  });
}

export function writeCsv(path: string, rows: Record<string, unknown>[]): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, toCsv(rows), 'utf8');
}

export function readCsv(path: string): Record<string, string>[] {
  return fromCsv(readFileSync(path, 'utf8'));
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/io/csv.test.ts`
Expected: PASS, 10 tests

- [ ] **Step 6: Fix the gitignore CSV trap**

In `.gitignore`, find the line `*.csv` and replace that single line with:

```
*.csv
# Keyword research: ignore intermediate data, keep the final backlog
!src/keyword-research/data/backlog.csv
src/keyword-research/data/
!src/keyword-research/data/backlog.csv
```

- [ ] **Step 7: Verify the gitignore rule works**

Run:
```bash
mkdir -p src/keyword-research/data && touch src/keyword-research/data/stage1.csv src/keyword-research/data/backlog.csv && git status --short src/keyword-research/data/
```
Expected: `?? src/keyword-research/data/backlog.csv` appears, `stage1.csv` does not.

- [ ] **Step 8: Commit**

```bash
git add .gitignore src/keyword-research/types/index.ts src/keyword-research/io/csv.ts src/keyword-research/io/csv.test.ts
git commit -m "Add keyword research types and CSV I/O"
```

---

### Task 2: Stage 0 seeds and Stage 1 autocomplete expansion

**Files:**
- Create: `src/keyword-research/config/seeds.ts`
- Create: `src/keyword-research/expand/autocomplete.ts`
- Test: `src/keyword-research/expand/autocomplete.test.ts`
- Create: `src/keyword-research/scripts/runExpand.ts`
- Modify: `package.json` (scripts section)

**Interfaces:**
- Consumes: `Keyword`, `Track` from `../types`; `writeCsv` from `../io/csv`
- Produces: `SEEDS: { term: string; track: Track }[]`; `buildSuggestUrl(query: string, locale: string): string`; `parseSuggestResponse(body: string): string[]`; `expansionQueries(seed: string): string[]`; `expandSeed(seed, track, locale, fetchFn): Promise<Keyword[]>`

- [ ] **Step 1: Write the failing test**

Create `src/keyword-research/expand/autocomplete.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { buildSuggestUrl, parseSuggestResponse, expansionQueries, expandSeed } from './autocomplete';

describe('buildSuggestUrl', () => {
  it('encodes the query and sets the locale', () => {
    const url = buildSuggestUrl('algolia vs', 'us');
    expect(url).toContain('q=algolia%20vs');
    expect(url).toContain('gl=us');
    expect(url).toContain('client=firefox');
  });
});

describe('parseSuggestResponse', () => {
  it('extracts the suggestion array from the Google response shape', () => {
    const body = JSON.stringify(['algolia', ['algolia pricing', 'algolia alternatives']]);
    expect(parseSuggestResponse(body)).toEqual(['algolia pricing', 'algolia alternatives']);
  });

  it('returns an empty array for malformed JSON rather than throwing', () => {
    expect(parseSuggestResponse('not json')).toEqual([]);
  });

  it('returns an empty array when the suggestion slot is missing', () => {
    expect(parseSuggestResponse(JSON.stringify(['algolia']))).toEqual([]);
  });
});

describe('expansionQueries', () => {
  it('includes the bare seed', () => {
    expect(expansionQueries('algolia')).toContain('algolia');
  });

  it('includes all 26 alphabet-soup variants', () => {
    const qs = expansionQueries('algolia');
    expect(qs).toContain('algolia a');
    expect(qs).toContain('algolia z');
  });

  it('includes intent modifiers', () => {
    const qs = expansionQueries('algolia');
    expect(qs).toContain('algolia vs');
    expect(qs).toContain('algolia alternatives');
    expect(qs).toContain('algolia pricing');
    expect(qs).toContain('best algolia');
    expect(qs).toContain('how algolia');
  });
});

describe('expandSeed', () => {
  it('deduplicates and lowercases suggestions across queries', async () => {
    const fetchFn = async () => JSON.stringify(['x', ['Algolia Pricing', 'algolia pricing']]);
    const out = await expandSeed('algolia', 'vendor', 'us', fetchFn);
    const terms = out.map((k) => k.term);
    expect(terms.filter((t) => t === 'algolia pricing')).toHaveLength(1);
  });

  it('tags every keyword with its seed, track and locale', async () => {
    const fetchFn = async () => JSON.stringify(['x', ['algolia pricing']]);
    const out = await expandSeed('algolia', 'vendor', 'us', fetchFn);
    expect(out[0]).toMatchObject({ seed: 'algolia', track: 'vendor', locale: 'us' });
  });

  it('survives a fetch failure on one query without losing the rest', async () => {
    let n = 0;
    const fetchFn = async () => {
      n++;
      if (n === 1) throw new Error('network');
      return JSON.stringify(['x', ['algolia pricing']]);
    };
    const out = await expandSeed('algolia', 'vendor', 'us', fetchFn);
    expect(out.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/expand/autocomplete.test.ts`
Expected: FAIL — `Failed to resolve import "./autocomplete"`

- [ ] **Step 3: Write the seeds**

Create `src/keyword-research/config/seeds.ts`:

```typescript
import type { Track } from '../types';

/**
 * Stage 0. Hand-curated seeds, tagged by audience track.
 * Adding a seed is cheap; adding a bad seed is expensive, because Stage 2's
 * blocklist has to learn its contamination pattern. See `site search` in the
 * design spec for the canonical example of a poisoned seed.
 */
export const SEEDS: { term: string; track: Track }[] = [
  // Vendor
  { term: 'algolia', track: 'vendor' },
  { term: 'coveo', track: 'vendor' },
  { term: 'bloomreach', track: 'vendor' },
  { term: 'constructor.io', track: 'vendor' },
  { term: 'klevu', track: 'vendor' },
  { term: 'searchspring', track: 'vendor' },
  { term: 'elasticsearch', track: 'vendor' },
  { term: 'opensearch', track: 'vendor' },
  { term: 'typesense', track: 'vendor' },
  { term: 'meilisearch', track: 'vendor' },
  { term: 'attraqt', track: 'vendor' },
  { term: 'lucidworks', track: 'vendor' },
  { term: 'nosto', track: 'vendor' },
  { term: "luigi's box", track: 'vendor' },

  // Buyer
  { term: 'ecommerce search', track: 'buyer' },
  { term: 'product discovery', track: 'buyer' },
  { term: 'zero results', track: 'buyer' },
  { term: 'search conversion', track: 'buyer' },
  { term: 'search merchandising', track: 'buyer' },
  { term: 'site search audit', track: 'buyer' },

  // Practitioner
  { term: 'search relevance', track: 'practitioner' },
  { term: 'query understanding', track: 'practitioner' },
  { term: 'search ranking', track: 'practitioner' },
  { term: 'vector search', track: 'practitioner' },
  { term: 'semantic search', track: 'practitioner' },
  { term: 'search analytics', track: 'practitioner' },
  { term: 'search synonyms', track: 'practitioner' },
  { term: 'faceted search', track: 'practitioner' },
];

/** Locales to expand across. */
export const LOCALES = ['us', 'gb', 'de'];
```

- [ ] **Step 4: Write the autocomplete expander**

Create `src/keyword-research/expand/autocomplete.ts`:

```typescript
import type { Keyword, Track } from '../types';

const ALPHABET = 'abcdefghijklmnopqrstuvwxyz'.split('');
const SUFFIX_MODIFIERS = ['vs', 'alternatives', 'pricing', 'for'];
const PREFIX_MODIFIERS = ['best', 'how', 'why'];

/** Delay between requests. The endpoint is undocumented; do not parallelise. */
const REQUEST_DELAY_MS = 50;

export type FetchFn = (url: string) => Promise<string>;

export function buildSuggestUrl(query: string, locale: string): string {
  const q = encodeURIComponent(query);
  return `https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=${locale}&q=${q}`;
}

export function parseSuggestResponse(body: string): string[] {
  try {
    const parsed = JSON.parse(body);
    const suggestions = parsed?.[1];
    return Array.isArray(suggestions) ? suggestions.filter((s) => typeof s === 'string') : [];
  } catch {
    return [];
  }
}

export function expansionQueries(seed: string): string[] {
  return [
    seed,
    ...ALPHABET.map((c) => `${seed} ${c}`),
    ...SUFFIX_MODIFIERS.map((m) => `${seed} ${m}`),
    ...PREFIX_MODIFIERS.map((m) => `${m} ${seed}`),
  ];
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function defaultFetch(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`suggest request failed: ${res.status}`);
  return res.text();
}

export async function expandSeed(
  seed: string,
  track: Track,
  locale: string,
  fetchFn: FetchFn = defaultFetch,
): Promise<Keyword[]> {
  const seen = new Set<string>();
  const out: Keyword[] = [];

  for (const query of expansionQueries(seed)) {
    let body: string;
    try {
      body = await fetchFn(buildSuggestUrl(query, locale));
    } catch {
      // One failed query must not abort the seed. Skip and continue.
      continue;
    }
    for (const suggestion of parseSuggestResponse(body)) {
      const term = suggestion.toLowerCase().trim();
      if (term === '' || seen.has(term)) continue;
      seen.add(term);
      out.push({ term, seed, track, locale });
    }
    await sleep(REQUEST_DELAY_MS);
  }

  return out;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/expand/autocomplete.test.ts`
Expected: PASS, 9 tests

- [ ] **Step 6: Write the runner script**

Create `src/keyword-research/scripts/runExpand.ts`:

```typescript
import { SEEDS, LOCALES } from '../config/seeds';
import { expandSeed } from '../expand/autocomplete';
import { writeCsv } from '../io/csv';
import type { Keyword } from '../types';

const OUT = 'src/keyword-research/data/stage1-raw.csv';

async function main() {
  const all: Keyword[] = [];
  for (const { term, track } of SEEDS) {
    for (const locale of LOCALES) {
      const got = await expandSeed(term, track, locale);
      console.log(`  ${term} [${locale}] -> ${got.length}`);
      all.push(...got);
    }
  }
  writeCsv(OUT, all as unknown as Record<string, unknown>[]);
  console.log(`\nWrote ${all.length} rows to ${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

- [ ] **Step 7: Add the npm script**

In `package.json`, in the `scripts` object, add after the `crm:update-sequences` entry:

```json
"kw:expand": "tsx src/keyword-research/scripts/runExpand.ts"
```

- [ ] **Step 8: Run the real expansion**

Run: `npm run kw:expand`
Expected: per-seed progress lines, then a total. Expect roughly 5,000–9,000 raw rows across 28 seeds × 3 locales. This takes several minutes — the delay is deliberate.

- [ ] **Step 9: Commit**

```bash
git add src/keyword-research/config/seeds.ts src/keyword-research/expand/ src/keyword-research/scripts/runExpand.ts package.json
git commit -m "Add autocomplete expansion stage for keyword research"
```

---

### Task 3: Stage 2 contamination filter

**Files:**
- Create: `src/keyword-research/filter/contamination.ts`
- Test: `src/keyword-research/filter/contamination.test.ts`
- Create: `src/keyword-research/scripts/runFilter.ts`
- Modify: `package.json`

**Interfaces:**
- Consumes: `Keyword` from `../types`; `readCsv`, `writeCsv` from `../io/csv`
- Produces: `BLOCKLIST_PATTERNS: RegExp[]`; `TOPIC_TOKENS: string[]`; `rejectionReason(term: string): string | null`; `filterKeywords(keywords: Keyword[]): { kept: Keyword[]; rejected: { term: string; reason: string }[] }`

- [ ] **Step 1: Write the failing test**

Create `src/keyword-research/filter/contamination.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { rejectionReason, filterKeywords } from './contamination';
import type { Keyword } from '../types';

const kw = (term: string): Keyword => ({ term, seed: 'test', track: 'vendor', locale: 'us' });

describe('rejectionReason — the site: operator trap', () => {
  it('rejects Google site: operator queries', () => {
    for (const t of ['site search command google', 'site search google dork', 'search q site']) {
      expect(rejectionReason(t)).toBe('SEARCH_OPERATOR');
    }
  });
});

describe('rejectionReason — job board contamination', () => {
  it('rejects job and career queries', () => {
    for (const t of ['best site to search jobs in india', 'job site search engines', 'algolia careers']) {
      expect(rejectionReason(t)).toBe('JOBS');
    }
  });
});

describe('rejectionReason — company trivia', () => {
  it('rejects investor and corporate queries', () => {
    for (const t of ['algolia valuation', 'algolia ceo', 'algolia revenue', 'algolia funding', 'algolia how many employees']) {
      expect(rejectionReason(t)).toBe('CORPORATE');
    }
  });

  it('rejects brand asset queries', () => {
    for (const t of ['algolia logo png', 'algolia logo svg', 'algolia icon']) {
      expect(rejectionReason(t)).toBe('BRAND_ASSET');
    }
  });

  it('rejects navigational queries', () => {
    for (const t of ['algolia login', 'algolia status', 'algolia dashboard login']) {
      expect(rejectionReason(t)).toBe('NAVIGATIONAL');
    }
  });

  it('rejects definition and pronunciation queries', () => {
    for (const t of ['algolia pronunciation', 'alogia meaning in psychiatry']) {
      expect(rejectionReason(t)).toBe('TRIVIA');
    }
  });
});

describe('rejectionReason — topic token requirement', () => {
  it('rejects terms with no topic token at all', () => {
    expect(rejectionReason('premio the best')).toBe('NO_TOPIC_TOKEN');
    expect(rejectionReason('tennessee ecommerce filing search')).not.toBeNull();
  });
});

describe('rejectionReason — keeps the good stuff', () => {
  it('keeps high-intent commercial terms', () => {
    for (const t of [
      'algolia pricing', 'algolia units', 'algolia alternatives',
      'algolia vs elasticsearch', 'algolia query rules', 'algolia typo tolerance',
      'zero results rate', 'ecommerce search relevance', 'search relevance metrics',
    ]) {
      expect(rejectionReason(t)).toBeNull();
    }
  });
});

describe('filterKeywords', () => {
  it('partitions into kept and rejected with reasons', () => {
    const out = filterKeywords([kw('algolia pricing'), kw('algolia careers')]);
    expect(out.kept.map((k) => k.term)).toEqual(['algolia pricing']);
    expect(out.rejected).toEqual([{ term: 'algolia careers', reason: 'JOBS' }]);
  });

  it('deduplicates terms that survive from multiple seeds', () => {
    const out = filterKeywords([kw('algolia pricing'), kw('algolia pricing')]);
    expect(out.kept).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/filter/contamination.test.ts`
Expected: FAIL — `Failed to resolve import "./contamination"`

- [ ] **Step 3: Write the filter**

Create `src/keyword-research/filter/contamination.ts`:

```typescript
import type { Keyword } from '../types';

/**
 * Stage 2. This is the stage that justifies building a script at all.
 *
 * Evidence: the seed `site search` returns 256 autocomplete suggestions, and
 * the majority are the Google `site:` operator or job boards. Without this
 * filter, a naive expander hands that back as a top cluster.
 *
 * Order matters — the first matching rule wins, so specific patterns must
 * precede general ones.
 */
const RULES: { reason: string; pattern: RegExp }[] = [
  { reason: 'SEARCH_OPERATOR', pattern: /\b(dork|operator|command|shortcut|keybind|boolean|extension|chrome|firefox|edge|brave|duckduckgo)\b/ },
  { reason: 'SEARCH_OPERATOR', pattern: /\bsearch q site\b|\bsite search (google|bing|command)\b/ },
  { reason: 'JOBS', pattern: /\b(job|jobs|career|careers|hiring|salary|recruit|vacanc|glassdoor|internship)\b/ },
  { reason: 'CORPORATE', pattern: /\b(valuation|revenue|funding|investor|crunchbase|ipo|stock|market cap|net worth|ceo|founder|headquarters|employees|layoffs|board of directors|acquisition)\b/ },
  { reason: 'BRAND_ASSET', pattern: /\b(logo|icon|png|svg|wallpaper|font)\b/ },
  { reason: 'NAVIGATIONAL', pattern: /\b(login|log in|sign in|dashboard|status|outage|down|support|contact|phone number|address|office)\b/ },
  { reason: 'TRIVIA', pattern: /\b(meaning|pronunciation|pronounce|wiki|wikipedia|que es|ne demek|definition|psychiatry)\b/ },
];

/**
 * A term must contain at least one of these to be plausibly on-topic.
 * Deliberately broad — the blocklist does the precision work.
 */
export const TOPIC_TOKENS = [
  'search', 'relevance', 'ranking', 'query', 'queries', 'index', 'indexing',
  'facet', 'filter', 'synonym', 'autocomplete', 'discovery', 'merchandis',
  'ecommerce', 'e-commerce', 'catalog', 'product', 'zero result', 'no result',
  'algolia', 'coveo', 'bloomreach', 'constructor', 'klevu', 'searchspring',
  'elasticsearch', 'opensearch', 'typesense', 'meilisearch', 'attraqt',
  'lucidworks', 'nosto', 'luigi', 'solr', 'vector', 'semantic', 'embedding',
  'typo', 'relevancy', 'conversion', 'boost',
];

export function rejectionReason(term: string): string | null {
  const t = term.toLowerCase();
  for (const { reason, pattern } of RULES) {
    if (pattern.test(t)) return reason;
  }
  if (!TOPIC_TOKENS.some((tok) => t.includes(tok))) return 'NO_TOPIC_TOKEN';
  return null;
}

export function filterKeywords(keywords: Keyword[]): {
  kept: Keyword[];
  rejected: { term: string; reason: string }[];
} {
  const kept: Keyword[] = [];
  const rejected: { term: string; reason: string }[] = [];
  const seen = new Set<string>();

  for (const k of keywords) {
    if (seen.has(k.term)) continue;
    seen.add(k.term);
    const reason = rejectionReason(k.term);
    if (reason) rejected.push({ term: k.term, reason });
    else kept.push(k);
  }

  return { kept, rejected };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/filter/contamination.test.ts`
Expected: PASS, 9 tests

- [ ] **Step 5: Write the runner script**

Create `src/keyword-research/scripts/runFilter.ts`:

```typescript
import { readCsv, writeCsv } from '../io/csv';
import { filterKeywords } from '../filter/contamination';
import type { Keyword } from '../types';

const IN = 'src/keyword-research/data/stage1-raw.csv';
const OUT = 'src/keyword-research/data/stage2-filtered.csv';
const REJECTS = 'src/keyword-research/data/stage2-rejected.csv';

const rows = readCsv(IN) as unknown as Keyword[];
const { kept, rejected } = filterKeywords(rows);

writeCsv(OUT, kept as unknown as Record<string, unknown>[]);
writeCsv(REJECTS, rejected);

const byReason = new Map<string, number>();
for (const r of rejected) byReason.set(r.reason, (byReason.get(r.reason) ?? 0) + 1);

console.log(`In:  ${rows.length}`);
console.log(`Kept: ${kept.length}`);
console.log(`Rejected: ${rejected.length}`);
for (const [reason, n] of [...byReason].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${reason}: ${n}`);
}
```

- [ ] **Step 6: Add the npm script**

In `package.json` scripts, add after `kw:expand`:

```json
"kw:filter": "tsx src/keyword-research/scripts/runFilter.ts"
```

- [ ] **Step 7: Run it and review the rejects by hand**

Run: `npm run kw:filter`

Then inspect `src/keyword-research/data/stage2-rejected.csv`. **This manual review is a required step, not optional.** You are looking for good keywords wrongly rejected. If you find any, add a narrowing rule and re-run. Expect the filter to remove 70–90% of raw rows.

- [ ] **Step 8: Commit**

```bash
git add src/keyword-research/filter/ src/keyword-research/scripts/runFilter.ts package.json
git commit -m "Add contamination filter for keyword research"
```

---

### Task 4: Stage 3 SERP recon

**Files:**
- Create: `src/keyword-research/serp/ownerClassifier.ts`
- Test: `src/keyword-research/serp/ownerClassifier.test.ts`
- Create: `src/keyword-research/serp/serpRecon.ts`
- Test: `src/keyword-research/serp/serpRecon.test.ts`

**Interfaces:**
- Consumes: `SerpResult`, `SerpOwnerType`, `SerpSnapshot` from `../types`
- Produces: `classifyOwner(url: string): SerpOwnerType`; `serpWeakness(results: SerpResult[]): number`; `buildSnapshot(term, results, peopleAlsoAsk): SerpSnapshot`

- [ ] **Step 1: Write the failing classifier test**

Create `src/keyword-research/serp/ownerClassifier.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { classifyOwner } from './ownerClassifier';

describe('classifyOwner', () => {
  it('identifies vendor docs', () => {
    expect(classifyOwner('https://www.algolia.com/doc/guides/')).toBe('vendor-docs');
    expect(classifyOwner('https://docs.coveo.com/en/123/')).toBe('vendor-docs');
  });

  it('identifies vendor blogs and marketing pages', () => {
    expect(classifyOwner('https://www.algolia.com/blog/ecommerce/')).toBe('vendor-blog');
    expect(classifyOwner('https://www.bloomreach.com/en/products')).toBe('vendor-blog');
  });

  it('identifies forums', () => {
    expect(classifyOwner('https://stackoverflow.com/questions/123')).toBe('forum');
    expect(classifyOwner('https://www.reddit.com/r/algolia/comments/x')).toBe('forum');
    expect(classifyOwner('https://news.ycombinator.com/item?id=1')).toBe('forum');
  });

  it('identifies review-site listicles', () => {
    expect(classifyOwner('https://www.g2.com/products/algolia/reviews')).toBe('listicle');
    expect(classifyOwner('https://www.capterra.com/p/1/algolia/')).toBe('listicle');
  });

  it('treats an unknown independent domain as independent', () => {
    expect(classifyOwner('https://someconsultant.com/algolia-pricing')).toBe('independent');
  });

  it('returns unknown for an unparseable url', () => {
    expect(classifyOwner('not a url')).toBe('unknown');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/serp/ownerClassifier.test.ts`
Expected: FAIL — `Failed to resolve import "./ownerClassifier"`

- [ ] **Step 3: Write the classifier**

Create `src/keyword-research/serp/ownerClassifier.ts`:

```typescript
import type { SerpOwnerType } from '../types';

const VENDOR_DOMAINS = [
  'algolia.com', 'coveo.com', 'bloomreach.com', 'constructor.io', 'klevu.com',
  'searchspring.com', 'elastic.co', 'opensearch.org', 'typesense.org',
  'meilisearch.com', 'attraqt.com', 'lucidworks.com', 'nosto.com',
  'luigisbox.com', 'aws.amazon.com',
];

const FORUM_DOMAINS = [
  'stackoverflow.com', 'reddit.com', 'news.ycombinator.com', 'quora.com',
  'discuss.elastic.co', 'stackexchange.com', 'github.com',
];

const LISTICLE_DOMAINS = [
  'g2.com', 'capterra.com', 'trustradius.com', 'getapp.com',
  'softwareadvice.com', 'sourceforge.net', 'slashdot.org',
];

const DOCS_PATH = /\/(doc|docs|documentation|api|reference|guides?)(\/|$)/;

function hostOf(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

export function classifyOwner(url: string): SerpOwnerType {
  const host = hostOf(url);
  if (host === null) return 'unknown';

  const matches = (list: string[]) => list.some((d) => host === d || host.endsWith(`.${d}`));

  if (matches(FORUM_DOMAINS)) return 'forum';
  if (matches(LISTICLE_DOMAINS)) return 'listicle';
  if (matches(VENDOR_DOMAINS)) {
    let path = '';
    try { path = new URL(url).pathname; } catch { path = ''; }
    return DOCS_PATH.test(path) || host.startsWith('docs.') ? 'vendor-docs' : 'vendor-blog';
  }
  return 'independent';
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/serp/ownerClassifier.test.ts`
Expected: PASS, 6 tests

- [ ] **Step 5: Write the failing weakness test**

Create `src/keyword-research/serp/serpRecon.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { serpWeakness } from './serpRecon';
import type { SerpResult } from '../types';

const r = (ownerType: SerpResult['ownerType'], wordCount = 1000): SerpResult =>
  ({ url: 'https://x.com/a', title: 't', ownerType, wordCount });

describe('serpWeakness', () => {
  it('scores a vendor-only SERP as highly winnable', () => {
    const results = [r('vendor-blog'), r('vendor-blog'), r('vendor-docs'), r('vendor-blog')];
    expect(serpWeakness(results)).toBeGreaterThan(0.7);
  });

  it('scores an independent-incumbent SERP as hard', () => {
    const results = [r('independent', 3000), r('independent', 3000), r('independent', 3000)];
    expect(serpWeakness(results)).toBeLessThan(0.3);
  });

  it('treats thin content as more winnable than deep content', () => {
    const thin = [r('independent', 300), r('independent', 300)];
    const deep = [r('independent', 4000), r('independent', 4000)];
    expect(serpWeakness(thin)).toBeGreaterThan(serpWeakness(deep));
  });

  it('returns 0.5 for an empty SERP rather than dividing by zero', () => {
    expect(serpWeakness([])).toBe(0.5);
  });
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/serp/serpRecon.test.ts`
Expected: FAIL — `Failed to resolve import "./serpRecon"`

- [ ] **Step 7: Write the recon module**

Create `src/keyword-research/serp/serpRecon.ts`:

```typescript
import type { SerpResult, SerpSnapshot } from '../types';

/**
 * How winnable a SERP is for an independent voice, 0..1.
 *
 * A page one owned entirely by vendors marking their own homework is winnable:
 * an honest independent piece has something they structurally cannot publish.
 * A page one of deep independent incumbents is not.
 */
const OWNER_WEAKNESS: Record<SerpResult['ownerType'], number> = {
  'vendor-blog': 0.9,
  'vendor-docs': 0.8,
  listicle: 0.7,
  forum: 0.85,
  independent: 0.15,
  unknown: 0.5,
};

/** Below this word count a result is treated as thin and easier to beat. */
const THIN_WORDS = 800;

export function serpWeakness(results: SerpResult[]): number {
  if (results.length === 0) return 0.5;

  const ownerScore =
    results.reduce((sum, r) => sum + OWNER_WEAKNESS[r.ownerType], 0) / results.length;

  const thinFraction =
    results.filter((r) => r.wordCount < THIN_WORDS).length / results.length;

  // Owner identity dominates; depth is a secondary adjustment.
  const score = ownerScore * 0.75 + thinFraction * 0.25;
  return Math.min(1, Math.max(0, score));
}

export function buildSnapshot(
  term: string,
  results: SerpResult[],
  peopleAlsoAsk: string[],
): SerpSnapshot {
  return { term, results, peopleAlsoAsk, weakness: serpWeakness(results) };
}
```

- [ ] **Step 8: Run both test files to verify they pass**

Run: `npx vitest run src/keyword-research/serp/`
Expected: PASS, 10 tests

- [ ] **Step 9: Commit**

```bash
git add src/keyword-research/serp/
git commit -m "Add SERP owner classification and weakness scoring"
```

---

### Task 5: Stage 4 Keyword Planner emit and ingest

**Files:**
- Create: `src/keyword-research/planner/keywordPlanner.ts`
- Test: `src/keyword-research/planner/keywordPlanner.test.ts`
- Create: `src/keyword-research/scripts/runPlannerEmit.ts`
- Create: `src/keyword-research/scripts/runPlannerMerge.ts`
- Modify: `package.json`

**Interfaces:**
- Consumes: `Keyword` from `../types`; `readCsv`, `writeCsv` from `../io/csv`
- Produces: `batchForPlanner(terms: string[], size?: number): string[][]`; `parseVolumeRange(raw: string): number`; `parsePlannerCsv(rows: Record<string, string>[]): Map<string, { avgMonthlySearches: number; topOfPageBid: number }>`; `mergePlannerData(keywords, plannerData): Keyword[]`

- [ ] **Step 1: Write the failing test**

Create `src/keyword-research/planner/keywordPlanner.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { batchForPlanner, parseVolumeRange, parsePlannerCsv, mergePlannerData } from './keywordPlanner';
import type { Keyword } from '../types';

const kw = (term: string): Keyword => ({ term, seed: 's', track: 'vendor', locale: 'us' });

describe('batchForPlanner', () => {
  it('splits into batches of at most 1000 (the paste limit)', () => {
    const terms = Array.from({ length: 2500 }, (_, i) => `term ${i}`);
    const batches = batchForPlanner(terms);
    expect(batches).toHaveLength(3);
    expect(batches[0]).toHaveLength(1000);
    expect(batches[2]).toHaveLength(500);
  });

  it('returns one batch when under the limit', () => {
    expect(batchForPlanner(['a', 'b'])).toEqual([['a', 'b']]);
  });
});

describe('parseVolumeRange', () => {
  it('parses a bucketed range to its midpoint', () => {
    expect(parseVolumeRange('10 – 100')).toBe(55);
    expect(parseVolumeRange('1K – 10K')).toBe(5500);
  });

  it('parses a plain number', () => {
    expect(parseVolumeRange('320')).toBe(320);
    expect(parseVolumeRange('1,300')).toBe(1300);
  });

  it('returns 0 for missing or unparseable values', () => {
    expect(parseVolumeRange('')).toBe(0);
    expect(parseVolumeRange('—')).toBe(0);
  });
});

describe('parsePlannerCsv', () => {
  it('indexes by lowercased keyword with volume and bid', () => {
    const rows = [{
      'Keyword': 'Algolia Pricing',
      'Avg. monthly searches': '10 – 100',
      'Top of page bid (high range)': '4.50',
    }];
    const map = parsePlannerCsv(rows);
    expect(map.get('algolia pricing')).toEqual({ avgMonthlySearches: 55, topOfPageBid: 4.5 });
  });

  it('ignores rows with no keyword column', () => {
    expect(parsePlannerCsv([{ foo: 'bar' }]).size).toBe(0);
  });
});

describe('mergePlannerData', () => {
  it('attaches volume and bid to matching keywords', () => {
    const map = new Map([['algolia pricing', { avgMonthlySearches: 55, topOfPageBid: 4.5 }]]);
    const out = mergePlannerData([kw('algolia pricing')], map);
    expect(out[0].avgMonthlySearches).toBe(55);
    expect(out[0].topOfPageBid).toBe(4.5);
  });

  it('defaults unmatched keywords to zero rather than dropping them', () => {
    const out = mergePlannerData([kw('algolia units')], new Map());
    expect(out[0].avgMonthlySearches).toBe(0);
    expect(out[0].topOfPageBid).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/planner/keywordPlanner.test.ts`
Expected: FAIL — `Failed to resolve import "./keywordPlanner"`

- [ ] **Step 3: Write the planner module**

Create `src/keyword-research/planner/keywordPlanner.ts`:

```typescript
import type { Keyword } from '../types';

/** Google Keyword Planner's paste limit for Discover-new-keywords. */
const PLANNER_BATCH_SIZE = 1000;

export function batchForPlanner(terms: string[], size = PLANNER_BATCH_SIZE): string[][] {
  const batches: string[][] = [];
  for (let i = 0; i < terms.length; i += size) batches.push(terms.slice(i, i + size));
  return batches;
}

function toNumber(raw: string): number {
  const n = Number(raw.replace(/[,\s]/g, '').replace(/K$/i, '000').replace(/M$/i, '000000'));
  return Number.isFinite(n) ? n : 0;
}

/**
 * On zero-spend Ads accounts Keyword Planner returns bucketed ranges such as
 * "10 – 100" rather than exact volume. Collapse to the midpoint. This is why
 * scoring leans on bid rather than volume — see the design spec.
 */
export function parseVolumeRange(raw: string): number {
  if (!raw || raw.trim() === '') return 0;
  const parts = raw.split(/[–\-—]/).map((p) => p.trim()).filter((p) => p !== '');
  if (parts.length === 2) {
    const lo = toNumber(parts[0]);
    const hi = toNumber(parts[1]);
    if (lo === 0 && hi === 0) return 0;
    return (lo + hi) / 2;
  }
  return toNumber(parts[0] ?? '');
}

const KEYWORD_COLUMNS = ['Keyword', 'Keyword (by relevance)', 'keyword'];
const VOLUME_COLUMNS = ['Avg. monthly searches', 'Avg monthly searches'];
const BID_COLUMNS = ['Top of page bid (high range)', 'Top of page bid (low range)'];

function pick(row: Record<string, string>, candidates: string[]): string {
  for (const c of candidates) if (row[c] !== undefined) return row[c];
  return '';
}

export function parsePlannerCsv(
  rows: Record<string, string>[],
): Map<string, { avgMonthlySearches: number; topOfPageBid: number }> {
  const map = new Map<string, { avgMonthlySearches: number; topOfPageBid: number }>();
  for (const row of rows) {
    const term = pick(row, KEYWORD_COLUMNS).toLowerCase().trim();
    if (term === '') continue;
    map.set(term, {
      avgMonthlySearches: parseVolumeRange(pick(row, VOLUME_COLUMNS)),
      topOfPageBid: toNumber(pick(row, BID_COLUMNS).replace(/[^0-9.]/g, '')),
    });
  }
  return map;
}

export function mergePlannerData(
  keywords: Keyword[],
  plannerData: Map<string, { avgMonthlySearches: number; topOfPageBid: number }>,
): Keyword[] {
  return keywords.map((k) => {
    const hit = plannerData.get(k.term);
    return {
      ...k,
      avgMonthlySearches: hit?.avgMonthlySearches ?? 0,
      topOfPageBid: hit?.topOfPageBid ?? 0,
    };
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/planner/keywordPlanner.test.ts`
Expected: PASS, 9 tests

- [ ] **Step 5: Write the emit script**

Create `src/keyword-research/scripts/runPlannerEmit.ts`:

```typescript
import { writeFileSync, mkdirSync } from 'node:fs';
import { readCsv } from '../io/csv';
import { batchForPlanner } from '../planner/keywordPlanner';
import type { Keyword } from '../types';

const IN = 'src/keyword-research/data/stage2-filtered.csv';
const OUT_DIR = 'src/keyword-research/data/planner';

const terms = (readCsv(IN) as unknown as Keyword[]).map((k) => k.term);
const batches = batchForPlanner(terms);

mkdirSync(OUT_DIR, { recursive: true });
batches.forEach((batch, i) => {
  const path = `${OUT_DIR}/seeds-batch-${i + 1}.txt`;
  writeFileSync(path, batch.join('\n'), 'utf8');
  console.log(`Wrote ${batch.length} terms to ${path}`);
});

console.log(`
Next steps (manual):
  1. Open Google Keyword Planner > Discover new keywords
  2. Paste the contents of each batch file
  3. Download the results as CSV
  4. Save them into ${OUT_DIR}/ as planner-results-*.csv
  5. Run: npm run kw:planner-merge
`);
```

- [ ] **Step 6: Write the merge script**

Create `src/keyword-research/scripts/runPlannerMerge.ts`:

```typescript
import { readdirSync } from 'node:fs';
import { readCsv, writeCsv } from '../io/csv';
import { parsePlannerCsv, mergePlannerData } from '../planner/keywordPlanner';
import type { Keyword } from '../types';

const IN = 'src/keyword-research/data/stage2-filtered.csv';
const PLANNER_DIR = 'src/keyword-research/data/planner';
const OUT = 'src/keyword-research/data/stage4-with-volume.csv';

const keywords = readCsv(IN) as unknown as Keyword[];

const merged = new Map<string, { avgMonthlySearches: number; topOfPageBid: number }>();
const files = readdirSync(PLANNER_DIR).filter((f) => f.startsWith('planner-results') && f.endsWith('.csv'));

if (files.length === 0) {
  console.error(`No planner-results-*.csv found in ${PLANNER_DIR}. Run kw:planner-emit first.`);
  process.exit(1);
}

for (const f of files) {
  // Keyword Planner CSVs carry two preamble lines before the header.
  const raw = readCsv(`${PLANNER_DIR}/${f}`);
  for (const [term, data] of parsePlannerCsv(raw)) merged.set(term, data);
  console.log(`Read ${f}`);
}

const out = mergePlannerData(keywords, merged);
writeCsv(OUT, out as unknown as Record<string, unknown>[]);

const matched = out.filter((k) => (k.topOfPageBid ?? 0) > 0).length;
console.log(`\nWrote ${out.length} rows to ${OUT}`);
console.log(`${matched} have a non-zero top-of-page bid (${Math.round((matched / out.length) * 100)}%)`);
console.log('If that percentage is very low, bid is not a usable signal for this niche —');
console.log('shift scoring weight to SERP weakness in src/keyword-research/score/scoring.ts.');
```

- [ ] **Step 7: Add the npm scripts**

In `package.json` scripts, add after `kw:filter`:

```json
"kw:planner-emit": "tsx src/keyword-research/scripts/runPlannerEmit.ts",
"kw:planner-merge": "tsx src/keyword-research/scripts/runPlannerMerge.ts"
```

- [ ] **Step 8: Verify the emit step runs**

Run: `npm run kw:planner-emit`
Expected: one or more `seeds-batch-N.txt` files plus the manual-steps message.

- [ ] **Step 9: Commit**

```bash
git add src/keyword-research/planner/ src/keyword-research/scripts/runPlanner*.ts package.json
git commit -m "Add Keyword Planner emit and merge stage"
```

---

### Task 6: Stage 5 GSC join

**Files:**
- Create: `src/keyword-research/gsc/gscJoin.ts`
- Test: `src/keyword-research/gsc/gscJoin.test.ts`

**Interfaces:**
- Consumes: `Keyword` from `../types`
- Produces: `parseGscCsv(rows: Record<string, string>[]): Map<string, { position: number; impressions: number }>`; `joinGscData(keywords, gscData): Keyword[]`; `strikingDistance(keywords: Keyword[]): Keyword[]`

- [ ] **Step 1: Write the failing test**

Create `src/keyword-research/gsc/gscJoin.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseGscCsv, joinGscData, strikingDistance } from './gscJoin';
import type { Keyword } from '../types';

const kw = (term: string, extra: Partial<Keyword> = {}): Keyword =>
  ({ term, seed: 's', track: 'vendor', locale: 'us', ...extra });

describe('parseGscCsv', () => {
  it('indexes queries with position and impressions', () => {
    const rows = [{ 'Top queries': 'query interpretation', 'Position': '11', 'Impressions': '24' }];
    const map = parseGscCsv(rows);
    expect(map.get('query interpretation')).toEqual({ position: 11, impressions: 24 });
  });

  it('accepts the alternate Query column name', () => {
    const rows = [{ 'Query': 'search failure', 'Position': '8.3', 'Impressions': '15' }];
    expect(parseGscCsv(rows).get('search failure')?.position).toBe(8.3);
  });

  it('ignores rows with no query', () => {
    expect(parseGscCsv([{ Position: '1' }]).size).toBe(0);
  });
});

describe('joinGscData', () => {
  it('attaches position and impressions when the term is already ranking', () => {
    const map = new Map([['algolia pricing', { position: 12, impressions: 30 }]]);
    const out = joinGscData([kw('algolia pricing')], map);
    expect(out[0].gscPosition).toBe(12);
    expect(out[0].gscImpressions).toBe(30);
  });

  it('leaves non-ranking terms undefined rather than zero', () => {
    const out = joinGscData([kw('algolia units')], new Map());
    expect(out[0].gscPosition).toBeUndefined();
  });
});

describe('strikingDistance', () => {
  it('selects terms ranking between positions 5 and 20 with impressions', () => {
    const out = strikingDistance([
      kw('a', { gscPosition: 12, gscImpressions: 30 }),
      kw('b', { gscPosition: 2, gscImpressions: 30 }),
      kw('c', { gscPosition: 45, gscImpressions: 30 }),
      kw('d', { gscPosition: 12, gscImpressions: 0 }),
      kw('e'),
    ]);
    expect(out.map((k) => k.term)).toEqual(['a']);
  });

  it('sorts by impressions descending so the biggest opportunity leads', () => {
    const out = strikingDistance([
      kw('low', { gscPosition: 10, gscImpressions: 5 }),
      kw('high', { gscPosition: 10, gscImpressions: 500 }),
    ]);
    expect(out[0].term).toBe('high');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/gsc/gscJoin.test.ts`
Expected: FAIL — `Failed to resolve import "./gscJoin"`

- [ ] **Step 3: Write the GSC module**

Create `src/keyword-research/gsc/gscJoin.ts`:

```typescript
import type { Keyword } from '../types';

/**
 * Stage 5. Ingests a Search Console query export rather than building an OAuth
 * flow — same manual-export pattern as Stage 4. Export from
 * Search Console > Performance > Queries > Export > CSV, and save as
 * src/keyword-research/data/gsc-queries.csv.
 *
 * Near-empty for findsherpas.com today (128 impressions, 0 clicks over 90 days).
 * Expected to become the highest-signal input by roughly month three, at which
 * point the striking-distance report should drive more decisions than the
 * autocomplete data.
 */

const QUERY_COLUMNS = ['Top queries', 'Query', 'query'];

function pick(row: Record<string, string>, candidates: string[]): string {
  for (const c of candidates) if (row[c] !== undefined) return row[c];
  return '';
}

export function parseGscCsv(
  rows: Record<string, string>[],
): Map<string, { position: number; impressions: number }> {
  const map = new Map<string, { position: number; impressions: number }>();
  for (const row of rows) {
    const term = pick(row, QUERY_COLUMNS).toLowerCase().trim();
    if (term === '') continue;
    map.set(term, {
      position: Number(row['Position'] ?? row['position'] ?? '0') || 0,
      impressions: Number((row['Impressions'] ?? row['impressions'] ?? '0').replace(/,/g, '')) || 0,
    });
  }
  return map;
}

export function joinGscData(
  keywords: Keyword[],
  gscData: Map<string, { position: number; impressions: number }>,
): Keyword[] {
  return keywords.map((k) => {
    const hit = gscData.get(k.term);
    if (!hit) return k;
    return { ...k, gscPosition: hit.position, gscImpressions: hit.impressions };
  });
}

/** Positions 5-20 with impressions: already visible, close enough to push. */
const MIN_POSITION = 5;
const MAX_POSITION = 20;

export function strikingDistance(keywords: Keyword[]): Keyword[] {
  return keywords
    .filter(
      (k) =>
        k.gscPosition !== undefined &&
        k.gscPosition >= MIN_POSITION &&
        k.gscPosition <= MAX_POSITION &&
        (k.gscImpressions ?? 0) > 0,
    )
    .sort((a, b) => (b.gscImpressions ?? 0) - (a.gscImpressions ?? 0));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/gsc/gscJoin.test.ts`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add src/keyword-research/gsc/
git commit -m "Add GSC join and striking-distance report"
```

---

### Task 7: Stage 6 clustering

**Files:**
- Create: `src/keyword-research/cluster/prefilter.ts`
- Test: `src/keyword-research/cluster/prefilter.test.ts`
- Create: `src/keyword-research/cluster/serpOverlap.ts`
- Test: `src/keyword-research/cluster/serpOverlap.test.ts`

**Interfaces:**
- Consumes: `Keyword`, `Cluster`, `SerpSnapshot` from `../types`
- Produces: `normalizeTerm(term: string): string`; `groupCandidates(keywords: Keyword[]): Keyword[][]`; `sharedUrlCount(a: SerpSnapshot, b: SerpSnapshot): number`; `clusterBySerpOverlap(snapshots: SerpSnapshot[], minShared?: number): Cluster[]`

- [ ] **Step 1: Write the failing prefilter test**

Create `src/keyword-research/cluster/prefilter.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { normalizeTerm, groupCandidates } from './prefilter';
import type { Keyword } from '../types';

const kw = (term: string): Keyword => ({ term, seed: 's', track: 'vendor', locale: 'us' });

describe('normalizeTerm', () => {
  it('strips stopwords and sorts tokens so word order stops mattering', () => {
    expect(normalizeTerm('pricing for algolia')).toBe(normalizeTerm('algolia pricing'));
  });

  it('collapses simple plurals', () => {
    expect(normalizeTerm('algolia alternatives')).toBe(normalizeTerm('algolia alternative'));
  });

  it('keeps genuinely different terms distinct', () => {
    expect(normalizeTerm('algolia pricing')).not.toBe(normalizeTerm('algolia ranking'));
  });
});

describe('groupCandidates', () => {
  it('groups obvious variants together to cut SERP fetch cost', () => {
    const groups = groupCandidates([kw('algolia pricing'), kw('pricing for algolia'), kw('algolia ranking')]);
    expect(groups).toHaveLength(2);
  });

  it('returns one group per keyword when nothing matches', () => {
    expect(groupCandidates([kw('algolia pricing'), kw('coveo ranking')])).toHaveLength(2);
  });

  it('handles an empty input', () => {
    expect(groupCandidates([])).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/cluster/prefilter.test.ts`
Expected: FAIL — `Failed to resolve import "./prefilter"`

- [ ] **Step 3: Write the prefilter**

Create `src/keyword-research/cluster/prefilter.ts`:

```typescript
import type { Keyword } from '../types';

/**
 * Cheap string-similarity pre-filter. Deliberately NOT the final clustering —
 * string similarity gets intent wrong (it splits `algolia cost` from
 * `algolia kosten` and merges terms Google treats separately). Its only job is
 * to collapse obvious variants so Stage 3 fetches fewer SERPs.
 */

const STOPWORDS = new Set([
  'a', 'an', 'the', 'for', 'to', 'of', 'in', 'on', 'is', 'are', 'and', 'or',
  'my', 'your', 'with', 'what', 'how', 'best',
]);

function singularize(token: string): string {
  if (token.endsWith('ies') && token.length > 4) return `${token.slice(0, -3)}y`;
  if (token.endsWith('es') && token.length > 3) return token.slice(0, -2);
  if (token.endsWith('s') && !token.endsWith('ss') && token.length > 3) return token.slice(0, -1);
  return token;
}

export function normalizeTerm(term: string): string {
  return term
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t !== '' && !STOPWORDS.has(t))
    .map(singularize)
    .sort()
    .join(' ');
}

export function groupCandidates(keywords: Keyword[]): Keyword[][] {
  const groups = new Map<string, Keyword[]>();
  for (const k of keywords) {
    const key = normalizeTerm(k.term);
    const existing = groups.get(key);
    if (existing) existing.push(k);
    else groups.set(key, [k]);
  }
  return [...groups.values()];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/cluster/prefilter.test.ts`
Expected: PASS, 6 tests

- [ ] **Step 5: Write the failing SERP-overlap test**

Create `src/keyword-research/cluster/serpOverlap.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { sharedUrlCount, clusterBySerpOverlap } from './serpOverlap';
import type { SerpSnapshot } from '../types';

const snap = (term: string, urls: string[], paa: string[] = []): SerpSnapshot => ({
  term,
  results: urls.map((url) => ({ url, title: 't', ownerType: 'independent' as const, wordCount: 1000 })),
  peopleAlsoAsk: paa,
  weakness: 0.5,
});

describe('sharedUrlCount', () => {
  it('counts URLs present in both SERPs', () => {
    const a = snap('a', ['u1', 'u2', 'u3']);
    const b = snap('b', ['u2', 'u3', 'u4']);
    expect(sharedUrlCount(a, b)).toBe(2);
  });

  it('returns 0 for disjoint SERPs', () => {
    expect(sharedUrlCount(snap('a', ['u1']), snap('b', ['u2']))).toBe(0);
  });
});

describe('clusterBySerpOverlap', () => {
  it('merges terms sharing at least 3 top-10 URLs', () => {
    const clusters = clusterBySerpOverlap([
      snap('algolia pricing', ['u1', 'u2', 'u3', 'u4']),
      snap('algolia cost', ['u1', 'u2', 'u3', 'u9']),
    ]);
    expect(clusters).toHaveLength(1);
    expect(clusters[0].terms).toHaveLength(2);
  });

  it('keeps terms separate below the shared-URL threshold', () => {
    const clusters = clusterBySerpOverlap([
      snap('algolia pricing', ['u1', 'u2', 'u3']),
      snap('algolia ranking', ['u1', 'u8', 'u9']),
    ]);
    expect(clusters).toHaveLength(2);
  });

  it('merges transitively through a shared middle term', () => {
    const clusters = clusterBySerpOverlap([
      snap('a', ['u1', 'u2', 'u3']),
      snap('b', ['u1', 'u2', 'u3']),
      snap('c', ['u1', 'u2', 'u3']),
    ]);
    expect(clusters).toHaveLength(1);
    expect(clusters[0].terms).toHaveLength(3);
  });

  it('picks the shortest term as the cluster primary', () => {
    const clusters = clusterBySerpOverlap([
      snap('algolia pricing explained in detail', ['u1', 'u2', 'u3']),
      snap('algolia pricing', ['u1', 'u2', 'u3']),
    ]);
    expect(clusters[0].primaryTerm).toBe('algolia pricing');
  });

  it('unions People Also Ask across the cluster without duplicates', () => {
    const clusters = clusterBySerpOverlap([
      snap('a', ['u1', 'u2', 'u3'], ['Q1', 'Q2']),
      snap('b', ['u1', 'u2', 'u3'], ['Q2', 'Q3']),
    ]);
    expect(clusters[0].peopleAlsoAsk.sort()).toEqual(['Q1', 'Q2', 'Q3']);
  });

  it('handles an empty input', () => {
    expect(clusterBySerpOverlap([])).toEqual([]);
  });
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/cluster/serpOverlap.test.ts`
Expected: FAIL — `Failed to resolve import "./serpOverlap"`

- [ ] **Step 7: Write the SERP-overlap clustering**

Create `src/keyword-research/cluster/serpOverlap.ts`:

```typescript
import type { Cluster, SerpSnapshot } from '../types';

/**
 * Terms sharing this many top-10 URLs are treated as one article, because
 * Google is already treating them as one intent.
 */
const MIN_SHARED_URLS = 3;

export function sharedUrlCount(a: SerpSnapshot, b: SerpSnapshot): number {
  const urlsB = new Set(b.results.map((r) => r.url));
  return a.results.filter((r) => urlsB.has(r.url)).length;
}

/** Union-find so overlap merges transitively: a~b and b~c puts a, b, c together. */
class DisjointSet {
  private parent: number[];
  constructor(size: number) {
    this.parent = Array.from({ length: size }, (_, i) => i);
  }
  find(i: number): number {
    if (this.parent[i] !== i) this.parent[i] = this.find(this.parent[i]);
    return this.parent[i];
  }
  union(a: number, b: number): void {
    const ra = this.find(a);
    const rb = this.find(b);
    if (ra !== rb) this.parent[rb] = ra;
  }
}

export function clusterBySerpOverlap(
  snapshots: SerpSnapshot[],
  minShared = MIN_SHARED_URLS,
): Cluster[] {
  if (snapshots.length === 0) return [];

  const ds = new DisjointSet(snapshots.length);
  for (let i = 0; i < snapshots.length; i++) {
    for (let j = i + 1; j < snapshots.length; j++) {
      if (sharedUrlCount(snapshots[i], snapshots[j]) >= minShared) ds.union(i, j);
    }
  }

  const byRoot = new Map<number, SerpSnapshot[]>();
  snapshots.forEach((snap, i) => {
    const root = ds.find(i);
    const existing = byRoot.get(root);
    if (existing) existing.push(snap);
    else byRoot.set(root, [snap]);
  });

  return [...byRoot.values()].map((members, i) => {
    // Shortest term is the head term: it is what people actually type.
    const primary = [...members].sort((a, b) => a.term.length - b.term.length)[0];
    const paa = new Set<string>();
    for (const m of members) for (const q of m.peopleAlsoAsk) paa.add(q);
    return {
      id: `c${i + 1}`,
      primaryTerm: primary.term,
      terms: members.map((m) => m.term),
      peopleAlsoAsk: [...paa],
    };
  });
}
```

- [ ] **Step 8: Run both cluster test files**

Run: `npx vitest run src/keyword-research/cluster/`
Expected: PASS, 13 tests

- [ ] **Step 9: Commit**

```bash
git add src/keyword-research/cluster/
git commit -m "Add SERP-overlap clustering with string prefilter"
```

---

### Task 8: Scoring and backlog output

**Files:**
- Create: `src/keyword-research/score/scoring.ts`
- Test: `src/keyword-research/score/scoring.test.ts`

**Interfaces:**
- Consumes: `Keyword`, `Cluster`, `SerpSnapshot`, `ScoredArticle`, `Track` from `../types`
- Produces: `WEIGHTS`; `normalizeBid(bid: number): number`; `normalizeVolume(v: number): number`; `scoreArticle(input): number`; `buildBacklog(clusters, keywordsByTerm, snapshotsByTerm): ScoredArticle[]`

- [ ] **Step 1: Write the failing test**

Create `src/keyword-research/score/scoring.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { normalizeBid, normalizeVolume, scoreArticle, buildBacklog } from './scoring';
import type { Cluster, Keyword, SerpSnapshot } from '../types';

describe('normalizeBid', () => {
  it('maps zero bid to zero', () => {
    expect(normalizeBid(0)).toBe(0);
  });

  it('saturates at the cap so one outlier cannot dominate', () => {
    expect(normalizeBid(1000)).toBe(1);
  });

  it('increases monotonically', () => {
    expect(normalizeBid(5)).toBeGreaterThan(normalizeBid(1));
  });
});

describe('normalizeVolume', () => {
  it('maps zero to zero and saturates at the cap', () => {
    expect(normalizeVolume(0)).toBe(0);
    expect(normalizeVolume(1_000_000)).toBe(1);
  });
});

describe('scoreArticle', () => {
  it('ranks a high-intent weak-SERP term above a low-intent strong-SERP term', () => {
    const good = scoreArticle({ bid: 8, volume: 500, weakness: 0.9, track: 'buyer' });
    const bad = scoreArticle({ bid: 0, volume: 500, weakness: 0.1, track: 'practitioner' });
    expect(good).toBeGreaterThan(bad);
  });

  it('returns a value between 0 and 1', () => {
    const s = scoreArticle({ bid: 8, volume: 500, weakness: 0.9, track: 'buyer' });
    expect(s).toBeGreaterThanOrEqual(0);
    expect(s).toBeLessThanOrEqual(1);
  });

  it('weights the buyer track above the practitioner track, all else equal', () => {
    const buyer = scoreArticle({ bid: 3, volume: 100, weakness: 0.5, track: 'buyer' });
    const prac = scoreArticle({ bid: 3, volume: 100, weakness: 0.5, track: 'practitioner' });
    expect(buyer).toBeGreaterThan(prac);
  });
});

describe('buildBacklog', () => {
  it('produces one row per cluster, sorted by score descending', () => {
    const clusters: Cluster[] = [
      { id: 'c1', primaryTerm: 'algolia units', terms: ['algolia units'], peopleAlsoAsk: ['What is a unit?'] },
      { id: 'c2', primaryTerm: 'search theory', terms: ['search theory'], peopleAlsoAsk: [] },
    ];
    const keywords = new Map<string, Keyword>([
      ['algolia units', { term: 'algolia units', seed: 'algolia', track: 'buyer', locale: 'us', topOfPageBid: 9, avgMonthlySearches: 300 }],
      ['search theory', { term: 'search theory', seed: 'x', track: 'practitioner', locale: 'us', topOfPageBid: 0, avgMonthlySearches: 10 }],
    ]);
    const snapshots = new Map<string, SerpSnapshot>([
      ['algolia units', { term: 'algolia units', results: [], peopleAlsoAsk: [], weakness: 0.9 }],
      ['search theory', { term: 'search theory', results: [], peopleAlsoAsk: [], weakness: 0.1 }],
    ]);

    const backlog = buildBacklog(clusters, keywords, snapshots);
    expect(backlog).toHaveLength(2);
    expect(backlog[0].primaryTerm).toBe('algolia units');
    expect(backlog[0].score).toBeGreaterThan(backlog[1].score);
  });

  it('serialises terms and PAA as pipe-joined strings for the CSV', () => {
    const clusters: Cluster[] = [
      { id: 'c1', primaryTerm: 'a', terms: ['a', 'b'], peopleAlsoAsk: ['Q1', 'Q2'] },
    ];
    const keywords = new Map<string, Keyword>([
      ['a', { term: 'a', seed: 's', track: 'buyer', locale: 'us' }],
    ]);
    const snapshots = new Map<string, SerpSnapshot>();
    const backlog = buildBacklog(clusters, keywords, snapshots);
    expect(backlog[0].terms).toBe('a|b');
    expect(backlog[0].peopleAlsoAsk).toBe('Q1|Q2');
  });

  it('defaults missing keyword and snapshot data without throwing', () => {
    const clusters: Cluster[] = [{ id: 'c1', primaryTerm: 'ghost', terms: ['ghost'], peopleAlsoAsk: [] }];
    const backlog = buildBacklog(clusters, new Map(), new Map());
    expect(backlog[0].score).toBeGreaterThanOrEqual(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/keyword-research/score/scoring.test.ts`
Expected: FAIL — `Failed to resolve import "./scoring"`

- [ ] **Step 3: Write the scoring module**

Create `src/keyword-research/score/scoring.ts`:

```typescript
import type { Cluster, Keyword, ScoredArticle, SerpSnapshot, Track } from '../types';

/**
 * PROVISIONAL WEIGHTS — tune these against the first real run.
 *
 * Bid is weighted above volume deliberately. On zero-spend Ads accounts volume
 * arrives as wide buckets that carry little information at this scale, whereas
 * bid is a direct read on commercial intent.
 *
 * If runPlannerMerge reports that very few terms carry a non-zero bid, that
 * assumption has failed for this niche: move weight from `bid` to `weakness`.
 */
export const WEIGHTS = {
  bid: 0.35,
  weakness: 0.30,
  volume: 0.15,
  track: 0.20,
};

const TRACK_VALUE: Record<Track, number> = {
  buyer: 1.0,
  vendor: 0.8,
  practitioner: 0.5,
};

/** Bids above this are treated as equivalently commercial. */
const BID_CAP = 20;
/** Volumes above this are treated as equivalently large. */
const VOLUME_CAP = 5000;

export function normalizeBid(bid: number): number {
  return Math.min(1, Math.max(0, bid / BID_CAP));
}

export function normalizeVolume(volume: number): number {
  if (volume <= 0) return 0;
  // Log scale: the gap between 10 and 100 matters more than 4000 to 5000.
  return Math.min(1, Math.log10(volume + 1) / Math.log10(VOLUME_CAP + 1));
}

export function scoreArticle(input: {
  bid: number;
  volume: number;
  weakness: number;
  track: Track;
}): number {
  const score =
    normalizeBid(input.bid) * WEIGHTS.bid +
    input.weakness * WEIGHTS.weakness +
    normalizeVolume(input.volume) * WEIGHTS.volume +
    TRACK_VALUE[input.track] * WEIGHTS.track;
  return Math.min(1, Math.max(0, score));
}

export function buildBacklog(
  clusters: Cluster[],
  keywordsByTerm: Map<string, Keyword>,
  snapshotsByTerm: Map<string, SerpSnapshot>,
): ScoredArticle[] {
  return clusters
    .map((cluster) => {
      const kw = keywordsByTerm.get(cluster.primaryTerm);
      const snap = snapshotsByTerm.get(cluster.primaryTerm);

      // A cluster's volume is the sum across its terms; its bid is the max.
      let volume = 0;
      let bid = 0;
      for (const term of cluster.terms) {
        const k = keywordsByTerm.get(term);
        volume += k?.avgMonthlySearches ?? 0;
        bid = Math.max(bid, k?.topOfPageBid ?? 0);
      }

      const track: Track = kw?.track ?? 'practitioner';
      const weakness = snap?.weakness ?? 0.5;

      return {
        clusterId: cluster.id,
        primaryTerm: cluster.primaryTerm,
        terms: cluster.terms.join('|'),
        track,
        score: scoreArticle({ bid, volume, weakness, track }),
        avgMonthlySearches: volume,
        topOfPageBid: bid,
        serpWeakness: weakness,
        peopleAlsoAsk: cluster.peopleAlsoAsk.join('|'),
      };
    })
    .sort((a, b) => b.score - a.score);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/keyword-research/score/scoring.test.ts`
Expected: PASS, 10 tests

- [ ] **Step 5: Run the full suite to confirm nothing regressed**

Run: `npm test`
Expected: PASS — all keyword-research tests plus the pre-existing `lib/crm/outreach-guard.test.ts`, `src/enrichment/providers/waterfall.test.ts`, `src/enrichment/email/emailQuality.test.ts`

- [ ] **Step 6: Commit**

```bash
git add src/keyword-research/score/
git commit -m "Add article scoring and backlog builder"
```

---

### Task 9: Pipeline README

**Files:**
- Create: `src/keyword-research/README.md`

**Interfaces:**
- Consumes: every stage built in Tasks 1-8
- Produces: nothing consumed by code

- [ ] **Step 1: Write the README**

Create `src/keyword-research/README.md`:

````markdown
# Keyword research pipeline

Replaces Ahrefs with free sources. Six stages, each writing a CSV the next
reads, so any stage can be inspected or hand-edited before the next runs.

Design spec: `docs/superpowers/specs/2026-07-31-content-keyword-program-design.md`

## Running it

```bash
npm run kw:expand          # Stage 1: autocomplete expansion (several minutes)
npm run kw:filter          # Stage 2: contamination filter — REVIEW THE REJECTS
npm run kw:planner-emit    # Stage 4a: write batches for Keyword Planner
# ... manual: paste into Keyword Planner, download CSVs into data/planner/
npm run kw:planner-merge   # Stage 4b: merge volume and bid back in
```

## Stages

| Stage | Module | What it does |
|---|---|---|
| 0 | `config/seeds.ts` | Hand-curated seeds tagged by track |
| 1 | `expand/autocomplete.ts` | Google autocomplete, alphabet soup + modifiers |
| 2 | `filter/contamination.ts` | Removes operator/jobs/corporate noise |
| 3 | `serp/` | Classifies who owns page one, scores winnability |
| 4 | `planner/` | Keyword Planner CSV emit and merge |
| 5 | `gsc/` | Search Console join, striking-distance report |
| 6 | `cluster/`, `score/` | Groups by SERP overlap, scores, writes backlog |

## Two things that will bite you

**Seed hygiene.** `site search` returns 256 suggestions, mostly the Google
`site:` operator and job boards. Stage 2 catches it, but a new bad seed brings
a new contamination pattern. **Always read `data/stage2-rejected.csv` after a
run** and check for good keywords wrongly rejected.

**Bid over volume.** On zero-spend Ads accounts, Keyword Planner returns
bucketed ranges (`10 – 100`), so volume is nearly uninformative here. Scoring
leans on top-of-page bid instead. `kw:planner-merge` prints what fraction of
terms carry a non-zero bid — if that is very low, the assumption has failed for
this niche and weight should move from `bid` to `weakness` in
`score/scoring.ts`.

## Manual inputs

Two stages take CSV exports rather than API calls, deliberately — neither is
worth an OAuth build:

- **Stage 4**: Keyword Planner > Discover new keywords > Download
  → `data/planner/planner-results-*.csv`
- **Stage 5**: Search Console > Performance > Queries > Export
  → `data/gsc-queries.csv`

## Scoring weights are provisional

`WEIGHTS` in `score/scoring.ts` is the tuning surface. It was set before any
real run and should be revisited once the first backlog exists.
````

- [ ] **Step 2: Verify every documented npm script exists**

Run: `npm run 2>&1 | grep "kw:"`
Expected: `kw:expand`, `kw:filter`, `kw:planner-emit`, `kw:planner-merge`

- [ ] **Step 3: Commit**

```bash
git add src/keyword-research/README.md
git commit -m "Document keyword research pipeline"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Stage 0 seeds, ~40 tagged by track | Task 2 (28 seeds — trimmed to remove near-duplicates) |
| Stage 1 autocomplete, alphabet soup + modifiers, multi-locale | Task 2 |
| Stage 2 contamination filter | Task 3 |
| Stage 3 SERP recon, owner classification, weakness, PAA | Task 4 |
| Stage 4 Keyword Planner batching and merge, bid over volume | Task 5 |
| Stage 5 GSC join, striking distance | Task 6 |
| Stage 6 clustering: string prefilter then SERP overlap | Task 7 |
| Scoring, backlog.csv one row per article | Task 8 |
| CSV between stages, inspectable | Tasks 1, 3, 5 |

**Known gaps, deliberate:**

1. **No live SERP fetcher.** Task 4 builds and tests the classification and
   scoring logic, but the actual fetch is not wired. Firecrawl rate limits are
   unknown until the filtered term count from Task 3 is real, and the spec
   defers that choice. Wire it after Task 3 has produced a count.
2. **Two-level autocomplete recursion not implemented.** The spec calls for
   re-expanding top suggestions. Level one already yields thousands of terms;
   add level two only if the backlog proves thin.
3. **`runCluster.ts` / `runScore.ts` orchestrator scripts are not included,**
   because they depend on the SERP fetcher from gap 1.

**Type consistency:** verified. `Keyword`, `SerpSnapshot`, `Cluster`,
`ScoredArticle` are defined once in Task 1 and used with matching field names
throughout. `topOfPageBid` and `avgMonthlySearches` are optional on `Keyword`
and defaulted at every read site.
