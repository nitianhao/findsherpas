/**
 * Hunter.io enrichment for the 25 target companies.
 *
 * Strategy per company:
 *   1. For every role that has a name but no email → Email Finder
 *   2. After named lookups, if any role email is still missing → Domain Search (limit 10)
 *      and fill from position-keyword matching
 *
 * Writes directly into the Excel workbooks.
 * Usage: npm run enrichment:hunter
 */

import * as path from "path";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import {
  readNormalizedRows,
  loadPrimarySheet,
  writeCellByHeader,
  saveWorkbookInPlace,
  createBackup,
} from "../io/workbookService";
import {
  findEmail,
  searchDomain,
  parseName,
  type HunterDomainEmail,
} from "../email/hunterAdapter";
import type { ProspectRowNormalized } from "../types/prospect";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

// ---------------------------------------------------------------------------
// Target companies
// ---------------------------------------------------------------------------

const TARGET_COMPANIES = new Set([
  "Flaconi", "Bergzeit", "Tennis-Point", "Fashionette", "Sweaty Betty",
  "Beauty Bay", "Cotswold Outdoor", "Sportamore", "Nordic Nest", "Desenio",
  "NA-KD", "Lyko", "Boozt", "Marimekko", "Miinto",
  "Backcountry", "Vuori", "Reformation", "True Classic", "Rothy's",
  "Tecovas", "Orvis", "Cotopaxi", "Huckberry", "Pendleton Woolen Mills",
]);

// ---------------------------------------------------------------------------
// Role definitions
// ---------------------------------------------------------------------------

interface RoleDef {
  label: string;
  nameField: keyof ProspectRowNormalized;
  emailField: keyof ProspectRowNormalized;
  emailColumn: string;
  nameColumn: (region: string) => string;
  domainKeywords: string[];
}

const ROLES: RoleDef[] = [
  {
    label: "CEO",
    nameField: "ceoName",
    emailField: "ceoEmail",
    emailColumn: "CEO Email",
    nameColumn: (region) => region === "EU" ? "CEO / MD Name" : "CEO / Founder Name",
    domainKeywords: ["ceo", "chief executive", "founder", "managing director", "md", "president"],
  },
  {
    label: "Head of Product",
    nameField: "headOfProductName",
    emailField: "headOfProductEmail",
    emailColumn: "Head of Product Email",
    nameColumn: () => "Head of Product (Name)",
    domainKeywords: ["product", "cpo", "chief product"],
  },
  {
    label: "Head of Ecommerce",
    nameField: "headOfEcommerceName",
    emailField: "headOfEcommerceEmail",
    emailColumn: "Head of Ecommerce Email",
    nameColumn: () => "Head of Ecommerce (Name)",
    domainKeywords: ["ecommerce", "e-commerce", "digital commerce", "online"],
  },
  {
    label: "Head of Growth",
    nameField: "headOfGrowthName",
    emailField: "headOfGrowthEmail",
    emailColumn: "Head of Growth / CMO Email",
    nameColumn: () => "Head of Growth / CMO (Name)",
    domainKeywords: ["growth", "marketing", "cmo", "chief marketing"],
  },
];

// ---------------------------------------------------------------------------
// Domain search helpers
// ---------------------------------------------------------------------------

function matchesRole(position: string | null, keywords: string[]): boolean {
  if (!position) return false;
  const lower = position.toLowerCase();
  return keywords.some((k) => lower.includes(k));
}

function pickBestByRole(
  emails: HunterDomainEmail[],
  keywords: string[],
): HunterDomainEmail | null {
  const matches = emails.filter((e) => matchesRole(e.position, keywords));
  if (!matches.length) return null;
  return matches.sort((a, b) => b.confidence - a.confidence)[0];
}

// ---------------------------------------------------------------------------
// Write helper
// ---------------------------------------------------------------------------

