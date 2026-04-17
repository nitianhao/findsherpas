import * as XLSX from "xlsx";
import type { Region, TargetRole, WorkbookConfig } from "../types/prospect";
import type { ResolvedRoleDecision } from "../types/resolution";
import type { ResolvedEmailDecision } from "../types/email";
import type { WritebackEligibilityDecision, WritebackFieldDecision } from "../types/quality";
import type {
  WriteAction,
  WriteActionType,
  WritebackConfig,
  WritebackRunSummary,
} from "../types/writeback";
import { getHeaderRow } from "../io/workbookService";

// ---------------------------------------------------------------------------
// Default config — conservative: never overwrite
// ---------------------------------------------------------------------------

export const DEFAULT_WRITEBACK_CONFIG: WritebackConfig = {
  overwriteExistingNames: false,
  overwriteExistingLinkedins: false,
  overwriteExistingEmails: false,
  allowedEligibilityStatuses: ["ELIGIBLE"],
};

// ---------------------------------------------------------------------------
// Column mapping: role+field → workbook column name
// ---------------------------------------------------------------------------

interface ColumnMapEntry {
  role: TargetRole;
  fieldType: "NAME" | "LINKEDIN" | "EMAIL";
  qualityField: string; // field name in WritebackFieldDecision
  columnByRegion: { US: string; EU: string };
}

const COLUMN_MAP: ColumnMapEntry[] = [
  {
    role: "CEO",
    fieldType: "NAME",
    qualityField: "CEO_NAME",
    columnByRegion: { US: "CEO / Founder Name", EU: "CEO / MD Name" },
  },
  {
    role: "CEO",
    fieldType: "LINKEDIN",
    qualityField: "CEO_LINKEDIN",
    columnByRegion: { US: "CEO LinkedIn Profile", EU: "CEO LinkedIn Profile" },
  },
  {
    role: "CEO",
    fieldType: "EMAIL",
    qualityField: "CEO_EMAIL",
    columnByRegion: { US: "CEO Email", EU: "CEO Email" },
  },
  {
    role: "HEAD_OF_PRODUCT",
    fieldType: "NAME",
    qualityField: "HEAD_OF_PRODUCT_NAME",
    columnByRegion: { US: "Head of Product (Name)", EU: "Head of Product (Name)" },
  },
  {
    role: "HEAD_OF_PRODUCT",
    fieldType: "EMAIL",
    qualityField: "HEAD_OF_PRODUCT_EMAIL",
    columnByRegion: { US: "Head of Product Email", EU: "Head of Product Email" },
  },
  {
    role: "HEAD_OF_ECOMMERCE",
    fieldType: "NAME",
    qualityField: "HEAD_OF_ECOMMERCE_NAME",
    columnByRegion: { US: "Head of Ecommerce (Name)", EU: "Head of Ecommerce (Name)" },
  },
  {
    role: "HEAD_OF_ECOMMERCE",
    fieldType: "EMAIL",
    qualityField: "HEAD_OF_ECOMMERCE_EMAIL",
    columnByRegion: { US: "Head of Ecommerce Email", EU: "Head of Ecommerce Email" },
  },
  {
    role: "HEAD_OF_GROWTH",
    fieldType: "NAME",
    qualityField: "HEAD_OF_GROWTH_NAME",
    columnByRegion: { US: "Head of Growth / CMO (Name)", EU: "Head of Growth / CMO (Name)" },
  },
  {
    role: "HEAD_OF_GROWTH",
    fieldType: "EMAIL",
    qualityField: "HEAD_OF_GROWTH_EMAIL",
    columnByRegion: { US: "Head of Growth / CMO Email", EU: "Head of Growth / CMO Email" },
  },
];

function getColumnName(role: TargetRole, fieldType: string, region: Region): string | null {
  const entry = COLUMN_MAP.find((e) => e.role === role && e.fieldType === fieldType);
  if (!entry) return null;
  return entry.columnByRegion[region];
}

// ---------------------------------------------------------------------------
// Read existing cell value
// ---------------------------------------------------------------------------

