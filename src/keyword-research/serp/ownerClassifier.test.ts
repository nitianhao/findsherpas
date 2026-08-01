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

  it('identifies community publishing platforms as forums', () => {
    expect(classifyOwner('https://dev.to/someuser/algolia-vs-elasticsearch-123')).toBe('forum');
    expect(classifyOwner('https://medium.com/@someuser/algolia-pricing-guide')).toBe('forum');
  });

  it('identifies review-site listicles', () => {
    expect(classifyOwner('https://www.g2.com/products/algolia/reviews')).toBe('listicle');
    expect(classifyOwner('https://www.capterra.com/p/1/algolia/')).toBe('listicle');
  });

  it('treats an UNRECOGNISED domain as unknown, not independent', () => {
    // The default must not be `independent`. serpWeakness scores independent
    // 0.15 (hardest to displace), so defaulting there made every unrecognised
    // content farm look like a formidable incumbent and inverted the output.
    expect(classifyOwner('https://someconsultant.com/algolia-pricing')).toBe('unknown');
    expect(classifyOwner('https://checkthat.ai/algolia-alternatives')).toBe('unknown');
  });

  it('classifies only named authorities as independent', () => {
    expect(classifyOwner('https://baymard.com/blog/ecommerce-search')).toBe('independent');
    expect(classifyOwner('https://www.nngroup.com/articles/search/')).toBe('independent');
  });

  it('classifies review aggregators and alternatives directories as listicles', () => {
    for (const u of [
      'https://www.gartner.com/reviews/market/insight-engines/vendor/algolia',
      'https://alternativeto.net/software/algolia/',
      'https://www.peerspot.com/products/algolia-reviews',
      'https://openalternative.co/alternatives/algolia',
    ]) {
      expect(classifyOwner(u)).toBe('listicle');
    }
  });

  it('classifies search vendors previously missed as vendor properties', () => {
    expect(classifyOwner('https://www.addsearch.com/blog/algolia-alternatives/')).toBe('vendor-blog');
    expect(classifyOwner('https://www.shaped.ai/blog/the-10-best-algolia-alternatives')).toBe('vendor-blog');
  });

  it('treats YouTube as forum-class, since a video is one fewer article slot', () => {
    expect(classifyOwner('https://www.youtube.com/watch?v=abc123')).toBe('forum');
  });

  it('returns unknown for an unparseable url', () => {
    expect(classifyOwner('not a url')).toBe('unknown');
  });
});
