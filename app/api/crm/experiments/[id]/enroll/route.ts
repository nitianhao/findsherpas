import { NextRequest, NextResponse } from 'next/server';
import { enrollInExperiment } from '@/lib/crm/queries/experiments';
import { z } from 'zod';

const schema = z.object({
  contact_ids: z.array(z.string().min(1)).min(1),
});

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await req.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.issues[0].message }, { status: 400 });
  }
  await enrollInExperiment(id, parsed.data.contact_ids);
  return NextResponse.json({ ok: true });
}
