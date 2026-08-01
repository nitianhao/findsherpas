import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 4 (Google Keyword Planner bridge)
//
// Google Keyword Planner has no API access for a zero-spend account, so this
// stage is manual: batch keywords for paste into "Discover new keywords",
// then merge the downloaded CSV back in to attach search volume and
// top-of-page bid.
// ---------------------------------------------------------------------------

/** Google Keyword Planner's paste limit for Discover-new-keywords. */
const PLANNER_BATCH_SIZE = 1000;

export function batchForPlanner(terms: string[], size = PLANNER_BATCH_SIZE): string[][] {
  const batches: string[][] = [];
  for (let i = 0; i < terms.length; i += size) batches.push(terms.slice(i, i + size));
  return batches;
}

function toNumber(raw: string): number {
  const n = Number(raw.replace(/[,\s]/g, '').replace(/K$/i, '000').replace(/M$/i, '000000'));
  return Number.isFinite(n) ? n : 0;
}

/**
 * On zero-spend Ads accounts Keyword Planner returns bucketed ranges such as
 * "10 – 100" rather than exact volume. Collapse to the midpoint. The dash
 * between the bounds can be an en dash (–), an em dash (—), or a plain
 * hyphen (-) depending on locale/export, so all three are accepted. This
 * bucketing is also why scoring leans on bid rather than volume — see the
 * design spec.
 */
export function parseVolumeRange(raw: string): number {
  if (!raw || raw.trim() === '') return 0;
  const parts = raw.split(/[–—-]/).map((p) => p.trim()).filter((p) => p !== '');
  if (parts.length === 2) {
    const lo = toNumber(parts[0]);
    const hi = toNumber(parts[1]);
    if (lo === 0 && hi === 0) return 0;
    return (lo + hi) / 2;
  }
  return toNumber(parts[0] ?? '');
}

const KEYWORD_COLUMNS = ['Keyword', 'Keyword (by relevance)', 'keyword'];
const VOLUME_COLUMNS = ['Avg. monthly searches', 'Avg monthly searches'];
const BID_COLUMNS = ['Top of page bid (high range)', 'Top of page bid (low range)'];

/**
 * Real Keyword Planner exports are inconsistent about surrounding whitespace
 * in header names (and about a trailing preamble before the real header
 * row — see runPlannerMerge.ts). Match candidate column names after
 * trimming both the row's keys and the candidates themselves so a header
 * like `" Keyword "` still resolves.
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

export function parsePlannerCsv(
  rows: Record<string, string>[],
): Map<string, { avgMonthlySearches: number; topOfPageBid: number }> {
  const map = new Map<string, { avgMonthlySearches: number; topOfPageBid: number }>();
  for (const row of rows) {
    const term = pick(row, KEYWORD_COLUMNS).toLowerCase().trim();
    if (term === '') continue;
    map.set(term, {
      avgMonthlySearches: parseVolumeRange(pick(row, VOLUME_COLUMNS)),
      topOfPageBid: toNumber(pick(row, BID_COLUMNS).replace(/[^0-9.]/g, '')),
    });
  }
  return map;
}

/**
 * Real Keyword Planner CSV exports carry a few preamble lines (report
 * title, date range, location) before the actual header row, and are
 * CRLF-terminated. `readCsv`/`fromCsv` always treat the first row as the
 * header, so feeding a raw export straight in would misparse everything:
 * the preamble becomes the "header" and the real header row becomes a
 * garbage data row. Strip everything up to the line whose first field is
 * a recognized keyword-column name before handing off to `fromCsv`. If no
 * such line is found, the input is returned unchanged so a differently
 * shaped export still gets a parse attempt rather than being silently
 * emptied.
 */
export function stripPlannerPreamble(raw: string): string {
  const lines = raw.split(/\r\n|\n/);
  const idx = lines.findIndex((line) => {
    const first = line.split(',')[0]?.trim().replace(/^"|"$/g, '').toLowerCase();
    return KEYWORD_COLUMNS.some((c) => c.toLowerCase() === first);
  });
  if (idx <= 0) return raw;
  return lines.slice(idx).join('\r\n');
}

export function mergePlannerData(
  keywords: Keyword[],
  plannerData: Map<string, { avgMonthlySearches: number; topOfPageBid: number }>,
): Keyword[] {
  return keywords.map((k) => {
    const hit = plannerData.get(k.term);
    return {
      ...k,
      avgMonthlySearches: hit?.avgMonthlySearches ?? 0,
      topOfPageBid: hit?.topOfPageBid ?? 0,
    };
  });
}
