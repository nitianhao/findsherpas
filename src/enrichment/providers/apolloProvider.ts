// ---------------------------------------------------------------------------
// Apollo.io provider. Last in the default waterfall (limited free reveals).
// Wraps the existing apolloAdapter people-search.
// ---------------------------------------------------------------------------

import { searchPeopleByCompanyAndTitles, type ApolloPerson } from "../email/apolloAdapter";
import { classifyEmail, type VerificationVerdict, type EmailQualityOptions } from "../email/emailQuality";
import { normalizeNameForEmail } from "../email/emailUtils";
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderEmailResult } from "./types";

function mapApolloStatus(status: string | null): VerificationVerdict {
  switch (status) {
    case "verified":
      return "valid";
    case "unverified":
      return "unverified";
    case "likely_to_engage":
      return "unknown";
    default:
      return "unverified";
  }
}

/** Apollo returns a placeholder when the email is gated behind a reveal credit. */
function isRevealedEmail(email: string | null): email is string {
  return !!email && !email.toLowerCase().includes("not_unlocked");
}

function pickPerson(people: ApolloPerson[], input: EnrichmentInput): ApolloPerson | null {
  if (people.length === 0) return null;
  if (input.fullName) {
    const want = normalizeNameForEmail(input.fullName);
    if (want) {
      const match = people.find((p) => {
        const got = normalizeNameForEmail(p.name);
        return got && got.first === want.first && got.last === want.last;
      });
      if (match) return match;
    }
  }
  // Prefer a person whose email is actually revealed.
  return people.find((p) => isRevealedEmail(p.email)) ?? people[0];
}

export const apolloProvider: EmailEnrichmentProvider = {
  name: "apollo",

  isEnabled() {
    return !!process.env.APOLLO_API_KEY?.trim();
  },

  async findEmail(input: EnrichmentInput, opts: EmailQualityOptions): Promise<ProviderEmailResult> {
    const base: ProviderEmailResult = {
      provider: "apollo",
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
      return { ...base, outcome: "disabled", error: "APOLLO_API_KEY not set" };
    }

    const titles = input.role ? [input.role] : [];
    try {
      const res = await searchPeopleByCompanyAndTitles(
        input.companyName ?? input.companyDomain,
        input.companyDomain,
        titles,
        5,
      );
      base.creditsUsed = 1; // search call

      if (res.status === "error") return { ...base, outcome: "error", error: res.errorMessage };
      if (res.status === "not_found") return { ...base, reasons: ["apollo: no people"] };

      const person = pickPerson(res.people, input);
      if (!person || !isRevealedEmail(person.email)) {
        return { ...base, reasons: ["apollo: email not revealed"] };
      }

      const verdict = mapApolloStatus(person.emailStatus);
      const classified = classifyEmail({
        email: person.email,
        guessed: false,
        verification: verdict,
        options: opts,
      });

      return {
        ...base,
        email: classified.status === "invalid" ? null : person.email,
        status: classified.status,
        verification: verdict,
        sourceUrl: person.linkedinUrl,
        reasons: [`apollo email_status=${person.emailStatus}`, ...classified.reasons],
        outcome: classified.status === "invalid" ? "not_found" : "found",
      };
    } catch (err) {
      return { ...base, outcome: "error", error: String(err) };
    }
  },
};
