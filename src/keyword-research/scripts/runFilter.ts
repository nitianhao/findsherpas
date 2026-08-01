import { writeCsv } from '../io/csv';
import { readKeywords } from '../io/keywordRows';
import { filterKeywords } from '../filter/contamination';
import type { Keyword } from '../types';

const IN = 'src/keyword-research/data/stage1-raw.csv';
const OUT = 'src/keyword-research/data/stage2-filtered.csv';
const REJECTS = 'src/keyword-research/data/stage2-rejected.csv';

const rows = readKeywords(IN);
const { kept, rejected } = filterKeywords(rows);

writeCsv(OUT, kept as unknown as Record<string, unknown>[]);
writeCsv(REJECTS, rejected);

const byReason = new Map<string, number>();
for (const r of rejected) byReason.set(r.reason, (byReason.get(r.reason) ?? 0) + 1);

console.log(`In:  ${rows.length}`);
console.log(`Kept: ${kept.length}`);
console.log(`Rejected: ${rejected.length}`);
for (const [reason, n] of [...byReason].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${reason}: ${n}`);
}
