/**
 * Imports the 25 target companies and all available contacts into the CRM.
 *
 * - Creates each company as a prospect
 * - Creates one contact per role that has both a name and an email
 * - Skips companies/contacts that already exist (matched by name)
 *
 * Usage:
 *   NEXT_PUBLIC_INSTANT_APP_ID=xxx INSTANT_APP_ADMIN_TOKEN=xxx npm run enrichment:import-crm
 */

import * as path from "path";
import { ALL_CONFIGS } from "../schema/workbookConfigs";
import { readNormalizedRows } from "../io/workbookService";
import { adminDb, id } from "@/lib/crm/instant-db";
import { getCompanies } from "@/lib/crm/queries/companies";
import { getContacts } from "@/lib/crm/queries/contacts";
import type { ProspectRowNormalized } from "../types/prospect";

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
  nameField: keyof ProspectRowNormalized;
  emailField: keyof ProspectRowNormalized;
  linkedinField?: keyof ProspectRowNormalized;
}

const ROLES: RoleDef[] = [
  { label: "CEO",                  nameField: "ceoName",             emailField: "ceoEmail",             linkedinField: "ceoLinkedin" },
  { label: "Head of Product",      nameField: "headOfProductName",   emailField: "headOfProductEmail" },
  { label: "Head of Ecommerce",    nameField: "headOfEcommerceName", emailField: "headOfEcommerceEmail" },
  { label: "Head of Growth / CMO", nameField: "headOfGrowthName",    emailField: "headOfGrowthEmail" },
];

async function main() {
  console.log("\n=== CRM IMPORT ===");

  // Load all workbook rows
  const allRows = ALL_CONFIGS.flatMap((c) => readNormalizedRows(c, ROOT_DIR));
  const byCompany = new Map<string, ProspectRowNormalized>();
  for (const row of allRows.filter((r) => TARGET_COMPANIES.has(r.companyName))) {
    if (!byCompany.has(row.companyName)) byCompany.set(row.companyName, row);
  }
  console.log(`Target companies found in workbooks: ${byCompany.size}`);

  // Fetch existing CRM data to avoid duplicates
  const { companies: existingCompanies } = await getCompanies({ limit: 500 });
  const { contacts: existingContacts } = await getContacts({ limit: 2000 });

  const existingCompanyNames = new Set(
    existingCompanies.map((c) => c.name.toLowerCase().trim()),
  );
  const existingContactEmails = new Set(
    existingContacts.map((c) => c.email.toLowerCase().trim()),
  );

  console.log(`Existing CRM companies: ${existingCompanies.length}`);
  console.log(`Existing CRM contacts:  ${existingContacts.length}\n`);

  let companiesCreated = 0;
  let companiesSkipped = 0;
  let contactsCreated = 0;
  let contactsSkipped = 0;

  for (const [companyName, row] of byCompany) {
    const alreadyExists = existingCompanyNames.has(companyName.toLowerCase().trim());

    let companyId: string;

    if (alreadyExists) {
      const existing = existingCompanies.find(
        (c) => c.name.toLowerCase().trim() === companyName.toLowerCase().trim(),
      )!;
      companyId = existing.id;
      console.log(`[SKIP]   ${companyName} (already in CRM)`);
      companiesSkipped++;
    } else {
      companyId = id();
      const ts = new Date().toISOString();
      // Only write fields that are in the remote InstantDB schema
      const attrs: Record<string, unknown> = {
        name: companyName,
        status: "prospect",
        created_at: ts,
        updated_at: ts,
      };
      if (row.websiteUrl)          attrs.website = row.websiteUrl;
      if (row.category)            attrs.industry = row.category;
      if (row.estimatedRevenue)    attrs.revenue_estimate = row.estimatedRevenue;
      if (row.linkedinCompanyPage) attrs.social_linkedin = row.linkedinCompanyPage;
      if (row.notes)               attrs.notes = row.notes;
      // country / language were added to schema later — skip to avoid remote schema mismatch

      await adminDb.transact([adminDb.tx.companies[companyId].update(attrs)]);
      console.log(`[CREATE] ${companyName} (${row.region})`);
      companiesCreated++;
    }

    // Create contacts for every role with both name and email
    for (const role of ROLES) {
      const name = (row[role.nameField] as string).trim();
      const email = (row[role.emailField] as string).trim();
      if (!name || !email) continue;

      if (existingContactEmails.has(email.toLowerCase())) {
        console.log(`         [SKIP contact] ${name} <${email}>`);
        contactsSkipped++;
        continue;
      }

      const linkedin = role.linkedinField
        ? (row[role.linkedinField] as string).trim() || null
        : null;

      const contactId = id();
      const ts = new Date().toISOString();
      const contactAttrs: Record<string, unknown> = {
        name,
        email,
        role: role.label,
        status: "active",
        created_at: ts,
        updated_at: ts,
      };
      if (linkedin) contactAttrs.linkedin_url = linkedin;

      await adminDb.transact([
        adminDb.tx.contacts[contactId].update(contactAttrs),
        adminDb.tx.contacts[contactId].link({ company: companyId }),
      ]);

      console.log(`         [contact] ${role.label}: ${name} <${email}>`);
      contactsCreated++;
      existingContactEmails.add(email.toLowerCase()); // prevent dupes within this run
    }
  }

  console.log("\n=== DONE ===");
  console.log(`Companies created: ${companiesCreated}`);
  console.log(`Companies skipped: ${companiesSkipped}`);
  console.log(`Contacts  created: ${contactsCreated}`);
  console.log(`Contacts  skipped: ${contactsSkipped}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  if (err?.hint) console.error("Hint:", JSON.stringify(err.hint, null, 2));
  process.exit(1);
});
