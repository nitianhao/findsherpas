import { NextResponse } from 'next/server';
import { z } from 'zod';
import { updateEnrollmentDealStage, DEAL_STAGES } from '@/lib/crm/queries/pipeline';

const patchSchema = z.object({
  deal_stage: z.enum(DEAL_STAGES).nullable(),
});

export async function PATCH(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.json();
  const parsed = patchSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }
  await updateEnrollmentDealStage(id, parsed.data.deal_stage);
  return NextResponse.json({ ok: true });
}
