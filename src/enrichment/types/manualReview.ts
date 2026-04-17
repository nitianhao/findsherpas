import type { TargetRole } from "./prospect";
import type { ReviewBucket, ReviewPriority } from "./review";

// ---------------------------------------------------------------------------
// Manual review decision values
// ---------------------------------------------------------------------------

export type ManualReviewDecision =
  | "APPROVE_CANDIDATE"
  | "REJECT_CANDIDATE"
  | "KEEP_EXISTING"
  | "APPROVE_EMAIL_ONLY"
  | "APPROVE_ROLE_ONLY"
  | "APPROVE_ROLE_AND_LINKEDIN"
  | "NEEDS_MORE_RESEARCH"
  | "SKIP";

export const VALID_DECISIONS: ManualReviewDecision[] = [
  "APPROVE_CANDIDATE",
  "REJECT_CANDIDATE",
  "KEEP_EXISTING",
  "APPROVE_EMAIL_ONLY",
  "APPROVE_ROLE_ONLY",
  "APPROVE_ROLE_AND_LINKEDIN",
  "NEEDS_MORE_RESEARCH",
  "SKIP",
];

// ---------------------------------------------------------------------------
// Raw CSV row (loaded from human-reviewed CSV)
// ---------------------------------------------------------------------------

export interface ManualReviewRow {
  reviewId: string;
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  role: string;
  bucket: string;
  priority: string;
  existingName: string;
  candidateName: string;
  existingLinkedin: string;
  candidateLinkedin: string;
  candidateEmail: string;
  roleStatus: string;
  emailStatus: string;
  plausibilityStatus: string;
  writebackEligibility: string;
  roleScore: number;
  emailScore: number;
  suggestedHumanAction: string;
  evidenceSummary: string;
  blockerSummary: string;
  humanDecision: string;
  humanNotes: string;
}

// ---------------------------------------------------------------------------
// Resolved decision (after processing)
// ---------------------------------------------------------------------------

export interface ResolvedManualReviewDecision {
  reviewId: string;
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  role: string;
  humanDecision: ManualReviewDecision | "SKIP";
  approvedFields: string[];
  approvedName: string | null;
  approvedLinkedin: string | null;
  approvedEmail: string | null;
  notes: string;
  blockingIssues: string[];
}
