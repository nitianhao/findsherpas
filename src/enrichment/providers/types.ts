// ---------------------------------------------------------------------------
// Email enrichment provider abstraction.
//
// Every email source (Hunter, Apollo, Prospeo, Findymail, Dropcontact, …) is a
// provider that implements this interface. The waterfall runner ([waterfall.ts])
// tries them in a configurable order. Hunter is just one provider, never the
// only one.
// ---------------------------------------------------------------------------

import type {
  EmailStatus,
  VerificationVerdict,
  EmailQualityOptions,
} from "../email/emailQuality";

/** Canonical provider identifiers. Used in config order and provenance. */
export type ProviderName =
  | "hunter"
  | "prospeo"
  | "findymail"
  | "dropcontact"
  | "apollo"
  | "inference"; // credit-free pattern inference — always the LAST resort

/** What we ask a provider to find an email for. `companyDomain` is required. */
export interface EnrichmentInput {
  fullName?: string;
  firstName?: string;
  lastName?: string;
  /** Job title / role to search for when the provider does people-search. */
  role?: string;
  companyName?: string;
  /** Bare domain, e.g. "example.com" (no scheme, no www). Required. */
  companyDomain: string;
  /**
   * Known example emails on this company's domain (e.g. other CRM contacts at
   * the same company, or addresses scraped from the site). Used ONLY by the
   * inference fallback to learn the domain's pattern when no paid provider has
   * credits. Credit-free.
   */
  knownDomainEmails?: string[];
}

/** One provider's attempt at finding an email. */
export interface ProviderEmailResult {
  provider: ProviderName;
  /** The address found, already passed through the quality gate, or null. */
  email: string | null;
  status: EmailStatus;
  verification: VerificationVerdict;
  /** Provider's own 0–100 confidence, if it reports one. */
  providerConfidence: number | null;
  /** A public URL the provider cited as evidence, if any. */
  sourceUrl: string | null;
  reasons: string[];
  /** Best-effort credits/reveals consumed by this call (for cost comparison). */
  creditsUsed: number;
  /** Set when the provider errored or is not configured. */
  error?: string;
  /** True when the provider reported it is out of credits/quota. */
  creditsExhausted?: boolean;
  /** "found" (usable email), "not_found", "error", or "disabled". */
  outcome: "found" | "not_found" | "error" | "disabled";
}

export interface EmailEnrichmentProvider {
  readonly name: ProviderName;
  /** True when the provider has the credentials it needs to run. */
  isEnabled(): boolean;
  /**
   * Attempt to find (and, where supported, verify) an email for the person.
   * Implementations MUST NOT throw — they return an `error`/`disabled`
   * outcome instead so the waterfall can continue to the next provider.
   */
  findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult>;
}

/** Where the final chosen email came from. */
export type EmailSource = "existing_crm" | ProviderName | "none";

/** Final decision produced by the waterfall for one contact. */
export interface WaterfallResult {
  email: string | null;
  status: EmailStatus;
  /** The provider that supplied the chosen email (null for existing_crm/none). */
  provider: ProviderName | null;
  source: EmailSource;
  confidence: number | null;
  verifiedAt: string | null;
  sourceUrl: string | null;
  reasons: string[];
  /** Every provider attempt made, in order — useful for debugging & comparison. */
  attempts: ProviderEmailResult[];
}
