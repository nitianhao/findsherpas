/**
 * Runs the full role search enrichment pipeline for a specific set of 25 target companies.
 * Results are cached and will be picked up by dryRunWriteback / applyWriteback.
 *
 * Usage: npm run enrichment:targeted
 */

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
import type { RoleSearchCompositeResult } from "../types/search";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// 25 target companies
// ---------------------------------------------------------------------------

const TARGET_COMPANIES = new Set([
  // EU
  "Flaconi",
  "Bergzeit",
  "Tennis-Point",
  "Fashionette",
  "Sweaty Betty",
  "Beauty Bay",
  "Cotswold Outdoor",
  "Sportamore",
  "Nordic Nest",
  "Desenio",
  "NA-KD",
  "Lyko",
  "Boozt",
  "Marimekko",
  "Miinto",
  // US
  "Backcountry",
  "Vuori",
  "Reformation",
  "True Classic",
  "Rothy's",
  "Tecovas",
  "Orvis",
  "Cotopaxi",
  "Huckberry",
  "Pendleton Woolen Mills",
]);

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);
  const readyTasks = getReadyRoleTasks(plannedRows);

  // Filter to target companies only
  const targetTasks = readyTasks.filter((t) =>
    TARGET_COMPANIES.has(t.companyName),
  );

  // Log coverage
  const foundCompanies = new Set(targetTasks.map((t) => t.companyName));
  const missing = [...TARGET_COMPANIES].filter((c) => !foundCompanies.has(c));

  console.log(`\n=== TARGETED ENRICHMENT ===`);
  console.log(`Target companies: ${TARGET_COMPANIES.size}`);
  console.log(`Found in workbooks: ${foundCompanies.size}`);
  console.log(`Tasks to run: ${targetTasks.length}`);
  if (missing.length > 0) {
    console.log(`\nWARNING — not found in workbooks:`);
    missing.forEach((c) => console.log(`  - ${c}`));
  }

  console.log(`\nTask breakdown:`);
  const byCompany = new Map<string, PlannedRoleTask[]>();
  for (const t of targetTasks) {
    if (!byCompany.has(t.companyName)) byCompany.set(t.companyName, []);
    byCompany.get(t.companyName)!.push(t);
  }
  for (const [company, tasks] of byCompany) {
    const roles = tasks.map((t) => t.role).join(", ");
    console.log(`  ${company} [${tasks[0].region}]: ${roles}`);
  }
  console.log("");

  // Run pipeline
  const results: RoleSearchCompositeResult[] = [];
  let cached = 0;
  let fetched = 0;
  let errors = 0;

  for (const task of targetTasks) {
    const cachedResult = getCachedRoleSearchResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.role,
      task.websiteUrl,
    );

    if (cachedResult) {
      console.log(`[CACHED] ${task.companyName} — ${task.role}`);
      results.push(cachedResult);
      cached++;
      printSummary(cachedResult);
      continue;
    }

    const discoveryResult = getCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
    );

    console.log(`[SEARCH] ${task.companyName} — ${task.role} (${task.region})...`);

    try {
      const result = await discoverRoleViaPublicSearch(task, discoveryResult);

      setCachedRoleSearchResult(
        task.sourceFile,
        task.sheetName,
        task.rowIndex,
        task.role,
        task.websiteUrl,
        result,
      );

      results.push(result);
      fetched++;
      printSummary(result);
    } catch (err) {
      console.error(`  ERROR: ${err}`);
      errors++;
    }

    // Rate limit: 3–5s between requests
    await sleep(3000 + Math.floor(Math.random() * 2000));
  }

  await releaseSearchPages();
  await closeBrowser();

  // Final summary
  console.log("\n=== DONE ===");
  console.log(`Cached (skipped): ${cached}`);
  console.log(`Fetched (new):    ${fetched}`);
  console.log(`Errors:           ${errors}`);
  console.log(`Total results:    ${results.length}`);
  console.log(
    `\nNext step: npm run enrichment:writeback:dry-run to preview what will be written.`,
  );

  // Write report
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const mdLines: string[] = [
    "# Targeted Enrichment Results",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    `| Metric | Count |`,
    `|--------|-------|`,
    `| Target companies | ${TARGET_COMPANIES.size} |`,
    `| Found in workbooks | ${foundCompanies.size} |`,
    `| Tasks run | ${targetTasks.length} |`,
    `| Cached | ${cached} |`,
    `| Fetched | ${fetched} |`,
    `| Errors | ${errors} |`,
    "",
    "## Results by Company",
    "",
    "| Company | Region | Role | Top Candidate | Score | LinkedIn |",
    "|---------|--------|------|---------------|-------|----------|",
  ];

  for (const r of results) {
    const top = r.rankedCandidates[0];
    const name = top?.fullName ?? "—";
    const score = top?.rankScore ?? "—";
    const li = top?.linkedinUrl ? "✓" : "—";
    mdLines.push(
      `| ${r.companyName} | ${r.region} | ${r.role} | ${name} | ${score} | ${li} |`,
    );
  }

  const mdPath = path.join(docsDir, "targeted-enrichment-results.md");
  fs.writeFileSync(mdPath, mdLines.join("\n"), "utf-8");
  console.log(`\nReport: ${mdPath}`);
}

function printSummary(r: RoleSearchCompositeResult) {
  const top = r.rankedCandidates[0];
  if (top) {
    const li = top.linkedinUrl ? " [LI]" : "";
    console.log(
      `  -> ${top.fullName}${li} (score: ${top.rankScore})`,
    );
  } else {
    console.log(`  -> No candidates found`);
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  releaseSearchPages()
    .then(() => closeBrowser())
    .finally(() => process.exit(1));
});
