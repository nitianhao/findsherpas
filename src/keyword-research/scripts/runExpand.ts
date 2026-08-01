import { SEEDS, LOCALES } from '../config/seeds';
import { expandSeed } from '../expand/autocomplete';
import { writeCsv } from '../io/csv';
import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 1 runner (autocomplete expansion)
// ---------------------------------------------------------------------------

const OUT = 'src/keyword-research/data/stage1-raw.csv';

async function main() {
  const all: Keyword[] = [];
  for (const { term, track } of SEEDS) {
    for (const locale of LOCALES) {
      const got = await expandSeed(term, track, locale);
      console.log(`  ${term} [${locale}] -> ${got.length}`);
      all.push(...got);
    }
  }
  writeCsv(OUT, all as unknown as Record<string, unknown>[]);
  console.log(`\nWrote ${all.length} rows to ${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
