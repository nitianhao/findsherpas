import * as path from "path";
import * as fs from "fs";
import * as XLSX from "xlsx";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import {
  readNormalizedRows,
  loadPrimarySheet,
  createBackup,
  saveWorkbookInPlace,
} from "../io/workbookService";
import { planAllRows } from "../planning/taskPlanner";
import { resolveRoleDecision } from "../resolution/roleResolver";
import { resolveEmailForRole } from "../email/emailResolver";
import { getWritebackEligibility } from "../quality/writebackEligibility";
import {
  buildApprovedWriteActions,
  applyWriteActionsToWorkbook,
  summarizeWriteActions,
  DEFAULT_WRITEBACK_CONFIG,
} from "../writeback/workbookWriteback";
import type { WritebackInput } from "../writeback/workbookWriteback";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { getCachedRoleSearchResult } from "../cache/searchCache";
import type { Region } from "../types/prospect";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

function main() {
  console.log("=== WRITEBACK APPLY ===\n");

  // Load workbooks (mutable)
  const workbooksByFile = new Map<string, XLSX.WorkBook>();
  const worksheetsByFile = new Map<string, XLSX.WorkSheet>();
  const filePathsByFile = new Map<string, string>();
  const regionByFile = new Map<string, Region>();

  for (const config of ALL_CONFIGS) {
    try {
      const { workbook, worksheet, filePath } = loadPrimarySheet(config, ROOT_DIR);
      workbooksByFile.set(config.filename, workbook);
      worksheetsByFile.set(config.filename, worksheet);
      filePathsByFile.set(config.filename, filePath);
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

  // Build writeback inputs
  const inputs: WritebackInput[] = [];
  let totalRoleDecisions = 0;

  for (const rowTask of plannedRows) {
    for (const roleTask of rowTask.roleTasks) {
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

  // Build write actions
  const actions = buildApprovedWriteActions(
    inputs,
    worksheetsByFile,
    DEFAULT_WRITEBACK_CONFIG,
  );

  const writeCells = actions.filter((a) => a.actionType === "WRITE_CELL");
  console.log(`\nTotal WRITE_CELL actions: ${writeCells.length}`);

  if (writeCells.length === 0) {
    console.log("No writes to apply. Exiting without modifying workbooks.");
    return;
  }

  // Create backups before writing
  console.log("\nCreating backups...");
  const filesToSave = new Set(writeCells.map((a) => a.sourceFile));

  for (const filename of filesToSave) {
    const filePath = filePathsByFile.get(filename);
    if (!filePath) {
      console.error(`FATAL: No file path for ${filename}`);
      process.exit(1);
    }
    const backupPath = createBackup(filePath);
    if (backupPath) {
      console.log(`  Backup: ${backupPath}`);
    } else {
      console.error(`FATAL: Could not create backup for ${filename}`);
      process.exit(1);
    }
  }

  // Apply writes
  console.log("\nApplying writes...");
  const { applied, errors } = applyWriteActionsToWorkbook(actions, worksheetsByFile);
  console.log(`  Applied: ${applied}`);
  if (errors.length > 0) {
    console.error(`  Errors: ${errors.length}`);
    for (const e of errors) console.error(`    ${e}`);
  }

  // Save workbooks
  console.log("\nSaving workbooks...");
  for (const filename of filesToSave) {
    const workbook = workbooksByFile.get(filename)!;
    const filePath = filePathsByFile.get(filename)!;
    saveWorkbookInPlace(workbook, filePath);
    console.log(`  Saved: ${filePath}`);
  }

  // Generate summary and reports
  const summary = summarizeWriteActions(actions, allRows.length, totalRoleDecisions);

  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "writeback-apply-report.json");
  fs.writeFileSync(
    jsonPath,
    JSON.stringify({ summary, actions }, null, 2),
    "utf-8",
  );
  console.log(`\nJSON report: ${jsonPath}`);

  const mdPath = path.join(docsDir, "writeback-apply-report.md");
  fs.writeFileSync(mdPath, generateApplyMarkdown(summary, actions), "utf-8");
  console.log(`Markdown report: ${mdPath}`);

  console.log("\nDone.");
}

function generateApplyMarkdown(
  summary: ReturnType<typeof summarizeWriteActions>,
  actions: ReturnType<typeof buildApprovedWriteActions>,
): string {
  const lines: string[] = [
    "# Writeback Apply Report",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    "## Summary",
    "",
    `| Metric | Count |`,
    `|--------|-------|`,
    `| Rows processed | ${summary.totalRowsProcessed} |`,
    `| Role decisions | ${summary.totalRoleDecisionsConsidered} |`,
    `| **Writes applied** | **${summary.writesApplied}** |`,
    `| Skips (existing) | ${summary.skipsExisting} |`,
    `| Skips (not approved) | ${summary.skipsNotApproved} |`,
    `| Skips (blocked) | ${summary.skipsBlocked} |`,
    `| Skips (empty) | ${summary.skipsEmpty} |`,
    `| Errors | ${summary.errors} |`,
    "",
    "## Applied Writes",
    "",
    "| Company | Role | Column | Value | Old Value | Confidence |",
    "|---------|------|--------|-------|-----------|------------|",
  ];

  const writes = actions.filter((a) => a.actionType === "WRITE_CELL");
  for (const a of writes) {
    lines.push(
      `| ${a.companyName} | ${a.role} | ${a.columnName} | ${a.newValue} | ${a.oldValue || "--"} | ${a.confidenceLabel ?? "--"} |`,
    );
  }

  return lines.join("\n");
}

main();
