/**
 * Hunter.io API adapter
 * Docs: https://hunter.io/api-documentation/v2
 */

const BASE_URL = "https://api.hunter.io/v2";

function getApiKey(): string {
  const key = process.env.HUNTER_API_KEY;
  if (!key) throw new Error("HUNTER_API_KEY env var not set");
  return key;
}

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return url.toLowerCase().replace(/^www\./, "");
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HunterEmailFinderResult {
  email: string | null;
  score: number | null; // 0–100 confidence
  firstName: string | null;
  lastName: string | null;
  domain: string;
  sources: string[];
  status: "found" | "not_found" | "error";
  errorMessage?: string;
}

export interface HunterDomainEmail {
  value: string;
  type: "personal" | "generic";
  confidence: number;
  firstName: string | null;
  lastName: string | null;
  position: string | null;
  linkedinUrl: string | null;
  sources: string[];
}

export interface HunterDomainSearchResult {
  domain: string;
  organization: string | null;
  emails: HunterDomainEmail[];
  status: "found" | "not_found" | "error";
  errorMessage?: string;
}

// ---------------------------------------------------------------------------
// Email Finder: find email for a specific person
// ---------------------------------------------------------------------------

export async function findEmail(
  websiteUrl: string,
  firstName: string,
  lastName: string,
): Promise<HunterEmailFinderResult> {
  const domain = extractDomain(websiteUrl);
  const apiKey = getApiKey();

  const params = new URLSearchParams({
    domain,
    first_name: firstName,
    last_name: lastName,
    api_key: apiKey,
  });

  try {
    const res = await fetch(`${BASE_URL}/email-finder?${params}`);
    const json = await res.json() as any;

    if (!res.ok) {
      const msg = json?.errors?.[0]?.details ?? json?.error ?? `HTTP ${res.status}`;
      return { email: null, score: null, firstName, lastName, domain, sources: [], status: "error", errorMessage: msg };
    }

    const data = json?.data;
    if (!data?.email) {
      return { email: null, score: null, firstName, lastName, domain, sources: [], status: "not_found" };
    }

    return {
      email: data.email,
      score: data.score ?? null,
      firstName: data.first_name ?? firstName,
      lastName: data.last_name ?? lastName,
      domain,
      sources: (data.sources ?? []).map((s: any) => s.uri ?? s.domain ?? ""),
      status: "found",
    };
  } catch (err) {
    return {
      email: null, score: null, firstName, lastName, domain, sources: [],
      status: "error",
      errorMessage: String(err),
    };
  }
}

// ---------------------------------------------------------------------------
// Domain Search: find all emails on a domain
// ---------------------------------------------------------------------------

export async function searchDomain(
  websiteUrl: string,
  limit = 10,
): Promise<HunterDomainSearchResult> {
  const domain = extractDomain(websiteUrl);
  const apiKey = getApiKey();

  const params = new URLSearchParams({
    domain,
    limit: String(limit),
    api_key: apiKey,
  });

  try {
    const res = await fetch(`${BASE_URL}/domain-search?${params}`);
    const json = await res.json() as any;

    if (!res.ok) {
      const msg = json?.errors?.[0]?.details ?? json?.error ?? `HTTP ${res.status}`;
      return { domain, organization: null, emails: [], status: "error", errorMessage: msg };
    }

    const data = json?.data;
    if (!data || !data.emails?.length) {
      return { domain, organization: data?.organization ?? null, emails: [], status: "not_found" };
    }

    const emails: HunterDomainEmail[] = (data.emails ?? []).map((e: any) => ({
      value: e.value,
      type: e.type,
      confidence: e.confidence ?? 0,
      firstName: e.first_name ?? null,
      lastName: e.last_name ?? null,
      position: e.position ?? null,
      linkedinUrl: e.linkedin ?? null,
      sources: (e.sources ?? []).map((s: any) => s.uri ?? s.domain ?? ""),
    }));

    return {
      domain,
      organization: data.organization ?? null,
      emails,
      status: "found",
    };
  } catch (err) {
    return {
      domain, organization: null, emails: [],
      status: "error",
      errorMessage: String(err),
    };
  }
}

// ---------------------------------------------------------------------------
// Parse a full name into first + last
// ---------------------------------------------------------------------------

export function parseName(fullName: string): { firstName: string; lastName: string } {
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 1) return { firstName: parts[0], lastName: "" };
  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ");
  return { firstName, lastName };
}
