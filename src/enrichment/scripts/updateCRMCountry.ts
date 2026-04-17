/**
 * Populates the country field for all 25 target companies.
 * Country derived from TLD where unambiguous; researched for .com domains.
 * Usage: npm run enrichment:update-country
 */

import { adminDb } from "@/lib/crm/instant-db";
import { getCompanies } from "@/lib/crm/queries/companies";

const COUNTRIES: Array<{ name: string; country: string }> = [
  // EU — Germany (.de TLD or known HQ)
  { name: "Flaconi",               country: "Germany" },
  { name: "Bergzeit",              country: "Germany" },
  { name: "Tennis-Point",          country: "Germany" },
  { name: "Fashionette",           country: "Germany" },
  // EU — United Kingdom
  { name: "Beauty Bay",            country: "United Kingdom" },
  { name: "Sweaty Betty",          country: "United Kingdom" },
  { name: "Cotswold Outdoor",      country: "United Kingdom" },
  // EU — Sweden
  { name: "Sportamore",            country: "Sweden" },
  { name: "Nordic Nest",           country: "Sweden" },
  { name: "Desenio",               country: "Sweden" },
  { name: "NA-KD",                 country: "Sweden" },
  { name: "Lyko",                  country: "Sweden" },
  // EU — Denmark
  { name: "Boozt",                 country: "Denmark" },
  { name: "Miinto",                country: "Denmark" },
  // EU — Finland
  { name: "Marimekko",             country: "Finland" },
  // US
  { name: "Backcountry",           country: "United States" },
  { name: "Vuori",                 country: "United States" },
  { name: "Reformation",           country: "United States" },
  { name: "True Classic",          country: "United States" },
  { name: "Rothy's",               country: "United States" },
  { name: "Tecovas",               country: "United States" },
  { name: "Orvis",                 country: "United States" },
  { name: "Cotopaxi",              country: "United States" },
  { name: "Huckberry",             country: "United States" },
  { name: "Pendleton Woolen Mills",country: "United States" },
];

async function main() {
  console.log("\n=== UPDATE CRM COUNTRY ===\n");

  const { companies } = await getCompanies({ limit: 500 });
  const byName = new Map(companies.map((c) => [c.name.toLowerCase().trim(), c]));

  let updated = 0;
  let notFound = 0;

  for (const entry of COUNTRIES) {
    const company = byName.get(entry.name.toLowerCase().trim());
    if (!company) {
      console.log(`NOT FOUND: ${entry.name}`);
      notFound++;
      continue;
    }

    await adminDb.transact([
      adminDb.tx.companies[company.id].update({
        country: entry.country,
        updated_at: new Date().toISOString(),
      }),
    ]);

    console.log(`${entry.name} → ${entry.country}`);
    updated++;
  }

  console.log("\n=== DONE ===");
  console.log(`Updated: ${updated}  |  Not found: ${notFound}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
