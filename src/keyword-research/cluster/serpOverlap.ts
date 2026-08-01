import type { Cluster, SerpSnapshot } from '../types';

// ---------------------------------------------------------------------------
// Real clustering on SERP evidence. Terms sharing this many top-10 URLs are
// treated as one article, because Google is already treating them as one
// intent. This is intentionally separate from the string-similarity
// prefilter (see prefilter.ts) — string similarity gets intent wrong.
// ---------------------------------------------------------------------------

const MIN_SHARED_URLS = 3;

export function sharedUrlCount(a: SerpSnapshot, b: SerpSnapshot): number {
  const urlsB = new Set(b.results.map((r) => r.url));
  return a.results.filter((r) => urlsB.has(r.url)).length;
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
