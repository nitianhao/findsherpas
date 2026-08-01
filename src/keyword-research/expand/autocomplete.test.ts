import { describe, it, expect } from 'vitest';
import { buildSuggestUrl, parseSuggestResponse, expansionQueries, expandSeed } from './autocomplete';

describe('buildSuggestUrl', () => {
  it('encodes the query and sets the locale', () => {
    const url = buildSuggestUrl('algolia vs', 'us');
    expect(url).toContain('q=algolia%20vs');
    expect(url).toContain('gl=us');
    expect(url).toContain('client=firefox');
  });
});

describe('parseSuggestResponse', () => {
  it('extracts the suggestion array from the Google response shape', () => {
    const body = JSON.stringify(['algolia', ['algolia pricing', 'algolia alternatives']]);
    expect(parseSuggestResponse(body)).toEqual(['algolia pricing', 'algolia alternatives']);
  });

  it('returns an empty array for malformed JSON rather than throwing', () => {
    expect(parseSuggestResponse('not json')).toEqual([]);
  });

  it('returns an empty array when the suggestion slot is missing', () => {
    expect(parseSuggestResponse(JSON.stringify(['algolia']))).toEqual([]);
  });
});

describe('expansionQueries', () => {
  it('includes the bare seed', () => {
    expect(expansionQueries('algolia')).toContain('algolia');
  });

  it('includes all 26 alphabet-soup variants', () => {
    const qs = expansionQueries('algolia');
    expect(qs).toContain('algolia a');
    expect(qs).toContain('algolia z');
  });

  it('includes intent modifiers', () => {
    const qs = expansionQueries('algolia');
    expect(qs).toContain('algolia vs');
    expect(qs).toContain('algolia alternatives');
    expect(qs).toContain('algolia pricing');
    expect(qs).toContain('best algolia');
    expect(qs).toContain('how algolia');
  });
});

describe('expandSeed', () => {
  it('deduplicates and lowercases suggestions across queries', async () => {
    const fetchFn = async () => JSON.stringify(['x', ['Algolia Pricing', 'algolia pricing']]);
    const out = await expandSeed('algolia', 'vendor', 'us', fetchFn);
    const terms = out.map((k) => k.term);
    expect(terms.filter((t) => t === 'algolia pricing')).toHaveLength(1);
  });

  it('tags every keyword with its seed, track and locale', async () => {
    const fetchFn = async () => JSON.stringify(['x', ['algolia pricing']]);
    const out = await expandSeed('algolia', 'vendor', 'us', fetchFn);
    expect(out[0]).toMatchObject({ seed: 'algolia', track: 'vendor', locale: 'us' });
  });

  it('survives a fetch failure on one query without losing the rest', async () => {
    let n = 0;
    const fetchFn = async () => {
      n++;
      if (n === 1) throw new Error('network');
      return JSON.stringify(['x', ['algolia pricing']]);
    };
    const out = await expandSeed('algolia', 'vendor', 'us', fetchFn);
    expect(out.length).toBeGreaterThan(0);
  });
});
