// ---------------------------------------------------------------------------
// Dropcontact provider — live adapter (EU / GDPR-friendly, no scraping).
// Async API:
//   POST https://api.dropcontact.com/v1/enrich/all   (header "X-Access-Token")
//        body { data: [{ first_name, last_name, company, website }], siren, language }
//        → { request_id, credits_left }
//   GET  https://api.dropcontact.com/v1/enrich/all/{request_id}  → poll until ready
//        response data[].email = [{ email, qualification }]  ("nominative@pro" = best)
// Out of credits: HTTP 403 "exceeded quota". Docs: https://developer.dropcontact.com/
// ---------------------------------------------------------------------------

import { classifyEmail, type VerificationVerdict, type EmailQualityOptions } from "../email/emailQuality";
import { parseName } from "../email/hunterAdapter";
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderEmailResult } from "./types";

const POST_URL = "https://api.dropcontact.com/v1/enrich/all";
const POLL_INTERVAL_MS = 8000;
const MAX_POLLS = 8; // ~64s worst case; rarely reached (only when nothing verified earlier)

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

export const dropcontactProvider: EmailEnrichmentProvider = {
  name: "dropcontact",

  isEnabled() {
    return !!process.env.DROPCONTACT_API_KEY?.trim();
  },

  async findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult> {
    const base: ProviderEmailResult = {
      provider: "dropcontact", email: null, status: "unavailable", verification: null,
      providerConfidence: null, sourceUrl: null, reasons: [], creditsUsed: 0, outcome: "not_found",
    };
    if (!this.isEnabled()) return { ...base, outcome: "disabled", error: "DROPCONTACT_API_KEY not set" };

    const token = process.env.DROPCONTACT_API_KEY!.trim();
    const first = input.firstName ?? (input.fullName ? parseName(input.fullName).firstName : "");
    const last = input.lastName ?? (input.fullName ? parseName(input.fullName).lastName : "");
    if (!first || !last) return { ...base, error: "Dropcontact needs first + last name", reasons: ["no name"] };

    try {
      const postRes = await fetch(POST_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Access-Token": token },
        body: JSON.stringify({
          data: [{ first_name: first, last_name: last, company: input.companyName ?? "", website: input.companyDomain }],
          siren: false,
          language: "en",
        }),
      });

      if (postRes.status === 403) {
        return { ...base, outcome: "error", creditsExhausted: true, error: "dropcontact 403 quota exceeded", reasons: ["OUT_OF_CREDITS"] };
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const postJson = (await postRes.json().catch(() => ({}))) as any;
      if (!postRes.ok || postJson?.error || !postJson?.request_id) {
        return { ...base, outcome: "error", error: `dropcontact post ${postRes.status} ${postJson?.reason ?? postJson?.error ?? ""}` };
      }

      const requestId: string = postJson.request_id;
      const getUrl = `${POST_URL}/${requestId}`;

      // Poll until results are ready.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let data: any = null;
      for (let i = 0; i < MAX_POLLS; i++) {
        await sleep(POLL_INTERVAL_MS);
        const getRes = await fetch(getUrl, { headers: { "X-Access-Token": token } });
        if (getRes.status === 403) {
          return { ...base, outcome: "error", creditsExhausted: true, error: "dropcontact 403 quota exceeded", reasons: ["OUT_OF_CREDITS"] };
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const getJson = (await getRes.json().catch(() => ({}))) as any;
        if (getJson?.success && Array.isArray(getJson?.data)) { data = getJson.data; break; }
        // else: "Request not ready yet" — keep polling.
      }

      base.creditsUsed = 1;
      if (!data) return { ...base, reasons: ["dropcontact: timed out waiting for results"] };

      const record = data[0];
      const emails: Array<{ email: string; qualification?: string }> = record?.email ?? [];
      if (!emails.length || !emails[0]?.email) return { ...base, reasons: ["dropcontact: no email"] };

      const top = emails[0];
      // "nominative@pro" = a verified professional, person-specific email.
      const verdict: VerificationVerdict = top.qualification?.startsWith("nominative@pro") ? "valid" : "unknown";
      const classified = classifyEmail({ email: top.email, guessed: false, verification: verdict, options: opts });
      return {
        ...base,
        email: classified.status === "invalid" ? null : top.email,
        status: classified.status,
        verification: verdict,
        reasons: [`dropcontact qualification=${top.qualification}`, ...classified.reasons],
        outcome: classified.status === "invalid" ? "not_found" : "found",
      };
    } catch (err) {
      return { ...base, outcome: "error", error: String(err) };
    }
  },
};
