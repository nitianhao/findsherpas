import { writeFileSync, mkdirSync } from 'node:fs';
import { readCsv } from '../io/csv';
import { batchForPlanner } from '../planner/keywordPlanner';
import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 4 runner (Keyword Planner batch emit)
// ---------------------------------------------------------------------------

const IN = 'src/keyword-research/data/stage2-filtered.csv';
const OUT_DIR = 'src/keyword-research/data/planner';

const terms = (readCsv(IN) as unknown as Keyword[]).map((k) => k.term);
const batches = batchForPlanner(terms);

mkdirSync(OUT_DIR, { recursive: true });
batches.forEach((batch, i) => {
  const path = `${OUT_DIR}/seeds-batch-${i + 1}.txt`;
  writeFileSync(path, batch.join('\n'), 'utf8');
  console.log(`Wrote ${batch.length} terms to ${path}`);
});

console.log(`
Next steps (manual):
  1. Open Google Keyword Planner > Discover new keywords
  2. Paste the contents of each batch file
  3. Download the results as CSV
  4. Save them into ${OUT_DIR}/ as planner-results-*.csv
  5. Run: npm run kw:planner-merge
`);
