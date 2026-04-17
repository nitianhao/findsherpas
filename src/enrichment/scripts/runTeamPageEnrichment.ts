/**
 * Team/leadership page scraper enrichment.
 *
 * For each target company, tries a set of common "about" / "team" / "leadership"
 * page URL patterns, extracts executive names + titles from the page text,
 * then feeds any new names into email pattern inference or Hunter Email Finder.
 *
 * Usage: HUNTER_API_KEY=xxx npm run enrichment:team-pages
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
import { newPage, closeBrowser } from "../browser/browserPool";
import { findEmail, parseName } from "../email/hunterAdapter";
import { classifyEmailPattern, inferDomainPatternFromObservedEmails } from "../email/emailPatternInference";
import { generateEmailCandidatesForPerson } from "../email/emailGenerator";
import { splitEmail } from "../email/emailUtils";
import type { ProspectRowNormalized, TargetRole } from "../types/prospect";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");

const TARGET_COMPANIES = new Set([
  "Flaconi", "Bergzeit", "Tennis-Point", "Fashionette", "Sweaty Betty",
  "Beauty Bay", "Cotswold Outdoor", "Sportamore", "Nordic Nest", "Desenio",
  "NA-KD", "Lyko", "Boozt", "Marimekko", "Miinto",
  "Backcountry", "Vuori", "Reformation", "True Classic", "Rothy's",
  "Tecovas", "Orvis", "Cotopaxi", "Huckberry", "Pendleton Woolen Mills",
]);

// URL slug candidates to try for each company — ordered most-specific first
const TEAM_PAGE_SLUGS = [
  // Dedicated leadership/team pages
  "/leadership", "/our-leadership", "/management", "/management-team",
  "/team", "/our-team", "/the-team",
  // Investor / press relations (common for EU companies)
  "/investor-relations/management", "/investor-relations/team",
  "/ir/management", "/ir/team", "/ir/board",
  "/investors/management", "/investors/team",
  "/en/investor-relations/management", "/en/ir/management",
  "/press/team", "/press/management",
  // About pages
  "/about/team", "/about/leadership", "/about/management",
  "/about-us/team", "/about-us/leadership",
  "/company/team", "/company/leadership", "/company/management",
  "/en/about/team", "/en/about/management",
  "/en/about", "/en/about-us",
  "/about-us", "/about", "/company",
];

// Title keywords that indicate a relevant executive
const CEO_TITLES = ["ceo", "chief executive", "founder", "managing director", "md", "president"];
const PRODUCT_TITLES = ["product", "cpo", "chief product"];
const ECOMMERCE_TITLES = ["ecommerce", "e-commerce", "digital commerce", "head of online"];
const GROWTH_TITLES = ["cmo", "chief marketing", "head of marketing", "head of growth", "vp marketing", "vp growth"];

interface RoleDef {
  role: TargetRole;
  label: string;
  titleKeywords: string[];
  nameField: keyof ProspectRowNormalized;
  emailField: keyof ProspectRowNormalized;
  emailColumn: string;
  nameColumn: (region: string) => string;
}

const ROLES: RoleDef[] = [
  {
    role: "CEO", label: "CEO", titleKeywords: CEO_TITLES,
    nameField: "ceoName", emailField: "ceoEmail",
    emailColumn: "CEO Email",
    nameColumn: (r) => r === "EU" ? "CEO / MD Name" : "CEO / Founder Name",
  },
  {
    role: "HEAD_OF_PRODUCT", label: "Head of Product", titleKeywords: PRODUCT_TITLES,
    nameField: "headOfProductName", emailField: "headOfProductEmail",
    emailColumn: "Head of Product Email",
    nameColumn: () => "Head of Product (Name)",
  },
  {
    role: "HEAD_OF_ECOMMERCE", label: "Head of Ecommerce", titleKeywords: ECOMMERCE_TITLES,
    nameField: "headOfEcommerceName", emailField: "headOfEcommerceEmail",
    emailColumn: "Head of Ecommerce Email",
    nameColumn: () => "Head of Ecommerce (Name)",
  },
  {
    role: "HEAD_OF_GROWTH", label: "Head of Growth", titleKeywords: GROWTH_TITLES,
    nameField: "headOfGrowthName", emailField: "headOfGrowthEmail",
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

// ---------------------------------------------------------------------------
// Page scraping
// ---------------------------------------------------------------------------

interface ScrapedPerson {
  name: string;
  title: string;
}

/**
 * Tries team/leadership pages and extracts person + title pairs.
 * Returns the found people and the URL that worked (or null).
 */
