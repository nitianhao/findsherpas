import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { getSequenceById, getStepsBySequenceId } from '@/lib/crm/queries/sequences';
import { resolveTemplate } from '@/lib/crm/template';
import { sendTestEmail } from '@/lib/crm/email';

const testEmailSchema = z.object({
  step_id: z.string().min(1),
  to_email: z.string().email(),
  vars: z.record(z.string(), z.string()).default({}),
});

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const [sequence, steps] = await Promise.all([
      getSequenceById(id),
      getStepsBySequenceId(id),
    ]);

    if (!sequence) {
      return NextResponse.json({ error: 'Sequence not found' }, { status: 404 });
    }

    const body = await request.json();
    const parsed = testEmailSchema.parse(body);

    const step = steps.find((s) => s.id === parsed.step_id);
    if (!step) {
      return NextResponse.json({ error: 'Step not found in this sequence' }, { status: 404 });
    }

    const subject = resolveTemplate(step.subject_template ?? '(no subject)', parsed.vars);
    const emailBody = resolveTemplate(step.body_template ?? '', parsed.vars);

    const messageId = await sendTestEmail(
      parsed.to_email,
      subject,
      emailBody,
      sequence.from_email ?? undefined
    );

    return NextResponse.json({ ok: true, messageId });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: error.errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to send test email' },
      { status: 500 }
    );
  }
}
