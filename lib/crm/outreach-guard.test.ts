import { describe, it, expect } from 'vitest';
import { getOutreachReadiness, isContactOutreachReady } from './outreach-guard';

describe('outreach guard — opt-out exclusion', () => {
  it('blocks unsubscribed contacts', () => {
    const r = getOutreachReadiness({ email: 'a@acme.com', status: 'unsubscribed', email_status: 'verified' });
    expect(r.ready).toBe(false);
    expect(r.code).toBe('UNSUBSCRIBED');
  });

  it('blocks bounced contacts', () => {
    const r = getOutreachReadiness({ email: 'a@acme.com', status: 'bounced', email_status: 'verified' });
    expect(r.ready).toBe(false);
    expect(r.code).toBe('BOUNCED');
  });

  it('blocks contacts flagged opt_out even if status is active', () => {
    const r = getOutreachReadiness({ email: 'a@acme.com', status: 'active', opt_out: 1, email_status: 'verified' });
    expect(r.ready).toBe(false);
    expect(r.code).toBe('OPTED_OUT');
  });
});

describe('outreach guard — email quality exclusion', () => {
  it('blocks guessed emails', () => {
    const r = getOutreachReadiness({ email: 'a@acme.com', status: 'active', email_status: 'guessed' });
    expect(r.ready).toBe(false);
    expect(r.code).toBe('EMAIL_NOT_VERIFIED');
  });

  it('blocks risky and invalid emails', () => {
    expect(isContactOutreachReady({ email: 'a@acme.com', status: 'active', email_status: 'risky' })).toBe(false);
    expect(isContactOutreachReady({ email: 'a@acme.com', status: 'active', email_status: 'invalid' })).toBe(false);
  });

  it('blocks contacts with no email', () => {
    const r = getOutreachReadiness({ email: '', status: 'active', email_status: 'verified' });
    expect(r.code).toBe('NO_EMAIL');
  });
});

describe('outreach guard — allowed cases', () => {
  it('allows verified, non-opted-out contacts', () => {
    const r = getOutreachReadiness({ email: 'a@acme.com', status: 'active', email_status: 'verified' });
    expect(r.ready).toBe(true);
    expect(r.code).toBe('OK');
  });

  it('allows legacy contacts with no email_status (backward compatible)', () => {
    const r = getOutreachReadiness({ email: 'a@acme.com', status: 'active' });
    expect(r.ready).toBe(true);
    expect(r.code).toBe('OK_LEGACY_UNVERIFIED');
  });
});
