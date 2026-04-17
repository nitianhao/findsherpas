import * as path from "path";
import * as fs from "fs";
import { loadManualReviewCsv } from "../review/manualReviewLoader";
import {
  resolveManualReviewRows,
  generateFollowUpWriteActions,
} from "../review/manualReviewResolver";
import type { ResolvedManualReviewDecision } from "../types/manualReview";
import type { WriteAction } from "../types/writeback";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

function main() {
  console.log("=== PROCESS MANUAL REVIEW DECISIONS ===\n");

  const csvPath = path.join(ROOT_DIR, "docs", "review-queue-for-human-review.csv");

  // Load and validate
  const { rows, errors, warnings } = loadManualReviewCsv(csvPath);

  if (errors.length > 0) {
    console.error("FATAL: CSV validation errors:");
    for (const e of errors) console.error(`  ${e}`);
    process.exit(1);
  }

  if (warnings.length > 0) {
    console.warn("Warnings:");
    for (const w of warnings) console.warn(`  ${w}`);
  }

  console.log(`Loaded ${rows.length} review rows\n`);

  // Resolve decisions
  const resolved = resolveManualReviewRows(rows);

  // Count decisions
  const decisionCounts: Record<string, number> = {};
  for (const r of resolved) {
    decisionCounts[r.humanDecision] = (decisionCounts[r.humanDecision] ?? 0) + 1;
  }

  console.log("Decision counts:");
  for (const [d, c] of Object.entries(decisionCounts)) {
    console.log(`  ${d}: ${c}`);
  }

  // Count approved fields
  const approved = resolved.filter((r) => r.approvedFields.length > 0);
  const rejected = resolved.filter((r) => r.humanDecision === "REJECT_CANDIDATE");
  const keepExisting = resolved.filter((r) => r.humanDecision === "KEEP_EXISTING");
  const needsResearch = resolved.filter((r) => r.humanDecision === "NEEDS_MORE_RESEARCH");
  const skipped = resolved.filter((r) => r.humanDecision === "SKIP");

  console.log(`\nApproved: ${approved.length}`);
  console.log(`Rejected: ${rejected.length}`);
  console.log(`Keep existing: ${keepExisting.length}`);
  console.log(`Needs research: ${needsResearch.length}`);
  console.log(`Skipped: ${skipped.length}`);

  // Check blocking issues
  const withIssues = resolved.filter((r) => r.blockingIssues.length > 0);
  if (withIssues.length > 0) {
    console.log(`\nBlocking issues (${withIssues.length}):`);
    for (const r of withIssues) {
      console.log(`  ${r.companyName} ${r.role}: ${r.blockingIssues.join(", ")}`);
    }
  }

  // Generate follow-up write actions
  const writeActions = generateFollowUpWriteActions(resolved);
  const writeCells = writeActions.filter((a) => a.actionType === "WRITE_CELL");
  const skipActions = writeActions.filter((a) => a.actionType !== "WRITE_CELL");

  console.log(`\n--- Follow-up Write Actions ---`);
  console.log(`WRITE_CELL: ${writeCells.length}`);
  console.log(`Skipped: ${skipActions.length}`);

  // By workbook
  const byWorkbook: Record<string, number> = {};
  for (const a of writeCells) {
    byWorkbook[a.sourceFile] = (byWorkbook[a.sourceFile] ?? 0) + 1;
  }
  console.log("\nBy workbook:");
  for (const [f, c] of Object.entries(byWorkbook)) {
    console.log(`  ${f}: ${c}`);
  }

  // By role
  const byRole: Record<string, number> = {};
  for (const a of writeCells) {
    byRole[a.role] = (byRole[a.role] ?? 0) + 1;
  }
  console.log("\nBy role:");
  for (const [r, c] of Object.entries(byRole)) {
    console.log(`  ${r}: ${c}`);
  }

  // By column
  const byColumn: Record<string, number> = {};
  for (const a of writeCells) {
    byColumn[a.columnName] = (byColumn[a.columnName] ?? 0) + 1;
  }
  console.log("\nBy column:");
  for (const [col, c] of Object.entries(byColumn)) {
    console.log(`  ${col}: ${c}`);
  }

  // Print examples
  if (writeCells.length > 0) {
    console.log(`\n--- Top approved write examples ---\n`);
    for (const a of writeCells.slice(0, 10)) {
      console.log(`  [WRITE] ${a.companyName.padEnd(22)} ${a.role.padEnd(20)} ${a.columnName}`);
      console.log(`          value="${a.newValue}"`);
      console.log(`          ${a.evidenceSummary.join(", ")}`);
      console.log("");
    }
  }

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");

  const decisionsPath = path.join(docsDir, "manual-review-decisions.json");
  fs.writeFileSync(decisionsPath, JSON.stringify(resolved, null, 2), "utf-8");
  console.log(`\nDecisions: ${decisionsPath}`);

  const actionsPath = path.join(docsDir, "manual-review-approved-actions.json");
  fs.writeFileSync(actionsPath, JSON.stringify(writeActions, null, 2), "utf-8");
  console.log(`Actions: ${actionsPath}`);

  const mdPath = path.join(docsDir, "manual-review-summary.md");
  fs.writeFileSync(mdPath, generateSummaryMarkdown(resolved, writeActions, decisionCounts), "utf-8");
  console.log(`Summary: ${mdPath}`);
}

