import { describe, it, expect } from 'vitest';
import {
  batchForPlanner,
  parseVolumeRange,
  parsePlannerCsv,
  mergePlannerData,
  stripPlannerPreamble,
} from './keywordPlanner';
import type { Keyword } from '../types';

const kw = (term: string): Keyword => ({ term, seed: 's', track: 'vendor', locale: 'us' });

describe('batchForPlanner', () => {
  it('splits into batches of at most 1000 (the paste limit)', () => {
    const terms = Array.from({ length: 2500 }, (_, i) => `term ${i}`);
    const batches = batchForPlanner(terms);
    expect(batches).toHaveLength(3);
    expect(batches[0]).toHaveLength(1000);
    expect(batches[2]).toHaveLength(500);
  });

  it('returns one batch when under the limit', () => {
    expect(batchForPlanner(['a', 'b'])).toEqual([['a', 'b']]);
  });
});

describe('parseVolumeRange', () => {
  it('parses a bucketed range to its midpoint', () => {
    expect(parseVolumeRange('10 – 100')).toBe(55);
    expect(parseVolumeRange('1K – 10K')).toBe(5500);
  });

  it('parses a plain number', () => {
    expect(parseVolumeRange('320')).toBe(320);
    expect(parseVolumeRange('1,300')).toBe(1300);
  });

  it('returns 0 for missing or unparseable values', () => {
    expect(parseVolumeRange('')).toBe(0);
    expect(parseVolumeRange('—')).toBe(0);
  });
});

describe('parsePlannerCsv', () => {
  it('indexes by lowercased keyword with volume and bid', () => {
    const rows = [{
      'Keyword': 'Algolia Pricing',
      'Avg. monthly searches': '10 – 100',
      'Top of page bid (high range)': '4.50',
    }];
    const map = parsePlannerCsv(rows);
    expect(map.get('algolia pricing')).toEqual({ avgMonthlySearches: 55, topOfPageBid: 4.5 });
  });

  it('ignores rows with no keyword column', () => {
    expect(parsePlannerCsv([{ foo: 'bar' }]).size).toBe(0);
  });
});

describe('stripPlannerPreamble', () => {
  it('strips preamble lines before the real CRLF-terminated header row', () => {
    const raw =
      'Keyword ideas were generated from the following: term\r\n' +
      'Location(s): United States\r\n' +
      '\r\n' +
      'Keyword,Avg. monthly searches,Top of page bid (high range)\r\n' +
      'algolia pricing,10 – 100,4.50\r\n';
    const stripped = stripPlannerPreamble(raw);
    expect(stripped.startsWith('Keyword,Avg. monthly searches')).toBe(true);
    expect(stripped).not.toContain('Location(s)');
  });

  it('returns the input unchanged when no recognizable header line is found', () => {
    const raw = 'foo,bar\r\n1,2';
    expect(stripPlannerPreamble(raw)).toBe(raw);
  });
});

describe('mergePlannerData', () => {
  it('attaches volume and bid to matching keywords', () => {
    const map = new Map([['algolia pricing', { avgMonthlySearches: 55, topOfPageBid: 4.5 }]]);
    const out = mergePlannerData([kw('algolia pricing')], map);
    expect(out[0].avgMonthlySearches).toBe(55);
    expect(out[0].topOfPageBid).toBe(4.5);
  });

  it('defaults unmatched keywords to zero rather than dropping them', () => {
    const out = mergePlannerData([kw('algolia units')], new Map());
    expect(out[0].avgMonthlySearches).toBe(0);
    expect(out[0].topOfPageBid).toBe(0);
  });
});
