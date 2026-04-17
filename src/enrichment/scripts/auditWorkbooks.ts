import * as path from "path";
import * as fs from "fs";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import {
  createBackup,
  loadPrimarySheet,
  getHeaderRow,
  ensureOutputColumns,
  readNormalizedRows,
  saveWorkbookInPlace,
} from "../io/workbookService";
import type { ProspectRowNormalized } from "../types/prospect";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

interface SheetAudit {
  filename: string;
  region: string;
  sheetName: string;
  totalRows: number;
  nonEmptyCompanyNames: number;
  nonEmptyWebsiteUrls: number;
  ceoNameFilled: number;
  ceoLinkedinFilled: number;
  ceoEmailFilled: number;
  headOfProductNameFilled: number;
  headOfProductEmailFilled: number;
  headOfEcommerceNameFilled: number;
  headOfEcommerceEmailFilled: number;
  headOfGrowthNameFilled: number;
  headOfGrowthEmailFilled: number;
  columnsAdded: string[];
  backupPath: string | null;
  saved: boolean;
}

function countFilled(
  rows: ProspectRowNormalized[],
  field: keyof ProspectRowNormalized,
): number {
  return rows.filter((r) => (r[field] as string) !== "").length;
}

function runAudit(): SheetAudit[] {
  const audits: SheetAudit[] = [];

  for (const config of ALL_CONFIGS) {
    const filePath = path.resolve(ROOT_DIR, config.filename);
    console.log(`\n--- ${config.filename} (${config.region}) ---`);

    // Backup
    const backupPath = createBackup(filePath);
    if (backupPath) {
      console.log(`  Backup created: ${path.basename(backupPath)}`);
    } else {
      console.log(`  Backup already exists for this timestamp`);
    }

    // Load and ensure columns
    const { workbook, worksheet } = loadPrimarySheet(config, ROOT_DIR);
    const columnsAdded = ensureOutputColumns(worksheet);
    if (columnsAdded.length > 0) {
      console.log(`  Columns added: ${columnsAdded.join(", ")}`);
    } else {
      console.log(`  All output columns already present`);
    }

    // Save only if columns were added
    const saved = columnsAdded.length > 0;
    if (saved) {
      saveWorkbookInPlace(workbook, filePath);
      console.log(`  Workbook saved with new columns`);
    }

    // Read normalized rows (reload after potential save)
    const rows = readNormalizedRows(config, ROOT_DIR);

    const audit: SheetAudit = {
      filename: config.filename,
      region: config.region,
      sheetName: config.primarySheet,
      totalRows: rows.length,
      nonEmptyCompanyNames: countFilled(rows, "companyName"),
      nonEmptyWebsiteUrls: countFilled(rows, "websiteUrl"),
      ceoNameFilled: countFilled(rows, "ceoName"),
      ceoLinkedinFilled: countFilled(rows, "ceoLinkedin"),
      ceoEmailFilled: countFilled(rows, "ceoEmail"),
      headOfProductNameFilled: countFilled(rows, "headOfProductName"),
      headOfProductEmailFilled: countFilled(rows, "headOfProductEmail"),
      headOfEcommerceNameFilled: countFilled(rows, "headOfEcommerceName"),
      headOfEcommerceEmailFilled: countFilled(rows, "headOfEcommerceEmail"),
      headOfGrowthNameFilled: countFilled(rows, "headOfGrowthName"),
      headOfGrowthEmailFilled: countFilled(rows, "headOfGrowthEmail"),
      columnsAdded,
      backupPath,
      saved,
    };
    audits.push(audit);

    // Print summary
    console.log(`  Total rows: ${audit.totalRows}`);
    console.log(`  Company names: ${audit.nonEmptyCompanyNames}`);
    console.log(`  Website URLs: ${audit.nonEmptyWebsiteUrls}`);
    console.log(`  CEO Name: ${audit.ceoNameFilled}`);
    console.log(`  CEO LinkedIn: ${audit.ceoLinkedinFilled}`);
    console.log(`  CEO Email: ${audit.ceoEmailFilled}`);
    console.log(`  Head of Product Name: ${audit.headOfProductNameFilled}`);
    console.log(`  Head of Product Email: ${audit.headOfProductEmailFilled}`);
    console.log(`  Head of Ecommerce Name: ${audit.headOfEcommerceNameFilled}`);
    console.log(
      `  Head of Ecommerce Email: ${audit.headOfEcommerceEmailFilled}`,
    );
    console.log(`  Head of Growth Name: ${audit.headOfGrowthNameFilled}`);
    console.log(`  Head of Growth Email: ${audit.headOfGrowthEmailFilled}`);
  }

  return audits;
}

function generateReport(audits: SheetAudit[]): string {
  const lines: string[] = [
    "# Workbook Normalization Report",
    "",
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
    "---",
    "",
  ];

  for (const a of audits) {
    lines.push(`## ${a.filename} (${a.region})`);
    lines.push("");
    lines.push(`- **Primary sheet:** ${a.sheetName}`);
    lines.push(`- **Total data rows:** ${a.totalRows}`);
    lines.push(
      `- **Backup:** ${a.backupPath ? path.basename(a.backupPath) : "already existed"}`,
    );
    lines.push(
      `- **Columns added:** ${a.columnsAdded.length > 0 ? a.columnsAdded.join(", ") : "none"}`,
    );
    lines.push(`- **Saved:** ${a.saved ? "yes" : "no (no changes needed)"}`);
    lines.push("");
    lines.push("| Field | Filled | Total | % |");
    lines.push("|-------|--------|-------|---|");

    const fields: [string, number][] = [
      ["Company Name", a.nonEmptyCompanyNames],
      ["Website URL", a.nonEmptyWebsiteUrls],
      ["CEO Name", a.ceoNameFilled],
      ["CEO LinkedIn", a.ceoLinkedinFilled],
      ["CEO Email", a.ceoEmailFilled],
      ["Head of Product Name", a.headOfProductNameFilled],
      ["Head of Product Email", a.headOfProductEmailFilled],
      ["Head of Ecommerce Name", a.headOfEcommerceNameFilled],
      ["Head of Ecommerce Email", a.headOfEcommerceEmailFilled],
      ["Head of Growth Name", a.headOfGrowthNameFilled],
      ["Head of Growth Email", a.headOfGrowthEmailFilled],
    ];

    for (const [label, count] of fields) {
      const pct = a.totalRows > 0 ? Math.round((count / a.totalRows) * 100) : 0;
      lines.push(`| ${label} | ${count} | ${a.totalRows} | ${pct}% |`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const audits = runAudit();
const report = generateReport(audits);

const docsDir = path.resolve(ROOT_DIR, "docs");
if (!fs.existsSync(docsDir)) fs.mkdirSync(docsDir, { recursive: true });
const reportPath = path.join(docsDir, "workbook-normalization-report.md");
fs.writeFileSync(reportPath, report, "utf-8");
console.log(`\nReport written to: ${reportPath}`);
