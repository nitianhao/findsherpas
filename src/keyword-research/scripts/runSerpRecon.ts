import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { readKeywords } from '../io/keywordRows';
import {
  fetchSerpsSequentially,
  DdgBlockedError,
  DDG_REQUEST_DELAY_MS,
} from '../serp/duckduckgoSerp';
import { CLASSIFIER_VERSION } from '../serp/serpRecon';
import type { SerpSnapshot } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 3 runner (live SERP fetch via DuckDuckGo)
//
// Fetches one SERP per DISTINCT TERM carrying a commercial-intent modifier —
// not per prefilter group. That's deliberate: `cluster/prefilter.ts` only
// collapses ~6.4% of terms and can wrongly merge different intents (see
// "Known limitations" in the README), so the small saving isn't worth the
// risk of losing a term's own SERP data.
//
// Resumable by construction: output is a term -> SerpSnapshot map written to
// disk after every fetch, so a crash, a 429, or a 402 partway through never
// loses more than the single in-flight request. Re-running the script loads
// whatever's already there and only fetches the terms still missing.
// ---------------------------------------------------------------------------

const IN = 'src/keyword-research/data/stage2-filtered.csv';
const OUT = 'src/keyword-research/data/stage3-serps.json';

/** Matched on word boundaries against the lowercased term. */
const COMMERCIAL_MODIFIERS = [
  'vs', 'versus', 'alternative', 'alternatives', 'pricing', 'price', 'cost',
  'costs', 'review', 'reviews', 'compare', 'comparison', 'best', 'competitor',
  'competitors',
];

const MODIFIER_RE = new RegExp(`\\b(${COMMERCIAL_MODIFIERS.join('|')})\\b`, 'i');

export function hasCommercialIntent(term: string): boolean {
  return MODIFIER_RE.test(term);
}

/** Optional `--limit=N` CLI flag, for cheap verification runs. */
/**
 * Parse `--limit=N` or `--limit N`.
 *
 * Throws on anything unrecognised. An earlier version accepted only the `=`
 * form and silently returned undefined for `--limit 3`, which means "no limit"
 * — so a run intended to fetch 3 terms scraped 76 before it was noticed. A
 * mistyped flag must fail loudly, never widen the job.
 */
function parseLimit(argv: string[]): number | undefined {
  if (argv.length === 0) return undefined;

  let raw: string | undefined;
  if (argv[0].startsWith('--limit=')) {
    raw = argv[0].slice('--limit='.length);
    if (argv.length > 1) throw new Error(`Unrecognised arguments: ${argv.slice(1).join(' ')}`);
  } else if (argv[0] === '--limit') {
    raw = argv[1];
    if (raw === undefined) throw new Error('--limit requires a value, e.g. --limit 3');
    if (argv.length > 2) throw new Error(`Unrecognised arguments: ${argv.slice(2).join(' ')}`);
  } else {
    throw new Error(`Unrecognised arguments: ${argv.join(' ')}. Usage: --limit N`);
  }

  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0 || !Number.isInteger(n)) {
    throw new Error(`--limit must be a positive integer, got: ${raw}`);
  }
  return n;
}

/**
 * Load the cache, refusing to resume onto snapshots classified under older
 * rules. ownerType and weakness are frozen at fetch time, and this script skips
 * terms already present — so without this check a classifier change never
 * reaches cached data and a re-run reports "Nothing to do" while the stale
 * values quietly feed clustering and scoring.
 */
function loadExisting(path: string): Record<string, SerpSnapshot> {
  if (!existsSync(path)) return {};
  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    console.warn(`Warning: ${path} exists but is not valid JSON — starting fresh.`);
    return {};
  }

  const isVersioned =
    !!parsed && typeof parsed === 'object' && 'snapshots' in (parsed as object);
  const version = isVersioned
    ? ((parsed as { classifierVersion?: number }).classifierVersion ?? 1)
    : 1;
  const snapshots = isVersioned
    ? (parsed as { snapshots: Record<string, SerpSnapshot> }).snapshots
    : (parsed as Record<string, SerpSnapshot>);

  if (version !== CLASSIFIER_VERSION) {
    throw new Error(
      `${path} was classified under v${version} but the current classifier is ` +
        `v${CLASSIFIER_VERSION}. Its stored ownerType and weakness are stale. ` +
        `Run: npm run kw:reclassify (offline, no refetch), then re-run this.`,
    );
  }

  return snapshots;
}

function save(path: string, data: Record<string, SerpSnapshot>): void {
  mkdirSync(dirname(path), { recursive: true });
  // Always stamp the version so a later classifier change is detected.
  const payload = { classifierVersion: CLASSIFIER_VERSION, snapshots: data };
  writeFileSync(path, JSON.stringify(payload, null, 2), 'utf8');
}

async function main() {
  const limit = parseLimit(process.argv.slice(2));

  const allTerms = readKeywords(IN).map((k) => k.term);
  const distinctCommercialTerms = [...new Set(allTerms.filter(hasCommercialIntent))];

  const results = loadExisting(OUT);
  const alreadyDone = new Set(Object.keys(results));
  let remaining = distinctCommercialTerms.filter((t) => !alreadyDone.has(t));
  if (limit !== undefined) remaining = remaining.slice(0, limit);

  console.log(`Commercial-intent terms: ${distinctCommercialTerms.length}`);
  console.log(`Already fetched: ${alreadyDone.size}`);
  console.log(`To fetch this run: ${remaining.length}`);
  if (remaining.length === 0) {
    console.log('Nothing to do.');
    return;
  }
  console.log(`Estimated time: ~${Math.ceil((remaining.length * DDG_REQUEST_DELAY_MS) / 1000)}s\n`);

  let fetched = 0;
  let stoppedEarly = false;

  try {
    await fetchSerpsSequentially(remaining, (term, snapshot) => {
      results[term] = snapshot;
      fetched++;
      console.log(
        `[${fetched}/${remaining.length}] ${term} -> ${snapshot.results.length} results, weakness=${snapshot.weakness.toFixed(2)}`,
      );
      // Persist after every fetch: at ~2.5s/request a long run takes many
      // minutes and will eventually fail partway (rate limit, quota, network
      // blip). Writing incrementally means a crash never loses more than the
      // single in-flight request, and a re-run resumes from here.
      save(OUT, results);
    });
  } catch (err) {
    if (err instanceof DdgBlockedError) {
      console.error(`\nStopping: ${err.message}`);
      console.error(`Saved ${Object.keys(results).length} snapshots to ${OUT}. Re-run to resume.`);
      stoppedEarly = true;
    } else {
      save(OUT, results);
      throw err;
    }
  }

  console.log(`\nWrote ${Object.keys(results).length} total snapshots to ${OUT}.`);
  if (stoppedEarly) process.exitCode = 1;
}

// Guard so importing this module (e.g. from a test, for `hasCommercialIntent`)
// never triggers a live run — only executing it directly does.
//
// pathToFileURL, not `file://` + the path: this repo lives under a directory
// containing a space, which import.meta.url percent-encodes and naive string
// concatenation does not. That mismatch made this guard silently false, so the
// script did nothing and exited 0 — the worst possible failure mode.
const isMain =
  !!process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
