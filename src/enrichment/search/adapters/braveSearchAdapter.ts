import { assertBraveApiKey, config } from "../../config/env";
import type {
  SearchResultCandidate,
  SearchEngineAdapter,
  ApiSearchResponseMeta,
  NormalizedSearchResultSet,
} from "../../types/search";

const BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search";

// ---------------------------------------------------------------------------
// Brave API response shapes (subset we care about)
// ---------------------------------------------------------------------------

interface BraveWebResult {
  title: string;
  url: string;
  description: string;
  meta_url?: { path?: string; hostname?: string };
}

interface BraveSearchResponse {
  query?: { original?: string };
  web?: { results?: BraveWebResult[]; totalEstimatedMatches?: number };
  mixed?: unknown;
}

// ---------------------------------------------------------------------------
// LinkedIn classification (mirrors logic from google adapter)
// ---------------------------------------------------------------------------

function classifyLinkedin(url: string): {
  isLinkedin: boolean;
  linkedinType: "PERSON_PROFILE" | "COMPANY_PAGE" | "OTHER" | null;
} {
  const lower = url.toLowerCase();
  if (!lower.includes("linkedin.com"))
    return { isLinkedin: false, linkedinType: null };
  if (lower.includes("/in/"))
    return { isLinkedin: true, linkedinType: "PERSON_PROFILE" };
  if (lower.includes("/company/"))
    return { isLinkedin: true, linkedinType: "COMPANY_PAGE" };
  return { isLinkedin: true, linkedinType: "OTHER" };
}

// ---------------------------------------------------------------------------
// Normalize a single Brave result into our pipeline type
// ---------------------------------------------------------------------------

function toSearchResultCandidate(
  raw: BraveWebResult,
  rank: number,
  query: string,
): SearchResultCandidate {
  const li = classifyLinkedin(raw.url);
  const signals: string[] = [];
  if (li.isLinkedin) signals.push("linkedin-url");
  if (li.linkedinType === "PERSON_PROFILE") signals.push("linkedin-person");

  const displayUrl =
    raw.meta_url?.hostname && raw.meta_url?.path
      ? `${raw.meta_url.hostname}${raw.meta_url.path}`
      : raw.url;

  return {
    query,
    engine: "BRAVE",
    title: raw.title ?? "",
    snippet: (raw.description ?? "").slice(0, 300),
    url: raw.url,
    displayUrl,
    rank,
    isLinkedin: li.isLinkedin,
    linkedinType: li.linkedinType,
    evidenceSignals: signals,
  };
}

// ---------------------------------------------------------------------------
// Core search function
// ---------------------------------------------------------------------------

export async function runBraveWebSearch(
  query: string,
): Promise<SearchResultCandidate[]> {
  const apiKey = assertBraveApiKey();
  const maxResults = config.ENRICHMENT_SEARCH_MAX_RESULTS;

  const url = new URL(BRAVE_API_URL);
  url.searchParams.set("q", query);
  url.searchParams.set("count", String(maxResults));
  url.searchParams.set("text_decorations", "false");
  url.searchParams.set("search_lang", "en");

  const start = Date.now();

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Accept: "application/json",
      "Accept-Encoding": "gzip",
      "X-Subscription-Token": apiKey,
    },
  });

  const elapsed = Date.now() - start;

  // Handle rate limits
  if (res.status === 429) {
    const retryAfter = res.headers.get("Retry-After") ?? "unknown";
    throw new Error(
      `Brave API rate limited (429). Retry-After: ${retryAfter}`,
    );
  }

  // Handle quota exceeded
  if (res.status === 402) {
    throw new Error("Brave API quota exceeded (402). Upgrade plan or wait.");
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `Brave API error: ${res.status} ${res.statusText} — ${body.slice(0, 200)}`,
    );
  }

  const data = (await res.json()) as BraveSearchResponse;
  const webResults = data.web?.results ?? [];

  return webResults
    .slice(0, maxResults)
    .map((r, i) => toSearchResultCandidate(r, i + 1, query));
}

/**
 * Richer return including metadata — useful for diagnostics.
 */
export async function runBraveWebSearchWithMeta(
  query: string,
): Promise<NormalizedSearchResultSet> {
  const apiKey = assertBraveApiKey();
  const maxResults = config.ENRICHMENT_SEARCH_MAX_RESULTS;

  const url = new URL(BRAVE_API_URL);
  url.searchParams.set("q", query);
  url.searchParams.set("count", String(maxResults));
  url.searchParams.set("text_decorations", "false");
  url.searchParams.set("search_lang", "en");

  const start = Date.now();

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Accept: "application/json",
      "Accept-Encoding": "gzip",
      "X-Subscription-Token": apiKey,
    },
  });

  const elapsed = Date.now() - start;

  if (res.status === 429) {
    throw new Error(
      `Brave API rate limited (429). Retry-After: ${res.headers.get("Retry-After") ?? "unknown"}`,
    );
  }
  if (res.status === 402) {
    throw new Error("Brave API quota exceeded (402).");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `Brave API error: ${res.status} ${res.statusText} — ${body.slice(0, 200)}`,
    );
  }

  const data = (await res.json()) as BraveSearchResponse;
  const webResults = data.web?.results ?? [];

  const rateLimitHeader = res.headers.get("X-RateLimit-Remaining");

  const meta: ApiSearchResponseMeta = {
    provider: "BRAVE",
    query,
    totalEstimatedResults: data.web?.totalEstimatedMatches ?? null,
    responseTimeMs: elapsed,
    rateLimitRemaining: rateLimitHeader ? Number(rateLimitHeader) : null,
  };

  return {
    meta,
    results: webResults
      .slice(0, maxResults)
      .map((r, i) => toSearchResultCandidate(r, i + 1, query)),
  };
}

// ---------------------------------------------------------------------------
// Adapter interface
// ---------------------------------------------------------------------------

export const braveAdapter: SearchEngineAdapter = {
  name: "BRAVE",
  runSearch: runBraveWebSearch,
};
