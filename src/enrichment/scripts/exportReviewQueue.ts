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
  DEFAULT_WRITEBACK_CONFIG,
} from "../writeback/workbookWriteback";
import type { WritebackInput } from "../writeback/workbookWriteback";
import {
  buildReviewQueue,
  summarizeReviewQueue,
} from "../review/reviewQueueBuilder";
import type { ReviewInput } from "../review/reviewQueueBuilder";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { getCachedRoleSearchResult } from "../cache/searchCache";
import type { ReviewQueueItem, ReviewQueueSummary } from "../types/review";
import type { Region } from "../types/prospect";
import type * as XLSX from "xlsx";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  console.log("=== REVIEW QUEUE EXPORT ===\n");

  // Load worksheets
  const worksheetsByFile = new Map<string, XLSX.WorkSheet>();
  const regionByFile = new Map<string, Region>();

  for (const config of ALL_CONFIGS) {
    const { worksheet } = loadPrimarySheet(config, ROOT_DIR);
    worksheetsByFile.set(config.filename, worksheet);
    regionByFile.set(config.filename, config.region);
    console.log(`Loaded: ${config.filename}`);
  }

  // Read and plan
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);

  console.log(`Total rows: ${allRows.length}\n`);

  // Build inputs for both writeback actions and review queue
  const writebackInputs: WritebackInput[] = [];
  const reviewInputs: ReviewInput[] = [];

  for (const rowTask of plannedRows) {
    for (const roleTask of rowTask.roleTasks) {
      if (roleTask.status !== "READY") continue;

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

      const region = regionByFile.get(roleTask.sourceFile) ?? "US";

      writebackInputs.push({
        roleDecision,
        emailDecision,
        eligibility,
        region,
      });

      // Build write actions for this role (to detect skips)
      const roleWriteActions = buildApprovedWriteActions(
        [{ roleDecision, emailDecision, eligibility, region }],
        worksheetsByFile,
        DEFAULT_WRITEBACK_CONFIG,
      );

      reviewInputs.push({
        task: roleTask,
        roleDecision,
        emailDecision,
        eligibility,
        writeActions: roleWriteActions,
        discovery,
        search,
      });
    }
  }

  console.log(`Review inputs: ${reviewInputs.length}\n`);

  // Build review queue
  const queue = buildReviewQueue(reviewInputs);
  const summary = summarizeReviewQueue(queue);

  printSummary(summary);
  printTopItems(queue);

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "review-queue.json");
  fs.writeFileSync(
    jsonPath,
    JSON.stringify({ summary, items: queue }, null, 2),
    "utf-8",
  );
  console.log(`\nJSON: ${jsonPath}`);

  const mdPath = path.join(docsDir, "review-queue.md");
  fs.writeFileSync(mdPath, generateMarkdown(summary, queue), "utf-8");
  console.log(`Markdown: ${mdPath}`);

  const csvPath = path.join(docsDir, "review-queue.csv");
  fs.writeFileSync(csvPath, generateCsv(queue), "utf-8");
  console.log(`CSV: ${csvPath}`);
}

// ---------------------------------------------------------------------------
// Print helpers
// ---------------------------------------------------------------------------

function printSummary(s: ReviewQueueSummary) {
  console.log("--- Summary ---");
  console.log(`Total review items: ${s.totalItems}\n`);

  console.log("By priority:");
  for (const [p, c] of Object.entries(s.byPriority)) {
    console.log(`  ${p}: ${c}`);
  }

  console.log("\nBy bucket:");
  for (const [b, c] of Object.entries(s.byBucket)) {
    console.log(`  ${b}: ${c}`);
  }

  console.log("\nBy role:");
  for (const [r, c] of Object.entries(s.byRole)) {
    console.log(`  ${r}: ${c}`);
  }

  console.log("\nBy workbook:");
  for (const [w, c] of Object.entries(s.byWorkbook)) {
    console.log(`  ${w}: ${c}`);
  }
}

function printTopItems(queue: ReviewQueueItem[]) {
  const highItems = queue.filter((i) => i.priority === "HIGH");
  console.log(`\n--- Top HIGH priority items (${Math.min(15, highItems.length)} of ${highItems.length}) ---\n`);

  for (const item of highItems.slice(0, 15)) {
    console.log(
      `  ${item.companyName.padEnd(22)} ${item.role.padEnd(20)} [${item.bucket}]`,
    );
    console.log(
      `    Candidate: ${item.candidateValues.candidateName ?? "none"} | LI: ${item.candidateValues.candidateLinkedin ? "yes" : "no"} | Email: ${item.candidateValues.candidateEmail ?? "none"}`,
    );
    console.log(
      `    Role: ${item.statusSummary.roleStatus} (${item.scores.roleScore}) | Plausibility: ${item.statusSummary.plausibilityStatus} (${item.scores.plausibilityScore})`,
    );
    console.log(`    Action: ${item.suggestedHumanAction}`);
    if (item.blockerSummary.length > 0) {
      console.log(`    Blockers: ${item.blockerSummary[0]}`);
    }
    console.log("");
  }
}

