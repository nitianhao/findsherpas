import type { SerpResult, SerpSnapshot } from '../types';
import { classifyOwner } from './ownerClassifier';

// ---------------------------------------------------------------------------
// Stage 3: SERP recon
//
// Scores how winnable a SERP is for an independent voice (0..1, higher is
// more winnable), and assembles the SerpSnapshot the rest of the pipeline
// consumes. This module is scoring logic only — no fetching. The live SERP
// fetch (Firecrawl or otherwise) is a separate task.
// ---------------------------------------------------------------------------

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

  // Page depth is only known when the fetcher can retrieve full page content
  // (e.g. a crawler that renders the body). Brave and most SERP APIs return
  // just title/url/description, so `wordCount` is frequently absent — and a
  // description is not a stand-in for it; estimating depth from snippet
  // length would fabricate a signal the source data doesn't provide. When
  // NO result carries a known word count, skip the thinness adjustment
  // entirely rather than silently treating "unknown" as "not thin" (which
  // dividing by results.length would otherwise do). When SOME results carry
  // a known word count, compute thinFraction only over that known subset so
  // the unknown ones don't dilute or bias the signal either way.
  const known = results.filter((r) => r.wordCount !== undefined);
  if (known.length === 0) return Math.min(1, Math.max(0, ownerScore));

  const thinFraction =
    known.filter((r) => (r.wordCount as number) < THIN_WORDS).length / known.length;

  // Owner identity sets the level; depth nudges it +/-0.1. Deliberately an
  // adjustment rather than a weighted average — averaging in thinness would
  // cap an all-vendor SERP of deep pages at 0.75, understating how winnable
  // it is. Who owns page one matters more than how long their pages are.
  const score = ownerScore + (thinFraction - 0.5) * 0.2;
  return Math.min(1, Math.max(0, score));
}

/**
 * Bump when classifyOwner's rules or serpWeakness's formula change. Stored
 * snapshots carry the version they were computed under, so a stale cache is
 * detected instead of silently reused.
 *
 * Why this exists: ownerType and weakness are computed at fetch time and
 * frozen into stage3-serps.json. A later classifier fix corrected 64.5% of
 * stored classifications in code — but the cached file kept the old values,
 * and the fetcher skips terms already present, so re-running printed
 * "Nothing to do" and exited 0. The fix was inert against the only data that
 * existed.
 */
export const CLASSIFIER_VERSION = 2;

/**
 * Recompute ownerType and weakness for a stored snapshot using today's rules.
 * Pure and offline — the URLs are already on disk, so no refetch is needed.
 */
export function reclassifySnapshot(snapshot: SerpSnapshot): SerpSnapshot {
  const results = snapshot.results.map((r) => ({ ...r, ownerType: classifyOwner(r.url) }));
  return { ...snapshot, results, weakness: serpWeakness(results) };
}

export function buildSnapshot(
  term: string,
  results: SerpResult[],
  peopleAlsoAsk: string[],
): SerpSnapshot {
  return { term, results, peopleAlsoAsk, weakness: serpWeakness(results) };
}
