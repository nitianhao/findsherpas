import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { planAllRows, getReadyRoleTasks } from "../planning/taskPlanner";
import { discoverRoleViaPublicSearch } from "../search/roleSearchDiscovery";
import {
  getCachedRoleSearchResult,
  setCachedRoleSearchResult,
} from "../cache/searchCache";
import { getCachedDiscoveryResult } from "../cache/discoveryCache";
import { closeBrowser } from "../browser/browserPool";
import { releaseSearchPages } from "../search/searchEngineRunner";
import type { PlannedRoleTask } from "../types/tasks";
import type { TargetRole } from "../types/prospect";
import type { RoleSearchCompositeResult } from "../types/search";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Select 16 diverse role tasks
// ---------------------------------------------------------------------------

function selectTestTasks(
  readyTasks: PlannedRoleTask[],
): PlannedRoleTask[] {
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
        if (!wantEU && task.region !== "US" && roleTasks.some(
          (t) => t.region === "US" && !usedCompanies.has(t.companyName),
        )) continue;
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
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);
  const readyTasks = getReadyRoleTasks(plannedRows);
  const testTasks = selectTestTasks(readyTasks);

  console.log(`Selected ${testTasks.length} role tasks for testing:\n`);
  for (const t of testTasks) {
    console.log(`  [${t.region}] ${t.companyName} — ${t.role}`);
  }
  console.log("");

  const results: RoleSearchCompositeResult[] = [];
  let googleCount = 0;
  let bingCount = 0;

  for (const task of testTasks) {
    const cached = getCachedRoleSearchResult(
      task.sourceFile, task.sheetName, task.rowIndex,
      task.role, task.websiteUrl,
    );

    if (cached) {
      console.log(`[CACHED] ${task.companyName} — ${task.role}`);
      results.push(cached);
      countEngines(cached);
      printResultSummary(cached);
      continue;
    }

    const discoveryResult = getCachedDiscoveryResult(
      task.sourceFile, task.sheetName, task.rowIndex, task.websiteUrl,
    );

    console.log(
      `[SEARCH] ${task.companyName} — ${task.role} (${task.region})...`,
    );
    const result = await discoverRoleViaPublicSearch(task, discoveryResult);

    setCachedRoleSearchResult(
      task.sourceFile, task.sheetName, task.rowIndex,
      task.role, task.websiteUrl, result,
    );

    results.push(result);
    countEngines(result);
    printResultSummary(result);

    await sleep(3000 + Math.floor(Math.random() * 2000));
  }

  function countEngines(r: RoleSearchCompositeResult) {
    for (const sr of r.rawSearchResults) {
      if (sr.engine === "GOOGLE") googleCount++;
      else if (sr.engine === "BING") bingCount++;
    }
  }

  await releaseSearchPages();
  await closeBrowser();

  // Summary
  console.log("\n=== ENGINE USAGE ===");
  console.log(`Google results: ${googleCount}`);
  console.log(`Bing results: ${bingCount}`);

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "test-role-search.json");
  fs.writeFileSync(jsonPath, JSON.stringify(results, null, 2), "utf-8");
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "test-role-search.md");
  fs.writeFileSync(mdPath, generateMarkdown(results, googleCount, bingCount), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

function printResultSummary(r: RoleSearchCompositeResult) {
  const engines = new Set(r.rawSearchResults.map((sr) => sr.engine));
  const engineStr = engines.size > 0 ? Array.from(engines).join("+") : "none";
  console.log(`  Engine: ${engineStr} | Queries: ${r.queryPlan.queries.length}`);
  console.log(`  Raw results: ${r.rawSearchResults.length}`);
  console.log(`  Parsed candidates: ${r.parsedCandidates.length}`);
  console.log(`  Ranked candidates: ${r.rankedCandidates.length}`);

  const top3 = r.rankedCandidates.slice(0, 3);
  if (top3.length === 0) {
    console.log(`  -> No good candidates found`);
  } else {
    for (const c of top3) {
      const li = c.linkedinUrl ? ` [LI]` : "";
      console.log(
        `  -> ${c.fullName}${li} (score: ${c.rankScore}) ${c.rankReasons.join(", ")}`,
      );
    }
  }
  if (r.errors.length > 0) {
    console.log(`  Errors: ${r.errors.length}`);
  }
  console.log("");
}

function generateMarkdown(
  results: RoleSearchCompositeResult[],
  googleCount: number,
  bingCount: number,
): string {
  const lines: string[] = [
    "# Test Role Search Results (Multi-Engine)",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    `Role tasks tested: ${results.length}`,
    `Google results: ${googleCount}`,
    `Bing results: ${bingCount}`,
    "",
    "---",
    "",
  ];

  for (const r of results) {
    const engines = new Set(r.rawSearchResults.map((sr) => sr.engine));
    lines.push(`## ${r.companyName} — ${r.role} (${r.region})`);
    lines.push("");
    lines.push(`- **Engines:** ${Array.from(engines).join(", ") || "none"}`);
    lines.push(`- **Queries tried:** ${r.queryPlan.queries.length}`);
    lines.push(`- **Raw results:** ${r.rawSearchResults.length}`);
    lines.push(`- **Parsed candidates:** ${r.parsedCandidates.length}`);
    lines.push(`- **Ranked candidates:** ${r.rankedCandidates.length}`);
    if (r.errors.length > 0) lines.push(`- **Errors:** ${r.errors.length}`);
    lines.push("");

    if (r.rankedCandidates.length > 0) {
      lines.push("### Top Candidates");
      lines.push("");
      lines.push("| # | Name | LinkedIn | Score | Key Signals |");
      lines.push("|---|------|----------|-------|-------------|");
      const top5 = r.rankedCandidates.slice(0, 5);
      top5.forEach((c, i) => {
        const li = c.linkedinUrl ? `[Profile](${c.linkedinUrl})` : "—";
        const signals = c.evidenceSignals.filter((s) =>
          ["LINKEDIN_TITLE_ROLE_MATCH", "COMPANY_MATCH_FROM_TITLE", "role-evidence"].includes(s),
        ).join(", ") || "—";
        lines.push(`| ${i + 1} | ${c.fullName} | ${li} | ${c.rankScore} | ${signals} |`);
      });
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
  console.error("Fatal error:", err);
  releaseSearchPages()
    .then(() => closeBrowser())
    .finally(() => process.exit(1));
});
