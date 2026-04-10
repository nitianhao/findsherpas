import { NextRequest, NextResponse } from 'next/server';
import { getSequenceById, getStepsBySequenceId, saveSteps } from '@/lib/crm/queries/sequences';
import { z } from 'zod';

const saveStepsSchema = z.object({
  steps: z.array(z.object({
    step_order: z.number().int().positive(),
    subject_template: z.string().nullable().optional(),
    body_template: z.string().nullable().optional(),
    delay_days: z.number().int().min(0),
  })),
});

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sequenceId = id;

    const sequence = await getSequenceById(sequenceId);
    if (!sequence) {
      return NextResponse.json({ error: 'Sequence not found' }, { status: 404 });
    }

    const steps = await getStepsBySequenceId(sequenceId);
    return NextResponse.json(steps);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch steps' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sequenceId = id;

    const sequence = await getSequenceById(sequenceId);
    if (!sequence) {
      return NextResponse.json({ error: 'Sequence not found' }, { status: 404 });
    }

    const body = await request.json();
    const parsed = saveStepsSchema.parse(body);
    const steps = await saveSteps(sequenceId, parsed.steps);
    return NextResponse.json(steps);
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to save steps' },
      { status: 500 }
    );
  }
}
