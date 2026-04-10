import { adminDb, id } from '@/lib/crm/instant-db';
import type { Reminder } from '@/lib/crm/types';
import { format } from 'date-fns';

function now() {
  return new Date().toISOString();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapReminder(r: any): Reminder {
  return {
    id: r.id as string,
    company_id: r.company?.id ?? null,
    contact_id: r.contact?.id ?? null,
    title: r.title ?? '',
    description: r.description ?? null,
    due_date: r.due_date ?? '',
    is_completed: r.is_completed ?? 0,
    created_at: r.created_at ?? now(),
    company_name: r.company?.name ?? undefined,
    contact_name: r.contact?.name ?? undefined,
  };
}

export async function getReminders(filters: { completed?: boolean; due_date?: string } = {}): Promise<Reminder[]> {
  const data = await adminDb.query({
    reminders: { company: {}, contact: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let results = (data.reminders as any[]).map(mapReminder);

  if (filters.completed !== undefined) {
    results = results.filter(r => r.is_completed === (filters.completed ? 1 : 0));
  }
  if (filters.due_date) {
    results = results.filter(r => r.due_date <= filters.due_date!);
  }

  results.sort((a, b) => a.due_date.localeCompare(b.due_date) || a.created_at.localeCompare(b.created_at));
  return results;
}

export async function getTodaysReminders(): Promise<Reminder[]> {
  const today = format(new Date(), 'yyyy-MM-dd');
  return getReminders({ completed: false, due_date: today });
}

export async function createReminder(data: {
  company_id?: string | null;
  contact_id?: string | null;
  title: string;
  description?: string | null;
  due_date: string;
}): Promise<Reminder> {
  const reminderId = id();
  const txns = [
    adminDb.tx.reminders[reminderId].update({
      title: data.title,
      description: data.description ?? null,
      due_date: data.due_date,
      is_completed: 0,
      created_at: now(),
    }),
  ];
  if (data.company_id) txns.push(adminDb.tx.reminders[reminderId].link({ company: data.company_id }));
  if (data.contact_id) txns.push(adminDb.tx.reminders[reminderId].link({ contact: data.contact_id }));

  await adminDb.transact(txns);

  const result = await adminDb.query({
    reminders: { $: { where: { id: reminderId } }, company: {}, contact: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return mapReminder((result.reminders as any[])[0]);
}

export async function updateReminder(reminderId: string, data: Record<string, unknown>): Promise<Reminder> {
  const allowed = ['title', 'description', 'due_date', 'is_completed'];
  const attrs: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data)) {
    if (allowed.includes(k) && v !== undefined) attrs[k] = v;
  }

  const txns = [adminDb.tx.reminders[reminderId].update(attrs)];

  if (data.company_id !== undefined) {
    const current = await adminDb.query({ reminders: { $: { where: { id: reminderId } }, company: {} } });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cur = (current.reminders as any[])[0];
    if (cur?.company?.id) txns.push(adminDb.tx.reminders[reminderId].unlink({ company: cur.company.id }));
    if (data.company_id) txns.push(adminDb.tx.reminders[reminderId].link({ company: data.company_id as string }));
  }

  await adminDb.transact(txns);
  const result = await adminDb.query({ reminders: { $: { where: { id: reminderId } }, company: {}, contact: {} } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return mapReminder((result.reminders as any[])[0]);
}

export async function deleteReminder(reminderId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.reminders[reminderId].delete());
}

export async function completeReminder(reminderId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.reminders[reminderId].update({ is_completed: 1 }));
}
