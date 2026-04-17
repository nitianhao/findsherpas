/**
 * Updates platform and search_solution fields for the 25 target companies in the CRM.
 * Usage: npm run enrichment:update-tech-stack
 */

import { adminDb } from "@/lib/crm/instant-db";
import { getCompanies } from "@/lib/crm/queries/companies";

const TECH_STACK: Array<{ name: string; platform: string; search_solution: string }> = [
  // EU
  { name: "Flaconi",               platform: "commercetools",                              search_solution: "Algolia" },
  { name: "Bergzeit",              platform: "novomind iSHOP",                             search_solution: "novomind (built-in)" },
  { name: "Tennis-Point",          platform: "Salesforce Commerce Cloud",                  search_solution: "Salesforce Einstein Search" },
  { name: "Fashionette",           platform: "Custom (The Platform Group)",                search_solution: "Custom/proprietary" },
  { name: "Beauty Bay",            platform: "Shopify Plus",                               search_solution: "Searchspring" },
  { name: "Sweaty Betty",          platform: "Salesforce Commerce Cloud",                  search_solution: "Salesforce Einstein Search" },
  { name: "Cotswold Outdoor",      platform: "Custom/proprietary",                         search_solution: "Fredhopper (Crownpeak)" },
  { name: "Sportamore",            platform: "Shopify",                                    search_solution: "Searchanise" },
  { name: "Nordic Nest",           platform: "commercetools (Avensia Excite)",             search_solution: "Voyado Elevate (Apptus eSales)" },
  { name: "Desenio",               platform: "Custom (Next.js)",                           search_solution: "Custom/proprietary" },
  { name: "NA-KD",                 platform: "Optimizely Commerce (Avensia Nitro)",        search_solution: "Voyado Elevate (Apptus eSales)" },
  { name: "Lyko",                  platform: "Optimizely Commerce (Avensia Nitro)",        search_solution: "Voyado Elevate (Apptus eSales)" },
  { name: "Boozt",                 platform: "Custom/in-house",                            search_solution: "Custom/in-house" },
  { name: "Marimekko",             platform: "commercetools",                              search_solution: "Custom/proprietary" },
  { name: "Miinto",                platform: "Custom/in-house (Google Cloud)",             search_solution: "Algonomy (RichRelevance)" },
  // US
  { name: "Backcountry",           platform: "Oracle Commerce (custom evolution)",         search_solution: "Constructor.io" },
  { name: "Vuori",                 platform: "Shopify Plus",                               search_solution: "Native Shopify Search" },
  { name: "Reformation",           platform: "Salesforce Commerce Cloud",                  search_solution: "Salesforce Einstein Search" },
  { name: "True Classic",          platform: "Shopify",                                    search_solution: "Native Shopify Search" },
  { name: "Rothy's",               platform: "Shopify Plus",                               search_solution: "Constructor.io" },
  { name: "Tecovas",               platform: "Shopify Plus",                               search_solution: "Native Shopify Search" },
  { name: "Orvis",                 platform: "Oracle Commerce",                            search_solution: "Custom/Elasticsearch" },
  { name: "Cotopaxi",              platform: "Shopify Plus",                               search_solution: "Google Vertex AI Search" },
  { name: "Huckberry",             platform: "Spree Commerce (custom Rails)",              search_solution: "Algolia" },
  { name: "Pendleton Woolen Mills",platform: "Salesforce Commerce Cloud",                  search_solution: "Salesforce Einstein Search" },
];

async function main() {
  console.log("\n=== UPDATE CRM TECH STACK ===\n");

  const { companies } = await getCompanies({ limit: 500 });
  const byName = new Map(companies.map((c) => [c.name.toLowerCase().trim(), c]));

  let updated = 0;
  let notFound = 0;

  for (const entry of TECH_STACK) {
    const company = byName.get(entry.name.toLowerCase().trim());
    if (!company) {
      console.log(`NOT FOUND: ${entry.name}`);
      notFound++;
      continue;
    }

    await adminDb.transact([
      adminDb.tx.companies[company.id].update({
        platform: entry.platform,
        search_solution: entry.search_solution,
        updated_at: new Date().toISOString(),
      }),
    ]);

    console.log(`${entry.name}`);
    console.log(`  platform:        ${entry.platform}`);
    console.log(`  search_solution: ${entry.search_solution}\n`);
    updated++;
  }

  console.log("=== DONE ===");
  console.log(`Updated: ${updated}  |  Not found: ${notFound}`);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
