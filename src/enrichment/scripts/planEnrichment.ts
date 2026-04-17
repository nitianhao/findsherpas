import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import {
  planAllRows,
  getReadyRoleTasks,
  summarizePlannedTasks,
} from "../planning/taskPlanner";
import type { PlannedRoleTask, PlannedRowTask } from "../types/tasks";
import type { ProspectRowNormalized } from "../types/prospect";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Load all rows
// ---------------------------------------------------------------------------

const allRows: ProspectRowNormalized[] = [];
for (const config of ALL_CONFIGS) {
  const rows = readNormalizedRows(config, ROOT_DIR);
  console.log(`Loaded ${rows.length} rows from ${config.filename}`);
  allRows.push(...rows);
}

// ---------------------------------------------------------------------------
// Plan
// ---------------------------------------------------------------------------

const plannedRows: PlannedRowTask[] = planAllRows(allRows);
const readyTasks: PlannedRoleTask[] = getReadyRoleTasks(plannedRows);
const summary = summarizePlannedTasks(plannedRows);

// ---------------------------------------------------------------------------
// Console output
// ---------------------------------------------------------------------------

console.log("\n=== ENRICHMENT TASK PLAN ===\n");
console.log(`Total rows:              ${summary.totalRows}`);
console.log(`Total planned row tasks: ${summary.totalPlannedRowTasks}`);
console.log(`Total READY role tasks:  ${summary.totalReadyRoleTasks}`);
console.log(`Skip (complete):         ${summary.skipComplete}`);
console.log(`Skip (no website):       ${summary.skipNoWebsite}`);
console.log(`Skip (no company name):  ${summary.skipNoCompanyName}`);

console.log("\nREADY tasks by workbook:");
for (const [file, count] of Object.entries(summary.readyByWorkbook)) {
  console.log(`  ${file}: ${count}`);
}

console.log("\nREADY tasks by role:");
for (const [role, count] of Object.entries(summary.readyByRole)) {
  console.log(`  ${role}: ${count}`);
}

console.log("\nTop 25 highest-priority READY tasks:");
console.log(
  "  " +
    ["#", "Workbook", "Row", "Company", "Role", "Missing", "Score"].join(
      " | ",
    ),
);
console.log("  " + "-".repeat(100));

const top25 = readyTasks.slice(0, 25);
top25.forEach((t, i) => {
  const fields = t.missingFields.join(", ");
  const company =
    t.companyName.length > 30
      ? t.companyName.slice(0, 27) + "..."
      : t.companyName;
  const wb =
    t.sourceFile.length > 20
      ? t.sourceFile.slice(0, 17) + "..."
      : t.sourceFile;
  console.log(
    `  ${String(i + 1).padStart(2)} | ${wb.padEnd(20)} | ${String(t.rowIndex).padStart(3)} | ${company.padEnd(30)} | ${t.role.padEnd(18)} | ${fields.padEnd(35)} | ${t.priorityScore}`,
  );
});

// ---------------------------------------------------------------------------
// Markdown report
// ---------------------------------------------------------------------------

function generateMarkdown(): string {
  const lines: string[] = [
    "# Enrichment Task Plan",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    "---",
    "",
    "## Summary",
    "",
    `| Metric | Count |`,
    `|--------|-------|`,
    `| Total rows | ${summary.totalRows} |`,
    `| Total planned row tasks | ${summary.totalPlannedRowTasks} |`,
    `| Total READY role tasks | ${summary.totalReadyRoleTasks} |`,
    `| Skip (complete) | ${summary.skipComplete} |`,
    `| Skip (no website) | ${summary.skipNoWebsite} |`,
    `| Skip (no company name) | ${summary.skipNoCompanyName} |`,
    "",
    "## READY Tasks by Workbook",
    "",
    "| Workbook | READY Tasks |",
    "|----------|-------------|",
  ];

  for (const [file, count] of Object.entries(summary.readyByWorkbook)) {
    lines.push(`| ${file} | ${count} |`);
  }

  lines.push("", "## READY Tasks by Role", "", "| Role | READY Tasks |", "|------|-------------|");
  for (const [role, count] of Object.entries(summary.readyByRole)) {
    lines.push(`| ${role} | ${count} |`);
  }

  lines.push(
    "",
    "## Top 25 Highest-Priority Tasks",
    "",
    "| # | Workbook | Row | Company | Role | Missing Fields | Score |",
    "|---|----------|-----|---------|------|----------------|-------|",
  );

  top25.forEach((t, i) => {
    lines.push(
      `| ${i + 1} | ${t.sourceFile} | ${t.rowIndex} | ${t.companyName} | ${t.role} | ${t.missingFields.join(", ")} | ${t.priorityScore} |`,
    );
  });

  lines.push("");
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Write outputs
// ---------------------------------------------------------------------------

const docsDir = path.resolve(ROOT_DIR, "docs");
if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

const mdPath = path.join(docsDir, "enrichment-task-plan.md");
fs.writeFileSync(mdPath, generateMarkdown(), "utf-8");
console.log(`\nMarkdown report: ${mdPath}`);

const jsonPath = path.join(docsDir, "enrichment-task-plan.json");
const jsonOutput = {
  generated: new Date().toISOString(),
  summary,
  top25: top25.map((t) => ({
    sourceFile: t.sourceFile,
    rowIndex: t.rowIndex,
    companyName: t.companyName,
    websiteUrl: t.websiteUrl,
    region: t.region,
    country: t.country,
    role: t.role,
    missingFields: t.missingFields,
    existingSignals: t.existingSignals,
    priorityScore: t.priorityScore,
    status: t.status,
  })),
  allReadyTaskCount: readyTasks.length,
};
fs.writeFileSync(jsonPath, JSON.stringify(jsonOutput, null, 2), "utf-8");
console.log(`JSON plan:       ${jsonPath}`);
