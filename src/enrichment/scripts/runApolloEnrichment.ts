/**
 * Apollo.io enrichment for the 25 target companies.
 * Fills in any role (CEO / Head of Product / Ecommerce / Growth) that still has no email.
 *
 * Usage: APOLLO_API_KEY=xxx npm run enrichment:apollo
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
  searchPeopleByCompanyAndTitles,
  APOLLO_TITLES,
  type ApolloRoleKey,
} from "../email/apolloAdapter";
import type { ProspectRowNormalized } from "../types/prospect";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function extractDomain(url: string): string {
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname
      .replace(/^www\./, "")
      .toLowerCase();
  } catch {
    return url;
  }
}

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

const TARGET_COMPANIES = new Set([
  "Flaconi", "Bergzeit", "Tennis-Point", "Fashionette", "Sweaty Betty",
  "Beauty Bay", "Cotswold Outdoor", "Sportamore", "Nordic Nest", "Desenio",
  "NA-KD", "Lyko", "Boozt", "Marimekko", "Miinto",
  "Backcountry", "Vuori", "Reformation", "True Classic", "Rothy's",
  "Tecovas", "Orvis", "Cotopaxi", "Huckberry", "Pendleton Woolen Mills",
]);

interface RoleDef {
  key: ApolloRoleKey;
  label: string;
  nameField: keyof ProspectRowNormalized;
  emailField: keyof ProspectRowNormalized;
  emailColumn: string;
  nameColumn: (region: string) => string;
}

const ROLES: RoleDef[] = [
  {
    key: "CEO",
    label: "CEO",
    nameField: "ceoName",
    emailField: "ceoEmail",
    emailColumn: "CEO Email",
    nameColumn: (r) => r === "EU" ? "CEO / MD Name" : "CEO / Founder Name",
  },
  {
    key: "HEAD_OF_PRODUCT",
    label: "Head of Product",
    nameField: "headOfProductName",
    emailField: "headOfProductEmail",
    emailColumn: "Head of Product Email",
    nameColumn: () => "Head of Product (Name)",
  },
  {
    key: "HEAD_OF_ECOMMERCE",
    label: "Head of Ecommerce",
    nameField: "headOfEcommerceName",
    emailField: "headOfEcommerceEmail",
    emailColumn: "Head of Ecommerce Email",
    nameColumn: () => "Head of Ecommerce (Name)",
  },
  {
    key: "HEAD_OF_GROWTH",
    label: "Head of Growth",
    nameField: "headOfGrowthName",
    emailField: "headOfGrowthEmail",
    emailColumn: "Head of Growth / CMO Email",
    nameColumn: () => "Head of Growth / CMO (Name)",
  },
];

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

async function main() {
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const byCompany = new Map<string, ProspectRowNormalized>();
  for (const row of allRows.filter((r) => TARGET_COMPANIES.has(r.companyName))) {
    if (!byCompany.has(row.companyName)) byCompany.set(row.companyName, row);
  }

  console.log(`\n=== APOLLO ENRICHMENT ===`);
  console.log(`Companies: ${byCompany.size}`);

  const wbCache = new Map<string, {
    workbook: ReturnType<typeof import("xlsx").readFile>;
    worksheet: import("xlsx").WorkSheet;
    filePath: string;
  }>();
  for (const config of ALL_CONFIGS) {
    const { workbook, worksheet, filePath } = loadPrimarySheet(config, ROOT_DIR);
    wbCache.set(config.filename, { workbook, worksheet, filePath });
  }
  for (const { filePath } of wbCache.values()) {
    const backup = createBackup(filePath);
    if (backup) console.log(`Backup: ${path.basename(backup)}`);
  }

  let written = 0;
  let skipped = 0;

  for (const [company, row] of byCompany) {
    const wb = wbCache.get(row.sourceFile);
    if (!wb) continue;

    // Collect roles that are missing an email
    const missingRoles = ROLES.filter(
      (r) => !(row[r.emailField] as string).trim(),
    );

    if (!missingRoles.length) {
      console.log(`\n[${row.region}] ${company} — all emails present, skipping`);
      skipped++;
      continue;
    }

    console.log(`\n[${row.region}] ${company} — missing: ${missingRoles.map((r) => r.label).join(", ")}`);

    const domain = extractDomain(row.websiteUrl);

    // Search Apollo per missing role (group by title set to reduce API calls)
    for (const role of missingRoles) {
      const titles = [...APOLLO_TITLES[role.key]];
      process.stdout.write(`  ${role.label} → `);

      const result = await searchPeopleByCompanyAndTitles(company, domain, titles, 3);
      await sleep(1500);

      if (result.status === "error") {
        console.log(`error — ${result.errorMessage}`);
        continue;
      }
      if (result.status === "not_found" || !result.people.length) {
        console.log("not found");
        continue;
      }

      // Pick the first person with an email; fall back to first person with a name
      const withEmail = result.people.find((p) => p.email);
      const best = withEmail ?? result.people[0];

      console.log(`${best.name} (${best.title})`);

      if (best.email) {
        writeCell(wb.worksheet, row.rowIndex, role.emailColumn, best.email, `  ${role.emailColumn}`);
        written++;
      } else {
        console.log(`    (no email returned — may need reveal credit)`);
      }

      // Write name if missing
      const existingName = (row[role.nameField] as string).trim();
      if (!existingName && best.name) {
        writeCell(wb.worksheet, row.rowIndex, role.nameColumn(row.region), best.name, `  ${role.label} Name`);
      }
    }
  }

  for (const { workbook, filePath } of wbCache.values()) {
    saveWorkbookInPlace(workbook, filePath);
    console.log(`\nSaved: ${path.basename(filePath)}`);
  }

  console.log(`\n=== DONE ===`);
  console.log(`Emails written: ${written}`);
  console.log(`Companies skipped (complete): ${skipped}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
