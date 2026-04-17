/**
 * Fixes three name/email mismatches introduced during CRM import.
 *
 * Root cause: domain search found an email for Person A, but the workbook
 * stored a different person's name (Person B) in the same role column,
 * so the import linked the wrong name to the email.
 *
 * Fixes:
 *  - Backcountry CEO: "Jonathan Nielsen" + mickell.walker@backcountry.com
 *    → rename to "Mickell Walker" (email owner)
 *  - Bergzeit CEO: "Stawros Koutis" + martin.stolzenberger@bergzeit.de
 *    → rename to "Martin Stolzenberger" (email owner)
 *  - Tecovas Head of Ecommerce: "Kirstin Grimm Smith" + krista.dalton@tecovas.com
 *    → rename to "Krista Dalton" (email owner)
 */

import { adminDb } from "@/lib/crm/instant-db";
import { getContacts } from "@/lib/crm/queries/contacts";

const FIXES: Array<{
  email: string;
  correctName: string;
  description: string;
}> = [
  {
    email: "mickell.walker@backcountry.com",
    correctName: "Mickell Walker",
    description: "Backcountry CEO — name was Jonathan Nielsen (CEO) but email belongs to Mickell Walker",
  },
  {
    email: "martin.stolzenberger@bergzeit.de",
    correctName: "Martin Stolzenberger",
    description: "Bergzeit CEO — name was Stawros Koutis (CEO) but email belongs to Martin Stolzenberger",
  },
  {
    email: "krista.dalton@tecovas.com",
    correctName: "Krista Dalton",
    description: "Tecovas Head of Ecommerce — name was Kirstin Grimm Smith but email belongs to Krista Dalton",
  },
];

async function main() {
  console.log("\n=== FIX CRM MISMATCHES ===\n");

  const { contacts } = await getContacts({ limit: 2000 });

  for (const fix of FIXES) {
    const contact = contacts.find(
      (c) => c.email.toLowerCase() === fix.email.toLowerCase(),
    );

    if (!contact) {
      console.log(`NOT FOUND: ${fix.email}`);
      continue;
    }

    if (contact.name === fix.correctName) {
      console.log(`ALREADY CORRECT: ${fix.email} → ${contact.name}`);
      continue;
    }

    console.log(`FIX: "${contact.name}" → "${fix.correctName}" <${fix.email}>`);
    console.log(`     (${fix.description})`);

    await adminDb.transact([
      adminDb.tx.contacts[contact.id].update({
        name: fix.correctName,
        updated_at: new Date().toISOString(),
      }),
    ]);

    console.log(`     ✓ Updated\n`);
  }

  console.log("=== DONE ===");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