function readCellValue(
  worksheet: XLSX.WorkSheet,
  rowIndex: number,
  columnName: string,
): string {
  const headers = getHeaderRow(worksheet);
  const colIdx = headers.indexOf(columnName);
  if (colIdx < 0) return "";
  const addr = XLSX.utils.encode_cell({ r: rowIndex, c: colIdx });
  const cell = worksheet[addr];
  return cell ? String(cell.v).trim() : "";
}

// ---------------------------------------------------------------------------
// Build evidence summary for a write action
// ---------------------------------------------------------------------------

function buildEvidenceSummary(
  roleDecision: ResolvedRoleDecision,
  emailDecision: ResolvedEmailDecision | null,
  eligibility: WritebackEligibilityDecision,
  fieldType: string,
): string[] {
  const evidence: string[] = [];

  evidence.push(`role=${roleDecision.status}`);
  evidence.push(`plausibility=${eligibility.plausibility.status}(${eligibility.plausibility.score})`);

  if (roleDecision.chosenCandidate) {
    evidence.push(`person_confidence=${roleDecision.chosenCandidate.confidenceLabel}(${roleDecision.chosenCandidate.confidenceScore})`);
    if (roleDecision.chosenCandidate.linkedinUrl) {
      evidence.push("linkedin=present");
    }
    evidence.push(`sources=${roleDecision.chosenCandidate.sourceKinds.join("+")}`);
  }

  if (fieldType === "EMAIL" && emailDecision) {
    evidence.push(`email=${emailDecision.status}`);
    if (emailDecision.confidenceLabel) {
      evidence.push(`email_confidence=${emailDecision.confidenceLabel}(${emailDecision.confidenceScore})`);
    }
    if (emailDecision.inferredPattern) {
      evidence.push(`pattern=${emailDecision.inferredPattern.patternType}`);
    }
  }

  return evidence;
}

// ---------------------------------------------------------------------------
// Build approved write actions for a single role
// ---------------------------------------------------------------------------

