import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { planAllRows, getReadyRoleTasks } from "../planning/taskPlanner";
import { resolveRoleDecision } from "../resolution/roleResolver";
import { resolveEmailForRole } from "../email/emailResolver";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { getCachedRoleSearchResult } from "../cache/searchCache";
import type { PlannedRoleTask } from "../types/tasks";
import type { TargetRole } from "../types/prospect";
import type { ResolvedRoleDecision } from "../types/resolution";
import type { ResolvedEmailDecision } from "../types/email";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Select 16 test tasks — prioritize resolved cases, mix roles and regions
// ---------------------------------------------------------------------------

function selectTestTasks(readyTasks: PlannedRoleTask[]): PlannedRoleTask[] {
  const targets: { role: TargetRole; count: number }[] = [
    { role: "CEO", count: 6 },
    { role: "HEAD_OF_ECOMMERCE", count: 4 },
    { role: "HEAD_OF_PRODUCT", count: 3 },
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
// Main
// ---------------------------------------------------------------------------

function main() {
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);
  const readyTasks = getReadyRoleTasks(plannedRows);
  const testTasks = selectTestTasks(readyTasks);

  console.log(`Testing email inference for ${testTasks.length} roles:\n`);

  const emailDecisions: Array<{
    roleDecision: ResolvedRoleDecision;
    emailDecision: ResolvedEmailDecision;
  }> = [];

  for (const task of testTasks) {
    const discovery = getCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
    );

    const search =
      getCachedRoleSearchResult(
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
        task.role,
        task.websiteUrl,
        "BRAVE",
      );

    const roleDecision = resolveRoleDecision(task, discovery, search);
    const emailDecision = resolveEmailForRole(roleDecision, discovery);

    emailDecisions.push({ roleDecision, emailDecision });
    printEmailDecision(roleDecision, emailDecision);
  }

  printAggregateSummary(emailDecisions.map((d) => d.emailDecision));

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "test-email-inference.json");
  fs.writeFileSync(
    jsonPath,
    JSON.stringify(emailDecisions.map((d) => d.emailDecision), null, 2),
    "utf-8",
  );
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "test-email-inference.md");
  fs.writeFileSync(mdPath, generateMarkdown(emailDecisions), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

function printEmailDecision(
  role: ResolvedRoleDecision,
  email: ResolvedEmailDecision,
) {
  const person = role.chosenCandidate
    ? `${role.chosenCandidate.fullName} (${role.status})`
    : `NONE (${role.status})`;

  const emailStr = email.chosenEmail
    ? `${email.chosenEmail} [${email.status}, ${email.confidenceLabel}, score:${email.confidenceScore}]`
    : `-- [${email.status}]`;

  console.log(
    `  ${email.companyName.padEnd(22)} ${email.role.padEnd(20)} ${person}`,
  );
  console.log(`    Email: ${emailStr}`);

  if (email.inferredPattern && email.inferredPattern.patternType !== "UNKNOWN") {
    console.log(
      `    Pattern: ${email.inferredPattern.patternType} (conf:${email.inferredPattern.confidenceScore}) from [${email.inferredPattern.evidenceEmails.join(", ")}]`,
    );
  }

  if (email.evidence.length > 0) {
    for (const e of email.evidence.slice(0, 3)) {
      console.log(`    ${e}`);
    }
  }

  if (email.blockingIssues.length > 0) {
    for (const b of email.blockingIssues) {
      console.log(`    BLOCKED: ${b}`);
    }
  }

  if (email.alternateEmails.length > 0) {
    console.log(
      `    Alternatives: ${email.alternateEmails.map((a) => a.email).join(", ")}`,
    );
  }

  console.log("");
}

function printAggregateSummary(decisions: ResolvedEmailDecision[]) {
  console.log("=== AGGREGATE SUMMARY ===\n");

  // By status
  const statusCounts: Record<string, number> = {};
  for (const d of decisions) {
    statusCounts[d.status] = (statusCounts[d.status] ?? 0) + 1;
  }
  console.log("By status:");
  for (const [status, count] of Object.entries(statusCounts)) {
    console.log(`  ${status}: ${count}`);
  }

  // By confidence
  const labelCounts: Record<string, number> = {};
  for (const d of decisions) {
    const label = d.confidenceLabel ?? "NONE";
    labelCounts[label] = (labelCounts[label] ?? 0) + 1;
  }
  console.log("\nBy confidence:");
  for (const [label, count] of Object.entries(labelCounts)) {
    console.log(`  ${label}: ${count}`);
  }

  // By role
  console.log("\nBy role:");
  const roleCounts: Record<string, { total: number; resolved: number }> = {};
  for (const d of decisions) {
    if (!roleCounts[d.role]) roleCounts[d.role] = { total: 0, resolved: 0 };
    roleCounts[d.role].total++;
    if (d.status !== "UNRESOLVED") roleCounts[d.role].resolved++;
  }
  for (const [role, counts] of Object.entries(roleCounts)) {
    console.log(`  ${role}: ${counts.resolved}/${counts.total} resolved`);
  }
}

function generateMarkdown(
  results: Array<{
    roleDecision: ResolvedRoleDecision;
    emailDecision: ResolvedEmailDecision;
  }>,
): string {
  const decisions = results.map((r) => r.emailDecision);
  const lines: string[] = [
    "# Email Inference Test Results",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    `Cases tested: ${decisions.length}`,
    "",
    "---",
    "",
    "## Summary",
    "",
    "| Company | Role | Person | Email Status | Email | Confidence | Pattern |",
    "|---------|------|--------|--------------|-------|------------|---------|",
  ];

  for (const { roleDecision: r, emailDecision: e } of results) {
    const person = r.chosenCandidate?.fullName ?? "--";
    const email = e.chosenEmail ?? "--";
    const conf = e.confidenceLabel
      ? `${e.confidenceLabel} (${e.confidenceScore})`
      : "--";
    const pattern = e.inferredPattern?.patternType ?? "--";
    lines.push(
      `| ${e.companyName} | ${e.role} | ${person} | ${e.status} | ${email} | ${conf} | ${pattern} |`,
    );
  }

  lines.push("", "---", "");

  for (const { roleDecision: r, emailDecision: e } of results) {
    lines.push(`## ${e.companyName} -- ${e.role}`);
    lines.push("");
    lines.push(`- **Person:** ${r.chosenCandidate?.fullName ?? "None"} (${r.status})`);
    lines.push(`- **Email status:** ${e.status}`);
    if (e.chosenEmail) lines.push(`- **Chosen email:** ${e.chosenEmail}`);
    if (e.confidenceLabel) {
      lines.push(`- **Confidence:** ${e.confidenceLabel} (${e.confidenceScore})`);
    }
    if (e.inferredPattern) {
      lines.push(
        `- **Pattern:** ${e.inferredPattern.patternType} (conf: ${e.inferredPattern.confidenceScore})`,
      );
      if (e.inferredPattern.evidenceEmails.length > 0) {
        lines.push(
          `- **Evidence emails:** ${e.inferredPattern.evidenceEmails.join(", ")}`,
        );
      }
    }
    if (e.evidence.length > 0) {
      lines.push("- **Evidence:**");
      for (const ev of e.evidence) lines.push(`  - ${ev}`);
    }
    if (e.alternateEmails.length > 0) {
      lines.push(
        `- **Alternatives:** ${e.alternateEmails.map((a) => `${a.email} (${a.patternType})`).join(", ")}`,
      );
    }
    if (e.blockingIssues.length > 0) {
      lines.push("- **Blocking:**");
      for (const b of e.blockingIssues) lines.push(`  - ${b}`);
    }
    lines.push("", "---", "");
  }

  return lines.join("\n");
}

main();
