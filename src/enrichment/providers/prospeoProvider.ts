// ---------------------------------------------------------------------------
// Prospeo provider — live adapter.
// API: POST https://api.prospeo.io/enrich-person  (header "X-KEY")
// (the old /email-finder endpoint was removed 2026-03-01)
// Docs: https://www.prospeo.io/api-docs/enrich-person
// ---------------------------------------------------------------------------

import { classifyEmail, type VerificationVerdict, type EmailQualityOptions } from "../email/emailQuality";
import { parseName } from "../email/hunterAdapter";
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderEmailResult } from "./types";

const URL = "https://api.prospeo.io/enrich-person";

export const prospeoProvider: EmailEnrichmentProvider = {
  name: "prospeo",

  isEnabled() {
    return !!process.env.PROSPEO_API_KEY?.trim();
  },

  async findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult> {
    const base: ProviderEmailResult = {
      provider: "prospeo", email: null, status: "unavailable", verification: null,
      providerConfidence: null, sourceUrl: null, reasons: [], creditsUsed: 0, outcome: "not_found",
    };
    if (!this.isEnabled()) return { ...base, outcome: "disabled", error: "PROSPEO_API_KEY not set" };

    const first = input.firstName ?? (input.fullName ? parseName(input.fullName).firstName : "");
    const last = input.lastName ?? (input.fullName ? parseName(input.fullName).lastName : "");
    if (!first || !last) return { ...base, error: "Prospeo needs first + last name", reasons: ["no name"] };

    try {
      const res = await fetch(URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-KEY": process.env.PROSPEO_API_KEY!.trim() },
        body: JSON.stringify({ data: { first_name: first, last_name: last, company_website: input.companyDomain } }),
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const json = (await res.json()) as any;

      // Out of credits / rate limit → tell the waterfall to move on.
      const code = json?.error_code ?? json?.message;
      if (res.status === 429 || code === "INSUFFICIENT_CREDITS") {
        return { ...base, outcome: "error", creditsExhausted: res.status !== 429,
          error: `prospeo ${res.status} ${code}`, reasons: [code === "INSUFFICIENT_CREDITS" ? "OUT_OF_CREDITS" : "RATE_LIMIT"] };
      }
      if (!res.ok || json?.error) {
        if (code === "NO_MATCH") return { ...base, reasons: ["prospeo: no match"] };
        return { ...base, outcome: "error", error: `prospeo ${res.status} ${code ?? ""}` };
      }

      const emailObj = json?.response?.person?.email ?? json?.person?.email;
      const email: string | null = emailObj?.email ?? null;
      base.creditsUsed = emailObj?.revealed === false ? 0 : 1;
      if (!email) return { ...base, reasons: ["prospeo: no email"] };

      const verdict: VerificationVerdict = emailObj?.status === "VERIFIED" ? "valid" : "unknown";
      const classified = classifyEmail({ email, guessed: false, verification: verdict, options: opts });
      return {
        ...base,
        email: classified.status === "invalid" ? null : email,
        status: classified.status,
        verification: verdict,
        reasons: [`prospeo status=${emailObj?.status}`, ...classified.reasons],
        outcome: classified.status === "invalid" ? "not_found" : "found",
      };
    } catch (err) {
      return { ...base, outcome: "error", error: String(err) };
    }
  },
};
