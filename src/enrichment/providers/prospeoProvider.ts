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

      // ---- Failure classification -------------------------------------------------
      // Distinguish "no result" (not an error) from the kinds of failure we care
      // about — especially OUT_OF_CREDITS vs a transient/rate-limit blip — so the
      // logs make clear whether Prospeo is exhausted or just flaky.
      if (!res.ok || json?.error) {
        const errorCode: string | undefined = json?.error_code;
        const message: string | undefined = json?.message;

        // Not failures — Prospeo simply has no match / not enough input.
        if (errorCode === "NO_MATCH") return { ...base, reasons: ["prospeo: no match"] };
        if (errorCode === "INVALID_DATAPOINTS") return { ...base, reasons: ["prospeo: insufficient input data"] };

        let kind: "OUT_OF_CREDITS" | "RATE_LIMIT" | "AUTH_ERROR" | "TRANSIENT_ERROR";
        let creditsExhausted = false;
        if (errorCode === "INSUFFICIENT_CREDITS" || res.status === 402) {
          kind = "OUT_OF_CREDITS";
          creditsExhausted = true;
        } else if (res.status === 429 || /rate.?limit/i.test(message ?? "")) {
          kind = "RATE_LIMIT";
        } else if (errorCode === "INVALID_API_KEY" || res.status === 401 || res.status === 403) {
          kind = "AUTH_ERROR";
        } else {
          kind = "TRANSIENT_ERROR";
        }

        return {
          ...base,
          outcome: "error",
          creditsExhausted,
          error: `prospeo ${kind}: HTTP ${res.status}${errorCode ? ` ${errorCode}` : ""}${message ? ` — ${message}` : ""}`,
          reasons: [kind],
        };
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
