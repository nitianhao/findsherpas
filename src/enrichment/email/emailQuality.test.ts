import { describe, it, expect } from 'vitest';
import {
  evaluateEmailQuality,
  classifyEmail,
  isRoleInbox,
  isOutreachReadyStatus,
} from './emailQuality';
import { isPersonalDomain } from './emailUtils';

describe('personal / free domain filtering', () => {
  it('rejects global free providers', () => {
    for (const d of ['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com', 'proton.me']) {
      expect(isPersonalDomain(d)).toBe(true);
    }
  });

  it('rejects Czech and regional free providers (Seznam etc.)', () => {
    for (const d of ['seznam.cz', 'email.cz', 'centrum.cz', 'atlas.cz', 'zoznam.sk']) {
      expect(isPersonalDomain(d)).toBe(true);
    }
  });

  it('accepts business domains', () => {
    for (const d of ['acme.com', 'shop.de', 'lyko.com']) {
      expect(isPersonalDomain(d)).toBe(false);
    }
  });

  it('quality gate rejects a personal-domain email', () => {
    const r = evaluateEmailQuality('john@gmail.com');
    expect(r.accepted).toBe(false);
    expect(r.rejectionReason).toBe('PERSONAL_DOMAIN');
  });
});

describe('role-based inbox rejection', () => {
  it('detects role inboxes', () => {
    expect(isRoleInbox('info@acme.com')).toBe(true);
    expect(isRoleInbox('sales@acme.com')).toBe(true);
    expect(isRoleInbox('support@acme.com')).toBe(true);
    expect(isRoleInbox('jane.doe@acme.com')).toBe(false);
  });

  it('rejects role inboxes by default', () => {
    const r = evaluateEmailQuality('info@acme.com');
    expect(r.accepted).toBe(false);
    expect(r.rejectionReason).toBe('ROLE_INBOX');
  });

  it('allows role inboxes when explicitly enabled', () => {
    const r = evaluateEmailQuality('info@acme.com', { allowRoleInboxes: true });
    expect(r.accepted).toBe(true);
    expect(r.isRoleInbox).toBe(true);
  });

  it('accepts a person-specific business email', () => {
    const r = evaluateEmailQuality('jane.doe@acme.com');
    expect(r.accepted).toBe(true);
  });
});

describe('classifyEmail status taxonomy', () => {
  it('marks personal-domain emails invalid', () => {
    expect(classifyEmail({ email: 'jane@gmail.com' }).status).toBe('invalid');
  });

  it('marks role inboxes invalid by default', () => {
    expect(classifyEmail({ email: 'info@acme.com' }).status).toBe('invalid');
  });

  it('verifier "valid" → verified', () => {
    expect(classifyEmail({ email: 'jane@acme.com', verification: 'valid' }).status).toBe('verified');
  });

  it('verifier "invalid" → invalid even on a good domain', () => {
    expect(classifyEmail({ email: 'jane@acme.com', verification: 'invalid' }).status).toBe('invalid');
  });

  it('accept_all / unknown → risky', () => {
    expect(classifyEmail({ email: 'jane@acme.com', verification: 'accept_all' }).status).toBe('risky');
    expect(classifyEmail({ email: 'jane@acme.com', verification: 'unknown' }).status).toBe('risky');
  });

  it('found but unverified → risky (never verified)', () => {
    expect(classifyEmail({ email: 'jane@acme.com', providerConfidence: 95 }).status).toBe('risky');
  });

  it('guessed and unverified → guessed', () => {
    expect(classifyEmail({ email: 'jane@acme.com', guessed: true }).status).toBe('guessed');
  });

  it('guessed but verifier-confirmed → verified', () => {
    expect(classifyEmail({ email: 'jane@acme.com', guessed: true, verification: 'valid' }).status).toBe('verified');
  });
});

describe('outreach readiness', () => {
  it('only verified is outreach-ready', () => {
    expect(isOutreachReadyStatus('verified')).toBe(true);
    for (const s of ['risky', 'guessed', 'invalid', 'unavailable', null, undefined] as const) {
      expect(isOutreachReadyStatus(s)).toBe(false);
    }
  });
});
