import type {
  ManualReviewRow,
  ManualReviewDecision,
  ResolvedManualReviewDecision,
} from "../types/manualReview";
import type { WriteAction } from "../types/writeback";
import type { Region, TargetRole } from "../types/prospect";

// ---------------------------------------------------------------------------
// Email-related buckets
// ---------------------------------------------------------------------------

const EMAIL_BUCKETS = new Set([
  "EMAIL_INFERRED_WEAK",
  "EMAIL_UNRESOLVED_BUT_DOMAIN_KNOWN",
]);

// ---------------------------------------------------------------------------
// Resolve a single review row into approved fields
// ---------------------------------------------------------------------------

function resolveOne(row: ManualReviewRow): ResolvedManualReviewDecision {
  const base: ResolvedManualReviewDecision = {
    reviewId: row.reviewId,
    sourceFile: row.sourceFile,
    sheetName: row.sheetName,
    rowIndex: row.rowIndex,
    companyName: row.companyName,
    role: row.role,
    humanDecision: row.humanDecision as ManualReviewDecision,
    approvedFields: [],
    approvedName: null,
    approvedLinkedin: null,
    approvedEmail: null,
    notes: row.humanNotes,
    blockingIssues: [],
  };

  const decision = row.humanDecision as ManualReviewDecision;

  if (
    decision === "SKIP" ||
    decision === "KEEP_EXISTING" ||
    decision === "REJECT_CANDIDATE" ||
    decision === "NEEDS_MORE_RESEARCH"
  ) {
    return base;
  }

  // Validate candidate values exist before approving
  const hasName = row.candidateName.trim() !== "";
  const hasLinkedin = row.candidateLinkedin.trim() !== "";
  const hasEmail = row.candidateEmail.trim() !== "";

  switch (decision) {
    case "APPROVE_CANDIDATE": {
      if (hasName) {
        base.approvedName = row.candidateName;
        base.approvedFields.push("NAME");
      } else {
        base.blockingIssues.push("APPROVE_CANDIDATE but no candidateName");
      }

      if (hasLinkedin) {
        base.approvedLinkedin = row.candidateLinkedin;
        base.approvedFields.push("LINKEDIN");
      }

      // Only approve email for email-related buckets
      if (hasEmail && EMAIL_BUCKETS.has(row.bucket)) {
        base.approvedEmail = row.candidateEmail;
        base.approvedFields.push("EMAIL");
      }
      break;
    }

    case "APPROVE_ROLE_ONLY": {
      if (hasName) {
        base.approvedName = row.candidateName;
        base.approvedFields.push("NAME");
      } else {
        base.blockingIssues.push("APPROVE_ROLE_ONLY but no candidateName");
      }
      break;
    }

    case "APPROVE_ROLE_AND_LINKEDIN": {
      if (hasName) {
        base.approvedName = row.candidateName;
        base.approvedFields.push("NAME");
      } else {
        base.blockingIssues.push("APPROVE_ROLE_AND_LINKEDIN but no candidateName");
      }

      if (hasLinkedin) {
        base.approvedLinkedin = row.candidateLinkedin;
        base.approvedFields.push("LINKEDIN");
      } else {
        base.blockingIssues.push("APPROVE_ROLE_AND_LINKEDIN but no candidateLinkedin");
      }
      break;
    }

    case "APPROVE_EMAIL_ONLY": {
      if (hasEmail) {
        base.approvedEmail = row.candidateEmail;
        base.approvedFields.push("EMAIL");
      } else {
        base.blockingIssues.push("APPROVE_EMAIL_ONLY but no candidateEmail");
      }
      break;
    }
  }

  return base;
}

// ---------------------------------------------------------------------------
// Resolve all review rows
// ---------------------------------------------------------------------------

export function resolveManualReviewRows(
  rows: ManualReviewRow[],
): ResolvedManualReviewDecision[] {
  return rows.map(resolveOne);
}

// ---------------------------------------------------------------------------
// Column mapping (reuse from writeback layer)
// ---------------------------------------------------------------------------

interface ColumnMapEntry {
  role: TargetRole;
  fieldType: "NAME" | "LINKEDIN" | "EMAIL";
  columnByRegion: { US: string; EU: string };
}

