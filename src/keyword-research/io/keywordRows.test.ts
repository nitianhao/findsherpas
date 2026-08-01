import { describe, it, expect } from 'vitest';
import { parseKeywordRow } from './keywordRows';

const base = { term: 'algolia pricing', seed: 'algolia', track: 'vendor', locale: 'us' };

describe('parseKeywordRow', () => {
  it('coerces numeric columns to numbers, not strings', () => {
    const k = parseKeywordRow({ ...base, avgMonthlySearches: '100', topOfPageBid: '4.5' });
    expect(typeof k.avgMonthlySearches).toBe('number');
    expect(typeof k.topOfPageBid).toBe('number');
    expect(k.avgMonthlySearches).toBe(100);
  });

  it('sums correctly rather than concatenating — the bug this module exists for', () => {
    const k = parseKeywordRow({ ...base, avgMonthlySearches: '100' });
    let volume = 0;
    for (const x of [k, k]) volume += x.avgMonthlySearches ?? 0;
    expect(volume).toBe(200);
  });

  it('treats empty and absent numeric cells as undefined, not 0', () => {
    const k = parseKeywordRow({ ...base, avgMonthlySearches: '' });
    expect(k.avgMonthlySearches).toBeUndefined();
    expect(parseKeywordRow(base).topOfPageBid).toBeUndefined();
  });

  it('throws on a missing term rather than emitting a nameless row', () => {
    expect(() => parseKeywordRow({ ...base, term: '' })).toThrow(/no term/);
  });

  it('throws on an unrecognised track instead of silently demoting the row', () => {
    expect(() => parseKeywordRow({ ...base, track: 'buyerr' })).toThrow(/invalid track/);
  });
});
