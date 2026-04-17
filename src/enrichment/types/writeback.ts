import type { TargetRole } from "./prospect";

// ---------------------------------------------------------------------------
// Write action types
// ---------------------------------------------------------------------------

export type WriteActionType =
  | "WRITE_CELL"
  | "SKIP_EXISTING_VALUE"
  | "SKIP_NOT_APPROVED"
  | "SKIP_BLOCKED"
  | "SKIP_EMPTY_VALUE"
  | "SKIP_COLUMN_MISSING"
  | "ERROR";

export interface WriteAction {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  role: TargetRole;
  columnName: string;
  actionType: WriteActionType;
  oldValue: string;
  newValue: string | null;
  reason: string;
  confidenceLabel: string | null;
  evidenceSummary: string[];
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Writeback config
// ---------------------------------------------------------------------------

export interface WritebackConfig {
  overwriteExistingNames: boolean;
  overwriteExistingLinkedins: boolean;
  overwriteExistingEmails: boolean;
  allowedEligibilityStatuses: string[];
}

// ---------------------------------------------------------------------------
// Run summary
// ---------------------------------------------------------------------------

export interface WritebackRunSummary {
  totalRowsProcessed: number;
  totalRoleDecisionsConsidered: number;
  totalActions: number;
  writesApplied: number;
  skipsExisting: number;
  skipsNotApproved: number;
  skipsBlocked: number;
  skipsEmpty: number;
  skipsColumnMissing: number;
  errors: number;
  byWorkbook: Record<string, { writes: number; skips: number }>;
  byRole: Record<string, { writes: number; skips: number }>;
  byColumn: Record<string, { writes: number; skips: number }>;
}
