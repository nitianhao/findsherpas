import type { TargetRole } from "./prospect";
import type { ResolvedRoleStatus, ConfidenceLabel } from "./resolution";
import type { EmailResolutionStatus, EmailConfidenceLabel } from "./email";

// ---------------------------------------------------------------------------
// Person plausibility
// ---------------------------------------------------------------------------

export type PersonPlausibilityStatus =
  | "PLAUSIBLE"
  | "SUSPICIOUS"
  | "IMPLAUSIBLE";

export interface PersonPlausibilityDecision {
  personName: string;
  companyName: string;
  role: TargetRole;
  status: PersonPlausibilityStatus;
  score: number;
  positiveSignals: string[];
  negativeSignals: string[];
  notes: string[];
}

// ---------------------------------------------------------------------------
// Writeback eligibility
// ---------------------------------------------------------------------------

export type WritebackEligibilityStatus =
  | "ELIGIBLE"
  | "REVIEW"
  | "BLOCKED";

export interface WritebackFieldDecision {
  field: string;
  status: WritebackEligibilityStatus;
  value: string | null;
  reason: string;
}

export interface WritebackEligibilityDecision {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  role: TargetRole;
  overallStatus: WritebackEligibilityStatus;
  plausibility: PersonPlausibilityDecision;
  fields: WritebackFieldDecision[];
  notes: string[];
}
