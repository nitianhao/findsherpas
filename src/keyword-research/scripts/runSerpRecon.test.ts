import { describe, it, expect } from 'vitest';
import { hasCommercialIntent } from './runSerpRecon';

describe('hasCommercialIntent', () => {
  it('matches each commercial modifier on a word boundary', () => {
    expect(hasCommercialIntent('algolia vs elasticsearch')).toBe(true);
    expect(hasCommercialIntent('algolia versus elasticsearch')).toBe(true);
    expect(hasCommercialIntent('algolia alternative')).toBe(true);
    expect(hasCommercialIntent('algolia alternatives')).toBe(true);
    expect(hasCommercialIntent('algolia pricing')).toBe(true);
    expect(hasCommercialIntent('algolia price')).toBe(true);
    expect(hasCommercialIntent('algolia cost')).toBe(true);
    expect(hasCommercialIntent('algolia costs')).toBe(true);
    expect(hasCommercialIntent('algolia review')).toBe(true);
    expect(hasCommercialIntent('algolia reviews')).toBe(true);
    expect(hasCommercialIntent('compare algolia')).toBe(true);
    expect(hasCommercialIntent('algolia comparison')).toBe(true);
    expect(hasCommercialIntent('best algolia')).toBe(true);
    expect(hasCommercialIntent('algolia competitor')).toBe(true);
    expect(hasCommercialIntent('algolia competitors')).toBe(true);
  });

  it('is case-insensitive', () => {
    expect(hasCommercialIntent('Algolia VS Elasticsearch')).toBe(true);
  });

  it('does not match a substring that is not a whole word', () => {
    // "vs" must not match inside "advswitch"-like tokens; "cost" must not
    // match "costume", "best" must not match "bestiary", etc.
    expect(hasCommercialIntent('costume search')).toBe(false);
    expect(hasCommercialIntent('bestiary lookup')).toBe(false);
    expect(hasCommercialIntent('advswitch tool')).toBe(false);
  });

  it('returns false for a term with no commercial modifier', () => {
    expect(hasCommercialIntent('algolia search api')).toBe(false);
  });
});
