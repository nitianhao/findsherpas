/**
 * Send a real, full-template sequence email (with real unsubscribe link +
 * List-Unsubscribe header) to a test recipient, using Miinto's company data.
 *
 * Usage: tsx --tsconfig tsconfig.json scripts/send-test-sequence.ts <A|B|C> <step 1-4> [--send]
 *   Without --send it only prints the fully-resolved email (dry run).
 */
import { config } from 'dotenv';
import { resolve } from 'path';
import { init } from '@instantdb/admin';
import schema from '../instant.schema';
import { buildSearchPlatformSentence } from '../lib/crm/template';

config({ path: resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
  schema,
});

const TO_EMAIL = 'michal.pekarcik@gmail.com';
const CONTACT_NAME = 'Michal Pekarcik';
const COMPANY_NAME = 'Miinto';

const SEQ_IDS: Record<string, string> = {
  A: '9fa450d1-1378-4b18-92ce-63a162de7ca6',
  B: 'd55b28f3-845d-4b5f-9cfa-4f2073cfb856',
  C: '0cf47441-59b3-4397-97f8-379c2dc37a50',
};

async function main() {
  const letter = (process.argv[2] ?? '').toUpperCase();
  const stepNum = Number(process.argv[3]);
  const doSend = process.argv.includes('--send');

  const seqId = SEQ_IDS[letter];
  if (!seqId || !stepNum) {
    console.error('Usage: <A|B|C> <step 1-4> [--send]');
    process.exit(1);
  }

  // Load sequence + steps
  const seqData = await db.query({
    sequences: { $: { where: { id: seqId } }, steps: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const seq = (seqData.sequences as any[])[0];
  if (!seq) throw new Error('Sequence not found');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const step = (seq.steps ?? []).find((s: any) => s.step_order === stepNum);
  if (!step) throw new Error(`Step ${stepNum} not found`);

  // Load Miinto company (audit vars, report_url, contacts)
  const coData = await db.query({
    companies: { $: { where: { name: COMPANY_NAME } }, contacts: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const co = (coData.companies as any[])[0];
  if (!co) throw new Error('Miinto company not found');
  const contactId: string = (co.contacts ?? [])[0]?.id;
  if (!contactId) throw new Error('No Miinto contact for unsubscribe token');

  // Build audit_vars exactly as getTodaysEmailTasks does
  const auditKeys = [
    'score', 'query_count', 'cap_count', 'top3rate', 'outside3rate',
    'worst_query', 'worst_pos', 'wrong_product', 'worst_example',
  ] as const;
  const audit_vars: Record<string, string> = {};
  for (const k of auditKeys) {
    const v = co[`audit_${k}`];
    if (typeof v === 'string' && v.length > 0) {
      audit_vars[k] = v;
      if (k === 'top3rate') audit_vars['top_3_rate'] = v;
      if (k === 'outside3rate') audit_vars['outside_3_rate'] = v;
    }
  }
  audit_vars['search_platform_sentence'] = buildSearchPlatformSentence(
    (co.search_solution as string | null) ?? null
  );

  // Build EmailTask mirroring lib/crm/queries/tasks.ts shape
  const task = {
    event_id: 'test',
    contact_name: CONTACT_NAME,
    contact_email: TO_EMAIL,
    contact_id: contactId,
    company_name: co.name ?? COMPANY_NAME,
    company_id: co.id,
    sequence_name: seq.name,
    step_order: step.step_order,
    subject_template: step.subject_template ?? null,
    body_template: step.body_template ?? null,
    scheduled_date: new Date().toISOString().slice(0, 10),
    send_hour: null,
    is_overdue: false,
    audit_vars: Object.keys(audit_vars).length > 0 ? audit_vars : null,
    report_url: (co.report_url as string | null) ?? null,
  };

  console.log(`\n=== ${seq.name} / Step ${step.step_order} ===`);
  console.log(`To: ${TO_EMAIL}`);
  console.log(`From: ${seq.from_email ?? process.env.RESEND_FROM_EMAIL}`);
  console.log(`Unsubscribe contact_id: ${contactId} (real Miinto contact — do NOT click in test)`);

  if (!doSend) {
    // Dry-run: resolve and print without sending
    const { resolveTemplate, buildVars } = await import('../lib/crm/template');
    const { buildUnsubscribeUrl } = await import('../lib/crm/unsubscribe');
    const vars = buildVars(task);
    Object.assign(vars, audit_vars);
    if (task.report_url) vars['report_url'] = task.report_url;
    vars['unsubscribe_url'] = buildUnsubscribeUrl(contactId);
    const subject = resolveTemplate(task.subject_template ?? '(no subject)', vars);
    let body = resolveTemplate(task.body_template ?? '', vars);
    if (!body.includes(vars['unsubscribe_url'])) {
      body += `\n\n---\nTo unsubscribe: ${vars['unsubscribe_url']}`;
    }
    const unresolved = (subject + body).match(/\{\{(\w+)\}\}/g);
    console.log(`\n--- DRY RUN (not sent) ---`);
    console.log(`Subject: ${subject}\n`);
    console.log(body);
    console.log(`\nList-Unsubscribe header: <${vars['unsubscribe_url']}>`);
    if (unresolved) console.log(`\n!! UNRESOLVED VARS: ${[...new Set(unresolved)].join(', ')}`);
    else console.log(`\nAll template variables resolved.`);
    return;
  }

  const { sendCrmEmail } = await import('../lib/crm/email');
  const messageId = await sendCrmEmail(task, seq.from_email ?? undefined);
  console.log(`\nSENT. Resend message id: ${messageId}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
