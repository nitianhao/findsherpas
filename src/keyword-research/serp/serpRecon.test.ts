import { describe, it, expect } from 'vitest';
import { serpWeakness } from './serpRecon';
import type { SerpResult } from '../types';

const r = (ownerType: SerpResult['ownerType'], wordCount = 1000): SerpResult =>
  ({ url: 'https://x.com/a', title: 't', ownerType, wordCount });

/** A result with genuinely no depth data — the key is absent, not `undefined`. */
const rNoDepth = (ownerType: SerpResult['ownerType']): SerpResult =>
  ({ url: 'https://x.com/a', title: 't', ownerType });

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

  it('applies no thinness adjustment when depth is unknown for every result', () => {
    const results = [rNoDepth('vendor-blog'), rNoDepth('vendor-blog'), rNoDepth('vendor-docs')];
    const ownerOnly =
      results.reduce((sum, x) => sum + (x.ownerType === 'vendor-docs' ? 0.8 : 0.9), 0) / results.length;
    expect(serpWeakness(results)).toBeCloseTo(ownerOnly, 10);
  });

  it('computes thinFraction only over results with known depth when depth is partially known', () => {
    // 1 known-thin independent result should pull the score up even though
    // two other independent results have no depth data at all.
    const partiallyKnown = [r('independent', 300), rNoDepth('independent'), rNoDepth('independent')];
    const allUnknown = [rNoDepth('independent'), rNoDepth('independent'), rNoDepth('independent')];
    expect(serpWeakness(partiallyKnown)).toBeGreaterThan(serpWeakness(allUnknown));
  });
});
