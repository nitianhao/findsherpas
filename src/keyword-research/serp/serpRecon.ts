import type { SerpResult, SerpSnapshot } from '../types';

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

  const thinFraction =
    results.filter((r) => r.wordCount < THIN_WORDS).length / results.length;

  // Owner identity sets the level; depth nudges it +/-0.1. Deliberately an
  // adjustment rather than a weighted average — averaging in thinness would
  // cap an all-vendor SERP of deep pages at 0.75, understating how winnable
  // it is. Who owns page one matters more than how long their pages are.
  const score = ownerScore + (thinFraction - 0.5) * 0.2;
  return Math.min(1, Math.max(0, score));
}

export function buildSnapshot(
  term: string,
  results: SerpResult[],
  peopleAlsoAsk: string[],
): SerpSnapshot {
  return { term, results, peopleAlsoAsk, weakness: serpWeakness(results) };
}
