import { config } from 'dotenv';
import { resolve } from 'path';
import { writeFileSync } from 'fs';
import { init } from '@instantdb/admin';
import schema from '../instant.schema';

config({ path: resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
  schema,
});

interface ExportedStep {
  step_order?: number;
  delay_days?: number;
  subject_template?: string | null;
  body_template?: string | null;
}

interface ExportedSequence {
  id?: string;
  name?: string | null;
  is_active?: number | boolean | null;
  from_email?: string | null;
  description?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  enrollments?: unknown[];
  steps?: ExportedStep[];
}

async function main() {
  const data = await db.query({
    sequences: { steps: {}, enrollments: {} },
  });

  const seqs = (data.sequences as ExportedSequence[]).sort((a, b) =>
    (a.created_at ?? '').localeCompare(b.created_at ?? '')
  );

  const lines: string[] = [];
  lines.push(`# CRM Sequences Export`);
  lines.push('');
  lines.push(`Exported: ${new Date().toISOString()}`);
  lines.push(`Total sequences: ${seqs.length}`);
  lines.push('');

  for (const s of seqs) {
    const steps = (s.steps ?? []).sort(
      (a, b) => (a.step_order ?? 0) - (b.step_order ?? 0)
    );
    lines.push(`---`);
    lines.push('');
    lines.push(`## ${s.name ?? '(unnamed)'}`);
    lines.push('');
    lines.push(`- **ID:** \`${s.id}\``);
    lines.push(`- **Active:** ${s.is_active ? 'yes' : 'no'}`);
    if (s.from_email) lines.push(`- **From email:** ${s.from_email}`);
    if (s.description) lines.push(`- **Description:** ${s.description}`);
    lines.push(`- **Created:** ${s.created_at ?? 'n/a'}`);
    lines.push(`- **Updated:** ${s.updated_at ?? 'n/a'}`);
    lines.push(`- **Enrollments:** ${(s.enrollments ?? []).length}`);
    lines.push(`- **Steps:** ${steps.length}`);
    lines.push('');

    for (const step of steps) {
      lines.push(`### Step ${step.step_order ?? 0} — delay ${step.delay_days ?? 0} day(s)`);
      lines.push('');
      lines.push(`**Subject:** ${step.subject_template ?? '(none)'}`);
      lines.push('');
      lines.push(`**Body:**`);
      lines.push('');
      lines.push('```');
      lines.push((step.body_template ?? '').toString());
      lines.push('```');
      lines.push('');
    }
  }

  const out = resolve(process.cwd(), 'crm-sequences-export.md');
  writeFileSync(out, lines.join('\n'), 'utf8');
  console.log(`Wrote ${out} (${seqs.length} sequences)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
