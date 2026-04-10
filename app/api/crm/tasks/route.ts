import { NextResponse } from 'next/server';
import { getTodaysEmailTasks } from '@/lib/crm/queries/tasks';
import { getTodaysReminders } from '@/lib/crm/queries/reminders';

export async function GET() {
  try {
    const email_tasks = await getTodaysEmailTasks();
    const reminders = getTodaysReminders();
    return NextResponse.json({ email_tasks, reminders });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch tasks' },
      { status: 500 }
    );
  }
}
