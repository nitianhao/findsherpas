import { readCsv } from './csv';
import type { Keyword, Track } from '../types';

// ---------------------------------------------------------------------------
// The CSV -> Keyword boundary.
//
// `readCsv` returns Record<string, string>: every value is a string, because
// that is what a CSV holds. Casting that straight to Keyword[] type-checks and
// then lies at runtime — `Keyword.avgMonthlySearches: number` is a string, and
// `volume += k.avgMonthlySearches` performs string concatenation. Summing two
// rows of 100 produced "0100100", which `normalizeVolume` then coerced to
// 100100 and pinned at its cap. Nothing threw; the backlog just ranked wrong.
//
// Every read of a keyword CSV must go through here rather than through a cast.
// ---------------------------------------------------------------------------

const TRACKS: Track[] = ['vendor', 'buyer', 'practitioner'];

/** Parses an optional numeric cell. Empty and absent both mean "not set". */
function optionalNumber(raw: string | undefined): number | undefined {
  if (raw === undefined || raw.trim() === '') return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

export function parseKeywordRow(row: Record<string, string>): Keyword {
  const term = (row.term ?? '').trim();
  if (term === '') throw new Error(`Keyword row has no term: ${JSON.stringify(row)}`);

  const rawTrack = (row.track ?? '').trim() as Track;
  // An unrecognised track would silently become the lowest-scoring bucket, so
  // fail instead — a malformed column should not quietly demote every row.
  if (!TRACKS.includes(rawTrack)) {
    throw new Error(`Keyword "${term}" has invalid track "${row.track}". Expected one of ${TRACKS.join(', ')}.`);
  }

  return {
    term,
    seed: (row.seed ?? '').trim(),
    track: rawTrack,
    locale: (row.locale ?? '').trim(),
    avgMonthlySearches: optionalNumber(row.avgMonthlySearches),
    topOfPageBid: optionalNumber(row.topOfPageBid),
    gscPosition: optionalNumber(row.gscPosition),
    gscImpressions: optionalNumber(row.gscImpressions),
  };
}

/** Read a keyword CSV with numeric fields actually numeric. */
export function readKeywords(path: string): Keyword[] {
  return readCsv(path).map(parseKeywordRow);
}