function buildActionsForRole(
  roleDecision: ResolvedRoleDecision,
  emailDecision: ResolvedEmailDecision | null,
  eligibility: WritebackEligibilityDecision,
  region: Region,
  worksheet: XLSX.WorkSheet,
  config: WritebackConfig,
): WriteAction[] {
  const actions: WriteAction[] = [];
  const now = new Date().toISOString();
  const headers = getHeaderRow(worksheet);

  for (const fieldDecision of eligibility.fields) {
    const fieldType = fieldDecision.field.replace(/^(CEO|HEAD_OF_\w+)_/, "");
    const columnName = getColumnName(roleDecision.role, fieldType, region);

    // No column in workbook for this field (e.g. non-CEO LinkedIn)
    if (!columnName) {
      // Only create skip action if there was a value to write
      if (fieldDecision.value) {
        actions.push({
          sourceFile: roleDecision.sourceFile,
          sheetName: roleDecision.sheetName,
          rowIndex: roleDecision.rowIndex,
          companyName: roleDecision.companyName,
          role: roleDecision.role,
          columnName: fieldDecision.field,
          actionType: "SKIP_COLUMN_MISSING",
          oldValue: "",
          newValue: fieldDecision.value,
          reason: `No workbook column for ${fieldDecision.field}`,
          confidenceLabel: null,
          evidenceSummary: [],
          timestamp: now,
        });
      }
      continue;
    }

    // Check column exists in actual worksheet headers
    if (!headers.includes(columnName)) {
      if (fieldDecision.value) {
        actions.push({
          sourceFile: roleDecision.sourceFile,
          sheetName: roleDecision.sheetName,
          rowIndex: roleDecision.rowIndex,
          companyName: roleDecision.companyName,
          role: roleDecision.role,
          columnName,
          actionType: "SKIP_COLUMN_MISSING",
          oldValue: "",
          newValue: fieldDecision.value,
          reason: `Column "${columnName}" not found in worksheet headers`,
          confidenceLabel: null,
          evidenceSummary: [],
          timestamp: now,
        });
      }
      continue;
    }

    const oldValue = readCellValue(worksheet, roleDecision.rowIndex, columnName);
    const newValue = fieldDecision.value;

    // No value to write
    if (!newValue || newValue.trim() === "") {
      actions.push({
        sourceFile: roleDecision.sourceFile,
        sheetName: roleDecision.sheetName,
        rowIndex: roleDecision.rowIndex,
        companyName: roleDecision.companyName,
        role: roleDecision.role,
        columnName,
        actionType: "SKIP_EMPTY_VALUE",
        oldValue,
        newValue: null,
        reason: "No value to write",
        confidenceLabel: null,
        evidenceSummary: [],
        timestamp: now,
      });
      continue;
    }

    // Field not approved
    if (fieldDecision.status === "BLOCKED") {
      actions.push({
        sourceFile: roleDecision.sourceFile,
        sheetName: roleDecision.sheetName,
        rowIndex: roleDecision.rowIndex,
        companyName: roleDecision.companyName,
        role: roleDecision.role,
        columnName,
        actionType: "SKIP_BLOCKED",
        oldValue,
        newValue,
        reason: fieldDecision.reason,
        confidenceLabel: null,
        evidenceSummary: [],
        timestamp: now,
      });
      continue;
    }

    if (fieldDecision.status === "REVIEW") {
      if (!config.allowedEligibilityStatuses.includes("REVIEW")) {
        actions.push({
          sourceFile: roleDecision.sourceFile,
          sheetName: roleDecision.sheetName,
          rowIndex: roleDecision.rowIndex,
          companyName: roleDecision.companyName,
          role: roleDecision.role,
          columnName,
          actionType: "SKIP_NOT_APPROVED",
          oldValue,
          newValue,
          reason: `Status REVIEW not in allowed statuses: ${fieldDecision.reason}`,
          confidenceLabel: null,
          evidenceSummary: [],
          timestamp: now,
        });
        continue;
      }
    }

    // Cell already has a value — check overwrite policy
    if (oldValue !== "") {
      const canOverwrite =
        (fieldType === "NAME" && config.overwriteExistingNames) ||
        (fieldType === "LINKEDIN" && config.overwriteExistingLinkedins) ||
        (fieldType === "EMAIL" && config.overwriteExistingEmails);

      if (!canOverwrite) {
        actions.push({
          sourceFile: roleDecision.sourceFile,
          sheetName: roleDecision.sheetName,
          rowIndex: roleDecision.rowIndex,
          companyName: roleDecision.companyName,
          role: roleDecision.role,
          columnName,
          actionType: "SKIP_EXISTING_VALUE",
          oldValue,
          newValue,
          reason: `Cell already has value "${oldValue}" — overwrite disabled`,
          confidenceLabel: roleDecision.chosenCandidate?.confidenceLabel ?? null,
          evidenceSummary: buildEvidenceSummary(roleDecision, emailDecision, eligibility, fieldType),
          timestamp: now,
        });
        continue;
      }
    }

    // Approved write
    actions.push({
      sourceFile: roleDecision.sourceFile,
      sheetName: roleDecision.sheetName,
      rowIndex: roleDecision.rowIndex,
      companyName: roleDecision.companyName,
      role: roleDecision.role,
      columnName,
      actionType: "WRITE_CELL",
      oldValue,
      newValue,
      reason: fieldDecision.reason,
      confidenceLabel: roleDecision.chosenCandidate?.confidenceLabel ?? null,
      evidenceSummary: buildEvidenceSummary(roleDecision, emailDecision, eligibility, fieldType),
      timestamp: now,
    });
  }

  return actions;
}

// ---------------------------------------------------------------------------
// Build all write actions across all rows and roles
// ---------------------------------------------------------------------------

export interface WritebackInput {
  roleDecision: ResolvedRoleDecision;
  emailDecision: ResolvedEmailDecision | null;
  eligibility: WritebackEligibilityDecision;
  region: Region;
}

