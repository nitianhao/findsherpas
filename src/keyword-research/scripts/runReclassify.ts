import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

import { reclassifySnapshot, CLASSIFIER_VERSION } from '../serp/serpRecon';
import type { SerpSnapshot } from '../types';

// ---------------------------------------------------------------------------
// Recompute ownerType and weakness over already-fetched SERPs, offline.
//
// ownerType and weakness are frozen into stage3-serps.json at fetch time, and
// runSerpRecon skips terms already present — so a classifier change does not
// reach cached data, and re-running the fetcher reports "Nothing to do".
// This closes that gap without spending a single network request.
// ---------------------------------------------------------------------------

const FILE = 'src/keyword-research/data/stage3-serps.json';

interface Cache {
  classifierVersion?: number;
  snapshots: Record<string, SerpSnapshot>;
}

/** Reads both the legacy bare-map shape and the versioned shape. */
export function readCache(raw: string): Cache {
  const parsed = JSON.parse(raw) as unknown;
  if (parsed && typeof parsed === 'object' && 'snapshots' in (parsed as object)) {
    return parsed as Cache;
  }
  return { snapshots: parsed as Record<string, SerpSnapshot> };
}

function main() {
  if (!existsSync(FILE)) {
    console.error(`No ${FILE}. Run npm run kw:serp first.`);
    process.exit(1);
  }

  const cache = readCache(readFileSync(FILE, 'utf8'));
  const before = cache.classifierVersion ?? 1;
  const terms = Object.keys(cache.snapshots);

  let changed = 0;
  const out: Record<string, SerpSnapshot> = {};
  for (const term of terms) {
    const old = cache.snapshots[term];
    const next = reclassifySnapshot(old);
    if (Math.abs(next.weakness - old.weakness) > 1e-9) changed++;
    out[term] = next;
  }

  writeFileSync(
    FILE,
    JSON.stringify({ classifierVersion: CLASSIFIER_VERSION, snapshots: out }, null, 2),
    'utf8',
  );

  console.log(`Reclassified ${terms.length} snapshots (v${before} -> v${CLASSIFIER_VERSION}).`);
  console.log(`${changed} had their weakness change.`);

  const w = Object.values(out).map((s) => s.weakness).sort((a, b) => a - b);
  const q = (p: number) => w[Math.floor(p * (w.length - 1))];
  console.log(
    `weakness now: min=${w[0].toFixed(3)} p50=${q(0.5).toFixed(3)} max=${w[w.length - 1].toFixed(3)}`,
  );
  console.log('If these bounds differ from WEAKNESS_OBSERVED_* in score/scoring.ts, update them.');
}

const isMain = !!process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
