import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { planAllRows, getReadyRoleTasks } from "../planning/taskPlanner";
import { resolveRoleDecision } from "../resolution/roleResolver";
import { resolveEmailForRole } from "../email/emailResolver";
import { evaluatePersonPlausibility } from "../quality/personPlausibility";
import { getWritebackEligibility } from "../quality/writebackEligibility";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { getCachedRoleSearchResult } from "../cache/searchCache";
import type { PlannedRoleTask } from "../types/tasks";
import type { TargetRole } from "../types/prospect";
import type { ResolvedRoleDecision } from "../types/resolution";
import type { ResolvedEmailDecision } from "../types/email";
import type {
  PersonPlausibilityDecision,
  WritebackEligibilityDecision,
} from "../types/quality";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Select 20 test tasks — mix of roles and regions, prioritize resolved
// ---------------------------------------------------------------------------

function selectTestTasks(readyTasks: PlannedRoleTask[]): PlannedRoleTask[] {
  const targets: { role: TargetRole; count: number }[] = [
    { role: "CEO", count: 8 },
    { role: "HEAD_OF_ECOMMERCE", count: 5 },
    { role: "HEAD_OF_PRODUCT", count: 4 },
    { role: "HEAD_OF_GROWTH", count: 3 },
  ];

  const selected: PlannedRoleTask[] = [];
  const usedCompanies = new Set<string>();

  for (const target of targets) {
    const roleTasks = readyTasks
      .filter((t) => t.role === target.role)
      .sort((a, b) => b.priorityScore - a.priorityScore);

    let added = 0;
    let preferEU = false;
    for (const task of roleTasks) {
      if (added >= target.count) break;
      if (usedCompanies.has(task.companyName)) continue;
      if (added > 0 && added < target.count) {
        const wantEU = preferEU;
        if (wantEU && task.region !== "EU") continue;
        if (
          !wantEU &&
          task.region !== "US" &&
          roleTasks.some(
            (t) => t.region === "US" && !usedCompanies.has(t.companyName),
          )
        )
          continue;
      }
      usedCompanies.add(task.companyName);
      selected.push(task);
      added++;
      preferEU = !preferEU;
    }

    if (added < target.count) {
      for (const task of roleTasks) {
        if (added >= target.count) break;
        if (usedCompanies.has(task.companyName)) continue;
        usedCompanies.add(task.companyName);
        selected.push(task);
        added++;
      }
    }
  }

  return selected;
}

// ---------------------------------------------------------------------------
// Synthetic bad-name test cases
// ---------------------------------------------------------------------------

interface SyntheticCase {
  name: string;
  company: string;
  role: TargetRole;
  linkedin: string;
  expectedStatus: "PLAUSIBLE" | "SUSPICIOUS" | "IMPLAUSIBLE";
  description: string;
}

