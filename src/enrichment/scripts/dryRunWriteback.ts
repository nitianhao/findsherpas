import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows, loadPrimarySheet } from "../io/workbookService";
import { planAllRows } from "../planning/taskPlanner";
import { resolveRoleDecision } from "../resolution/roleResolver";
import { resolveEmailForRole } from "../email/emailResolver";
import { getWritebackEligibility } from "../quality/writebackEligibility";
import {
  buildApprovedWriteActions,
  summarizeWriteActions,
  DEFAULT_WRITEBACK_CONFIG,
} from "../writeback/workbookWriteback";
import type { WritebackInput } from "../writeback/workbookWriteback";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { getCachedRoleSearchResult } from "../cache/searchCache";
import type { WriteAction, WritebackRunSummary } from "../types/writeback";
import type { Region } from "../types/prospect";
import type * as XLSX from "xlsx";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  console.log("=== WRITEBACK DRY RUN ===\n");

  // Load worksheets (read-only)
  const worksheetsByFile = new Map<string, XLSX.WorkSheet>();
  const regionByFile = new Map<string, Region>();

  for (const config of ALL_CONFIGS) {
    try {
      const { worksheet } = loadPrimarySheet(config, ROOT_DIR);
      worksheetsByFile.set(config.filename, worksheet);
      regionByFile.set(config.filename, config.region);
      console.log(`Loaded: ${config.filename} (${config.region})`);
    } catch (err) {
      console.error(`FATAL: Could not load ${config.filename}: ${err}`);
      process.exit(1);
    }
  }

  // Read and plan all rows
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);

  console.log(`Total rows: ${allRows.length}`);
  console.log(`Total planned row tasks: ${plannedRows.length}\n`);

  // Build writeback inputs by resolving each role task
  const inputs: WritebackInput[] = [];
  let totalRoleDecisions = 0;

  for (const rowTask of plannedRows) {
    for (const roleTask of rowTask.roleTasks) {
      // Skip tasks that can't produce results
      if (roleTask.status !== "READY") continue;

      totalRoleDecisions++;

      const discovery = getCachedDiscoveryResult(
        roleTask.sourceFile,
        roleTask.sheetName,
        roleTask.rowIndex,
        roleTask.websiteUrl,
      );

      const search = getCachedRoleSearchResult(
        roleTask.sourceFile,
        roleTask.sheetName,
        roleTask.rowIndex,
        roleTask.role,
        roleTask.websiteUrl,
        "BRAVE",
      );

      const roleDecision = resolveRoleDecision(roleTask, discovery, search);
      const emailDecision = resolveEmailForRole(roleDecision, discovery);
      const eligibility = getWritebackEligibility(roleDecision, emailDecision);

      inputs.push({
        roleDecision,
        emailDecision,
        eligibility,
        region: regionByFile.get(roleTask.sourceFile) ?? "US",
      });
    }
  }

  console.log(`Role decisions considered: ${totalRoleDecisions}`);
  console.log(`Writeback inputs generated: ${inputs.length}\n`);

  // Build write actions (dry run — no writes applied)
  const actions = buildApprovedWriteActions(
    inputs,
    worksheetsByFile,
    DEFAULT_WRITEBACK_CONFIG,
  );

  const summary = summarizeWriteActions(actions, allRows.length, totalRoleDecisions);

  // Print summary
  printSummary(summary);
  printExampleActions(actions);

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "writeback-dry-run.json");
  fs.writeFileSync(
    jsonPath,
    JSON.stringify({ summary, actions }, null, 2),
    "utf-8",
  );
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "writeback-dry-run.md");
  fs.writeFileSync(mdPath, generateMarkdown(summary, actions), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

// ---------------------------------------------------------------------------
// Print helpers
// ---------------------------------------------------------------------------

function printSummary(s: WritebackRunSummary) {
  console.log("--- Summary ---");
  console.log(`Total rows processed:    ${s.totalRowsProcessed}`);
  console.log(`Role decisions:          ${s.totalRoleDecisionsConsidered}`);
  console.log(`Total actions:           ${s.totalActions}`);
  console.log(`  WRITE_CELL:            ${s.writesApplied}`);
  console.log(`  SKIP_EXISTING_VALUE:   ${s.skipsExisting}`);
  console.log(`  SKIP_NOT_APPROVED:     ${s.skipsNotApproved}`);
  console.log(`  SKIP_BLOCKED:          ${s.skipsBlocked}`);
  console.log(`  SKIP_EMPTY_VALUE:      ${s.skipsEmpty}`);
  console.log(`  SKIP_COLUMN_MISSING:   ${s.skipsColumnMissing}`);
  console.log(`  ERROR:                 ${s.errors}`);

  console.log("\nBy workbook:");
  for (const [file, counts] of Object.entries(s.byWorkbook)) {
    console.log(`  ${file}: ${counts.writes} writes, ${counts.skips} skips`);
  }

  console.log("\nBy role:");
  for (const [role, counts] of Object.entries(s.byRole)) {
    console.log(`  ${role}: ${counts.writes} writes, ${counts.skips} skips`);
  }

  console.log("\nBy column:");
  for (const [col, counts] of Object.entries(s.byColumn)) {
    console.log(`  ${col}: ${counts.writes} writes, ${counts.skips} skips`);
  }
}

function printExampleActions(actions: WriteAction[]) {
  const writes = actions.filter((a) => a.actionType === "WRITE_CELL");
  const skips = actions.filter((a) => a.actionType !== "WRITE_CELL");

  console.log(`\n--- Example WRITE_CELL actions (${Math.min(30, writes.length)} of ${writes.length}) ---\n`);
  for (const a of writes.slice(0, 30)) {
    console.log(
      `  [WRITE] ${a.companyName.padEnd(22)} ${a.role.padEnd(20)} ${a.columnName}`,
    );
    console.log(
      `          value="${a.newValue}" conf=${a.confidenceLabel}`,
    );
    console.log(
      `          evidence: ${a.evidenceSummary.join(", ")}`,
    );
    console.log("");
  }

  console.log(`--- Example SKIP/BLOCKED actions (${Math.min(30, skips.length)} of ${skips.length}) ---\n`);
  for (const a of skips.slice(0, 30)) {
    console.log(
      `  [${a.actionType}] ${a.companyName.padEnd(22)} ${a.role.padEnd(20)} ${a.columnName}`,
    );
    console.log(`          reason: ${a.reason}`);
    if (a.newValue) console.log(`          would-write: "${a.newValue}"`);
    if (a.oldValue) console.log(`          existing: "${a.oldValue}"`);
    console.log("");
  }
}

// ---------------------------------------------------------------------------
// Markdown report
// ---------------------------------------------------------------------------

function generateMarkdown(summary: WritebackRunSummary, actions: WriteAction[]): string {
  const lines: string[] = [
    "# Writeback Dry Run Report",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    "## Summary",
    "",
    `| Metric | Count |`,
    `|--------|-------|`,
    `| Rows processed | ${summary.totalRowsProcessed} |`,
    `| Role decisions | ${summary.totalRoleDecisionsConsidered} |`,
    `| Total actions | ${summary.totalActions} |`,
    `| **WRITE_CELL** | **${summary.writesApplied}** |`,
    `| SKIP_EXISTING_VALUE | ${summary.skipsExisting} |`,
    `| SKIP_NOT_APPROVED | ${summary.skipsNotApproved} |`,
    `| SKIP_BLOCKED | ${summary.skipsBlocked} |`,
    `| SKIP_EMPTY_VALUE | ${summary.skipsEmpty} |`,
    `| SKIP_COLUMN_MISSING | ${summary.skipsColumnMissing} |`,
    `| ERROR | ${summary.errors} |`,
    "",
    "## By Workbook",
    "",
    "| Workbook | Writes | Skips |",
    "|----------|--------|-------|",
  ];

  for (const [file, counts] of Object.entries(summary.byWorkbook)) {
    lines.push(`| ${file} | ${counts.writes} | ${counts.skips} |`);
  }

  lines.push("", "## By Role", "", "| Role | Writes | Skips |", "|------|--------|-------|");
  for (const [role, counts] of Object.entries(summary.byRole)) {
    lines.push(`| ${role} | ${counts.writes} | ${counts.skips} |`);
  }

  lines.push("", "## By Column", "", "| Column | Writes | Skips |", "|--------|--------|-------|");
  for (const [col, counts] of Object.entries(summary.byColumn)) {
    lines.push(`| ${col} | ${counts.writes} | ${counts.skips} |`);
  }

  // Write examples
  const writes = actions.filter((a) => a.actionType === "WRITE_CELL");
  lines.push("", "## Write Examples", "");
  lines.push("| Company | Role | Column | Value | Confidence | Evidence |");
  lines.push("|---------|------|--------|-------|------------|----------|");
  for (const a of writes.slice(0, 30)) {
    lines.push(
      `| ${a.companyName} | ${a.role} | ${a.columnName} | ${a.newValue} | ${a.confidenceLabel ?? "--"} | ${a.evidenceSummary.join("; ")} |`,
    );
  }

  // Skip examples
  const skips = actions.filter((a) => a.actionType !== "WRITE_CELL");
  lines.push("", "## Skip/Block Examples", "");
  lines.push("| Company | Role | Column | Action | Reason |");
  lines.push("|---------|------|--------|--------|--------|");
  for (const a of skips.slice(0, 30)) {
    lines.push(`| ${a.companyName} | ${a.role} | ${a.columnName} | ${a.actionType} | ${a.reason} |`);
  }

  return lines.join("\n");
}

main();
