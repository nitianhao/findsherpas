import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 5 (Search Console join)
//
// Search Console has no zero-config API access worth building an OAuth flow
// for at this stage, so this stage is manual, same pattern as Stage 4: export
// from Search Console > Performance > Queries > Export > CSV, and save as
// src/keyword-research/data/gsc-queries.csv.
//
// Real GSC data for findsherpas.com is near-empty today (128 impressions, 0
// clicks over 90 days). Expected to become the highest-signal input by
// roughly month three, at which point the striking-distance report should
// drive more decisions than the autocomplete data.
// ---------------------------------------------------------------------------

const QUERY_COLUMNS = ['Top queries', 'Query', 'query'];
const POSITION_COLUMNS = ['Position', 'position'];
const IMPRESSIONS_COLUMNS = ['Impressions', 'impressions'];

/**
 * Real Search Console exports, like Keyword Planner exports, are
 * inconsistent about surrounding whitespace in header names. Match candidate
 * column names after trimming both the row's keys and the candidates
 * themselves so a header like `" Position "` still resolves. Mirrors
 * `pick` in ../planner/keywordPlanner.ts rather than inventing a second
 * column-matching pattern.
 */
function pick(row: Record<string, string>, candidates: string[]): string {
  const normalized = new Map<string, string>();
  for (const [key, value] of Object.entries(row)) normalized.set(key.trim(), value);
  for (const c of candidates) {
    const v = normalized.get(c.trim());
    if (v !== undefined) return v;
  }
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
      position: Number(pick(row, POSITION_COLUMNS)) || 0,
      impressions: Number(pick(row, IMPRESSIONS_COLUMNS).replace(/,/g, '')) || 0,
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
