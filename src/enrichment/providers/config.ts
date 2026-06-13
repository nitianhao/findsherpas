// ---------------------------------------------------------------------------
// Provider waterfall configuration. Everything is env-driven so you can test
// providers without touching code.
//
//   ENRICHMENT_PROVIDER_ORDER   comma list, e.g. "hunter,prospeo,apollo"
//                               (default: hunter,prospeo,findymail,dropcontact,apollo)
//   ENRICHMENT_ALLOW_ROLE_INBOXES   "true" to allow info@/sales@/support@
//   ENRICHMENT_ACCEPT_STATUSES  which statuses stop the waterfall
//                               (default: "verified")
//   ENRICHMENT_REVERIFY_EXISTING   "true" to re-verify an existing CRM email
//
// Per-provider API keys (absent key = provider disabled, treated as a stub):
//   HUNTER_API_KEY, PROSPEO_API_KEY, FINDYMAIL_API_KEY,
//   DROPCONTACT_API_KEY, APOLLO_API_KEY
// ---------------------------------------------------------------------------

import type { ProviderName } from "./types";
import type { EmailStatus } from "../email/emailQuality";

const DEFAULT_ORDER: ProviderName[] = [
  "hunter", // domain pattern discovery + verification (free tier friendly)
  "prospeo",
  "findymail",
  "dropcontact",
  "apollo", // limited free reveals
  "inference", // credit-free last resort: pattern inference from known examples
];

const ALL_PROVIDERS: ProviderName[] = [
  "hunter",
  "prospeo",
  "findymail",
  "dropcontact",
  "apollo",
  "inference",
];

export interface WaterfallConfig {
  order: ProviderName[];
  allowRoleInboxes: boolean;
  /** Waterfall stops as soon as it gets an email with one of these statuses. */
  acceptStatuses: EmailStatus[];
  /** Re-verify an existing CRM email through a provider instead of trusting it. */
  reverifyExisting: boolean;
}

function parseOrder(raw: string | undefined): ProviderName[] {
  if (!raw) return DEFAULT_ORDER;
  const names = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s): s is ProviderName => (ALL_PROVIDERS as string[]).includes(s));
  return names.length > 0 ? names : DEFAULT_ORDER;
}

function parseStatuses(raw: string | undefined): EmailStatus[] {
  const valid: EmailStatus[] = ["verified", "risky", "guessed", "invalid", "unavailable"];
  if (!raw) return ["verified"];
  const out = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s): s is EmailStatus => (valid as string[]).includes(s));
  return out.length > 0 ? out : ["verified"];
}

export function loadWaterfallConfig(): WaterfallConfig {
  return {
    order: parseOrder(process.env.ENRICHMENT_PROVIDER_ORDER),
    allowRoleInboxes: process.env.ENRICHMENT_ALLOW_ROLE_INBOXES === "true",
    acceptStatuses: parseStatuses(process.env.ENRICHMENT_ACCEPT_STATUSES),
    reverifyExisting: process.env.ENRICHMENT_REVERIFY_EXISTING === "true",
  };
}

/** Names of providers that currently have an API key configured. */
export function configuredProviderNames(): ProviderName[] {
  const keyByProvider: Record<ProviderName, string | undefined> = {
    hunter: process.env.HUNTER_API_KEY,
    prospeo: process.env.PROSPEO_API_KEY,
    findymail: process.env.FINDYMAIL_API_KEY,
    dropcontact: process.env.DROPCONTACT_API_KEY,
    apollo: process.env.APOLLO_API_KEY,
    inference: "no-key-needed", // credit-free, always available
  };
  return ALL_PROVIDERS.filter((p) => {
    const k = keyByProvider[p];
    return typeof k === "string" && k.trim().length > 0;
  });
}

export { ALL_PROVIDERS, DEFAULT_ORDER };