async function scrapeTeamPage(
  baseUrl: string,
): Promise<{ people: ScrapedPerson[]; pageUrl: string | null }> {
  const base = baseUrl.replace(/\/$/, "");
  const page = await newPage();

  try {
    for (const slug of TEAM_PAGE_SLUGS) {
      const url = `${base}${slug}`;
      try {
        const response = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
        if (!response || !response.ok()) continue;

        await sleep(1500); // let JS render

        const people = await page.evaluate(() => {
          const results: Array<{ name: string; title: string }> = [];

          // Strategy 1: JSON-LD structured data (most reliable)
          const jsonLdTags = document.querySelectorAll('script[type="application/ld+json"]');
          for (const tag of Array.from(jsonLdTags)) {
            try {
              const data = JSON.parse(tag.textContent ?? "");
              const items = Array.isArray(data) ? data : [data];
              for (const item of items) {
                // Direct Person type
                if (item["@type"] === "Person" && item.name) {
                  results.push({ name: item.name, title: item.jobTitle ?? item.role ?? "" });
                }
                // Organization with employees/members
                const members = item.employee ?? item.member ?? item.member ?? [];
                for (const m of (Array.isArray(members) ? members : [members])) {
                  if (m?.name) results.push({ name: m.name, title: m.jobTitle ?? m.role ?? "" });
                }
              }
            } catch { /* invalid JSON-LD */ }
          }
          if (results.length > 0) return results;

          // Strategy 2: plain text scan — look for name/title line pairs
          // Title keywords that indicate an executive position
          const titleKeywords = [
            "ceo", "chief executive", "managing director", "founder",
            "chief product", "head of product", "vp product",
            "head of ecommerce", "head of e-commerce", "director of ecommerce",
            "head of digital", "vp digital", "digital director",
            "cmo", "chief marketing", "head of marketing", "head of growth",
            "vp marketing", "director of marketing",
            "president", "chief operating", "coo",
          ];

          // Get all visible text lines, stripped
          const allText = document.body.innerText ?? "";
          const lines = allText
            .split(/\n/)
            .map((l) => l.trim())
            .filter((l) => l.length > 1);

          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i];
            const next = lines[i + 1];

            // Check if this line looks like a person name (2-4 words, no special chars)
            const isName = /^[A-ZÀ-Ö][a-zà-ö]+(\s[A-ZÀ-Ö][a-zà-ö\-]+){1,3}$/.test(line);
            // Check if next line looks like a job title
            const isTitle = titleKeywords.some((k) => next.toLowerCase().includes(k));

            if (isName && isTitle) {
              results.push({ name: line, title: next });
              i++; // skip the title line
              continue;
            }

            // Also check reverse: title line then name line
            const thisIsTitle = titleKeywords.some((k) => line.toLowerCase().includes(k));
            const nextIsName = /^[A-ZÀ-Ö][a-zà-ö]+(\s[A-ZÀ-Ö][a-zà-ö\-]+){1,3}$/.test(next);

            if (thisIsTitle && nextIsName && line.length < 80) {
              results.push({ name: next, title: line });
              i++;
            }
          }

          return results;
        });

        // Deduplicate by name
        const seen = new Set<string>();
        const deduped = people.filter((p) => {
          if (seen.has(p.name)) return false;
          seen.add(p.name);
          return true;
        });

        if (deduped.length > 0) {
          await page.close();
          return { people: deduped, pageUrl: url };
        }
      } catch {
        // Try next slug
      }
    }

    await page.close();
    return { people: [], pageUrl: null };
  } catch (err) {
    try { await page.close(); } catch { /* ignore */ }
    return { people: [], pageUrl: null };
  }
}