function generateSummaryMarkdown(
  resolved: ResolvedManualReviewDecision[],
  writeActions: WriteAction[],
  decisionCounts: Record<string, number>,
): string {
  const writeCells = writeActions.filter((a) => a.actionType === "WRITE_CELL");

  const lines: string[] = [
    "# Manual Review Summary",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    `Total reviewed: ${resolved.length}`,
    "",
    "## Decision Counts",
    "",
    "| Decision | Count |",
    "|----------|-------|",
  ];

  for (const [d, c] of Object.entries(decisionCounts)) {
    lines.push(`| ${d} | ${c} |`);
  }

  // Approved actions
  lines.push("", "## Approved Write Actions", "");

  if (writeCells.length === 0) {
    lines.push("No approved write actions.");
  } else {
    // By workbook
    const byWb: Record<string, number> = {};
    const byRole: Record<string, number> = {};
    const byCol: Record<string, number> = {};
    for (const a of writeCells) {
      byWb[a.sourceFile] = (byWb[a.sourceFile] ?? 0) + 1;
      byRole[a.role] = (byRole[a.role] ?? 0) + 1;
      byCol[a.columnName] = (byCol[a.columnName] ?? 0) + 1;
    }

    lines.push("### By Workbook", "", "| Workbook | Writes |", "|----------|--------|");
    for (const [f, c] of Object.entries(byWb)) lines.push(`| ${f} | ${c} |`);

    lines.push("", "### By Role", "", "| Role | Writes |", "|------|--------|");
    for (const [r, c] of Object.entries(byRole)) lines.push(`| ${r} | ${c} |`);

    lines.push("", "### By Column", "", "| Column | Writes |", "|--------|--------|");
    for (const [col, c] of Object.entries(byCol)) lines.push(`| ${col} | ${c} |`);

    lines.push(
      "",
      "### Write Examples",
      "",
      "| Company | Role | Column | Value | Decision |",
      "|---------|------|--------|-------|----------|",
    );
    for (const a of writeCells.slice(0, 15)) {
      lines.push(`| ${a.companyName} | ${a.role} | ${a.columnName} | ${a.newValue} | ${a.reason} |`);
    }
  }

  // Rejected
  const rejected = resolved.filter((r) => r.humanDecision === "REJECT_CANDIDATE");
  if (rejected.length > 0) {
    lines.push("", "## Rejected", "");
    lines.push("| Company | Role | Candidate | Notes |");
    lines.push("|---------|------|-----------|-------|");
    for (const r of rejected) {
      lines.push(`| ${r.companyName} | ${r.role} | ${r.approvedName ?? "--"} | ${r.notes} |`);
    }
  }

  // Needs research
  const research = resolved.filter((r) => r.humanDecision === "NEEDS_MORE_RESEARCH");
  if (research.length > 0) {
    lines.push("", "## Needs More Research", "");
    lines.push("| Company | Role | Candidate | Notes |");
    lines.push("|---------|------|-----------|-------|");
    for (const r of research) {
      lines.push(`| ${r.companyName} | ${r.role} | ${r.approvedName ?? "--"} | ${r.notes} |`);
    }
  }

  return lines.join("\n");
}

main();
