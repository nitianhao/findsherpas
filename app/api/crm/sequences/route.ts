import { NextRequest, NextResponse } from 'next/server';
import { getSequences, createSequence } from '@/lib/crm/queries/sequences';
import { sequenceCreateSchema } from '@/lib/crm/validations';

export async function GET() {
  try {
    const sequences = await getSequences();
    return NextResponse.json(sequences);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch sequences' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = sequenceCreateSchema.parse(body);
    const sequence = await createSequence(parsed);
    return NextResponse.json(sequence, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to create sequence' },
      { status: 500 }
    );
  }
}