export function buildApprovedWriteActions(
  inputs: WritebackInput[],
  worksheetsByFile: Map<string, XLSX.WorkSheet>,
  config: WritebackConfig = DEFAULT_WRITEBACK_CONFIG,
): WriteAction[] {
  const allActions: WriteAction[] = [];

  for (const input of inputs) {
    const worksheet = worksheetsByFile.get(input.roleDecision.sourceFile);
    if (!worksheet) {
      allActions.push({
        sourceFile: input.roleDecision.sourceFile,
        sheetName: input.roleDecision.sheetName,
        rowIndex: input.roleDecision.rowIndex,
        companyName: input.roleDecision.companyName,
        role: input.roleDecision.role,
        columnName: "N/A",
        actionType: "ERROR",
        oldValue: "",
        newValue: null,
        reason: `Worksheet not loaded for file ${input.roleDecision.sourceFile}`,
        confidenceLabel: null,
        evidenceSummary: [],
        timestamp: new Date().toISOString(),
      });
      continue;
    }

    const actions = buildActionsForRole(
      input.roleDecision,
      input.emailDecision,
      input.eligibility,
      input.region,
      worksheet,
      config,
    );
    allActions.push(...actions);
  }

  return allActions;
}

// ---------------------------------------------------------------------------
// Apply write actions to workbook worksheets
// ---------------------------------------------------------------------------

export function applyWriteActionsToWorkbook(
  actions: WriteAction[],
  worksheetsByFile: Map<string, XLSX.WorkSheet>,
): { applied: number; errors: string[] } {
  let applied = 0;
  const errors: string[] = [];

  const writeCells = actions.filter((a) => a.actionType === "WRITE_CELL");

  for (const action of writeCells) {
    const worksheet = worksheetsByFile.get(action.sourceFile);
    if (!worksheet) {
      errors.push(`No worksheet for ${action.sourceFile}`);
      continue;
    }

    const headers = getHeaderRow(worksheet);
    const colIdx = headers.indexOf(action.columnName);
    if (colIdx < 0) {
      errors.push(`Column "${action.columnName}" not found in ${action.sourceFile}`);
      continue;
    }

    const addr = XLSX.utils.encode_cell({ r: action.rowIndex, c: colIdx });
    worksheet[addr] = { t: "s", v: action.newValue };
    applied++;
  }

  return { applied, errors };
}

// ---------------------------------------------------------------------------
// Summarize write actions
// ---------------------------------------------------------------------------

export function summarizeWriteActions(
  actions: WriteAction[],
  totalRowsProcessed: number,
  totalRoleDecisions: number,
): WritebackRunSummary {
  const summary: WritebackRunSummary = {
    totalRowsProcessed,
    totalRoleDecisionsConsidered: totalRoleDecisions,
    totalActions: actions.length,
    writesApplied: 0,
    skipsExisting: 0,
    skipsNotApproved: 0,
    skipsBlocked: 0,
    skipsEmpty: 0,
    skipsColumnMissing: 0,
    errors: 0,
    byWorkbook: {},
    byRole: {},
    byColumn: {},
  };

  for (const a of actions) {
    // Top-level counts
    switch (a.actionType) {
      case "WRITE_CELL": summary.writesApplied++; break;
      case "SKIP_EXISTING_VALUE": summary.skipsExisting++; break;
      case "SKIP_NOT_APPROVED": summary.skipsNotApproved++; break;
      case "SKIP_BLOCKED": summary.skipsBlocked++; break;
      case "SKIP_EMPTY_VALUE": summary.skipsEmpty++; break;
      case "SKIP_COLUMN_MISSING": summary.skipsColumnMissing++; break;
      case "ERROR": summary.errors++; break;
    }

    const isWrite = a.actionType === "WRITE_CELL";

    // By workbook
    if (!summary.byWorkbook[a.sourceFile]) {
      summary.byWorkbook[a.sourceFile] = { writes: 0, skips: 0 };
    }
    if (isWrite) summary.byWorkbook[a.sourceFile].writes++;
    else summary.byWorkbook[a.sourceFile].skips++;

    // By role
    if (!summary.byRole[a.role]) {
      summary.byRole[a.role] = { writes: 0, skips: 0 };
    }
    if (isWrite) summary.byRole[a.role].writes++;
    else summary.byRole[a.role].skips++;

    // By column
    if (!summary.byColumn[a.columnName]) {
      summary.byColumn[a.columnName] = { writes: 0, skips: 0 };
    }
    if (isWrite) summary.byColumn[a.columnName].writes++;
    else summary.byColumn[a.columnName].skips++;
  }

  return summary;
}
