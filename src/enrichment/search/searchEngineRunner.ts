import {
  runGoogleSearch,
  isGoogleInCaptchaBackoff,
  releaseGooglePage,
} from "./adapters/googleSearchAdapter";
import { runBingSearch, releaseBingPage } from "./adapters/bingSearchAdapter";
import type {
  SearchResultCandidate,
  SearchQueryPlan,
  RoleSearchDiscoveryResult,
} from "../types/search";

const DELAY_BETWEEN_QUERIES_MIN_MS = 5000;
const DELAY_BETWEEN_QUERIES_MAX_MS = 8000;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function randomDelay(): number {
  return (
    DELAY_BETWEEN_QUERIES_MIN_MS +
    Math.floor(
      Math.random() * (DELAY_BETWEEN_QUERIES_MAX_MS - DELAY_BETWEEN_QUERIES_MIN_MS),
    )
  );
}

// ---------------------------------------------------------------------------
// Multi-engine query execution
// ---------------------------------------------------------------------------

interface QueryResult {
  results: SearchResultCandidate[];
  engine: "GOOGLE" | "BING";
  error?: string;
}

async function runQueryWithFallback(query: string): Promise<QueryResult> {
  // Try Google first (unless in CAPTCHA backoff)
  if (!isGoogleInCaptchaBackoff()) {
    try {
      const results = await runGoogleSearch(query);
      if (results.length > 0) {
        return { results, engine: "GOOGLE" };
      }
      // Google returned 0 results -- may be soft-blocked, try Bing
    } catch (err: any) {
      // Google failed -- fall through to Bing
    }
  }

  // Fallback to Bing
  try {
    const results = await runBingSearch(query);
    return { results, engine: "BING" };
  } catch (err: any) {
    return {
      results: [],
      engine: "BING",
      error: `Both engines failed for "${query}": ${err.message}`,
    };
  }
}

// ---------------------------------------------------------------------------
// Role-level search runner
// ---------------------------------------------------------------------------

export async function runRoleSearchDiscovery(
  queryPlan: SearchQueryPlan,
  sourceFile: string,
  sheetName: string,
  rowIndex: number,
): Promise<RoleSearchDiscoveryResult> {
  const result: RoleSearchDiscoveryResult = {
    sourceFile,
    sheetName,
    rowIndex,
    companyName: queryPlan.companyName,
    websiteUrl: queryPlan.websiteUrl,
    role: queryPlan.role,
    queriesTried: [],
    searchResults: [],
    errors: [],
  };

  for (let i = 0; i < queryPlan.queries.length; i++) {
    const query = queryPlan.queries[i];
    result.queriesTried.push(query);

    const qr = await runQueryWithFallback(query);
    result.searchResults.push(...qr.results);
    if (qr.error) result.errors.push(qr.error);

    // Early termination: if we have enough LinkedIn person hits, stop
    const linkedinPersonHits = result.searchResults.filter(
      (r) => r.linkedinType === "PERSON_PROFILE",
    ).length;
    if (linkedinPersonHits >= 3 && i >= 1) break;

    // Rate limit between queries
    if (i < queryPlan.queries.length - 1) {
      await sleep(randomDelay());
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

export async function releaseSearchPages(): Promise<void> {
  await releaseGooglePage();
  await releaseBingPage();
}

// Backwards-compatible export
export const releaseSearchPage = releaseSearchPages;
