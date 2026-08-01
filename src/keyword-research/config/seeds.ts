import type { Track } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 0 seed keywords
// ---------------------------------------------------------------------------

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
/**
 * Locales to expand across.
 *
 * Deliberately just `us`. The plan originally specified ['us','gb','de'], but a
 * full measured run showed all three return an identical 5,155-term set — the
 * union across all three is 5,157, so gb and de together contributed 2 terms,
 * both German grammar fragments that Stage 2 filters anyway.
 *
 * Root cause: `buildSuggestUrl` sends `hl=en`. For this endpoint the host
 * language (`hl`) dominates and the geo parameter (`gl`) barely moves results,
 * so varying `gl` alone was never going to surface non-English suggestions.
 *
 * To genuinely target DACH later, vary `hl` (e.g. `hl=de&gl=de`) rather than
 * adding entries here — and expect to write German articles to match.
 */
export const LOCALES = ['us'];
