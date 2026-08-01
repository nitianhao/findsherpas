import type { Cluster, SerpSnapshot } from '../types';

// ---------------------------------------------------------------------------
// Real clustering on SERP evidence. Terms sharing this many top-10 URLs are
// treated as one article, because Google is already treating them as one
// intent.
//
// A string-similarity prefilter was built to cut SERP fetch cost by collapsing
// obvious variants first. It was measured and deleted: it collapsed 4,286 terms
// to 4,011, only 6.4%, because autocomplete already returns distinct
// suggestions. That saving did not justify its risk of merging different
// intents (it treated "search for products" and "product search" as one) before
// SERP evidence could separate them. Clustering runs on distinct terms.
// ---------------------------------------------------------------------------

const MIN_SHARED_URLS = 3;

/**
 * Count of DISTINCT URLs appearing in both SERPs.
 *
 * Both sides are deduped deliberately. A single SERP snapshot can repeat a URL
 * (sitelink artifacts, a flaky fetch merging pages), and without deduping those
 * repeats count individually — three copies of one URL would cross
 * MIN_SHARED_URLS on their own and merge two unrelated terms into one article.
 * The threshold means three distinct URLs, so the count must be distinct too.
 */
export function sharedUrlCount(a: SerpSnapshot, b: SerpSnapshot): number {
  const urlsA = new Set(a.results.map((r) => r.url));
  const urlsB = new Set(b.results.map((r) => r.url));
  let shared = 0;
  for (const url of urlsA) if (urlsB.has(url)) shared++;
  return shared;
}

/** Union-find so overlap merges transitively: a~b and b~c puts a, b, c together. */
class DisjointSet {
  private parent: number[];
  constructor(size: number) {
    this.parent = Array.from({ length: size }, (_, i) => i);
  }
  find(i: number): number {
    if (this.parent[i] !== i) this.parent[i] = this.find(this.parent[i]);
    return this.parent[i];
  }
  union(a: number, b: number): void {
    const ra = this.find(a);
    const rb = this.find(b);
    if (ra !== rb) this.parent[rb] = ra;
  }
}

export function clusterBySerpOverlap(
  snapshots: SerpSnapshot[],
  minShared = MIN_SHARED_URLS,
): Cluster[] {
  if (snapshots.length === 0) return [];

  const ds = new DisjointSet(snapshots.length);
  for (let i = 0; i < snapshots.length; i++) {
    for (let j = i + 1; j < snapshots.length; j++) {
      if (sharedUrlCount(snapshots[i], snapshots[j]) >= minShared) ds.union(i, j);
    }
  }

  const byRoot = new Map<number, SerpSnapshot[]>();
  snapshots.forEach((snap, i) => {
    const root = ds.find(i);
    const existing = byRoot.get(root);
    if (existing) existing.push(snap);
    else byRoot.set(root, [snap]);
  });

  return [...byRoot.values()].map((members, i) => {
    // Shortest term is the head term: it is what people actually type.
    const primary = [...members].sort((a, b) => a.term.length - b.term.length)[0];
    const paa = new Set<string>();
    for (const m of members) for (const q of m.peopleAlsoAsk) paa.add(q);
    return {
      id: `c${i + 1}`,
      primaryTerm: primary.term,
      terms: members.map((m) => m.term),
      peopleAlsoAsk: [...paa],
    };
  });
}
