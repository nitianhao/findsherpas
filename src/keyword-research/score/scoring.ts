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

/**
 * Observed bounds of `serpWeakness` on real data, used to rescale it.
 *
 * Weakness is nominally 0..1 but does not use that range in practice. Measured
 * across 82 real SERPs: min 0.520, median 0.640, max 0.850 — a span of 0.33.
 * Fed in raw it contributed at most 0.33 x 0.30 = 0.099 of score spread, while
 * bid contributed up to 1.0 x 0.35 = 0.35. That made the most actionable signal
 * the weakest discriminator, purely as an artifact of the range it occupies.
 *
 * Rescaling restores the discriminating power the weight implies, and makes
 * weakness symmetric with bid and volume, which were already normalized.
 * Revisit these bounds when the SERP set grows — they are measured, not
 * theoretical.
 */
const WEAKNESS_OBSERVED_MIN = 0.5;
const WEAKNESS_OBSERVED_MAX = 0.85;

export function normalizeWeakness(weakness: number): number {
  const span = WEAKNESS_OBSERVED_MAX - WEAKNESS_OBSERVED_MIN;
  return Math.min(1, Math.max(0, (weakness - WEAKNESS_OBSERVED_MIN) / span));
}

export function scoreArticle(input: {
  bid: number;
  volume: number;
  weakness: number;
  track: Track;
}): number {
  const score =
    normalizeBid(input.bid) * WEIGHTS.bid +
    normalizeWeakness(input.weakness) * WEIGHTS.weakness +
    normalizeVolume(input.volume) * WEIGHTS.volume +
    TRACK_VALUE[input.track] * WEIGHTS.track;
  return Math.min(1, Math.max(0, score));
}

/**
 * Queries that name a platform are asking for that platform's content, and no
 * article can win them. `algolia pricing reddit` returns a 10/10 forum SERP,
 * which serpWeakness correctly reads as "easy to displace" — but the user wants
 * Reddit, and Reddit is the right answer. Left in, these rank top precisely
 * because they are unwinnable.
 *
 * They remain useful demand evidence (people explicitly seeking non-vendor
 * opinion on pricing), which is why they are excluded from the backlog rather
 * than dropped from the pipeline.
 */
const PLATFORM_QUALIFIERS = /\b(reddit|quora|youtube|linkedin|twitter|hacker\s*news|stackoverflow|github)\b/i;

export function isPlatformQualifiedQuery(term: string): boolean {
  return PLATFORM_QUALIFIERS.test(term);
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

      // Whether this row rests on real data or on defaults. A cluster missing
      // both lookups still scores mid-table, and in the output CSV that is
      // otherwise indistinguishable from a genuinely researched thin topic —
      // so a data-join gap can outrank real signal. Surfacing it as its own
      // column lets a reader filter those rows out without distorting the
      // score formula or the provisional weights.
      const hasData = kw !== undefined && snap !== undefined;

      return {
        clusterId: cluster.id,
        primaryTerm: cluster.primaryTerm,
        terms: cluster.terms.join('|'),
        track,
        score: scoreArticle({ bid, volume, weakness, track }),
        avgMonthlySearches: volume,
        topOfPageBid: bid,
        serpWeakness: weakness,
        hasData,
        peopleAlsoAsk: cluster.peopleAlsoAsk.join('|'),
      };
    })
    .sort((a, b) => b.score - a.score);
}
