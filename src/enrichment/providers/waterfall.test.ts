import { describe, it, expect } from 'vitest';
import { runEmailWaterfall } from './waterfall';
import type { EmailEnrichmentProvider, ProviderEmailResult, ProviderName } from './types';
import type { EmailStatus } from '../email/emailQuality';

/** Build a fake provider that always returns a fixed result. */
function fakeProvider(
  name: ProviderName,
  result: Partial<ProviderEmailResult> & { status: EmailStatus; outcome: ProviderEmailResult['outcome'] },
): EmailEnrichmentProvider {
  const calls: number[] = [];
  const p: EmailEnrichmentProvider & { calls: number[] } = {
    name,
    calls,
    isEnabled: () => true,
    findEmail: async () => {
      calls.push(1);
      return {
        provider: name,
        email: result.email ?? null,
        status: result.status,
        verification: result.verification ?? null,
        providerConfidence: result.providerConfidence ?? null,
        sourceUrl: result.sourceUrl ?? null,
        reasons: result.reasons ?? [],
        creditsUsed: result.creditsUsed ?? 1,
        outcome: result.outcome,
      };
    },
  };
  return p;
}

const baseInput = { fullName: 'Jane Doe', companyDomain: 'acme.com' };
const acceptVerified = { config: { acceptStatuses: ['verified'] as EmailStatus[] } };

describe('waterfall ordering', () => {
  it('stops at the first provider returning a verified email', async () => {
    const hunter = fakeProvider('hunter', { email: 'jane@acme.com', status: 'verified', outcome: 'found' });
    const apollo = fakeProvider('apollo', { email: 'jane2@acme.com', status: 'verified', outcome: 'found' });
    const res = await runEmailWaterfall(baseInput, { ...acceptVerified, providers: [hunter, apollo] });

    expect(res.status).toBe('verified');
    expect(res.email).toBe('jane@acme.com');
    expect(res.provider).toBe('hunter');
    expect(res.source).toBe('hunter');
    // Apollo should not have been consulted.
    expect((apollo as unknown as { calls: number[] }).calls.length).toBe(0);
    expect((hunter as unknown as { calls: number[] }).calls.length).toBe(1);
  });

  it('falls through providers in order until one verifies', async () => {
    const hunter = fakeProvider('hunter', { status: 'unavailable', outcome: 'not_found' });
    const apollo = fakeProvider('apollo', { email: 'jane@acme.com', status: 'verified', outcome: 'found' });
    const res = await runEmailWaterfall(baseInput, { ...acceptVerified, providers: [hunter, apollo] });

    expect(res.provider).toBe('apollo');
    expect(res.attempts.map((a) => a.provider)).toEqual(['hunter', 'apollo']);
  });

  it('returns the best risky email when nothing reaches verified', async () => {
    const hunter = fakeProvider('hunter', { email: 'jane@acme.com', status: 'risky', outcome: 'found' });
    const apollo = fakeProvider('apollo', { status: 'unavailable', outcome: 'not_found' });
    const res = await runEmailWaterfall(baseInput, { ...acceptVerified, providers: [hunter, apollo] });

    expect(res.status).toBe('risky');
    expect(res.email).toBe('jane@acme.com');
    // Both consulted because nothing hit the accept threshold.
    expect(res.attempts.length).toBe(2);
  });
});

describe('existing CRM email (step 0)', () => {
  it('short-circuits when existing email is already verified', async () => {
    const hunter = fakeProvider('hunter', { email: 'x@acme.com', status: 'verified', outcome: 'found' });
    const res = await runEmailWaterfall(
      { ...baseInput, existingEmail: 'jane@acme.com', existingStatus: 'verified' },
      { ...acceptVerified, providers: [hunter] },
    );
    expect(res.source).toBe('existing_crm');
    expect(res.email).toBe('jane@acme.com');
    expect((hunter as unknown as { calls: number[] }).calls.length).toBe(0);
  });

  it('ignores a personal-domain existing email and uses providers', async () => {
    const hunter = fakeProvider('hunter', { email: 'jane@acme.com', status: 'verified', outcome: 'found' });
    const res = await runEmailWaterfall(
      { ...baseInput, existingEmail: 'jane@gmail.com' },
      { ...acceptVerified, providers: [hunter] },
    );
    expect(res.source).toBe('hunter');
    expect(res.email).toBe('jane@acme.com');
  });
});

