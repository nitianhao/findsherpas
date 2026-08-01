import { describe, it, expect } from 'vitest';
import { serpWeakness } from './serpRecon';
import type { SerpResult } from '../types';

const r = (ownerType: SerpResult['ownerType'], wordCount = 1000): SerpResult =>
  ({ url: 'https://x.com/a', title: 't', ownerType, wordCount });

describe('serpWeakness', () => {
  it('scores a vendor-only SERP as highly winnable', () => {
    const results = [r('vendor-blog'), r('vendor-blog'), r('vendor-docs'), r('vendor-blog')];
    expect(serpWeakness(results)).toBeGreaterThan(0.7);
  });

  it('scores an independent-incumbent SERP as hard', () => {
    const results = [r('independent', 3000), r('independent', 3000), r('independent', 3000)];
    expect(serpWeakness(results)).toBeLessThan(0.3);
  });

  it('treats thin content as more winnable than deep content', () => {
    const thin = [r('independent', 300), r('independent', 300)];
    const deep = [r('independent', 4000), r('independent', 4000)];
    expect(serpWeakness(thin)).toBeGreaterThan(serpWeakness(deep));
  });

  it('returns 0.5 for an empty SERP rather than dividing by zero', () => {
    expect(serpWeakness([])).toBe(0.5);
  });
});
