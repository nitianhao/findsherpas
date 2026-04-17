import type { Region, TargetRole } from "./prospect";

export interface SearchQueryPlan {
  companyName: string;
  websiteUrl: string;
  domain: string;
  role: TargetRole;
  region: Region;
  country: string;
  queries: string[];
}

export type SearchEngine = "GOOGLE" | "BING" | "BRAVE" | "DUCKDUCKGO";

export interface SearchResultCandidate {
  query: string;
  engine: SearchEngine;
  title: string;
  snippet: string;
  url: string;
  displayUrl: string;
  rank: number;
  isLinkedin: boolean;
  linkedinType: "PERSON_PROFILE" | "COMPANY_PAGE" | "OTHER" | null;
  evidenceSignals: string[];
}

export interface RoleSearchDiscoveryResult {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  websiteUrl: string;
  role: TargetRole;
  queriesTried: string[];
  searchResults: SearchResultCandidate[];
  errors: string[];
}

export interface ParsedIdentityCandidate {
  fullName: string;
  normalizedName: string;
  role: TargetRole;
  inferredCompany: string;
  sourceUrl: string;
  sourceTitle: string;
  sourceSnippet: string;
  linkedinUrl: string;
  evidenceSignals: string[];
  confidenceScore: number;
}

export interface RankedIdentityCandidate extends ParsedIdentityCandidate {
  rankScore: number;
  rankReasons: string[];
}

export interface SearchEngineAdapter {
  name: SearchEngine;
  runSearch(query: string): Promise<SearchResultCandidate[]>;
}

// ---------------------------------------------------------------------------
// API search metadata
// ---------------------------------------------------------------------------

export interface ApiSearchResponseMeta {
  provider: SearchEngine;
  query: string;
  totalEstimatedResults: number | null;
  responseTimeMs: number;
  rateLimitRemaining: number | null;
}

export interface NormalizedSearchResultSet {
  meta: ApiSearchResponseMeta;
  results: SearchResultCandidate[];
}

// ---------------------------------------------------------------------------
// Composite result
// ---------------------------------------------------------------------------

export interface RoleSearchCompositeResult {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  websiteUrl: string;
  role: TargetRole;
  region: Region;
  queryPlan: SearchQueryPlan;
  rawSearchResults: SearchResultCandidate[];
  parsedCandidates: ParsedIdentityCandidate[];
  rankedCandidates: RankedIdentityCandidate[];
  errors: string[];
}