function writeCell(
  worksheet: import("xlsx").WorkSheet,
  rowIndex: number,
  column: string,
  value: string,
  label: string,
) {
  try {
    writeCellByHeader(worksheet, rowIndex, column, value);
    console.log(`    ${label}: ${value}`);
  } catch (err) {
    console.warn(`    WARN — ${label}: ${err}`);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const targetRows = allRows.filter((r) => TARGET_COMPANIES.has(r.companyName));

  // One representative row per company (all 4 roles live on the same row)
  const byCompany = new Map<string, ProspectRowNormalized>();
  for (const row of targetRows) {
    if (!byCompany.has(row.companyName)) byCompany.set(row.companyName, row);
  }

  const missing = [...TARGET_COMPANIES].filter((c) => !byCompany.has(c));
  console.log(`\n=== HUNTER ENRICHMENT ===`);
  console.log(`Target companies: ${TARGET_COMPANIES.size}`);
  console.log(`Found in workbooks: ${byCompany.size}`);
  if (missing.length > 0) {
    console.log(`WARNING — not in workbooks: ${missing.join(", ")}`);
  }

  // Load workbooks
  const wbCache = new Map<string, {
    workbook: ReturnType<typeof import("xlsx").readFile>;
    worksheet: import("xlsx").WorkSheet;
    filePath: string;
  }>();

  for (const config of ALL_CONFIGS) {
    const { workbook, worksheet, filePath } = loadPrimarySheet(config, ROOT_DIR);
    wbCache.set(config.filename, { workbook, worksheet, filePath });
  }

  // Backup before writing
  for (const { filePath } of wbCache.values()) {
    const backup = createBackup(filePath);
    if (backup) console.log(`Backup: ${path.basename(backup)}`);
  }

  let emailsFound = 0;
  let apiCalls = 0;

  for (const [company, row] of byCompany) {
    const wb = wbCache.get(row.sourceFile);
    if (!wb) { console.warn(`WARN — no workbook for ${row.sourceFile}`); continue; }

    console.log(`\n[${row.region}] ${company}`);

    // Track which roles still need email after Email Finder pass
    const stillMissing: RoleDef[] = [];

    // ------------------------------------------------------------------
    // Pass 1: Email Finder for every role that has a name but no email
    // ------------------------------------------------------------------
    for (const role of ROLES) {
      const name = (row[role.nameField] as string).trim();
      const existingEmail = (row[role.emailField] as string).trim();

      if (!name) { stillMissing.push(role); continue; }
      if (existingEmail) { console.log(`  ${role.label}: already set (${existingEmail})`); continue; }

      const { firstName, lastName } = parseName(name);
      process.stdout.write(`  ${role.label}: ${name} → `);
      apiCalls++;

      const result = await findEmail(row.websiteUrl, firstName, lastName);
      await sleep(1500); // Hunter rate limit

      if (result.status === "found" && result.email) {
        console.log(result.email);
        writeCell(wb.worksheet, row.rowIndex, role.emailColumn, result.email, role.emailColumn);
        emailsFound++;
      } else if (result.status === "not_found") {
        console.log("not found");
        stillMissing.push(role);
      } else {
        console.log(`error — ${result.errorMessage}`);
        stillMissing.push(role);
      }
    }

    // ------------------------------------------------------------------
    // Pass 2: Domain Search to fill roles with no name OR not found above
    // ------------------------------------------------------------------
    if (stillMissing.length > 0) {
      console.log(`  Domain Search (${stillMissing.map((r) => r.label).join(", ")})...`);
      apiCalls++;

      const ds = await searchDomain(row.websiteUrl, 10); // free plan cap
      await sleep(1500);

      if (ds.status === "found") {
        for (const role of stillMissing) {
          const existingEmail = (row[role.emailField] as string).trim();
          if (existingEmail) continue;

          const match = pickBestByRole(ds.emails, role.domainKeywords);
          if (!match) { console.log(`  ${role.label}: no domain match`); continue; }

          writeCell(wb.worksheet, row.rowIndex, role.emailColumn, match.value, role.emailColumn);
          emailsFound++;

          // Write name too if missing
          const existingName = (row[role.nameField] as string).trim();
          if (!existingName && match.firstName) {
            const fullName = [match.firstName, match.lastName].filter(Boolean).join(" ");
            writeCell(wb.worksheet, row.rowIndex, role.nameColumn(row.region), fullName, `${role.label} Name`);
          }
        }
      } else {
        console.log(`  Domain Search: ${ds.status}${ds.errorMessage ? ` — ${ds.errorMessage}` : ""}`);
      }
    }
  }

  // Save
  for (const { workbook, filePath } of wbCache.values()) {
    saveWorkbookInPlace(workbook, filePath);
    console.log(`\nSaved: ${path.basename(filePath)}`);
  }

  console.log(`\n=== DONE ===`);
  console.log(`API calls made: ${apiCalls}`);
  console.log(`Emails written: ${emailsFound}`);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
