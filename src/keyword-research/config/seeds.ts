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
export const LOCALES = ['us', 'gb', 'de'];
