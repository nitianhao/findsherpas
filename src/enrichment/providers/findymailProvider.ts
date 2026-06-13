// ---------------------------------------------------------------------------
// Findymail provider — live adapter.
// API: POST https://app.findymail.com/api/search/name
//      header "Authorization: Bearer <key>"; body { name, domain }
//      response: { contact: { email, verified, ... } }
// Out of credits: HTTP 402. Docs: https://app.findymail.com/docs/
// ---------------------------------------------------------------------------

import { classifyEmail, type VerificationVerdict, type EmailQualityOptions } from "../email/emailQuality";
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderEmailResult } from "./types";

const URL = "https://app.findymail.com/api/search/name";

export const findymailProvider: EmailEnrichmentProvider = {
  name: "findymail",

  isEnabled() {
    return !!process.env.FINDYMAIL_API_KEY?.trim();
  },

  async findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult> {
    const base: ProviderEmailResult = {
      provider: "findymail", email: null, status: "unavailable", verification: null,
      providerConfidence: null, sourceUrl: null, reasons: [], creditsUsed: 0, outcome: "not_found",
    };
    if (!this.isEnabled()) return { ...base, outcome: "disabled", error: "FINDYMAIL_API_KEY not set" };

    const name = input.fullName ?? [input.firstName, input.lastName].filter(Boolean).join(" ").trim();
    if (!name) return { ...base, error: "Findymail needs a person name", reasons: ["no name"] };

    try {
      const res = await fetch(URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${process.env.FINDYMAIL_API_KEY!.trim()}`,
        },
        body: JSON.stringify({ name, domain: input.companyDomain }),
      });

      if (res.status === 402) {
        return { ...base, outcome: "error", creditsExhausted: true, error: "findymail 402 payment required", reasons: ["OUT_OF_CREDITS"] };
      }
      if (res.status === 429) {
        return { ...base, outcome: "error", error: "findymail 429 rate limit", reasons: ["RATE_LIMIT"] };
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const json = (await res.json().catch(() => ({}))) as any;
      if (!res.ok) {
        return { ...base, outcome: "error", error: `findymail ${res.status} ${json?.message ?? ""}` };
      }

      const contact = json?.contact;
      const email: string | null = contact?.email ?? null;
      if (!email) return { ...base, reasons: ["findymail: no email"] };
      base.creditsUsed = 1; // Findymail charges on a successful find

      // Findymail returns verified emails; `verified` flag confirms deliverability.
      const verdict: VerificationVerdict = contact?.verified === false ? "unknown" : "valid";
      const classified = classifyEmail({ email, guessed: false, verification: verdict, options: opts });
      return {
        ...base,
        email: classified.status === "invalid" ? null : email,
        status: classified.status,
        verification: verdict,
        reasons: [`findymail verified=${contact?.verified}`, ...classified.reasons],
        outcome: classified.status === "invalid" ? "not_found" : "found",
      };
    } catch (err) {
      return { ...base, outcome: "error", error: String(err) };
    }
  },
};
