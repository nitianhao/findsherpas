/**
 * Email pattern inference enrichment.
 *
 * For each target company that already has at least one email from Hunter,
 * detects the company's email format (firstname.lastname, flastname, etc.),
 * then generates email addresses for any role that has a name but no email.
 *
 * No external API calls — pure logic using existing data.
 * Usage: npm run enrichment:pattern
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
import { classifyEmailPattern, inferDomainPatternFromObservedEmails } from "../email/emailPatternInference";
import { generateEmailCandidatesForPerson } from "../email/emailGenerator";
import { splitEmail } from "../email/emailUtils";
import type { ProspectRowNormalized, TargetRole } from "../types/prospect";

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

const TARGET_COMPANIES = new Set([
  "Flaconi", "Bergzeit", "Tennis-Point", "Fashionette", "Sweaty Betty",
  "Beauty Bay", "Cotswold Outdoor", "Sportamore", "Nordic Nest", "Desenio",
  "NA-KD", "Lyko", "Boozt", "Marimekko", "Miinto",
  "Backcountry", "Vuori", "Reformation", "True Classic", "Rothy's",
  "Tecovas", "Orvis", "Cotopaxi", "Huckberry", "Pendleton Woolen Mills",
]);

interface RoleDef {
  label: string;
  role: TargetRole;
  nameField: keyof ProspectRowNormalized;
  emailField: keyof ProspectRowNormalized;
  emailColumn: string;
  nameColumn: (region: string) => string;
}

const ROLES: RoleDef[] = [
  {
    role: "CEO",
    label: "CEO",
    nameField: "ceoName",
    emailField: "ceoEmail",
    emailColumn: "CEO Email",
    nameColumn: (r) => r === "EU" ? "CEO / MD Name" : "CEO / Founder Name",
  },
  {
    role: "HEAD_OF_PRODUCT",
    label: "Head of Product",
    nameField: "headOfProductName",
    emailField: "headOfProductEmail",
    emailColumn: "Head of Product Email",
    nameColumn: () => "Head of Product (Name)",
  },
  {
    role: "HEAD_OF_ECOMMERCE",
    label: "Head of Ecommerce",
    nameField: "headOfEcommerceName",
    emailField: "headOfEcommerceEmail",
    emailColumn: "Head of Ecommerce Email",
    nameColumn: () => "Head of Ecommerce (Name)",
  },
  {
    role: "HEAD_OF_GROWTH",
    label: "Head of Growth",
    nameField: "headOfGrowthName",
    emailField: "headOfGrowthEmail",
    emailColumn: "Head of Growth / CMO Email",
    nameColumn: () => "Head of Growth / CMO (Name)",
  },
];

function extractDomain(url: string): string {
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname
      .replace(/^www\./, "").toLowerCase();
  } catch { return ""; }
}

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

  console.log(`\n=== PATTERN INFERENCE ENRICHMENT ===`);

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

  let inferred = 0;
  let noPattern = 0;

  for (const [company, row] of byCompany) {
    const wb = wbCache.get(row.sourceFile);
    if (!wb) continue;

    const domain = extractDomain(row.websiteUrl);

    // Collect all known emails + person names for this company to infer the pattern
    const knownEmails: Array<{ email: string; localPart: string; domain: string }> = [];
    const knownNames: string[] = [];

    for (const role of ROLES) {
      const email = (row[role.emailField] as string).trim();
      const name = (row[role.nameField] as string).trim();
      if (email) {
        const parts = splitEmail(email);
        if (parts && parts.domain === domain) knownEmails.push({ email, ...parts });
      }
      if (name) knownNames.push(name);
    }

    // Need at least one on-domain email to infer a pattern
    if (!knownEmails.length) {
      console.log(`\n[${row.region}] ${company} — no known emails, skipping pattern inference`);
      noPattern++;
      continue;
    }

    const inferredPattern = inferDomainPatternFromObservedEmails(domain, knownEmails, knownNames);

    if (!inferredPattern || inferredPattern.patternType === "UNKNOWN" || inferredPattern.confidenceScore < 40) {
      console.log(`\n[${row.region}] ${company} — pattern unclear (${inferredPattern?.patternType ?? "none"}, confidence ${inferredPattern?.confidenceScore ?? 0})`);
      noPattern++;
      continue;
    }

    console.log(`\n[${row.region}] ${company} — pattern: ${inferredPattern.patternType} (confidence ${inferredPattern.confidenceScore})`);
    console.log(`  Evidence: ${inferredPattern.evidenceEmails.join(", ")}`);

    // Generate emails for roles with a name but no email
    for (const role of ROLES) {
      const existingEmail = (row[role.emailField] as string).trim();
      const name = (row[role.nameField] as string).trim();

      if (existingEmail) continue; // already have it
      if (!name) continue;        // no name to work from

      const candidates = generateEmailCandidatesForPerson(name, domain, inferredPattern, role.role);
      const best = candidates[0];
      if (!best) continue;

      // Only write if confidence is reasonable
      if (best.confidenceScore < 40) {
        console.log(`  ${role.label}: ${name} → low confidence (${best.confidenceScore}), skipping`);
        continue;
      }

      console.log(`  ${role.label}: ${name} → ${best.email} [${best.confidenceLabel}, ${best.confidenceScore}]`);
      writeCell(wb.worksheet, row.rowIndex, role.emailColumn, best.email, role.emailColumn);
      inferred++;
    }
  }

  for (const { workbook, filePath } of wbCache.values()) {
    saveWorkbookInPlace(workbook, filePath);
    console.log(`\nSaved: ${path.basename(filePath)}`);
  }

  console.log(`\n=== DONE ===`);
  console.log(`Emails inferred and written: ${inferred}`);
  console.log(`Companies skipped (no pattern): ${noPattern}`);
  console.log(`\nNOTE: Inferred emails are guesses based on the domain pattern.`);
  console.log(`Verify important ones before sending.`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
