import type { Keyword, Track } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 1 autocomplete expansion
// ---------------------------------------------------------------------------

const ALPHABET = 'abcdefghijklmnopqrstuvwxyz'.split('');
const SUFFIX_MODIFIERS = ['vs', 'alternatives', 'pricing', 'for'];
const PREFIX_MODIFIERS = ['best', 'how', 'why'];

/** Delay between requests. The endpoint is undocumented; do not parallelise. */
export const REQUEST_DELAY_MS = 50;

/**
 * Mutable counter a caller can pass to `expandSeed` to observe how many of
 * the seed's queries failed. A fully-failed seed returns `[]`, which is
 * otherwise indistinguishable from the endpoint legitimately having no
 * suggestions -- this is how a caller (e.g. the runner script) tells the
 * difference and detects an outage or IP block.
 */
export interface ExpandStats {
  failures: number;
}

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
  stats?: ExpandStats,
): Promise<Keyword[]> {
  const seen = new Set<string>();
  const out: Keyword[] = [];

  for (const query of expansionQueries(seed)) {
    let body: string | undefined;
    try {
      body = await fetchFn(buildSuggestUrl(query, locale));
    } catch (err) {
      // One failed query must not abort the seed, but a failure is the
      // leading indicator of the exact condition the delay exists to
      // prevent (e.g. a soft IP block starting mid-run). Count it and log
      // it so an outage is detectable instead of silently looking like an
      // empty result, and let the `finally` below pay the delay exactly as
      // it would on success -- the delay must never be skippable via this
      // path.
      if (stats) stats.failures++;
      console.error(`[autocomplete] request failed for "${query}" [${locale}]:`, err);
    } finally {
      await sleep(REQUEST_DELAY_MS);
    }
    if (body === undefined) continue;
    for (const suggestion of parseSuggestResponse(body)) {
      const term = suggestion.toLowerCase().trim();
      if (term === '' || seen.has(term)) continue;
      seen.add(term);
      out.push({ term, seed, track, locale });
    }
  }

  return out;
}