function matchesRole(title: string, keywords: string[]): boolean {
  const lower = title.toLowerCase();
  return keywords.some((k) => lower.includes(k));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const useHunter = !!process.env.HUNTER_API_KEY;

  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const byCompany = new Map<string, ProspectRowNormalized>();
  for (const row of allRows.filter((r) => TARGET_COMPANIES.has(r.companyName))) {
    if (!byCompany.has(row.companyName)) byCompany.set(row.companyName, row);
  }

  console.log(`\n=== TEAM PAGE ENRICHMENT ===`);
  console.log(`Companies: ${byCompany.size}`);
  console.log(`Hunter Email Finder: ${useHunter ? "enabled" : "disabled (set HUNTER_API_KEY)"}`);

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

  let namesFound = 0;
  let emailsWritten = 0;

  for (const [company, row] of byCompany) {
    const wb = wbCache.get(row.sourceFile);
    if (!wb) continue;

    // Skip if all 4 emails already present
    const allPresent = ROLES.every((r) => (row[r.emailField] as string).trim());
    if (allPresent) {
      console.log(`\n[${row.region}] ${company} — complete, skipping`);
      continue;
    }

    console.log(`\n[${row.region}] ${company} — scraping team pages...`);

    const { people, pageUrl } = await scrapeTeamPage(row.websiteUrl);

    if (!people.length) {
      console.log(`  No team page found`);
      await sleep(1000);
      continue;
    }

    console.log(`  Found ${people.length} people on ${pageUrl}`);
    for (const p of people.slice(0, 6)) {
      console.log(`    - "${p.name}" / "${p.title}"`);
    }

    // Build pattern from existing emails for this company
    const domain = extractDomain(row.websiteUrl);
    const existingEmails = ROLES
      .map((r) => (row[r.emailField] as string).trim())
      .filter(Boolean)
      .map((email) => { const p = splitEmail(email); return p ? { email, ...p } : null; })
      .filter((p): p is NonNullable<typeof p> => p !== null && p.domain === domain);

    const existingNames = ROLES
      .map((r) => (row[r.nameField] as string).trim())
      .filter(Boolean);

    const inferredPattern = existingEmails.length > 0
      ? inferDomainPatternFromObservedEmails(domain, existingEmails, existingNames)
      : null;

    // For each role missing an email, look for a matching person in scraped data
    for (const role of ROLES) {
      const existingEmail = (row[role.emailField] as string).trim();
      const existingName = (row[role.nameField] as string).trim();
      if (existingEmail) continue;

      const match = people.find((p) => matchesRole(p.title, role.titleKeywords));
      if (!match) continue;

      namesFound++;
      console.log(`  ${role.label}: found ${match.name} (${match.title})`);

      // Write name if we don't have one
      if (!existingName) {
        writeCell(wb.worksheet, row.rowIndex, role.nameColumn(row.region), match.name, `${role.label} Name`);
      }

      // Try to get email via Hunter Email Finder
      if (useHunter) {
        const { firstName, lastName } = parseName(match.name);
        const result = await findEmail(row.websiteUrl, firstName, lastName);
        await sleep(1500);

        if (result.status === "found" && result.email) {
          writeCell(wb.worksheet, row.rowIndex, role.emailColumn, result.email, role.emailColumn);
          emailsWritten++;
          continue;
        }
      }

      // Fall back to pattern inference
      if (inferredPattern && inferredPattern.patternType !== "UNKNOWN" && inferredPattern.confidenceScore >= 40) {
        const candidates = generateEmailCandidatesForPerson(match.name, domain, inferredPattern, role.role);
        const best = candidates[0];
        if (best && best.confidenceScore >= 40) {
          writeCell(wb.worksheet, row.rowIndex, role.emailColumn, best.email, `${role.emailColumn} [inferred]`);
          emailsWritten++;
        }
      }
    }

    await sleep(2000);
  }

  await closeBrowser();

  for (const { workbook, filePath } of wbCache.values()) {
    saveWorkbookInPlace(workbook, filePath);
    console.log(`\nSaved: ${path.basename(filePath)}`);
  }

  console.log(`\n=== DONE ===`);
  console.log(`Names found via scraping: ${namesFound}`);
  console.log(`Emails written: ${emailsWritten}`);
}

main().catch(async (err) => {
  console.error("Fatal:", err);
  await closeBrowser();
  process.exit(1);
});
