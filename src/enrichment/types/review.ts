import type { Region, TargetRole } from "./prospect";

// ---------------------------------------------------------------------------
// Review queue types
// ---------------------------------------------------------------------------

export type ReviewPriority = "HIGH" | "MEDIUM" | "LOW";

export type ReviewBucket =
  | "ROLE_PROBABLE_NOT_WRITTEN"
  | "ROLE_WEAK_WITH_CANDIDATE"
  | "INVALID_PERSON_BUT_HIGH_SIGNAL"
  | "EMAIL_INFERRED_WEAK"
  | "EMAIL_UNRESOLVED_BUT_DOMAIN_KNOWN"
  | "SEARCH_GOOD_LINKEDIN_BUT_ROLE_UNCLEAR"
  | "EXISTING_CELL_BLOCKED_NEW_VALUE";

export interface ReviewQueueItem {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  region: Region;
  companyName: string;
  websiteUrl: string;
  country: string;
  role: TargetRole;
  bucket: ReviewBucket;
  priority: ReviewPriority;
  currentWorkbookValues: {
    existingName: string;
    existingLinkedin: string;
    existingEmail: string;
  };
  candidateValues: {
    candidateName: string | null;
    candidateLinkedin: string | null;
    candidateEmail: string | null;
  };
  statusSummary: {
    roleStatus: string;
    emailStatus: string;
    plausibilityStatus: string;
    writebackEligibility: string;
  };
  scores: {
    roleScore: number;
    emailScore: number;
    plausibilityScore: number;
  };
  evidenceSummary: string[];
  blockerSummary: string[];
  suggestedHumanAction: string;
  rawReferences: {
    topSearchQueries: string[];
    topSearchUrls: string[];
    topWebsitePages: string[];
  };
}

export interface ReviewQueueSummary {
  totalItems: number;
  byBucket: Record<string, number>;
  byPriority: Record<string, number>;
  byRole: Record<string, number>;
  byWorkbook: Record<string, number>;
}
