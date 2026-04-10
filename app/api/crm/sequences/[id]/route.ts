import { NextRequest, NextResponse } from 'next/server';
import { getSequenceById, updateSequence, deleteSequence } from '@/lib/crm/queries/sequences';
import { sequenceUpdateSchema } from '@/lib/crm/validations';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sequence = await getSequenceById(id);
    if (!sequence) {
      return NextResponse.json({ error: 'Sequence not found' }, { status: 404 });
    }
    return NextResponse.json(sequence);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch sequence' },
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

    const existing = await getSequenceById(sequenceId);
    if (!existing) {
      return NextResponse.json({ error: 'Sequence not found' }, { status: 404 });
    }

    const body = await request.json();
    const parsed = sequenceUpdateSchema.parse(body);
    const sequence = await updateSequence(sequenceId, parsed);
    return NextResponse.json(sequence);
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to update sequence' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const sequenceId = id;

    const existing = await getSequenceById(sequenceId);
    if (!existing) {
      return NextResponse.json({ error: 'Sequence not found' }, { status: 404 });
    }

    deleteSequence(sequenceId);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete sequence' },
      { status: 500 }
    );
  }
}
