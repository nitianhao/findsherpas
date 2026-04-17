/**
 * Apollo.io People Search API adapter
 * Docs: https://apolloio.github.io/apollo-api-docs/
 * Free plan: 50 email reveals/month; searches are unlimited.
 */

const BASE_URL = "https://api.apollo.io/api/v1";

function getApiKey(): string {
  const key = process.env.APOLLO_API_KEY;
  if (!key) throw new Error("APOLLO_API_KEY env var not set");
  return key;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApolloPerson {
  name: string;
  firstName: string | null;
  lastName: string | null;
  title: string | null;
  email: string | null;          // null if not revealed / not in index
  emailStatus: string | null;    // "verified", "unverified", "likely_to_engage", etc.
  linkedinUrl: string | null;
  organization: string | null;
}

export interface ApolloSearchResult {
  people: ApolloPerson[];
  status: "found" | "not_found" | "error";
  errorMessage?: string;
}

// ---------------------------------------------------------------------------
// Title groups per role
// ---------------------------------------------------------------------------

export const APOLLO_TITLES = {
  CEO: [
    "CEO", "Chief Executive Officer", "Co-CEO", "Founder & CEO",
    "Managing Director", "President & CEO", "CEO & Founder",
  ],
  HEAD_OF_PRODUCT: [
    "Chief Product Officer", "CPO", "VP of Product", "VP Product",
    "Head of Product", "Director of Product", "SVP Product",
  ],
  HEAD_OF_ECOMMERCE: [
    "Head of Ecommerce", "Head of E-Commerce", "VP Ecommerce", "VP E-Commerce",
    "Director of Ecommerce", "Head of Digital Commerce", "Director Digital Commerce",
    "Head of Online", "VP Digital", "Head of Digital",
  ],
  HEAD_OF_GROWTH: [
    "CMO", "Chief Marketing Officer", "VP Marketing", "VP of Marketing",
    "Head of Growth", "VP Growth", "Head of Marketing", "Director of Marketing",
    "Director of Growth", "SVP Marketing",
  ],
} as const;

export type ApolloRoleKey = keyof typeof APOLLO_TITLES;

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export async function searchPeopleByCompanyAndTitles(
  companyName: string,
  websiteDomain: string,
  titles: string[],
  maxResults = 5,
): Promise<ApolloSearchResult> {
  const apiKey = getApiKey();

  const body = {
    q_organization_name: companyName,
    person_titles: titles,
    contact_email_status: ["verified", "unverified", "likely_to_engage"],
    page: 1,
    per_page: maxResults,
  };

  try {
    const res = await fetch(`${BASE_URL}/mixed_people/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": apiKey,
      },
      body: JSON.stringify(body),
    });

    const json = await res.json() as any;

    if (!res.ok) {
      const msg = json?.error ?? json?.message ?? `HTTP ${res.status}`;
      return { people: [], status: "error", errorMessage: msg };
    }

    const raw: any[] = json?.people ?? [];
    if (!raw.length) {
      return { people: [], status: "not_found" };
    }

    // Filter to people that actually belong to the target company (Apollo can drift)
    const domainLower = websiteDomain.toLowerCase().replace(/^www\./, "");
    const people: ApolloPerson[] = raw
      .filter((p) => {
        const orgWebsite = (p.organization?.website_url ?? "").toLowerCase().replace(/^www\./, "");
        const orgName = (p.organization?.name ?? "").toLowerCase();
        const companyLower = companyName.toLowerCase();
        return (
          orgWebsite.includes(domainLower) ||
          domainLower.includes(orgWebsite.replace(/^https?:\/\//, "").split("/")[0]) ||
          orgName.includes(companyLower) ||
          companyLower.includes(orgName)
        );
      })
      .map((p) => ({
        name: p.name ?? [p.first_name, p.last_name].filter(Boolean).join(" "),
        firstName: p.first_name ?? null,
        lastName: p.last_name ?? null,
        title: p.title ?? null,
        email: p.email ?? null,
        emailStatus: p.email_status ?? null,
        linkedinUrl: p.linkedin_url ?? null,
        organization: p.organization?.name ?? null,
      }));

    if (!people.length) return { people: [], status: "not_found" };

    return { people, status: "found" };
  } catch (err) {
    return { people: [], status: "error", errorMessage: String(err) };
  }
}
