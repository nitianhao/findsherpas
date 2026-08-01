import { describe, it, expect } from 'vitest';
import { parseGscCsv, joinGscData, strikingDistance } from './gscJoin';
import type { Keyword } from '../types';

const kw = (term: string, extra: Partial<Keyword> = {}): Keyword =>
  ({ term, seed: 's', track: 'vendor', locale: 'us', ...extra });

describe('parseGscCsv', () => {
  it('indexes queries with position and impressions', () => {
    const rows = [{ 'Top queries': 'query interpretation', 'Position': '11', 'Impressions': '24' }];
    const map = parseGscCsv(rows);
    expect(map.get('query interpretation')).toEqual({ position: 11, impressions: 24 });
  });

  it('accepts the alternate Query column name', () => {
    const rows = [{ 'Query': 'search failure', 'Position': '8.3', 'Impressions': '15' }];
    expect(parseGscCsv(rows).get('search failure')?.position).toBe(8.3);
  });

  it('ignores rows with no query', () => {
    expect(parseGscCsv([{ Position: '1' }]).size).toBe(0);
  });

  it('handles whitespace-padded header names', () => {
    const rows = [{ ' Top queries ': 'padded header', ' Position ': '9', ' Impressions ': '1,200' }];
    expect(parseGscCsv(rows).get('padded header')).toEqual({ position: 9, impressions: 1200 });
  });
});

describe('joinGscData', () => {
  it('attaches position and impressions when the term is already ranking', () => {
    const map = new Map([['algolia pricing', { position: 12, impressions: 30 }]]);
    const out = joinGscData([kw('algolia pricing')], map);
    expect(out[0].gscPosition).toBe(12);
    expect(out[0].gscImpressions).toBe(30);
  });

  it('leaves non-ranking terms undefined rather than zero', () => {
    const out = joinGscData([kw('algolia units')], new Map());
    expect(out[0].gscPosition).toBeUndefined();
  });
});

describe('strikingDistance', () => {
  it('selects terms ranking between positions 5 and 20 with impressions', () => {
    const out = strikingDistance([
      kw('a', { gscPosition: 12, gscImpressions: 30 }),
      kw('b', { gscPosition: 2, gscImpressions: 30 }),
      kw('c', { gscPosition: 45, gscImpressions: 30 }),
      kw('d', { gscPosition: 12, gscImpressions: 0 }),
      kw('e'),
    ]);
    expect(out.map((k) => k.term)).toEqual(['a']);
  });

  it('sorts by impressions descending so the biggest opportunity leads', () => {
    const out = strikingDistance([
      kw('low', { gscPosition: 10, gscImpressions: 5 }),
      kw('high', { gscPosition: 10, gscImpressions: 500 }),
    ]);
    expect(out[0].term).toBe('high');
  });
});
