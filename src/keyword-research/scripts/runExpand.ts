import { SEEDS, LOCALES } from '../config/seeds';
import { expandSeed, type ExpandStats } from '../expand/autocomplete';
import { writeCsv } from '../io/csv';
import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Keyword research pipeline - Stage 1 runner (autocomplete expansion)
// ---------------------------------------------------------------------------

const OUT = 'src/keyword-research/data/stage1-raw.csv';

async function main() {
  const all: Keyword[] = [];
  let totalFailures = 0;
  for (const { term, track } of SEEDS) {
    for (const locale of LOCALES) {
      const stats: ExpandStats = { failures: 0 };
      const got = await expandSeed(term, track, locale, undefined, stats);
      // Surface failures alongside the count: a fully-failed seed returns
      // an empty array that looks identical to a legitimate zero-result
      // query, so the failure count is what makes an outage (e.g. a soft
      // IP block) visible in the run log instead of silently blending in.
      console.log(`  ${term} [${locale}] -> ${got.length} (${stats.failures} failures)`);
      totalFailures += stats.failures;
      all.push(...got);
    }
  }
  writeCsv(OUT, all as unknown as Record<string, unknown>[]);
  console.log(`\nWrote ${all.length} rows to ${OUT} (${totalFailures} total failures)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
