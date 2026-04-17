import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { planAllRows, getReadyRoleTasks } from "../planning/taskPlanner";
import { resolveRoleDecision } from "../resolution/roleResolver";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { getCachedRoleSearchResult } from "../cache/searchCache";
import type { PlannedRoleTask } from "../types/tasks";
import type { TargetRole } from "../types/prospect";
import type { ResolvedRoleDecision } from "../types/resolution";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Select test tasks (same logic as Brave test)
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

  console.log(`Resolving ${testTasks.length} role decisions (Brave-backed):\n`);

  const decisions: ResolvedRoleDecision[] = [];

  for (const task of testTasks) {
    const discovery = getCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
    );

    // Try Brave cache first, fall back to legacy v2 cache
    const search =
      getCachedRoleSearchResult(
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
        task.role,
        task.websiteUrl,
        "BRAVE",
      ) ??
      getCachedRoleSearchResult(
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
        task.role,
        task.websiteUrl,
        "BROWSER",
      );

    const decision = resolveRoleDecision(task, discovery, search);
    decisions.push(decision);
    printDecision(decision);
  }

  printAggregateSummary(decisions);

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "test-role-resolution-brave.json");
  fs.writeFileSync(jsonPath, JSON.stringify(decisions, null, 2), "utf-8");
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "test-role-resolution-brave.md");
  fs.writeFileSync(mdPath, generateMarkdown(decisions), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

function printDecision(d: ResolvedRoleDecision) {
  const chosen = d.chosenCandidate;
  const li = chosen?.linkedinUrl ? " [LI]" : "";
  const candidateStr = chosen
    ? `${chosen.fullName}${li} (score: ${chosen.confidenceScore}, ${chosen.confidenceLabel})`
    : "NONE";

  console.log(
    `  [${d.status.padEnd(18)}] ${d.companyName.padEnd(22)} ${d.role.padEnd(20)} -> ${candidateStr}`,
  );

  if (chosen && chosen.evidence.length > 0) {
    for (const e of chosen.evidence.slice(0, 3)) {
      console.log(`    ${e}`);
    }
  }

  if (d.alternateCandidates.length > 0) {
    console.log(
      `    alternates: ${d.alternateCandidates.map((a) => `${a.fullName}(${a.confidenceScore})`).join(", ")}`,
    );
  }
  console.log("");
}

function printAggregateSummary(decisions: ResolvedRoleDecision[]) {
  console.log("\n=== AGGREGATE SUMMARY ===\n");

  const statusCounts: Record<string, number> = {};
  for (const d of decisions) {
    statusCounts[d.status] = (statusCounts[d.status] ?? 0) + 1;
  }
  console.log("By status:");
  for (const [status, count] of Object.entries(statusCounts)) {
    console.log(`  ${status}: ${count}`);
  }

  console.log("\nBy role:");
  const roleCounts: Record<string, { total: number; resolved: number }> = {};
  for (const d of decisions) {
    if (!roleCounts[d.role]) roleCounts[d.role] = { total: 0, resolved: 0 };
    roleCounts[d.role].total++;
    if (d.status.startsWith("RESOLVED")) roleCounts[d.role].resolved++;
  }
  for (const [role, counts] of Object.entries(roleCounts)) {
    console.log(`  ${role}: ${counts.resolved}/${counts.total} resolved`);
  }

  const withLinkedin = decisions.filter(
    (d) => d.chosenCandidate?.linkedinUrl,
  ).length;
  console.log(`\nChosen with LinkedIn: ${withLinkedin}/${decisions.length}`);

  const websiteContrib = decisions.filter(
    (d) => d.chosenCandidate?.sourceKinds.includes("WEBSITE"),
  ).length;
  console.log(`Website evidence contributed: ${websiteContrib}/${decisions.length}`);
}

function generateMarkdown(decisions: ResolvedRoleDecision[]): string {
  const lines: string[] = [
    "# Role Resolution Results (Brave-backed)",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    `Roles tested: ${decisions.length}`,
    "",
    "---",
    "",
    "## Summary",
    "",
    "| Company | Role | Status | Candidate | Score | LinkedIn |",
    "|---------|------|--------|-----------|-------|----------|",
  ];

  for (const d of decisions) {
    const c = d.chosenCandidate;
    const name = c ? c.fullName : "--";
    const score = c ? String(c.confidenceScore) : "--";
    const li = c?.linkedinUrl ? "Yes" : "No";
    lines.push(
      `| ${d.companyName} | ${d.role} | ${d.status} | ${name} | ${score} | ${li} |`,
    );
  }

  lines.push("", "---", "");

  for (const d of decisions) {
    lines.push(`## ${d.companyName} -- ${d.role}`);
    lines.push("");
    lines.push(`- **Status:** ${d.status}`);
    lines.push(`- **Region:** ${d.region}`);

    if (d.chosenCandidate) {
      const c = d.chosenCandidate;
      lines.push(
        `- **Chosen:** ${c.fullName} (score: ${c.confidenceScore}, ${c.confidenceLabel})`,
      );
      if (c.linkedinUrl) lines.push(`- **LinkedIn:** ${c.linkedinUrl}`);
      lines.push(`- **Sources:** ${c.sourceKinds.join(", ")}`);
      if (c.evidence.length > 0) {
        lines.push("- **Evidence:**");
        for (const e of c.evidence) lines.push(`  - ${e}`);
      }
    } else {
      lines.push("- **Chosen:** None");
    }

    if (d.alternateCandidates.length > 0) {
      lines.push("- **Alternates:**");
      for (const a of d.alternateCandidates) {
        lines.push(
          `  - ${a.fullName} (score: ${a.confidenceScore}${a.linkedinUrl ? ", LI" : ""})`,
        );
      }
    }

    lines.push("", "---", "");
  }

  return lines.join("\n");
}

main();
