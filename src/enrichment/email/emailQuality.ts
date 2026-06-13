// ---------------------------------------------------------------------------
// Email quality taxonomy & rules — single source of truth for the CRM/provider
// waterfall. Conservative by design: an address is only "outreach-ready" when
// we have positive verification AND it is a business, person-or-allowed-role
// inbox. Everything else degrades safely.
// ---------------------------------------------------------------------------

import { isPersonalDomain, isGenericInbox, splitEmail, isValidWorkEmail } from "./emailUtils";

/**
 * The status a CRM contact's email can hold.
 *
 * - verified   : a provider confirmed deliverability (e.g. Hunter "valid",
 *                Apollo "verified"). Safe for outreach.
 * - risky      : found but not confirmed deliverable (accept-all, unverified,
 *                low provider confidence). NOT sent by default.
 * - guessed    : produced by pattern inference, never confirmed by a human or
 *                a verifier. NEVER sent.
 * - invalid    : provider says undeliverable, or fails our format/domain rules.
 * - unavailable: no email could be found at all.
 */
export type EmailStatus = "verified" | "risky" | "guessed" | "invalid" | "unavailable";

/** Only `verified` emails are eligible for automated cold outreach. */
export function isOutreachReadyStatus(status: EmailStatus | null | undefined): boolean {
  return status === "verified";
}

// ---------------------------------------------------------------------------
// Role-based inboxes (info@, sales@, support@ …). Rejected by default because
// they are not a person and tend to be GDPR-sensitive shared mailboxes. Can be
// explicitly allowed via config when you knowingly want to contact them.
// ---------------------------------------------------------------------------

/**
 * A role/generic inbox is just a generic local-part (re-uses the shared
 * GENERIC_PREFIXES list so the two never drift).
 */
export function isRoleInbox(email: string): boolean {
  const parts = splitEmail(email);
  if (!parts) return false;
  return isGenericInbox(parts.localPart);
}

export interface EmailQualityOptions {
  /** Allow role/generic inboxes (info@, sales@…) to pass the gate. Default false. */
  allowRoleInboxes?: boolean;
}

export interface EmailQualityResult {
  /** Passed all hard rules (format, not personal, role-inbox policy). */
  accepted: boolean;
  /** Why it was rejected, if it was. */
  rejectionReason:
    | null
    | "MALFORMED"
    | "PERSONAL_DOMAIN"
    | "ROLE_INBOX"
    | "INVALID_FORMAT";
  isPersonal: boolean;
  isRoleInbox: boolean;
}

/**
 * Hard quality gate applied to ANY candidate email before it can be considered
 * for the CRM. Independent of verification — verification refines status, this
 * decides whether the address is even allowed.
 */
export function evaluateEmailQuality(
  email: string,
  opts: EmailQualityOptions = {},
): EmailQualityResult {
  const parts = splitEmail(email);
  if (!parts) {
    return { accepted: false, rejectionReason: "MALFORMED", isPersonal: false, isRoleInbox: false };
  }

  const personal = isPersonalDomain(parts.domain);
  const role = isGenericInbox(parts.localPart);

  if (!isValidWorkEmail(email)) {
    // isValidWorkEmail already rejects personal domains + malformed extractions.
    return {
      accepted: false,
      rejectionReason: personal ? "PERSONAL_DOMAIN" : "INVALID_FORMAT",
      isPersonal: personal,
      isRoleInbox: role,
    };
  }

  if (role && !opts.allowRoleInboxes) {
    return { accepted: false, rejectionReason: "ROLE_INBOX", isPersonal: false, isRoleInbox: true };
  }

  return { accepted: true, rejectionReason: null, isPersonal: false, isRoleInbox: role };
}

// ---------------------------------------------------------------------------
// Map a provider's raw verification verdict + our own quality gate into a
// single EmailStatus. Keeps every provider adapter from inventing its own
// vocabulary.
// ---------------------------------------------------------------------------

/** Normalized provider verification verdict. */
export type VerificationVerdict =
  | "valid" // deliverable confirmed
  | "accept_all" // domain accepts everything — cannot confirm the person
  | "unknown" // verifier could not decide
  | "invalid" // undeliverable
  | "unverified" // provider returned an address but did not verify it
  | null;

export interface ClassifyEmailInput {
  email: string;
  /** Was this address produced by pattern inference (a guess)? */
  guessed?: boolean;
  /** Provider verification verdict, if any. */
  verification?: VerificationVerdict;
  /** Provider 0–100 confidence, if any. */
  providerConfidence?: number | null;
  options?: EmailQualityOptions;
}

export interface ClassifyEmailResult {
  status: EmailStatus;
  /** Human-readable reasons, for provenance/logging. */
  reasons: string[];
  quality: EmailQualityResult;
}

/**
 * Decide the final EmailStatus for a candidate. Order matters:
 *   1. hard quality gate (personal/role/malformed) → invalid
 *   2. guessed addresses are never better than "guessed"
 *   3. verifier verdict drives verified/risky/invalid
 *   4. high provider confidence with no verdict → risky (not verified)
 */
export function classifyEmail(input: ClassifyEmailInput): ClassifyEmailResult {
  const reasons: string[] = [];
  const quality = evaluateEmailQuality(input.email, input.options);

  if (!quality.accepted) {
    reasons.push(`rejected: ${quality.rejectionReason}`);
    return { status: "invalid", reasons, quality };
  }

  if (input.verification === "invalid") {
    reasons.push("verifier: undeliverable");
    return { status: "invalid", reasons, quality };
  }

  if (input.guessed) {
    // A guess can only be confirmed by an explicit verifier "valid".
    if (input.verification === "valid") {
      reasons.push("guessed but verifier confirmed valid");
      return { status: "verified", reasons, quality };
    }
    reasons.push("pattern-inferred (guess) — not verified");
    return { status: "guessed", reasons, quality };
  }

  if (input.verification === "valid") {
    reasons.push("verifier: valid");
    return { status: "verified", reasons, quality };
  }

  if (input.verification === "accept_all" || input.verification === "unknown") {
    reasons.push(`verifier: ${input.verification} — cannot confirm`);
    return { status: "risky", reasons, quality };
  }

  // No verdict at all. High provider confidence is still only "risky" — we did
  // not confirm deliverability, so we never auto-send.
  if (typeof input.providerConfidence === "number") {
    reasons.push(`provider confidence ${input.providerConfidence}, unverified`);
  } else {
    reasons.push("found, unverified");
  }
  return { status: "risky", reasons, quality };
}
