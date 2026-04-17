import type { PlannedRoleTask } from "../types/tasks";
import type { CompanyDiscoveryResult } from "../types/discovery";
import type { RoleSearchCompositeResult } from "../types/search";
import { config } from "../config/env";
import { buildRoleSearchQueryPlan } from "./queryBuilder";
import { runApiRoleSearchDiscovery } from "./apiSearchRunner";
import { runRoleSearchDiscovery as runBrowserRoleSearchDiscovery } from "./searchEngineRunner";
import { extractIdentityCandidatesFromSearchResults } from "../matching/identityParser";
import { rankIdentityCandidates } from "../matching/roleCandidateRanker";

/**
 * Primary entry point for role search discovery.
 * Uses API search (Brave) by default, falls back to legacy browser
 * scraping only when explicitly configured.
 */
export async function discoverRoleViaPublicSearch(
  task: PlannedRoleTask,
  discoveryResult?: CompanyDiscoveryResult | null,
): Promise<RoleSearchCompositeResult> {
  const queryPlan = buildRoleSearchQueryPlan(task, discoveryResult);

  const useBrowserLegacy =
    config.ENRICHMENT_SEARCH_PROVIDER === "GOOGLE_BROWSER" ||
    config.ENRICHMENT_SEARCH_PROVIDER === "BING_BROWSER";

  const searchResult = useBrowserLegacy
    ? await runBrowserRoleSearchDiscovery(
        queryPlan,
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
      )
    : await runApiRoleSearchDiscovery(
        queryPlan,
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
      );

  const parsedCandidates =
    extractIdentityCandidatesFromSearchResults(searchResult);

  const rankedCandidates = rankIdentityCandidates(
    task,
    parsedCandidates,
    discoveryResult,
  );

  return {
    sourceFile: task.sourceFile,
    sheetName: task.sheetName,
    rowIndex: task.rowIndex,
    companyName: task.companyName,
    websiteUrl: task.websiteUrl,
    role: task.role,
    region: task.region,
    queryPlan,
    rawSearchResults: searchResult.searchResults,
    parsedCandidates,
    rankedCandidates,
    errors: searchResult.errors,
  };
}
