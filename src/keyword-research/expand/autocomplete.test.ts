import { describe, it, expect, vi } from 'vitest';
import {
  buildSuggestUrl,
  parseSuggestResponse,
  expansionQueries,
  expandSeed,
  REQUEST_DELAY_MS,
  type ExpandStats,
} from './autocomplete';

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

describe('expandSeed rate limiting on the failure path', () => {
  it('still pays the request delay when every request fails', async () => {
    // Regression test: the catch block must not be able to skip the delay.
    // If a soft IP block starts mid-run, every subsequent request fails --
    // and that is exactly the moment the endpoint needs backing off from,
    // not hammering. Assert on elapsed wall-clock time (the pacing), not on
    // call counts, since call counts alone would pass even if the delay
    // were skipped entirely.
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const failingFetch = async (): Promise<string> => {
      throw new Error('network');
    };
    const totalQueries = expansionQueries('algolia').length;

    const start = Date.now();
    const out = await expandSeed('algolia', 'vendor', 'us', failingFetch);
    const elapsed = Date.now() - start;

    // Allow some slack for timer jitter, but if the failure path skipped
    // `sleep`, elapsed would collapse toward ~0ms instead of tracking
    // totalQueries * REQUEST_DELAY_MS -- a 20% margin is generous enough to
    // avoid CI flakiness while still catching a fully-skipped delay.
    expect(elapsed).toBeGreaterThanOrEqual(totalQueries * REQUEST_DELAY_MS * 0.8);
    expect(out).toEqual([]);

    errorSpy.mockRestore();
  });

  it('surfaces failures via the optional stats parameter without changing the return type', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const failingFetch = async (): Promise<string> => {
      throw new Error('network');
    };
    const stats: ExpandStats = { failures: 0 };
    const totalQueries = expansionQueries('algolia').length;

    const out = await expandSeed('algolia', 'vendor', 'us', failingFetch, stats);

    expect(Array.isArray(out)).toBe(true);
    expect(stats.failures).toBe(totalQueries);
    expect(errorSpy).toHaveBeenCalled();

    errorSpy.mockRestore();
  });

  it('counts only the failed queries when some succeed', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    let n = 0;
    const fetchFn = async () => {
      n++;
      if (n <= 2) throw new Error('network');
      return JSON.stringify(['x', ['algolia pricing']]);
    };
    const stats: ExpandStats = { failures: 0 };

    await expandSeed('algolia', 'vendor', 'us', fetchFn, stats);

    expect(stats.failures).toBe(2);

    errorSpy.mockRestore();
  });
});