const SYNTHETIC_CASES: SyntheticCase[] = [
  {
    name: "Faherty Brand",
    company: "Faherty",
    role: "CEO",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "Company name masquerading as person",
  },
  {
    name: "Preisgekrönter Onlineshop",
    company: "hessnatur",
    role: "CEO",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "German marketing phrase",
  },
  {
    name: "The Reformation",
    company: "Reformation",
    role: "CEO",
    linkedin: "https://linkedin.com/company/reformation",
    expectedStatus: "IMPLAUSIBLE",
    description: "Company LinkedIn page, not person",
  },
  {
    name: "Beitrag von Guenter Lichtner",
    company: "hessnatur",
    role: "CEO",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "LinkedIn post artifact",
  },
  {
    name: "Sustainable Dresses",
    company: "Reformation",
    role: "HEAD_OF_PRODUCT",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "Ecommerce product noise",
  },
  {
    name: "Customer Service",
    company: "Tecovas",
    role: "HEAD_OF_GROWTH",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "Generic department name",
  },
  {
    name: "12345 Test",
    company: "TestCo",
    role: "CEO",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "Starts with digits",
  },
  {
    name: "alex",
    company: "Faherty",
    role: "CEO",
    linkedin: "",
    expectedStatus: "IMPLAUSIBLE",
    description: "Single lowercase word",
  },
  {
    name: "JOHN SMITH",
    company: "TestCo",
    role: "CEO",
    linkedin: "",
    expectedStatus: "SUSPICIOUS",
    description: "All uppercase — suspicious but could be real",
  },
  // Good names that should pass
  {
    name: "Alex Faherty",
    company: "Faherty",
    role: "CEO",
    linkedin: "https://linkedin.com/in/alexfaherty",
    expectedStatus: "PLAUSIBLE",
    description: "Real CEO with LinkedIn — last name matches company but first name is real",
  },
  {
    name: "Yael Aflalo",
    company: "Reformation",
    role: "CEO",
    linkedin: "https://linkedin.com/in/yael-aflalo-12345",
    expectedStatus: "PLAUSIBLE",
    description: "Real CEO with LinkedIn profile",
  },
  {
    name: "Paul Hedrick",
    company: "Tecovas",
    role: "CEO",
    linkedin: "https://linkedin.com/in/paulhedrick",
    expectedStatus: "PLAUSIBLE",
    description: "Real CEO with matching LinkedIn slug",
  },
  {
    name: "Marc Rosen",
    company: "JTV",
    role: "CEO",
    linkedin: "https://linkedin.com/in/marc-rosen-456",
    expectedStatus: "PLAUSIBLE",
    description: "Standard 2-token name with LinkedIn",
  },
  {
    name: "Guenter Lichtner",
    company: "hessnatur",
    role: "CEO",
    linkedin: "https://linkedin.com/in/guenterlichtner",
    expectedStatus: "PLAUSIBLE",
    description: "German name with LinkedIn",
  },
  {
    name: "Jean-Pierre Dupont",
    company: "SomeCompany",
    role: "HEAD_OF_PRODUCT",
    linkedin: "",
    expectedStatus: "PLAUSIBLE",
    description: "Hyphenated French name, no LinkedIn",
  },
];

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  // --- Part 1: Synthetic cases ---
  console.log("=== SYNTHETIC PLAUSIBILITY TESTS ===\n");

  let syntheticPass = 0;
  let syntheticFail = 0;

  for (const tc of SYNTHETIC_CASES) {
    const result = evaluatePersonPlausibility(
      tc.name,
      tc.company,
      tc.role,
      tc.linkedin,
      null,
    );

    const passed = result.status === tc.expectedStatus;
    const icon = passed ? "PASS" : "FAIL";
    if (passed) syntheticPass++;
    else syntheticFail++;

    console.log(
      `  [${icon}] "${tc.name}" => ${result.status} (expected ${tc.expectedStatus}, score: ${result.score})`,
    );
    console.log(`         ${tc.description}`);
    if (result.negativeSignals.length > 0) {
      console.log(`         Negative: ${result.negativeSignals.join("; ")}`);
    }
    if (result.positiveSignals.length > 0) {
      console.log(`         Positive: ${result.positiveSignals.join("; ")}`);
    }
    if (!passed) {
      console.log(`         !!! UNEXPECTED RESULT !!!`);
    }
    console.log("");
  }

  console.log(
    `Synthetic results: ${syntheticPass}/${SYNTHETIC_CASES.length} passed, ${syntheticFail} failed\n`,
  );

  // --- Part 2: Real pipeline data ---
  console.log("=== PIPELINE QUALITY GATE (real data) ===\n");

  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);
  const readyTasks = getReadyRoleTasks(plannedRows);
  const testTasks = selectTestTasks(readyTasks);

  console.log(`Testing quality gate for ${testTasks.length} roles:\n`);

  const results: WritebackEligibilityDecision[] = [];

  for (const task of testTasks) {
    const discovery = getCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
    );

    const search = getCachedRoleSearchResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.role,
      task.websiteUrl,
      "BRAVE",
    );

    const roleDecision = resolveRoleDecision(task, discovery, search);
    const emailDecision = resolveEmailForRole(roleDecision, discovery);
    const writeback = getWritebackEligibility(roleDecision, emailDecision);

    results.push(writeback);
    printWritebackDecision(writeback, roleDecision, emailDecision);
  }

  printAggregateSummary(results);

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "test-quality-gate.json");
  fs.writeFileSync(jsonPath, JSON.stringify(results, null, 2), "utf-8");
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "test-quality-gate.md");
  fs.writeFileSync(mdPath, generateMarkdown(results), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

function printWritebackDecision(
  wb: WritebackEligibilityDecision,
  role: ResolvedRoleDecision,
  email: ResolvedEmailDecision,
) {
  const person = role.chosenCandidate?.fullName ?? "NONE";
  const plaus = wb.plausibility;

  console.log(
    `  ${wb.companyName.padEnd(22)} ${wb.role.padEnd(20)} ${person}`,
  );
  console.log(
    `    Plausibility: ${plaus.status} (score: ${plaus.score})`,
  );
  console.log(`    Overall writeback: ${wb.overallStatus}`);

  for (const f of wb.fields) {
    const val = f.value ? f.value.substring(0, 50) : "--";
    console.log(`      ${f.field.padEnd(25)} ${f.status.padEnd(10)} ${val}`);
    if (f.status !== "ELIGIBLE") {
      console.log(`        Reason: ${f.reason}`);
    }
  }

  if (plaus.negativeSignals.length > 0) {
    console.log(`    Negatives: ${plaus.negativeSignals.join("; ")}`);
  }
  if (wb.notes.length > 0) {
    console.log(`    Notes: ${wb.notes.join("; ")}`);
  }

  console.log("");
}

function printAggregateSummary(results: WritebackEligibilityDecision[]) {
  console.log("=== AGGREGATE SUMMARY ===\n");

  // Plausibility breakdown
  const plausCounts: Record<string, number> = {};
  for (const r of results) {
    plausCounts[r.plausibility.status] =
      (plausCounts[r.plausibility.status] ?? 0) + 1;
  }
  console.log("Plausibility:");
  for (const [status, count] of Object.entries(plausCounts)) {
    console.log(`  ${status}: ${count}`);
  }

  // Writeback overall
  const wbCounts: Record<string, number> = {};
  for (const r of results) {
    wbCounts[r.overallStatus] = (wbCounts[r.overallStatus] ?? 0) + 1;
  }
  console.log("\nWriteback eligibility:");
  for (const [status, count] of Object.entries(wbCounts)) {
    console.log(`  ${status}: ${count}`);
  }

  // Field-level
  const fieldCounts: Record<string, Record<string, number>> = {};
  for (const r of results) {
    for (const f of r.fields) {
      const key = f.field.replace(/^(CEO|HEAD_OF_\w+)_/, "");
      if (!fieldCounts[key]) fieldCounts[key] = {};
      fieldCounts[key][f.status] = (fieldCounts[key][f.status] ?? 0) + 1;
    }
  }
  console.log("\nBy field type:");
  for (const [field, counts] of Object.entries(fieldCounts)) {
    const parts = Object.entries(counts)
      .map(([s, c]) => `${s}:${c}`)
      .join(", ");
    console.log(`  ${field}: ${parts}`);
  }

  // By role
  console.log("\nBy role:");
  const roleCounts: Record<string, { total: number; eligible: number; review: number; blocked: number }> = {};
  for (const r of results) {
    if (!roleCounts[r.role])
      roleCounts[r.role] = { total: 0, eligible: 0, review: 0, blocked: 0 };
    roleCounts[r.role].total++;
    if (r.overallStatus === "ELIGIBLE") roleCounts[r.role].eligible++;
    else if (r.overallStatus === "REVIEW") roleCounts[r.role].review++;
    else roleCounts[r.role].blocked++;
  }
  for (const [role, counts] of Object.entries(roleCounts)) {
    console.log(
      `  ${role}: ${counts.eligible} eligible, ${counts.review} review, ${counts.blocked} blocked (of ${counts.total})`,
    );
  }
}

function generateMarkdown(results: WritebackEligibilityDecision[]): string {
  const lines: string[] = [
    "# Quality Gate Test Results",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    `Cases tested: ${results.length}`,
    "",
    "---",
    "",
    "## Summary",
    "",
    "| Company | Role | Person | Plausibility | Writeback | Name | LinkedIn | Email |",
    "|---------|------|--------|--------------|-----------|------|----------|-------|",
  ];

  for (const r of results) {
    const person = r.plausibility.personName || "--";
    const nameF = r.fields.find((f) => f.field.endsWith("_NAME"));
    const liF = r.fields.find((f) => f.field.endsWith("_LINKEDIN"));
    const emF = r.fields.find((f) => f.field.endsWith("_EMAIL"));
    lines.push(
      `| ${r.companyName} | ${r.role} | ${person} | ${r.plausibility.status} (${r.plausibility.score}) | ${r.overallStatus} | ${nameF?.status ?? "--"} | ${liF?.status ?? "--"} | ${emF?.status ?? "--"} |`,
    );
  }

  lines.push("", "---", "");

  for (const r of results) {
    lines.push(`## ${r.companyName} -- ${r.role}`);
    lines.push("");
    lines.push(`- **Person:** ${r.plausibility.personName || "None"}`);
    lines.push(
      `- **Plausibility:** ${r.plausibility.status} (score: ${r.plausibility.score})`,
    );
    lines.push(`- **Overall writeback:** ${r.overallStatus}`);

    if (r.plausibility.positiveSignals.length > 0) {
      lines.push(`- **Positive signals:** ${r.plausibility.positiveSignals.join(", ")}`);
    }
    if (r.plausibility.negativeSignals.length > 0) {
      lines.push(`- **Negative signals:** ${r.plausibility.negativeSignals.join(", ")}`);
    }

    lines.push("");
    lines.push("| Field | Status | Value | Reason |");
    lines.push("|-------|--------|-------|--------|");
    for (const f of r.fields) {
      lines.push(
        `| ${f.field} | ${f.status} | ${f.value ?? "--"} | ${f.reason} |`,
      );
    }

    if (r.notes.length > 0) {
      lines.push("");
      lines.push(`- **Notes:** ${r.notes.join(", ")}`);
    }

    lines.push("", "---", "");
  }

  return lines.join("\n");
}

main();
