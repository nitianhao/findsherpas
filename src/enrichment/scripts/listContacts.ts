/**
 * Lists all CRM contacts with their current linkedin_url values.
 * Usage: npm run enrichment:list-contacts
 */

import { getContacts } from "@/lib/crm/queries/contacts";

async function main() {
  const { contacts } = await getContacts({ limit: 500 });
  const sorted = [...contacts].sort((a, b) => {
    const cn = (a.company_name ?? "").localeCompare(b.company_name ?? "");
    return cn !== 0 ? cn : (a.role ?? "").localeCompare(b.role ?? "");
  });

  console.log(JSON.stringify(
    sorted.map(c => ({
      id: c.id,
      name: c.name,
      email: c.email,
      role: c.role,
      company: c.company_name,
      linkedin_url: c.linkedin_url ?? null,
    })),
    null,
    2
  ));
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