describe('credit exhaustion → skip to next, then inference fallback', () => {
  it('skips an out-of-credits provider and uses the next one', async () => {
    const hunter = fakeProvider('hunter', {
      status: 'unavailable', outcome: 'error', creditsExhausted: true, reasons: ['OUT_OF_CREDITS'],
    });
    const prospeo = fakeProvider('prospeo', { email: 'jane@acme.com', status: 'verified', outcome: 'found' });
    const res = await runEmailWaterfall(baseInput, { ...acceptVerified, providers: [hunter, prospeo] });
    expect(res.provider).toBe('prospeo');
    expect(res.status).toBe('verified');
  });

  it('falls back to inference (guessed) when every paid provider is out of credits', async () => {
    const { inferenceProvider } = await import('./inferenceProvider');
    const hunter = fakeProvider('hunter', { status: 'unavailable', outcome: 'error', creditsExhausted: true });
    const prospeo = fakeProvider('prospeo', { status: 'unavailable', outcome: 'error', creditsExhausted: true });
    const res = await runEmailWaterfall(
      { ...baseInput, knownDomainEmails: ['john.smith@acme.com', 'mary.jones@acme.com'] },
      { ...acceptVerified, providers: [hunter, prospeo, inferenceProvider] },
    );
    expect(res.provider).toBe('inference');
    expect(res.status).toBe('guessed');
    expect(res.email).toMatch(/@acme\.com$/);
    // Guessed is NOT verified → outreach guard will block it.
    expect(res.status).not.toBe('verified');
  });

  it('does NOT reach inference when a provider already verified', async () => {
    const { inferenceProvider } = await import('./inferenceProvider');
    const hunter = fakeProvider('hunter', { email: 'jane@acme.com', status: 'verified', outcome: 'found' });
    const res = await runEmailWaterfall(
      { ...baseInput, knownDomainEmails: ['john.smith@acme.com'] },
      { ...acceptVerified, providers: [hunter, inferenceProvider] },
    );
    expect(res.provider).toBe('hunter');
    // inference attempt should not appear.
    expect(res.attempts.some((a) => a.provider === 'inference')).toBe(false);
  });
});

describe('guessed emails are never auto-accepted', () => {
  it('a guessed email does not satisfy the default verified accept threshold', async () => {
    const hunter = fakeProvider('hunter', { email: 'jane@acme.com', status: 'guessed', outcome: 'found' });
    const res = await runEmailWaterfall(baseInput, { ...acceptVerified, providers: [hunter] });
    expect(res.status).toBe('guessed');
    // It is returned (best effort) but is NOT verified — the outreach guard blocks it.
    expect(res.status).not.toBe('verified');
  });
});

describe('provenance metadata', () => {
  it('captures provider, source, verifiedAt and every attempt', async () => {
    const hunter = fakeProvider('hunter', {
      email: 'jane@acme.com',
      status: 'verified',
      outcome: 'found',
      providerConfidence: 88,
      sourceUrl: 'https://acme.com/team',
    });
    const res = await runEmailWaterfall(baseInput, { ...acceptVerified, providers: [hunter] });
    expect(res.provider).toBe('hunter');
    expect(res.confidence).toBe(88);
    expect(res.sourceUrl).toBe('https://acme.com/team');
    expect(res.verifiedAt).not.toBeNull();
    expect(res.attempts.length).toBe(1);
  });

  it('returns unavailable with no domain', async () => {
    const res = await runEmailWaterfall({ fullName: 'Jane Doe' }, { providers: [] });
    expect(res.status).toBe('unavailable');
    expect(res.email).toBeNull();
  });
});
