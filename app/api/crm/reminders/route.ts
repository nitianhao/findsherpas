import { NextRequest, NextResponse } from 'next/server';
import { getReminders, createReminder } from '@/lib/crm/queries/reminders';
import { reminderCreateSchema } from '@/lib/crm/validations';

export async function GET() {
  try {
    const reminders = await getReminders({ completed: false });
    return NextResponse.json(reminders);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch reminders' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = reminderCreateSchema.parse(body);
    const reminder = await createReminder(parsed);
    return NextResponse.json(reminder, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as unknown as { errors: unknown }).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to create reminder' },
      { status: 500 }
    );
  }
}