// ---------------------------------------------------------------------------
// Markdown report
// ---------------------------------------------------------------------------

function generateMarkdown(summary: ReviewQueueSummary, queue: ReviewQueueItem[]): string {
  const lines: string[] = [
    "# Review Queue Export",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    `Total items: ${summary.totalItems}`,
    "",
    "## Summary",
    "",
    "### By Priority",
    "",
    "| Priority | Count |",
    "|----------|-------|",
  ];

  for (const [p, c] of Object.entries(summary.byPriority)) {
    lines.push(`| ${p} | ${c} |`);
  }

  lines.push("", "### By Bucket", "", "| Bucket | Count |", "|--------|-------|");
  for (const [b, c] of Object.entries(summary.byBucket)) {
    lines.push(`| ${b} | ${c} |`);
  }

  lines.push("", "### By Role", "", "| Role | Count |", "|------|-------|");
  for (const [r, c] of Object.entries(summary.byRole)) {
    lines.push(`| ${r} | ${c} |`);
  }

  lines.push("", "### By Workbook", "", "| Workbook | Count |", "|----------|-------|");
  for (const [w, c] of Object.entries(summary.byWorkbook)) {
    lines.push(`| ${w} | ${c} |`);
  }

  // Top 25 HIGH priority
  const highItems = queue.filter((i) => i.priority === "HIGH");
  lines.push(
    "",
    "---",
    "",
    `## Top HIGH Priority Items (${Math.min(25, highItems.length)} of ${highItems.length})`,
    "",
    "| # | Company | Role | Bucket | Candidate | LinkedIn | Score | Action |",
    "|---|---------|------|--------|-----------|----------|-------|--------|",
  );

  for (let i = 0; i < Math.min(25, highItems.length); i++) {
    const item = highItems[i];
    lines.push(
      `| ${i + 1} | ${item.companyName} | ${item.role} | ${item.bucket} | ${item.candidateValues.candidateName ?? "--"} | ${item.candidateValues.candidateLinkedin ? "yes" : "no"} | ${item.scores.roleScore} | ${item.suggestedHumanAction} |`,
    );
  }

  // Sections by bucket
  const buckets = [...new Set(queue.map((i) => i.bucket))];
  for (const bucket of buckets) {
    const bucketItems = queue.filter((i) => i.bucket === bucket);
    lines.push(
      "",
      "---",
      "",
      `## ${bucket} (${bucketItems.length} items)`,
      "",
      "| Company | Role | Priority | Candidate | Score | Action |",
      "|---------|------|----------|-----------|-------|--------|",
    );

    for (const item of bucketItems.slice(0, 20)) {
      lines.push(
        `| ${item.companyName} | ${item.role} | ${item.priority} | ${item.candidateValues.candidateName ?? "--"} | ${item.scores.roleScore} | ${item.suggestedHumanAction} |`,
      );
    }

    if (bucketItems.length > 20) {
      lines.push(`| ... | ... | ... | ${bucketItems.length - 20} more | ... | ... |`);
    }
  }

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// CSV export
// ---------------------------------------------------------------------------

function escapeCsv(val: string): string {
  if (val.includes(",") || val.includes('"') || val.includes("\n")) {
    return `"${val.replace(/"/g, '""')}"`;
  }
  return val;
}

function generateCsv(queue: ReviewQueueItem[]): string {
  const header = [
    "workbook",
    "rowIndex",
    "company",
    "role",
    "bucket",
    "priority",
    "existingName",
    "candidateName",
    "existingLinkedin",
    "candidateLinkedin",
    "candidateEmail",
    "roleStatus",
    "emailStatus",
    "plausibilityStatus",
    "writebackEligibility",
    "roleScore",
    "emailScore",
    "suggestedHumanAction",
    "evidenceSummary",
    "blockerSummary",
  ].join(",");

  const rows = queue.map((item) =>
    [
      escapeCsv(item.sourceFile),
      String(item.rowIndex),
      escapeCsv(item.companyName),
      item.role,
      item.bucket,
      item.priority,
      escapeCsv(item.currentWorkbookValues.existingName),
      escapeCsv(item.candidateValues.candidateName ?? ""),
      escapeCsv(item.currentWorkbookValues.existingLinkedin),
      escapeCsv(item.candidateValues.candidateLinkedin ?? ""),
      escapeCsv(item.candidateValues.candidateEmail ?? ""),
      item.statusSummary.roleStatus,
      item.statusSummary.emailStatus,
      item.statusSummary.plausibilityStatus,
      item.statusSummary.writebackEligibility,
      String(item.scores.roleScore),
      String(item.scores.emailScore),
      escapeCsv(item.suggestedHumanAction),
      escapeCsv(item.evidenceSummary.join("; ")),
      escapeCsv(item.blockerSummary.join("; ")),
    ].join(","),
  );

  return [header, ...rows].join("\n");
}

main();
