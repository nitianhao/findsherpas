/**
 * Updates sequence step body templates to replace the calendar link placeholder
 * with the real cal.eu booking URL.
 *
 * Replaces occurrences of [calendar link] with the actual URL.
 * Also replaces "Is [specific day] at [time] open for 30 minutes?" with a
 * direct booking CTA pointing to the cal link.
 *
 * Idempotent — only updates steps that still contain the placeholder.
 */

import { init } from '@instantdb/admin';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
});

const CAL_URL = 'https://cal.eu/michal-pekarcik-r6j8fb';

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

    let newBody = body;

    // Replace [calendar link] placeholder
    newBody = newBody.replace(/\[calendar link\]/gi, CAL_URL);

    // Replace "Is [specific day] at [time] open for 30 minutes?" with direct CTA
    newBody = newBody.replace(
      /Is \[specific day\] at \[time\] open for 30 minutes\?/gi,
      `Book a 30-minute call: ${CAL_URL}`
    );

    if (newBody === body) {
      console.log(`  SKIP  ${label} — no placeholder found`);
      skipped++;
      continue;
    }

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
