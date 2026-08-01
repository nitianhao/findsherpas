import type { Cluster, Keyword, ScoredArticle, SerpSnapshot, Track } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 8 (scoring and backlog builder)
//
// Turns keyword clusters into a ranked list of articles to write. Each
// cluster gets a single 0..1 score from four weighted signals: bid, SERP
// weakness, volume, and track. buildBacklog assembles one ScoredArticle row
// per cluster, sorted best-first, ready to hand to the CSV writer.
// ---------------------------------------------------------------------------

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
