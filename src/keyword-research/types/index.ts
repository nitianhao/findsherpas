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
  /**
   * Page word count, when known. Brave (and most SERP APIs) return only
   * title/url/description — not page body content — so this is genuinely
   * optional rather than a value to estimate from the snippet. See
   * `serpWeakness` in `serp/serpRecon.ts` for how absence is handled.
   */
  wordCount?: number;
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
