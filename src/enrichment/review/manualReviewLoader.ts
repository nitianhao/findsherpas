import * as fs from "fs";
import Papa from "papaparse";
import type { ManualReviewRow } from "../types/manualReview";
import { VALID_DECISIONS } from "../types/manualReview";

// ---------------------------------------------------------------------------
// Required columns
// ---------------------------------------------------------------------------

const REQUIRED_COLUMNS = [
  "reviewId",
  "workbook",
  "rowIndex",
  "company",
  "role",
  "bucket",
  "priority",
  "candidateName",
  "candidateLinkedin",
  "candidateEmail",
  "humanDecision",
];

// ---------------------------------------------------------------------------
// Load and validate
// ---------------------------------------------------------------------------

export interface LoadResult {
  rows: ManualReviewRow[];
  errors: string[];
  warnings: string[];
}

export function loadManualReviewCsv(csvPath: string): LoadResult {
  if (!fs.existsSync(csvPath)) {
    return { rows: [], errors: [`File not found: ${csvPath}`], warnings: [] };
  }

  const raw = fs.readFileSync(csvPath, "utf-8");
  const parsed = Papa.parse(raw, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (h) => h.trim(),
  });

  const errors: string[] = [];
  const warnings: string[] = [];

  // Validate headers
  const headers = parsed.meta.fields ?? [];
  for (const col of REQUIRED_COLUMNS) {
    if (!headers.includes(col)) {
      errors.push(`Missing required column: "${col}"`);
    }
  }

  if (errors.length > 0) {
    return { rows: [], errors, warnings };
  }

  const rows: ManualReviewRow[] = [];

  for (let i = 0; i < parsed.data.length; i++) {
    const raw = parsed.data[i] as Record<string, string>;
    const lineNum = i + 2; // +1 for header, +1 for 1-based

    const reviewId = (raw.reviewId ?? "").trim();
    const sourceFile = (raw.workbook ?? "").trim();
    const rowIndex = parseInt(raw.rowIndex ?? "", 10);
    const companyName = (raw.company ?? "").trim();
    const role = (raw.role ?? "").trim();
    const bucket = (raw.bucket ?? "").trim();
    const priority = (raw.priority ?? "").trim();
    const humanDecision = (raw.humanDecision ?? "").trim().toUpperCase();
    const humanNotes = (raw.humanNotes ?? "").trim();

    // Skip completely empty rows
    if (!reviewId && !companyName && !role) continue;

    // Validate reviewId
    if (!reviewId) {
      errors.push(`Line ${lineNum}: missing reviewId`);
      continue;
    }

    // Validate rowIndex
    if (isNaN(rowIndex)) {
      errors.push(`Line ${lineNum}: invalid rowIndex "${raw.rowIndex}"`);
      continue;
    }

    // Validate decision (blank = SKIP)
    const normalizedDecision = humanDecision || "SKIP";
    if (
      normalizedDecision !== "SKIP" &&
      !VALID_DECISIONS.includes(normalizedDecision as any)
    ) {
      errors.push(
        `Line ${lineNum} (${companyName}): invalid humanDecision "${raw.humanDecision}". Valid values: ${VALID_DECISIONS.join(", ")}`,
      );
      continue;
    }

    rows.push({
      reviewId,
      sourceFile,
      sheetName: (raw.sheetName ?? "").trim(),
      rowIndex,
      companyName,
      role,
      bucket,
      priority,
      existingName: (raw.existingName ?? "").trim(),
      candidateName: (raw.candidateName ?? "").trim(),
      existingLinkedin: (raw.existingLinkedin ?? "").trim(),
      candidateLinkedin: (raw.candidateLinkedin ?? "").trim(),
      candidateEmail: (raw.candidateEmail ?? "").trim(),
      roleStatus: (raw.roleStatus ?? "").trim(),
      emailStatus: (raw.emailStatus ?? "").trim(),
      plausibilityStatus: (raw.plausibilityStatus ?? "").trim(),
      writebackEligibility: (raw.writebackEligibility ?? "").trim(),
      roleScore: parseInt(raw.roleScore ?? "0", 10) || 0,
      emailScore: parseInt(raw.emailScore ?? "0", 10) || 0,
      suggestedHumanAction: (raw.suggestedHumanAction ?? "").trim(),
      evidenceSummary: (raw.evidenceSummary ?? "").trim(),
      blockerSummary: (raw.blockerSummary ?? "").trim(),
      humanDecision: normalizedDecision,
      humanNotes,
    });
  }

  return { rows, errors, warnings };
}
