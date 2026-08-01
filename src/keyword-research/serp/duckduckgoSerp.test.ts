import { describe, it, expect } from 'vitest';
import { selectOrganicResults } from './duckduckgoSerp';

const a = (url: string, title = 't') => ({ url, title });

describe('selectOrganicResults', () => {
  it('drops DuckDuckGo chrome so navigation never appears as a result', () => {
    const out = selectOrganicResults([
      a('https://duckduckgo.com/settings'),
      a('https://duck.co/help'),
      a('https://spreadprivacy.com/post'),
      a('https://www.algolia.com/pricing'),
    ]);
    expect(out.map((r) => r.url)).toEqual(['https://www.algolia.com/pricing']);
  });

  it('deduplicates repeated URLs, which would otherwise inflate overlap counts', () => {
    const out = selectOrganicResults([
      a('https://example.com/a'),
      a('https://example.com/a'),
      a('https://example.com/b'),
    ]);
    expect(out).toHaveLength(2);
  });

  it('caps at ten results', () => {
    const out = selectOrganicResults(
      Array.from({ length: 25 }, (_, i) => a(`https://example.com/${i}`)),
    );
    expect(out).toHaveLength(10);
  });

  it('classifies owners as it goes', () => {
    const out = selectOrganicResults([
      a('https://www.algolia.com/blog/x'),
      a('https://www.reddit.com/r/x'),
      a('https://www.g2.com/products/algolia'),
      a('https://randomsite.example/x'),
    ]);
    expect(out.map((r) => r.ownerType)).toEqual(['vendor-blog', 'forum', 'listicle', 'unknown']);
  });

  it('returns an empty array when the page yielded only chrome — the blocked signal', () => {
    expect(selectOrganicResults([a('https://duckduckgo.com/')])).toEqual([]);
  });

  it('leaves wordCount undefined, since a SERP gives no page length', () => {
    const out = selectOrganicResults([a('https://example.com/a')]);
    expect(out[0].wordCount).toBeUndefined();
  });
});
