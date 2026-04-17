import type { Region, TargetRole } from "./prospect";
import type { EmailSourceType, PageType } from "./discovery";

// ---------------------------------------------------------------------------
// Observed email from website discovery
// ---------------------------------------------------------------------------

export interface ObservedWorkEmail {
  email: string;
  domain: string;
  localPart: string;
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  pageUrl: string;
  pageType: PageType;
  sourceType: EmailSourceType;
  confidenceSignals: string[];
}

// ---------------------------------------------------------------------------
// Email pattern classification
// ---------------------------------------------------------------------------

export type EmailPatternType =
  | "FIRST_LAST"     // john.smith
  | "FIRST.DOT.LAST" // john.smith (alias for clarity)
  | "FIRSTLAST"      // johnsmith
  | "F_LAST"         // jsmith
  | "F.DOT.LAST"     // j.smith
  | "FIRST"          // john
  | "LAST"           // smith
  | "UNKNOWN";

export interface InferredDomainPattern {
  domain: string;
  patternType: EmailPatternType;
  confidenceScore: number;
  evidenceEmails: string[];
  notes: string[];
}

// ---------------------------------------------------------------------------
// Generated email candidates
// ---------------------------------------------------------------------------

export type EmailConfidenceLabel = "STRONG" | "PROBABLE" | "WEAK";

export interface GeneratedEmailCandidate {
  email: string;
  domain: string;
  patternType: EmailPatternType;
  personName: string;
  role: TargetRole;
  evidence: string[];
  confidenceScore: number;
  confidenceLabel: EmailConfidenceLabel;
}

// ---------------------------------------------------------------------------
// Final email resolution
// ---------------------------------------------------------------------------

export type EmailResolutionStatus =
  | "RESOLVED_PUBLIC"
  | "RESOLVED_INFERRED"
  | "UNRESOLVED";

export interface ResolvedEmailDecision {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  websiteUrl: string;
  role: TargetRole;
  personName: string;
  status: EmailResolutionStatus;
  chosenEmail: string | null;
  alternateEmails: GeneratedEmailCandidate[];
  inferredPattern: InferredDomainPattern | null;
  evidence: string[];
  confidenceScore: number;
  confidenceLabel: EmailConfidenceLabel | null;
  blockingIssues: string[];
}
