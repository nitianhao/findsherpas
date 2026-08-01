import { describe, it, expect } from 'vitest';
import { classifyOwner } from './ownerClassifier';

describe('classifyOwner', () => {
  it('identifies vendor docs', () => {
    expect(classifyOwner('https://www.algolia.com/doc/guides/')).toBe('vendor-docs');
    expect(classifyOwner('https://docs.coveo.com/en/123/')).toBe('vendor-docs');
  });

  it('identifies vendor blogs and marketing pages', () => {
    expect(classifyOwner('https://www.algolia.com/blog/ecommerce/')).toBe('vendor-blog');
    expect(classifyOwner('https://www.bloomreach.com/en/products')).toBe('vendor-blog');
  });

  it('identifies forums', () => {
    expect(classifyOwner('https://stackoverflow.com/questions/123')).toBe('forum');
    expect(classifyOwner('https://www.reddit.com/r/algolia/comments/x')).toBe('forum');
    expect(classifyOwner('https://news.ycombinator.com/item?id=1')).toBe('forum');
  });

  it('identifies review-site listicles', () => {
    expect(classifyOwner('https://www.g2.com/products/algolia/reviews')).toBe('listicle');
    expect(classifyOwner('https://www.capterra.com/p/1/algolia/')).toBe('listicle');
  });

  it('treats an unknown independent domain as independent', () => {
    expect(classifyOwner('https://someconsultant.com/algolia-pricing')).toBe('independent');
  });

  it('returns unknown for an unparseable url', () => {
    expect(classifyOwner('not a url')).toBe('unknown');
  });
});
