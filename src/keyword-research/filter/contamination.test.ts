import { describe, it, expect } from 'vitest';
import { rejectionReason, filterKeywords } from './contamination';
import type { Keyword } from '../types';

const kw = (term: string): Keyword => ({ term, seed: 'test', track: 'vendor', locale: 'us' });

describe('rejectionReason — the site: operator trap', () => {
  it('rejects Google site: operator queries', () => {
    for (const t of ['site search command google', 'site search google dork', 'search q site']) {
      expect(rejectionReason(t)).toBe('SEARCH_OPERATOR');
    }
  });
});

describe('rejectionReason — narrowed operator/browser context, not bare tokens', () => {
  it('still rejects genuine search-operator and browser-extension noise', () => {
    for (const t of [
      'site search command google', 'site search google dork', 'search q site',
      'site search chrome extension',
    ]) {
      expect(rejectionReason(t)).toBe('SEARCH_OPERATOR');
    }
  });

  it('keeps legitimate Kubernetes-operator, boolean-syntax, and product-extension terms', () => {
    for (const t of [
      'elasticsearch operator', 'opensearch operator', 'typesense boolean',
      'coveo explorer extension',
    ]) {
      expect(rejectionReason(t)).toBeNull();
    }
  });
});

describe('rejectionReason — job board contamination', () => {
  it('rejects job and career queries', () => {
    for (const t of ['best site to search jobs in india', 'job site search engines', 'algolia careers']) {
      expect(rejectionReason(t)).toBe('JOBS');
    }
  });
});

describe('rejectionReason — company trivia', () => {
  it('rejects investor and corporate queries', () => {
    for (const t of ['algolia valuation', 'algolia ceo', 'algolia revenue', 'algolia funding', 'algolia how many employees']) {
      expect(rejectionReason(t)).toBe('CORPORATE');
    }
  });

  it('rejects brand asset queries', () => {
    for (const t of ['algolia logo png', 'algolia logo svg', 'algolia icon']) {
      expect(rejectionReason(t)).toBe('BRAND_ASSET');
    }
  });

  it('rejects navigational queries', () => {
    for (const t of ['algolia login', 'algolia status', 'algolia dashboard login']) {
      expect(rejectionReason(t)).toBe('NAVIGATIONAL');
    }
  });

  it('rejects definition and pronunciation queries', () => {
    for (const t of ['algolia pronunciation', 'alogia meaning in psychiatry']) {
      expect(rejectionReason(t)).toBe('TRIVIA');
    }
  });
});

describe('rejectionReason — topic token requirement', () => {
  it('rejects terms with no topic token at all', () => {
    expect(rejectionReason('premio the best')).toBe('NO_TOPIC_TOKEN');
  });
});

describe('rejectionReason — registry contamination', () => {
  it('rejects business-registry queries that carry a topic token', () => {
    // These contain "search"/"ecommerce" so the topic-token check passes them.
    // They need an explicit rule.
    expect(rejectionReason('tennessee ecommerce filing search')).toBe('REGISTRY');
    expect(rejectionReason('site search llc')).toBe('REGISTRY');
  });
});

describe('rejectionReason — keeps the good stuff', () => {
  it('keeps high-intent commercial terms', () => {
    for (const t of [
      'algolia pricing', 'algolia units', 'algolia alternatives',
      'algolia vs elasticsearch', 'algolia query rules', 'algolia typo tolerance',
      'zero results rate', 'ecommerce search relevance', 'search relevance metrics',
    ]) {
      expect(rejectionReason(t)).toBeNull();
    }
  });
});

describe('filterKeywords', () => {
  it('partitions into kept and rejected with reasons', () => {
    const out = filterKeywords([kw('algolia pricing'), kw('algolia careers')]);
    expect(out.kept.map((k) => k.term)).toEqual(['algolia pricing']);
    expect(out.rejected).toEqual([{ term: 'algolia careers', reason: 'JOBS' }]);
  });

  it('deduplicates terms that survive from multiple seeds', () => {
    const out = filterKeywords([kw('algolia pricing'), kw('algolia pricing')]);
    expect(out.kept).toHaveLength(1);
  });
});
