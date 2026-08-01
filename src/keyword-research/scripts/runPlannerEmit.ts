import { writeFileSync, mkdirSync } from 'node:fs';
import { readKeywords } from '../io/keywordRows';
import { batchForPlanner } from '../planner/keywordPlanner';
import type { Keyword } from '../types';
import { pathToFileURL } from 'node:url';

function main() {

  // ---------------------------------------------------------------------------
  // Keyword research pipeline - Stage 4 runner (Keyword Planner batch emit)
  // ---------------------------------------------------------------------------

  const IN = 'src/keyword-research/data/stage2-filtered.csv';
  const OUT_DIR = 'src/keyword-research/data/planner';

  const terms = readKeywords(IN).map((k) => k.term);
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
}

// Guard so importing this module never triggers a live run. pathToFileURL, not
// a hand-built file:// string: this repo path contains a space, which
// import.meta.url percent-encodes and concatenation does not — that mismatch
// silently disabled an earlier guard and made a script a no-op that exited 0.
const isMain = !!process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
