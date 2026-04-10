import { createHmac } from 'node:crypto';

function secret() {
  const s = process.env.UNSUBSCRIBE_SECRET;
  if (!s) throw new Error('UNSUBSCRIBE_SECRET env var not set');
  return s;
}

/** Returns HMAC(contactId) — use as ?token= param alongside ?contact_id= */
export function generateToken(contactId: string): string {
  return createHmac('sha256', secret()).update(contactId).digest('hex');
}

/** Constant-time comparison of expected vs provided token */
export function verifyContactToken(contactId: string, token: string): boolean {
  const expected = generateToken(contactId);
  if (expected.length !== token.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= expected.charCodeAt(i) ^ token.charCodeAt(i);
  }
  return diff === 0;
}

/** Build the full unsubscribe URL to embed in emails */
export function buildUnsubscribeUrl(contactId: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL ?? '';
  const token = generateToken(contactId);
  return `${baseUrl}/api/crm/unsubscribe?contact_id=${contactId}&token=${token}`;
}