const COLUMN_MAP: ColumnMapEntry[] = [
  { role: "CEO", fieldType: "NAME", columnByRegion: { US: "CEO / Founder Name", EU: "CEO / MD Name" } },
  { role: "CEO", fieldType: "LINKEDIN", columnByRegion: { US: "CEO LinkedIn Profile", EU: "CEO LinkedIn Profile" } },
  { role: "CEO", fieldType: "EMAIL", columnByRegion: { US: "CEO Email", EU: "CEO Email" } },
  { role: "HEAD_OF_PRODUCT", fieldType: "NAME", columnByRegion: { US: "Head of Product (Name)", EU: "Head of Product (Name)" } },
  { role: "HEAD_OF_PRODUCT", fieldType: "EMAIL", columnByRegion: { US: "Head of Product Email", EU: "Head of Product Email" } },
  { role: "HEAD_OF_ECOMMERCE", fieldType: "NAME", columnByRegion: { US: "Head of Ecommerce (Name)", EU: "Head of Ecommerce (Name)" } },
  { role: "HEAD_OF_ECOMMERCE", fieldType: "EMAIL", columnByRegion: { US: "Head of Ecommerce Email", EU: "Head of Ecommerce Email" } },
  { role: "HEAD_OF_GROWTH", fieldType: "NAME", columnByRegion: { US: "Head of Growth / CMO (Name)", EU: "Head of Growth / CMO (Name)" } },
  { role: "HEAD_OF_GROWTH", fieldType: "EMAIL", columnByRegion: { US: "Head of Growth / CMO Email", EU: "Head of Growth / CMO Email" } },
];

function getColumnName(role: string, fieldType: string, region: Region): string | null {
  const entry = COLUMN_MAP.find((e) => e.role === role && e.fieldType === fieldType);
  if (!entry) return null;
  return entry.columnByRegion[region];
}

function getRegionFromFile(sourceFile: string): Region {
  return sourceFile.startsWith("EU") ? "EU" : "US";
}

// ---------------------------------------------------------------------------
// Generate follow-up write actions from approved decisions
// ---------------------------------------------------------------------------

export function generateFollowUpWriteActions(
  resolved: ResolvedManualReviewDecision[],
  overwriteExisting: boolean = false,
): WriteAction[] {
  const actions: WriteAction[] = [];
  const now = new Date().toISOString();

  for (const decision of resolved) {
    if (decision.approvedFields.length === 0) continue;

    const region = getRegionFromFile(decision.sourceFile);

    for (const fieldType of decision.approvedFields) {
      let value: string | null = null;
      if (fieldType === "NAME") value = decision.approvedName;
      if (fieldType === "LINKEDIN") value = decision.approvedLinkedin;
      if (fieldType === "EMAIL") value = decision.approvedEmail;

      if (!value || value.trim() === "") continue;

      const columnName = getColumnName(decision.role, fieldType, region);
      if (!columnName) {
        actions.push({
          sourceFile: decision.sourceFile,
          sheetName: decision.sheetName,
          rowIndex: decision.rowIndex,
          companyName: decision.companyName,
          role: decision.role as TargetRole,
          columnName: `${decision.role}_${fieldType}`,
          actionType: "SKIP_COLUMN_MISSING",
          oldValue: "",
          newValue: value,
          reason: `No workbook column for ${decision.role} ${fieldType}`,
          confidenceLabel: "MANUAL_REVIEW",
          evidenceSummary: [`Manually approved: ${decision.humanDecision}`, decision.notes].filter(Boolean),
          timestamp: now,
        });
        continue;
      }

      actions.push({
        sourceFile: decision.sourceFile,
        sheetName: decision.sheetName,
        rowIndex: decision.rowIndex,
        companyName: decision.companyName,
        role: decision.role as TargetRole,
        columnName,
        actionType: "WRITE_CELL",
        oldValue: "",
        newValue: value,
        reason: `Manually approved via ${decision.humanDecision}`,
        confidenceLabel: "MANUAL_REVIEW",
        evidenceSummary: [
          `reviewId: ${decision.reviewId}`,
          `decision: ${decision.humanDecision}`,
          decision.notes,
        ].filter(Boolean),
        timestamp: now,
      });
    }
  }

  return actions;
}
