// ---------------------------------------------------------------------------
// Waterfall runner. Resolves the best email for a contact by trying sources in
// order:
//   0. existing CRM email (if present and passes the quality gate)
//   1..n. each configured provider, in ENRICHMENT_PROVIDER_ORDER
//
// Stops at the first provider that returns an email with an accepted status
// (default: "verified"). Always returns full provenance + every attempt.
//
// Pure orchestration: providers do the I/O, this decides ordering and stop
// conditions. No throwing — providers report errors as results.
// ---------------------------------------------------------------------------

import {
  classifyEmail,
  evaluateEmailQuality,
  type EmailStatus,
  type EmailQualityOptions,
} from "../email/emailQuality";
import { extractDomain } from "../email/emailUtils";
import { loadWaterfallConfig, type WaterfallConfig } from "./config";
import { resolveProviders } from "./registry";
import type { EmailEnrichmentProvider, EnrichmentInput, WaterfallResult } from "./types";

export interface WaterfallContactInput extends Omit<EnrichmentInput, "companyDomain"> {
  /** Domain or website URL — normalized to a bare domain internally. */
  companyDomain?: string;
  companyWebsite?: string;
  /** Email already on the CRM record, if any. */
  existingEmail?: string | null;
  /** Stored status of the existing email, if known. */
  existingStatus?: EmailStatus | null;
}

export interface RunWaterfallOptions {
  /** Override the loaded config (mainly for tests). */
  config?: Partial<WaterfallConfig>;
  /** Override the provider list (mainly for tests). */
  providers?: EmailEnrichmentProvider[];
}

function nowIso(): string {
  return new Date().toISOString();
}

function emptyResult(reason: string): WaterfallResult {
  return {
    email: null,
    status: "unavailable",
    provider: null,
    source: "none",
    confidence: null,
    verifiedAt: null,
    sourceUrl: null,
    reasons: [reason],
    attempts: [],
  };
}

export async function runEmailWaterfall(
  input: WaterfallContactInput,
  opts: RunWaterfallOptions = {},
): Promise<WaterfallResult> {
  const cfg: WaterfallConfig = { ...loadWaterfallConfig(), ...opts.config };
  const qopts: EmailQualityOptions = { allowRoleInboxes: cfg.allowRoleInboxes };
  const accept = new Set(cfg.acceptStatuses);

  const domain =
    input.companyDomain?.trim() ||
    (input.companyWebsite ? extractDomain(input.companyWebsite) : "");

  if (!domain) {
    return emptyResult("No company domain — cannot enrich");
  }

  // -------------------------------------------------------------------------
  // Step 0 — existing CRM email
  // -------------------------------------------------------------------------
  if (input.existingEmail?.trim()) {
    const existing = input.existingEmail.trim();
    const quality = evaluateEmailQuality(existing, qopts);
    if (quality.accepted) {
      if (input.existingStatus === "verified") {
        return {
          email: existing,
          status: "verified",
          provider: null,
          source: "existing_crm",
          confidence: null,
          verifiedAt: null,
          sourceUrl: null,
          reasons: ["existing CRM email already verified"],
          attempts: [],
        };
      }
      if (!cfg.reverifyExisting) {
        // Keep it, but reflect that we have not confirmed it ourselves.
        const status: EmailStatus = input.existingStatus ?? "risky";
        return {
          email: existing,
          status,
          provider: null,
          source: "existing_crm",
          confidence: null,
          verifiedAt: null,
          sourceUrl: null,
          reasons: [`existing CRM email kept (status: ${status})`],
          attempts: [],
        };
      }
      // else: fall through and let a provider verify/replace it.
    }
    // Personal/role/invalid existing emails are ignored and we try providers.
  }

  // -------------------------------------------------------------------------
  // Steps 1..n — providers in order
  // -------------------------------------------------------------------------
  const providers = opts.providers ?? resolveProviders();
  const enrichInput: EnrichmentInput = { ...input, companyDomain: domain };

  const attempts: WaterfallResult["attempts"] = [];
  let best: WaterfallResult | null = null;

  for (const provider of providers) {
    const result = await provider.findEmail(enrichInput, qopts);
    attempts.push(result);

    if (result.outcome === "found" && result.email) {
      const candidate: WaterfallResult = {
        email: result.email,
        status: result.status,
        provider: result.provider,
        source: result.provider,
        confidence: result.providerConfidence,
        verifiedAt: result.status === "verified" ? nowIso() : null,
        sourceUrl: result.sourceUrl,
        reasons: result.reasons,
        attempts: [],
      };

      // Track the best non-accepted candidate (e.g. a "risky" email) in case
      // nothing reaches the accept threshold.
      if (!best || rank(candidate.status) > rank(best.status)) best = candidate;

      if (accept.has(result.status)) {
        return { ...candidate, attempts };
      }
    }
  }

  if (best) return { ...best, attempts };

  return { ...emptyResult("No provider returned a usable email"), attempts };
}

/** Higher is better, for choosing a fallback when nothing is "accepted". */
function rank(status: EmailStatus): number {
  switch (status) {
    case "verified":
      return 4;
    case "risky":
      return 3;
    case "guessed":
      return 2;
    case "invalid":
      return 1;
    default:
      return 0;
  }
}

// Re-export classifyEmail for convenience in scripts that post-process.
export { classifyEmail };
