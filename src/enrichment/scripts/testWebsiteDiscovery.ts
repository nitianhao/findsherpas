import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { planAllRows, getReadyRoleTasks } from "../planning/taskPlanner";
import { discoverCompanyWebsiteData } from "../discovery/companyWebsiteDiscovery";
import {
  getCachedDiscoveryResult,
  setCachedDiscoveryResult,
} from "../cache/discoveryCache";
import { closeBrowser } from "../browser/browserPool";
import type { PlannedRowTask } from "../types/tasks";
import type { CompanyDiscoveryResult } from "../types/discovery";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Select 10 diverse high-priority companies
// ---------------------------------------------------------------------------

function selectTestCompanies(
  plannedRows: PlannedRowTask[],
  count: number,
): PlannedRowTask[] {
  // Sort by total priority score descending
  const sorted = [...plannedRows].sort(
    (a, b) => b.totalPriorityScore - a.totalPriorityScore,
  );

  const selected: PlannedRowTask[] = [];
  const seenDomains = new Set<string>();
  const targetPerWorkbook = Math.ceil(count / 2);
  const perWorkbook: Record<string, PlannedRowTask[]> = {};

  for (const row of sorted) {
    const domain = extractDomain(row.websiteUrl);
    if (seenDomains.has(domain)) continue;

    const wb = row.sourceFile;
    if (!perWorkbook[wb]) perWorkbook[wb] = [];
    if (perWorkbook[wb].length >= targetPerWorkbook) continue;

    seenDomains.add(domain);
    perWorkbook[wb].push(row);
    selected.push(row);

    if (selected.length >= count) break;
  }

  return selected;
}

function extractDomain(url: string): string {
  try {
    const parsed = new URL(
      url.startsWith("http") ? url : `https://${url}`,
    );
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return url;
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  // Load all rows and plan
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const plannedRows = planAllRows(allRows);
  const testCompanies = selectTestCompanies(plannedRows, 10);

  console.log(`Selected ${testCompanies.length} companies for testing:\n`);
  for (const t of testCompanies) {
    console.log(`  [${t.region}] ${t.companyName} — ${t.websiteUrl}`);
  }
  console.log("");

  const results: CompanyDiscoveryResult[] = [];

  for (const task of testCompanies) {
    // Check cache first
    const cached = getCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
    );

    if (cached) {
      console.log(`[CACHED] ${task.companyName}`);
      results.push(cached);
      continue;
    }

    console.log(`[VISIT]  ${task.companyName} (${task.websiteUrl})...`);
    const result = await discoverCompanyWebsiteData(task);

    // Cache result
    setCachedDiscoveryResult(
      task.sourceFile,
      task.sheetName,
      task.rowIndex,
      task.websiteUrl,
      result,
    );

    results.push(result);
    printResultSummary(result);
  }

  await closeBrowser();

  // Write outputs
  const docsDir = path.resolve(ROOT_DIR, "docs");
  if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });

  const jsonPath = path.join(docsDir, "test-website-discovery.json");
  fs.writeFileSync(jsonPath, JSON.stringify(results, null, 2), "utf-8");
  console.log(`\nJSON results: ${jsonPath}`);

  const mdPath = path.join(docsDir, "test-website-discovery.md");
  fs.writeFileSync(mdPath, generateMarkdown(results), "utf-8");
  console.log(`Markdown report: ${mdPath}`);
}

function printResultSummary(r: CompanyDiscoveryResult) {
  console.log(`  Pages visited: ${r.discoveredPages.length}`);
  console.log(`  Persons found: ${r.personCandidates.length}`);
  console.log(`  Emails found:  ${r.emailCandidates.length}`);
  console.log(`  LinkedIn URLs: ${r.linkedinCandidates.length}`);
  if (r.errors.length > 0) {
    console.log(`  Errors: ${r.errors.length}`);
  }

  if (r.personCandidates.length > 0) {
    const top = r.personCandidates.slice(0, 3);
    for (const p of top) {
      const hints =
        p.matchedRoleHints.length > 0
          ? ` [${p.matchedRoleHints.join(", ")}]`
          : "";
      console.log(
        `    -> ${p.fullName}${hints}${p.titleText ? " — " + p.titleText.slice(0, 60) : ""}`,
      );
    }
  }
  if (r.emailCandidates.length > 0) {
    console.log(
      `    -> Emails: ${r.emailCandidates.map((e) => e.email).join(", ")}`,
    );
  }
  console.log("");
}

function generateMarkdown(results: CompanyDiscoveryResult[]): string {
  const lines: string[] = [
    "# Test Website Discovery Results",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    `Companies tested: ${results.length}`,
    "",
    "---",
    "",
  ];

  for (const r of results) {
    lines.push(`## ${r.companyName}`);
    lines.push("");
    lines.push(`- **Website:** ${r.websiteUrl}`);
    lines.push(`- **Final URL:** ${r.homepageFinalUrl}`);
    lines.push(`- **Region:** ${r.region}`);
    lines.push(`- **Pages visited:** ${r.discoveredPages.length}`);
    lines.push(`- **Persons found:** ${r.personCandidates.length}`);
    lines.push(`- **Emails found:** ${r.emailCandidates.length}`);
    lines.push(`- **LinkedIn URLs:** ${r.linkedinCandidates.length}`);
    if (r.errors.length > 0) {
      lines.push(`- **Errors:** ${r.errors.length}`);
    }
    lines.push("");

    if (r.discoveredPages.length > 0) {
      lines.push("### Pages Visited");
      lines.push("");
      lines.push("| URL | Type | Status |");
      lines.push("|-----|------|--------|");
      for (const p of r.discoveredPages) {
        lines.push(`| ${p.url} | ${p.pageType} | ${p.httpStatus} |`);
      }
      lines.push("");
    }

    if (r.personCandidates.length > 0) {
      lines.push("### Person Candidates");
      lines.push("");
      lines.push("| Name | Title | Role Hints | Page Type |");
      lines.push("|------|-------|------------|-----------|");
      for (const p of r.personCandidates) {
        lines.push(
          `| ${p.fullName} | ${p.titleText.slice(0, 60)} | ${p.matchedRoleHints.join(", ") || "—"} | ${p.pageType} |`,
        );
      }
      lines.push("");
    }

    if (r.emailCandidates.length > 0) {
      lines.push("### Emails");
      lines.push("");
      for (const e of r.emailCandidates) {
        lines.push(`- \`${e.email}\` (${e.sourceType}, ${e.pageType})`);
      }
      lines.push("");
    }

    if (r.linkedinCandidates.length > 0) {
      lines.push("### LinkedIn URLs");
      lines.push("");
      for (const l of r.linkedinCandidates) {
        lines.push(`- ${l.url} (${l.sourceType})`);
      }
      lines.push("");
    }

    lines.push("---");
    lines.push("");
  }

  return lines.join("\n");
}

main().catch((err) => {
  console.error("Fatal error:", err);
  closeBrowser().finally(() => process.exit(1));
});
