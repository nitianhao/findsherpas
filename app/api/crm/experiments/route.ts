import { NextRequest, NextResponse } from 'next/server';
import { getExperiments, createExperiment } from '@/lib/crm/queries/experiments';
import { z } from 'zod';

const createSchema = z.object({
  name: z.string().min(1),
  sequence_a_id: z.string().min(1),
  sequence_b_id: z.string().min(1),
});

export async function GET() {
  const experiments = await getExperiments();
  return NextResponse.json({ experiments });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const parsed = createSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.issues[0].message }, { status: 400 });
  }
  const { name, sequence_a_id, sequence_b_id } = parsed.data;
  if (sequence_a_id === sequence_b_id) {
    return NextResponse.json({ error: 'Variant A and B must be different sequences' }, { status: 400 });
  }
  const experiment = await createExperiment(name, sequence_a_id, sequence_b_id);
  return NextResponse.json(experiment, { status: 201 });
}
