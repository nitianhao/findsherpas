import { writeFileSync, mkdirSync } from 'node:fs';
import { readKeywords } from '../io/keywordRows';
import { batchForPlanner } from '../planner/keywordPlanner';
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
    1. ads.google.com > Tools (spanner icon) > Planning > Keyword Planner
    2. Choose "Get search volume and forecasts".
       NOT "Discover new keywords" — that treats your input as seeds and
       returns different keywords. You want metrics for exactly this list.
    3. Paste one batch file's contents (or upload the .txt). Get started.
    4. Open the "Historical metrics" tab — it lands on "Forecasts" first.
    5. Set the date range to the last 12 months.
    6. Download > .csv into ${OUT_DIR}/ as planner-results-1.csv (etc)
    7. Repeat per batch, then run: npm run kw:planner-merge

    Export in ENGLISH. A localised export now throws rather than silently
    producing an all-zero merge.
  `);
}

// Guard so importing this module never triggers a live run. pathToFileURL, not
// a hand-built file:// string: this repo path contains a space, which
// import.meta.url percent-encodes and concatenation does not — that mismatch
// silently disabled an earlier guard and made a script a no-op that exited 0.
const isMain = !!process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
