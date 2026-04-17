/**
 * Appends a CAN-SPAM/GDPR compliant footer to all sequence step body templates.
 *
 * Footer added:
 *   --
 *   Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
 *   Lucni 19, 130 00, Prague, Czech Republic
 *
 * Idempotent — skips any step that already contains the address.
 */

import { init } from '@instantdb/admin';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
});

const FOOTER = `\n\n--\nMichal Pekarcik  |  Find Sherpas  |  findsherpas.com\nLucni 19, 130 00, Prague, Czech Republic`;
const FOOTER_MARKER = 'Lucni 19';

async function main() {
  const data = await db.query({ sequenceSteps: { sequence: {} } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const steps = data.sequenceSteps as any[];

  console.log(`Found ${steps.length} sequence steps`);

  let updated = 0;
  let skipped = 0;

  for (const step of steps) {
    const body: string = step.body_template ?? '';
    const seqName: string = step.sequence?.name ?? 'unknown';
    const label = `[${seqName} — Step ${step.step_order}]`;

    if (body.includes(FOOTER_MARKER)) {
      console.log(`  SKIP  ${label} — footer already present`);
      skipped++;
      continue;
    }

    const newBody = body + FOOTER;
    await db.transact(
      db.tx.sequenceSteps[step.id as string].update({ body_template: newBody })
    );
    console.log(`  OK    ${label}`);
    updated++;
  }

  console.log(`\nDone. Updated: ${updated}, Skipped: ${skipped}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
