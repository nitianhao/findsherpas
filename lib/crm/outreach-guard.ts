// ---------------------------------------------------------------------------
// Outreach safety guard — the single chokepoint that decides whether a contact
// may receive an automated cold email.
//
// CONSERVATIVE BY DESIGN. A contact is blocked if ANY of these hold:
//   - no email address
//   - contact.status is 'unsubscribed' or 'bounced'
//   - opt_out flag is set
//   - email_status is explicitly set to anything other than 'verified'
//     (guessed / risky / invalid / unavailable are never auto-sent)
//
// Backward compatibility: contacts created before the email_status field
// existed have email_status == null. Those are ALLOWED (we don't retroactively
// block legacy hand-curated contacts), but flagged so you can audit them. Only
// the opt-out / bounce / explicit-non-verified rules hard-block.
//
// This is defense-in-depth: enrollment pausing on unsubscribe already keeps
// most opted-out contacts out of the task queue, but this guard runs at the
// actual send point so a direct send-by-id can never leak past it.
// ---------------------------------------------------------------------------

import type { EmailStatus } from './types';

export interface OutreachGuardContact {
  email?: string | null;
  status?: string | null;
  email_status?: EmailStatus | string | null;
  opt_out?: number | null;
}

export interface OutreachReadiness {
  ready: boolean;
  /** Stable code for programmatic handling / logging. */
  code:
    | 'OK'
    | 'OK_LEGACY_UNVERIFIED'
    | 'NO_EMAIL'
    | 'UNSUBSCRIBED'
    | 'BOUNCED'
    | 'OPTED_OUT'
    | 'EMAIL_NOT_VERIFIED';
  reason: string;
}

export function getOutreachReadiness(contact: OutreachGuardContact): OutreachReadiness {
  if (!contact.email || String(contact.email).trim() === '') {
    return { ready: false, code: 'NO_EMAIL', reason: 'Contact has no email address' };
  }

  if (contact.status === 'unsubscribed') {
    return { ready: false, code: 'UNSUBSCRIBED', reason: 'Contact has unsubscribed' };
  }

  if (contact.status === 'bounced') {
    return { ready: false, code: 'BOUNCED', reason: 'Contact email previously bounced' };
  }

  if (contact.opt_out === 1) {
    return { ready: false, code: 'OPTED_OUT', reason: 'Contact is flagged opt_out' };
  }

  const es = contact.email_status;
  if (es != null && es !== 'verified') {
    return {
      ready: false,
      code: 'EMAIL_NOT_VERIFIED',
      reason: `Email status is "${es}" — only verified emails are eligible for outreach`,
    };
  }

  if (es == null) {
    // Legacy contact (pre-enrichment-fields). Allowed, but surfaced.
    return {
      ready: true,
      code: 'OK_LEGACY_UNVERIFIED',
      reason: 'No email_status recorded (legacy contact) — allowed but unverified',
    };
  }

  return { ready: true, code: 'OK', reason: 'Verified and not opted out' };
}

export function isContactOutreachReady(contact: OutreachGuardContact): boolean {
  return getOutreachReadiness(contact).ready;
}
