// ---------------------------------------------------------------------------
// Inference provider — the credit-free LAST RESORT.
//
// When no paid provider has credits (or none found a verified email), fall back
// to the original workflow: infer the company's email pattern from OTHER KNOWN
// EXAMPLES on the same domain, then generate the most likely address for this
// person. Result is always `guessed` (never auto-sent) unless a verifier later
// confirms it.
//
// Uses the existing pattern-inference + generator engine. Spends NO API credits
// — it only reads `input.knownDomainEmails` supplied by the caller (e.g. other
// CRM contacts at the same company).
// ---------------------------------------------------------------------------

import {
  inferDomainPatternFromObservedEmails,
} from "../email/emailPatternInference";
import {
  generateEmailCandidatesForPerson,
  generateFallbackEmailCandidates,
} from "../email/emailGenerator";
import { splitEmail } from "../email/emailUtils";
import { classifyEmail, type EmailQualityOptions } from "../email/emailQuality";
import type { TargetRole } from "../types/prospect";
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderEmailResult } from "./types";

export const inferenceProvider: EmailEnrichmentProvider = {
  name: "inference",

  // Always available — it needs no API key. The waterfall only reaches it last.
  isEnabled() {
    return true;
  },

  async findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult> {
    const base: ProviderEmailResult = {
      provider: "inference", email: null, status: "unavailable", verification: null,
      providerConfidence: null, sourceUrl: null, reasons: [], creditsUsed: 0, outcome: "not_found",
    };

    const personName = input.fullName ?? [input.firstName, input.lastName].filter(Boolean).join(" ").trim();
    if (!personName) return { ...base, reasons: ["inference: no person name"] };

    // Build observed-email evidence from known examples on the domain.
    const observed = (input.knownDomainEmails ?? [])
      .map((e) => {
        const parts = splitEmail(e);
        return parts && parts.domain === input.companyDomain
          ? { email: e.toLowerCase(), localPart: parts.localPart, domain: parts.domain }
          : null;
      })
      .filter((x): x is { email: string; localPart: string; domain: string } => x !== null);

    const pattern = inferDomainPatternFromObservedEmails(input.companyDomain, observed, [personName]);
    // role is only used for evidence labelling; CRM roles are free text.
    const role = "CEO" as TargetRole;

    const candidates = pattern
      ? generateEmailCandidatesForPerson(personName, input.companyDomain, pattern, role)
      : generateFallbackEmailCandidates(personName, input.companyDomain, role);

    if (!candidates.length) return { ...base, reasons: ["inference: could not generate a candidate"] };

    const top = candidates[0];
    // Inference output is a GUESS by definition — classifyEmail keeps it `guessed`
    // (and still enforces the personal-domain / role-inbox quality gate).
    const classified = classifyEmail({ email: top.email, guessed: true, options: opts });
    if (classified.status === "invalid") {
      return { ...base, reasons: [`inference rejected: ${classified.reasons.join(", ")}`] };
    }

    return {
      ...base,
      email: top.email,
      status: classified.status, // "guessed"
      providerConfidence: top.confidenceScore,
      reasons: [
        `inferred from ${observed.length} known domain email(s)`,
        pattern ? `pattern ${pattern.patternType} (conf ${pattern.confidenceScore})` : "no pattern — fallback candidates",
        ...classified.reasons,
      ],
      outcome: "found",
    };
  },
};
