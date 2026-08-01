import { describe, it, expect } from 'vitest';
import { sharedUrlCount, clusterBySerpOverlap } from './serpOverlap';
import type { SerpSnapshot } from '../types';

const snap = (term: string, urls: string[], paa: string[] = []): SerpSnapshot => ({
  term,
  results: urls.map((url) => ({ url, title: 't', ownerType: 'independent' as const, wordCount: 1000 })),
  peopleAlsoAsk: paa,
  weakness: 0.5,
});

describe('sharedUrlCount', () => {
  it('counts URLs present in both SERPs', () => {
    const a = snap('a', ['u1', 'u2', 'u3']);
    const b = snap('b', ['u2', 'u3', 'u4']);
    expect(sharedUrlCount(a, b)).toBe(2);
  });

  it('returns 0 for disjoint SERPs', () => {
    expect(sharedUrlCount(snap('a', ['u1']), snap('b', ['u2']))).toBe(0);
  });

  it('counts distinct URLs only, so repeats within one SERP cannot inflate it', () => {
    // Without deduping this returns 3 and would merge two unrelated terms on
    // the strength of a single shared URL repeated by a fetch artifact.
    expect(sharedUrlCount(snap('a', ['u1', 'u1', 'u1']), snap('b', ['u1', 'u2']))).toBe(1);
  });

  it('does not let repeats on either side cross the merge threshold', () => {
    const clusters = clusterBySerpOverlap([
      snap('unrelated one', ['u1', 'u1', 'u1']),
      snap('unrelated two', ['u1', 'u1', 'u1']),
    ]);
    expect(clusters).toHaveLength(2);
  });
});

describe('clusterBySerpOverlap', () => {
  it('merges terms sharing at least 3 top-10 URLs', () => {
    const clusters = clusterBySerpOverlap([
      snap('algolia pricing', ['u1', 'u2', 'u3', 'u4']),
      snap('algolia cost', ['u1', 'u2', 'u3', 'u9']),
    ]);
    expect(clusters).toHaveLength(1);
    expect(clusters[0].terms).toHaveLength(2);
  });

  it('keeps terms separate below the shared-URL threshold', () => {
    const clusters = clusterBySerpOverlap([
      snap('algolia pricing', ['u1', 'u2', 'u3']),
      snap('algolia ranking', ['u1', 'u8', 'u9']),
    ]);
    expect(clusters).toHaveLength(2);
  });

  it('merges transitively through a shared middle term', () => {
    const clusters = clusterBySerpOverlap([
      snap('a', ['u1', 'u2', 'u3']),
      snap('b', ['u1', 'u2', 'u3']),
      snap('c', ['u1', 'u2', 'u3']),
    ]);
    expect(clusters).toHaveLength(1);
    expect(clusters[0].terms).toHaveLength(3);
  });

  it('picks the shortest term as the cluster primary', () => {
    const clusters = clusterBySerpOverlap([
      snap('algolia pricing explained in detail', ['u1', 'u2', 'u3']),
      snap('algolia pricing', ['u1', 'u2', 'u3']),
    ]);
    expect(clusters[0].primaryTerm).toBe('algolia pricing');
  });

  it('unions People Also Ask across the cluster without duplicates', () => {
    const clusters = clusterBySerpOverlap([
      snap('a', ['u1', 'u2', 'u3'], ['Q1', 'Q2']),
      snap('b', ['u1', 'u2', 'u3'], ['Q2', 'Q3']),
    ]);
    expect(clusters[0].peopleAlsoAsk.sort()).toEqual(['Q1', 'Q2', 'Q3']);
  });

  it('handles an empty input', () => {
    expect(clusterBySerpOverlap([])).toEqual([]);
  });
});
