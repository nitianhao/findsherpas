import { existsSync, readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

import { writeCsv } from '../io/csv';
import { readKeywords } from '../io/keywordRows';
import { clusterBySerpOverlap } from '../cluster/serpOverlap';
import { buildBacklog, isPlatformQualifiedQuery } from '../score/scoring';
import { CLASSIFIER_VERSION } from '../serp/serpRecon';
import type { Keyword, SerpSnapshot } from '../types';

// ---------------------------------------------------------------------------
// Stage 6 runner: cluster the fetched SERPs, score each cluster, write the
// article backlog.
//
// This is the stage that turns research into a to-do list, so it errs toward
// refusing to produce output it cannot stand behind: a stale SERP cache is
// fatal rather than silently ranked, and rows resting on defaults are flagged
// in their own column rather than blending into the ranking.
// ---------------------------------------------------------------------------

const KEYWORDS_IN = 'src/keyword-research/data/stage2-filtered.csv';
const SERPS_IN = 'src/keyword-research/data/stage3-serps.json';
const OUT = 'src/keyword-research/data/backlog.csv';

interface Cache {
  classifierVersion?: number;
  snapshots: Record<string, SerpSnapshot>;
}

/**
 * Load the SERP cache, refusing a version mismatch.
 *
 * ownerType and weakness are frozen at fetch time. Ranking on values computed
 * under superseded rules is exactly the failure this pipeline already shipped
 * once — a classifier fix that never reached the cached data.
 */
export function loadSerps(path: string): Record<string, SerpSnapshot> {
  const parsed = JSON.parse(readFileSync(path, 'utf8')) as unknown;
  const isVersioned =
    !!parsed && typeof parsed === 'object' && 'snapshots' in (parsed as object);
  const version = isVersioned
    ? ((parsed as Cache).classifierVersion ?? 1)
    : 1;

  if (version !== CLASSIFIER_VERSION) {
    throw new Error(
      `${path} was classified under v${version}, current classifier is ` +
        `v${CLASSIFIER_VERSION}. Run: npm run kw:reclassify`,
    );
  }
  return isVersioned
    ? (parsed as Cache).snapshots
    : (parsed as Record<string, SerpSnapshot>);
}

function main() {
  for (const [label, path] of [['keywords', KEYWORDS_IN], ['SERPs', SERPS_IN]] as const) {
    if (!existsSync(path)) {
      console.error(`Missing ${label} at ${path}. Run the earlier stages first.`);
      process.exit(1);
    }
  }

  const keywords: Keyword[] = readKeywords(KEYWORDS_IN);
  const keywordsByTerm = new Map(keywords.map((k) => [k.term, k]));

  const snapshots = loadSerps(SERPS_IN);
  const snapshotsByTerm = new Map(Object.entries(snapshots));

  const allClusters = clusterBySerpOverlap(Object.values(snapshots));

  // A cluster whose primary term names a platform cannot be won by an article.
  const clusters = allClusters.filter((c) => !isPlatformQualifiedQuery(c.primaryTerm));
  const excluded = allClusters.length - clusters.length;

  const backlog = buildBacklog(clusters, keywordsByTerm, snapshotsByTerm);

  writeCsv(OUT, backlog as unknown as Record<string, unknown>[]);

  const withData = backlog.filter((a) => a.hasData).length;
  const withBid = backlog.filter((a) => a.topOfPageBid > 0).length;

  console.log(`SERPs:    ${Object.keys(snapshots).length}`);
  console.log(`Clusters: ${clusters.length} (${excluded} excluded as platform-qualified, e.g. "... reddit")`);
  console.log(`Backlog:  ${backlog.length} rows -> ${OUT}`);
  console.log(`  ${withData} rest on real keyword+SERP data (${backlog.length - withData} on defaults)`);
  console.log(`  ${withBid} carry a non-zero top-of-page bid`);
  if (withBid === 0) {
    console.log('');
    console.log('  No bid data. Either kw:planner-merge has not run, or bid is');
    console.log('  not a usable signal in this niche. Scoring currently weights');
    console.log('  bid at 0.35 — consider shifting that to weakness.');
  }

  console.log('\nTop 15 by score:\n');
  for (const a of backlog.slice(0, 15)) {
    const flag = a.hasData ? ' ' : '!';
    console.log(
      `${flag} ${a.score.toFixed(3)}  w=${a.serpWeakness.toFixed(2)}  ${a.track.padEnd(12)} ${a.primaryTerm}`,
    );
  }
  console.log('\n(! = row rests on defaults, not real data)');
}

const isMain = !!process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
