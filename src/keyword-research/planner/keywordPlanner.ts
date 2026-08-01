import { pick, pickOrThrow } from '../io/columns';
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
 * Parse a money cell, tolerating EU formatting.
 *
 * Stripping everything but digits and dots corrupts EU output badly and
 * silently: German/Czech exports render a bid as "1,23", which becomes "123" —
 * a 100x overstatement. Since BID_CAP is 20, normalizeBid then returns 1.0 for
 * every keyword and bid, the heaviest weight in the model, becomes a constant.
 *
 * Comma-as-decimal is detected by shape: a comma with exactly two digits after
 * it and no dot is a decimal separator, not a thousands separator.
 */
export function parseMoney(raw: string): number {
  const cleaned = raw.replace(/[^0-9.,]/g, '').trim();
  if (cleaned === '') return 0;

  const isEuDecimal = /^\d{1,3}(\.\d{3})*,\d{1,2}$/.test(cleaned) || /^\d+,\d{1,2}$/.test(cleaned);
  const normalized = isEuDecimal
    ? cleaned.replace(/\./g, '').replace(',', '.')
    : cleaned.replace(/,/g, '');

  const n = Number(normalized);
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
export function parsePlannerCsv(
  rows: Record<string, string>[],
): Map<string, { avgMonthlySearches: number; topOfPageBid: number }> {
  const map = new Map<string, { avgMonthlySearches: number; topOfPageBid: number }>();
  for (const row of rows) {
    const term = pickOrThrow(row, KEYWORD_COLUMNS, 'keyword').toLowerCase().trim();
    if (term === '') continue;
    map.set(term, {
      avgMonthlySearches: parseVolumeRange(pick(row, VOLUME_COLUMNS)),
      topOfPageBid: parseMoney(pick(row, BID_COLUMNS)),
    });
  }

  // A non-empty export that yields no rows means the columns were not
  // recognised — a localised or restructured file. Failing here beats
  // returning an empty map, which downstream reports as "0% have a bid" and
  // then advises moving scoring weight off bid: the tool arguing you into the
  // wrong conclusion.
  if (rows.length > 0 && map.size === 0) {
    throw new Error(
      `Parsed ${rows.length} rows from the Keyword Planner export but matched none. ` +
        `The keyword column was not recognised. Re-export in English.`,
    );
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
  // idx === 0 means there was no preamble, which is fine. idx === -1 means no
  // header was found anywhere — returning `raw` there would hand the preamble
  // to the CSV parser as the header row and corrupt every column mapping.
  if (idx === 0) return raw;
  if (idx < 0) {
    throw new Error(
      `No Keyword Planner header row found. Looked for a line starting with one of: ` +
        `${KEYWORD_COLUMNS.join(', ')}. Is this a Keyword Planner export, and is it in English?`,
    );
  }
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
