import { describe, it, expect } from 'vitest';
import { normalizeBid, normalizeVolume, normalizeWeakness, scoreArticle, buildBacklog } from './scoring';
import type { Cluster, Keyword, SerpSnapshot } from '../types';

describe('normalizeBid', () => {
  it('maps zero bid to zero', () => {
    expect(normalizeBid(0)).toBe(0);
  });

  it('saturates at the cap so one outlier cannot dominate', () => {
    expect(normalizeBid(1000)).toBe(1);
  });

  it('increases monotonically', () => {
    expect(normalizeBid(5)).toBeGreaterThan(normalizeBid(1));
  });
});

describe('normalizeVolume', () => {
  it('maps zero to zero and saturates at the cap', () => {
    expect(normalizeVolume(0)).toBe(0);
    expect(normalizeVolume(1_000_000)).toBe(1);
  });
});

describe('scoreArticle', () => {
  it('ranks a high-intent weak-SERP term above a low-intent strong-SERP term', () => {
    const good = scoreArticle({ bid: 8, volume: 500, weakness: 0.9, track: 'buyer' });
    const bad = scoreArticle({ bid: 0, volume: 500, weakness: 0.1, track: 'practitioner' });
    expect(good).toBeGreaterThan(bad);
  });

  it('returns a value between 0 and 1', () => {
    const s = scoreArticle({ bid: 8, volume: 500, weakness: 0.9, track: 'buyer' });
    expect(s).toBeGreaterThanOrEqual(0);
    expect(s).toBeLessThanOrEqual(1);
  });

  it('weights the buyer track above the practitioner track, all else equal', () => {
    const buyer = scoreArticle({ bid: 3, volume: 100, weakness: 0.5, track: 'buyer' });
    const prac = scoreArticle({ bid: 3, volume: 100, weakness: 0.5, track: 'practitioner' });
    expect(buyer).toBeGreaterThan(prac);
  });
});

describe('buildBacklog', () => {
  it('produces one row per cluster, sorted by score descending', () => {
    const clusters: Cluster[] = [
      { id: 'c1', primaryTerm: 'algolia units', terms: ['algolia units'], peopleAlsoAsk: ['What is a unit?'] },
      { id: 'c2', primaryTerm: 'search theory', terms: ['search theory'], peopleAlsoAsk: [] },
    ];
    const keywords = new Map<string, Keyword>([
      ['algolia units', { term: 'algolia units', seed: 'algolia', track: 'buyer', locale: 'us', topOfPageBid: 9, avgMonthlySearches: 300 }],
      ['search theory', { term: 'search theory', seed: 'x', track: 'practitioner', locale: 'us', topOfPageBid: 0, avgMonthlySearches: 10 }],
    ]);
    const snapshots = new Map<string, SerpSnapshot>([
      ['algolia units', { term: 'algolia units', results: [], peopleAlsoAsk: [], weakness: 0.9 }],
      ['search theory', { term: 'search theory', results: [], peopleAlsoAsk: [], weakness: 0.1 }],
    ]);

    const backlog = buildBacklog(clusters, keywords, snapshots);
    expect(backlog).toHaveLength(2);
    expect(backlog[0].primaryTerm).toBe('algolia units');
    expect(backlog[0].score).toBeGreaterThan(backlog[1].score);
  });

  it('serialises terms and PAA as pipe-joined strings for the CSV', () => {
    const clusters: Cluster[] = [
      { id: 'c1', primaryTerm: 'a', terms: ['a', 'b'], peopleAlsoAsk: ['Q1', 'Q2'] },
    ];
    const keywords = new Map<string, Keyword>([
      ['a', { term: 'a', seed: 's', track: 'buyer', locale: 'us' }],
    ]);
    const snapshots = new Map<string, SerpSnapshot>();
    const backlog = buildBacklog(clusters, keywords, snapshots);
    expect(backlog[0].terms).toBe('a|b');
    expect(backlog[0].peopleAlsoAsk).toBe('Q1|Q2');
  });

  it('defaults missing keyword and snapshot data without throwing', () => {
    const clusters: Cluster[] = [{ id: 'c1', primaryTerm: 'ghost', terms: ['ghost'], peopleAlsoAsk: [] }];
    const backlog = buildBacklog(clusters, new Map(), new Map());
    expect(backlog[0].score).toBeGreaterThanOrEqual(0);
  });
});

describe('normalizeWeakness', () => {
  it('rescales the observed range onto 0..1', () => {
    // Measured across 82 real SERPs: min 0.520, max 0.850.
    expect(normalizeWeakness(0.5)).toBe(0);
    expect(normalizeWeakness(0.85)).toBe(1);
    expect(normalizeWeakness(0.675)).toBeCloseTo(0.5, 5);
  });

  it('clamps outside the observed range rather than going negative or above 1', () => {
    expect(normalizeWeakness(0)).toBe(0);
    expect(normalizeWeakness(1)).toBe(1);
  });

  it('restores discriminating power that raw weakness lacked', () => {
    // Raw, these two differ by 0.33. Weighted at 0.30 that was under 0.1 of
    // score spread, making the most actionable signal the weakest one.
    const spread = normalizeWeakness(0.85) - normalizeWeakness(0.52);
    expect(spread).toBeGreaterThan(0.9);
  });
});

describe('buildBacklog hasData flag', () => {
  it('marks a row false when the cluster has neither keyword nor SERP data', () => {
    const backlog = buildBacklog(
      [{ id: 'c1', primaryTerm: 'ghost', terms: ['ghost'], peopleAlsoAsk: [] }],
      new Map(),
      new Map(),
    );
    expect(backlog[0].hasData).toBe(false);
  });

  it('marks a row true only when both lookups hit', () => {
    const clusters = [{ id: 'c1', primaryTerm: 'algolia units', terms: ['algolia units'], peopleAlsoAsk: [] }];
    const kws = new Map([['algolia units', { term: 'algolia units', seed: 'algolia', track: 'buyer' as const, locale: 'us' }]]);
    const snaps = new Map([['algolia units', { term: 'algolia units', results: [], peopleAlsoAsk: [], weakness: 0.7 }]]);
    expect(buildBacklog(clusters, kws, snaps)[0].hasData).toBe(true);
    // Keyword present, SERP missing -> still resting on a default.
    expect(buildBacklog(clusters, kws, new Map())[0].hasData).toBe(false);
  });
});
