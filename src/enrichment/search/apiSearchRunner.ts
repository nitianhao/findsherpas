import { config } from "../config/env";
import type {
  SearchResultCandidate,
  SearchQueryPlan,
  RoleSearchDiscoveryResult,
} from "../types/search";
import { runBraveWebSearch } from "./adapters/braveSearchAdapter";
import {
  getCachedQueryResult,
  setCachedQueryResult,
} from "../cache/searchCache";

// ---------------------------------------------------------------------------
// Provider routing
// ---------------------------------------------------------------------------

async function runApiSearch(
  query: string,
): Promise<SearchResultCandidate[]> {
  const provider = config.ENRICHMENT_SEARCH_PROVIDER;

  switch (provider) {
    case "BRAVE":
      return runBraveWebSearch(query);
    default:
      throw new Error(`Unsupported API search provider: ${provider}`);
  }
}

// ---------------------------------------------------------------------------
// Cached API search (per-query)
// ---------------------------------------------------------------------------

async function runCachedApiSearch(
  query: string,
): Promise<SearchResultCandidate[]> {
  const provider = config.ENRICHMENT_SEARCH_PROVIDER;

  const cached = getCachedQueryResult(provider, query);
  if (cached) return cached as SearchResultCandidate[];

  const results = await runApiSearch(query);
  setCachedQueryResult(provider, query, results);
  return results;
}

// ---------------------------------------------------------------------------
// Role-level API search runner
// ---------------------------------------------------------------------------

const DELAY_BETWEEN_API_QUERIES_MS = 500; // API is cheaper, shorter delay

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export async function runApiRoleSearchDiscovery(
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

    try {
      const queryResults = await runCachedApiSearch(query);
      result.searchResults.push(...queryResults);
    } catch (err: any) {
      result.errors.push(`Query "${query}": ${err.message}`);

      // Stop on rate limit / quota errors
      if (err.message.includes("429") || err.message.includes("402")) {
        result.errors.push("Stopping remaining queries due to rate/quota limit");
        break;
      }
    }

    // Early termination: enough LinkedIn person hits
    const linkedinPersonHits = result.searchResults.filter(
      (r) => r.linkedinType === "PERSON_PROFILE",
    ).length;
    if (linkedinPersonHits >= 3 && i >= 1) break;

    // Brief delay between API calls (respectful but fast)
    if (i < queryPlan.queries.length - 1) {
      await sleep(DELAY_BETWEEN_API_QUERIES_MS);
    }
  }

  return result;
}
