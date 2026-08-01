import { writeCsv } from '../io/csv';
import { readKeywords } from '../io/keywordRows';
import { filterKeywords, rejectionReason } from '../filter/contamination';
import { SEEDS } from '../config/seeds';
import { pathToFileURL } from 'node:url';

function main() {

  const IN = 'src/keyword-research/data/stage1-raw.csv';
  const OUT = 'src/keyword-research/data/stage2-filtered.csv';
  const REJECTS = 'src/keyword-research/data/stage2-rejected.csv';

  // A seed whose own term the filter rejects contributes nothing: all ~35 of its
  // expansions are dropped as NO_TOPIC_TOKEN, and the histogram still looks
  // healthy. TOPIC_TOKENS is coupled to SEEDS with nothing enforcing it, so
  // check the invariant loudly rather than relying on someone reading the rejects.
  const badSeeds = SEEDS.map((s) => ({ term: s.term, reason: rejectionReason(s.term) })).filter((s) => s.reason !== null);
  if (badSeeds.length > 0) {
    console.error('These seeds are rejected by the filter, so they contribute nothing:');
    for (const b of badSeeds) console.error(`  ${b.term} -> ${b.reason}`);
    console.error('Add the seed\u2019s topic token to TOPIC_TOKENS in filter/contamination.ts.');
    process.exit(1);
  }

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
}

// Guard so importing this module never triggers a live run. pathToFileURL, not
// a hand-built file:// string: this repo path contains a space, which
// import.meta.url percent-encodes and concatenation does not — that mismatch
// silently disabled an earlier guard and made a script a no-op that exited 0.
const isMain = !!process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
