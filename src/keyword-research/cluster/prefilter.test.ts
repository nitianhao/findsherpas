import { describe, it, expect } from 'vitest';
import { normalizeTerm, groupCandidates } from './prefilter';
import type { Keyword } from '../types';

const kw = (term: string): Keyword => ({ term, seed: 's', track: 'vendor', locale: 'us' });

describe('normalizeTerm', () => {
  it('strips stopwords and sorts tokens so word order stops mattering', () => {
    expect(normalizeTerm('pricing for algolia')).toBe(normalizeTerm('algolia pricing'));
  });

  it('collapses simple plurals', () => {
    expect(normalizeTerm('algolia alternatives')).toBe(normalizeTerm('algolia alternative'));
  });

  it('keeps genuinely different terms distinct', () => {
    expect(normalizeTerm('algolia pricing')).not.toBe(normalizeTerm('algolia ranking'));
  });
});

describe('groupCandidates', () => {
  it('groups obvious variants together to cut SERP fetch cost', () => {
    const groups = groupCandidates([kw('algolia pricing'), kw('pricing for algolia'), kw('algolia ranking')]);
    expect(groups).toHaveLength(2);
  });

  it('returns one group per keyword when nothing matches', () => {
    expect(groupCandidates([kw('algolia pricing'), kw('coveo ranking')])).toHaveLength(2);
  });

  it('handles an empty input', () => {
    expect(groupCandidates([])).toEqual([]);
  });
});
