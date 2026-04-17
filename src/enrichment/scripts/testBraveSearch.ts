import * as path from "path";
import * as fs from "fs";
import { assertBraveApiKey } from "../config/env";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { planAllRows, getReadyRoleTasks } from "../planning/taskPlanner";
import { discoverRoleViaPublicSearch } from "../search/roleSearchDiscovery";
import {
  getCachedRoleSearchResult,
  setCachedRoleSearchResult,
} from "../cache/searchCache";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import type { PlannedRoleTask } from "../types/tasks";
import type { TargetRole } from "../types/prospect";
import type { RoleSearchCompositeResult } from "../types/search";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Select 16 diverse role tasks
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

    // Fill remaining
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

async function main() {
  // Requirement 12: stop cleanly if no key
  try {
    assertBraveApiKey();
  } catch (err: any) {
    console.error(err.message);
    process.exit(1);
  }

  console.log("Brave Search API key: OK\n");

  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);
  const readyTasks = getReadyRoleTasks(plannedRows);
  const testTasks = selectTestTasks(readyTasks);

  console.log(`Selected ${testTasks.length} role tasks for testing:\n`);
  for (const t of testTasks) {
    console.log(`  [${t.region}] ${t.companyName} -- ${t.role}`);
  }
  console.log("");

  const results: RoleSearchCompositeResult[] = [];
  let braveResultCount = 0;
  let queriesUsed = 0;

  for (const task of testTasks) {
    const cached = getCachedRoleSearchResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.role,
      task.websiteUrl,
      "BRAVE",
    );

    if (cached) {
      console.log(`[CACHED] ${task.companyName} -- ${task.role}`);
      results.push(cached);
      braveResultCount += cached.rawSearchResults.length;
      queriesUsed += cached.queryPlan.queries.length;
      printResultSummary(cached);
      continue;
    }

    const discoveryResult = getCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
    );

    console.log(
      `[BRAVE] ${task.companyName} -- ${task.role} (${task.region})...`,
    );

    try {
      const result = await discoverRoleViaPublicSearch(task, discoveryResult);

      setCachedRoleSearchResult(
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
        task.role,
        task.websiteUrl,
        result,
        "BRAVE",
      );

      results.push(result);
      braveResultCount += result.rawSearchResults.length;
      queriesUsed += result.queryPlan.queries.length;
      printResultSummary(result);
    } catch (err: any) {
      console.error(`  ERROR: ${err.message}`);
      if (err.message.includes("429") || err.message.includes("402")) {
        console.error("  Stopping: rate/quota limit reached.");
        break;
      }
    }
  }

  // Summary
  console.log("\n=== BRAVE SEARCH SUMMARY ===");
  console.log(`Tasks tested: ${results.length}`);
  console.log(`Queries used: ${queriesUsed}`);
  console.log(`Total search results: ${braveResultCount}`);

  const withCandidates = results.filter((r) => r.rankedCandidates.length > 0).length;
  const withLinkedin = results.filter((r) =>
    r.rankedCandidates.some((c) => c.linkedinUrl),
  ).length;
  console.log(`Tasks with candidates: ${withCandidates}/${results.length}`);
  console.log(`Tasks with LinkedIn hit: ${withLinkedin}/${results.length}`);

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "test-brave-search.json");
  fs.writeFileSync(jsonPath, JSON.stringify(results, null, 2), "utf-8");
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "test-brave-search.md");
  fs.writeFileSync(mdPath, generateMarkdown(results, queriesUsed, braveResultCount), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

function printResultSummary(r: RoleSearchCompositeResult) {
  console.log(`  Queries: ${r.queryPlan.queries.length}`);
  console.log(`  Raw results: ${r.rawSearchResults.length}`);
  console.log(`  Parsed candidates: ${r.parsedCandidates.length}`);
  console.log(`  Ranked candidates: ${r.rankedCandidates.length}`);

  const top3 = r.rankedCandidates.slice(0, 3);
  if (top3.length === 0) {
    console.log(`  -> No candidates found`);
  } else {
    for (const c of top3) {
      const li = c.linkedinUrl ? ` [LI]` : "";
      console.log(
        `  -> ${c.fullName}${li} (score: ${c.rankScore}) ${c.rankReasons.join(", ")}`,
      );
    }
  }
  if (r.errors.length > 0) {
    for (const e of r.errors) console.log(`  ERR: ${e}`);
  }
  console.log("");
}

function generateMarkdown(
  results: RoleSearchCompositeResult[],
  queriesUsed: number,
  totalResults: number,
): string {
  const lines: string[] = [
    "# Brave Search Test Results",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    `Tasks tested: ${results.length}`,
    `Queries used: ${queriesUsed}`,
    `Total search results: ${totalResults}`,
    "",
    "---",
    "",
  ];

  for (const r of results) {
    lines.push(`## ${r.companyName} -- ${r.role} (${r.region})`);
    lines.push("");
    lines.push(`- **Queries:** ${r.queryPlan.queries.length}`);
    lines.push(`- **Raw results:** ${r.rawSearchResults.length}`);
    lines.push(`- **Parsed candidates:** ${r.parsedCandidates.length}`);
    lines.push(`- **Ranked candidates:** ${r.rankedCandidates.length}`);
    if (r.errors.length > 0) lines.push(`- **Errors:** ${r.errors.join("; ")}`);
    lines.push("");

    if (r.rankedCandidates.length > 0) {
      lines.push("| # | Name | LinkedIn | Score | Signals |");
      lines.push("|---|------|----------|-------|---------|");
      for (const [i, c] of r.rankedCandidates.slice(0, 5).entries()) {
        const li = c.linkedinUrl ? `[Profile](${c.linkedinUrl})` : "--";
        const sig = c.rankReasons.join(", ");
        lines.push(`| ${i + 1} | ${c.fullName} | ${li} | ${c.rankScore} | ${sig} |`);
      }
      lines.push("");
    } else {
      lines.push("*No candidates found.*");
      lines.push("");
    }

    lines.push("---");
    lines.push("");
  }

  return lines.join("\n");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
