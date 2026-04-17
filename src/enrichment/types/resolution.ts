import type { Region, TargetRole } from "./prospect";

export type ResolvedRoleStatus =
  | "RESOLVED_STRONG"
  | "RESOLVED_PROBABLE"
  | "UNRESOLVED_WEAK"
  | "UNRESOLVED_NONE";

export type ConfidenceLabel = "STRONG" | "PROBABLE" | "WEAK";

export interface ResolvedRoleCandidate {
  fullName: string;
  normalizedName: string;
  role: TargetRole;
  linkedinUrl: string;
  sourceKinds: ("SEARCH" | "WEBSITE")[];
  evidence: string[];
  confidenceScore: number;
  confidenceLabel: ConfidenceLabel;
  supportingSearchCandidatesCount: number;
  supportingWebsiteCandidatesCount: number;
}

export interface ResolvedRoleDecision {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  region: Region;
  companyName: string;
  websiteUrl: string;
  country: string;
  role: TargetRole;
  status: ResolvedRoleStatus;
  chosenCandidate: ResolvedRoleCandidate | null;
  alternateCandidates: ResolvedRoleCandidate[];
  blockingIssues: string[];
  notes: string[];
  rawSummary: {
    websitePersonCandidates: number;
    websiteLinkedinCandidates: number;
    searchResultCount: number;
    parsedSearchCandidateCount: number;
    rankedSearchCandidateCount: number;
  };
}

export interface ResolvedRowDecision {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  websiteUrl: string;
  region: Region;
  roleDecisions: ResolvedRoleDecision[];
}
