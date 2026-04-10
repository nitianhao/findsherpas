import { NextRequest, NextResponse } from 'next/server';
import { updateReminder, deleteReminder } from '@/lib/crm/queries/reminders';
import { reminderUpdateSchema } from '@/lib/crm/validations';

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const reminderId = id;
    const body = await request.json();
    const parsed = reminderUpdateSchema.parse(body);
    const reminder = await updateReminder(reminderId, parsed);
    return NextResponse.json(reminder);
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as unknown as { errors: unknown }).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to update reminder' },
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
    deleteReminder(id);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete reminder' },
      { status: 500 }
    );
  }
}
