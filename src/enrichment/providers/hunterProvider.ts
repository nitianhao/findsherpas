// ---------------------------------------------------------------------------
// Hunter.io provider. ONE source in the waterfall — used mainly for domain
// pattern discovery + verification. Wraps the existing hunterAdapter.
// ---------------------------------------------------------------------------

import { findEmail, verifyEmail, parseName } from "../email/hunterAdapter";
import { classifyEmail, type VerificationVerdict, type EmailQualityOptions } from "../email/emailQuality";
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderEmailResult } from "./types";

function mapHunterVerdict(status: string): VerificationVerdict {
  switch (status) {
    case "valid":
      return "valid";
    case "invalid":
    case "disposable":
    case "webmail":
      return "invalid";
    case "accept_all":
      return "accept_all";
    default:
      return "unknown";
  }
}

export const hunterProvider: EmailEnrichmentProvider = {
  name: "hunter",

  isEnabled() {
    return !!process.env.HUNTER_API_KEY?.trim();
  },

  async findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult> {
    const base: ProviderEmailResult = {
      provider: "hunter",
      email: null,
      status: "unavailable",
      verification: null,
      providerConfidence: null,
      sourceUrl: null,
      reasons: [],
      creditsUsed: 0,
      outcome: "not_found",
    };

    if (!this.isEnabled()) {
      return { ...base, outcome: "disabled", error: "HUNTER_API_KEY not set" };
    }

    const first = input.firstName ?? (input.fullName ? parseName(input.fullName).firstName : "");
    const last = input.lastName ?? (input.fullName ? parseName(input.fullName).lastName : "");
    if (!first && !last) {
      return { ...base, error: "Hunter email-finder needs a person name", reasons: ["no name"] };
    }

    try {
      const res = await findEmail(input.companyDomain, first, last);
      base.creditsUsed = 1;

      if (res.status === "error") {
        return { ...base, outcome: "error", error: res.errorMessage };
      }
      if (res.status === "not_found" || !res.email) {
        return { ...base, reasons: ["hunter: not found"] };
      }

      // Verify deliverability (separate credit pool, 100/mo on free tier).
      const v = await verifyEmail(res.email);
      base.creditsUsed = 2;
      const verdict = v.status === "error" ? null : mapHunterVerdict(v.status);

      const classified = classifyEmail({
        email: res.email,
        guessed: false,
        verification: verdict,
        providerConfidence: res.score,
        options: opts,
      });

      return {
        ...base,
        email: classified.status === "invalid" ? null : res.email,
        status: classified.status,
        verification: verdict,
        providerConfidence: res.score,
        sourceUrl: res.sources[0] ?? null,
        reasons: [`hunter score ${res.score}`, `verify=${v.status}`, ...classified.reasons],
        outcome: classified.status === "invalid" ? "not_found" : "found",
      };
    } catch (err) {
      return { ...base, outcome: "error", error: String(err) };
    }
  },
};
