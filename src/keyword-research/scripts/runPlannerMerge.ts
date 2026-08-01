import { readdirSync, readFileSync } from 'node:fs';
import { readCsv, writeCsv, fromCsv } from '../io/csv';
import { parsePlannerCsv, mergePlannerData, stripPlannerPreamble } from '../planner/keywordPlanner';
import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 4 runner (Keyword Planner CSV merge)
// ---------------------------------------------------------------------------

const IN = 'src/keyword-research/data/stage2-filtered.csv';
const PLANNER_DIR = 'src/keyword-research/data/planner';
const OUT = 'src/keyword-research/data/stage4-with-volume.csv';

const keywords = readCsv(IN) as unknown as Keyword[];

const merged = new Map<string, { avgMonthlySearches: number; topOfPageBid: number }>();
const files = readdirSync(PLANNER_DIR).filter((f) => f.startsWith('planner-results') && f.endsWith('.csv'));

if (files.length === 0) {
  console.error(`No planner-results-*.csv found in ${PLANNER_DIR}. Run kw:planner-emit first.`);
  process.exit(1);
}

for (const f of files) {
  // Keyword Planner CSVs carry preamble lines (report title, date range,
  // location) before the real header row, and are CRLF-terminated.
  // `readCsv` always treats the first row as the header, so the preamble
  // must be stripped first or the whole file misparses.
  const text = readFileSync(`${PLANNER_DIR}/${f}`, 'utf8');
  const rows = fromCsv(stripPlannerPreamble(text));
  for (const [term, data] of parsePlannerCsv(rows)) merged.set(term, data);
  console.log(`Read ${f}`);
}

const out = mergePlannerData(keywords, merged);
writeCsv(OUT, out as unknown as Record<string, unknown>[]);

const matched = out.filter((k) => (k.topOfPageBid ?? 0) > 0).length;
console.log(`\nWrote ${out.length} rows to ${OUT}`);
console.log(`${matched} have a non-zero top-of-page bid (${Math.round((matched / out.length) * 100)}%)`);
console.log('If that percentage is very low, bid is not a usable signal for this niche —');
console.log('shift scoring weight to SERP weakness in src/keyword-research/score/scoring.ts.');
