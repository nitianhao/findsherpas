import { adminDb } from '@/lib/crm/instant-db';
import { format } from 'date-fns';

export interface EmailTask {
  event_id: string;
  contact_name: string;
  contact_email: string;
  contact_id: string;
  company_name: string;
  company_id: string;
  sequence_name: string;
  step_order: number;
  subject_template: string | null;
  body_template: string | null;
  scheduled_date: string;
  send_hour: number | null;
  is_overdue: boolean;
}

export async function getTodaysEmailTasks(): Promise<EmailTask[]> {
  const today = format(new Date(), 'yyyy-MM-dd');

  const data = await adminDb.query({
    events: {
      $: { where: { status: 'pending' } },
      enrollment: {
        contact: { company: {} },
        sequence: {},
      },
      step: {},
    },
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tasks = (data.events as any[])
    .filter(ev => {
      const scheduledDate = ev.scheduled_date as string;
      return scheduledDate <= today && ev.enrollment?.status === 'active';
    })
    .map(ev => ({
      event_id: ev.id as string,
      contact_name: ev.enrollment?.contact?.name ?? '',
      contact_email: ev.enrollment?.contact?.email ?? '',
      contact_id: ev.enrollment?.contact?.id ?? '',
      company_name: ev.enrollment?.contact?.company?.name ?? '',
      company_id: ev.enrollment?.contact?.company?.id ?? '',
      sequence_name: ev.enrollment?.sequence?.name ?? '',
      step_order: ev.step?.step_order ?? 0,
      subject_template: ev.step?.subject_template ?? null,
      body_template: ev.step?.body_template ?? null,
      scheduled_date: ev.scheduled_date as string,
      send_hour: (ev.enrollment?.send_hour as number | undefined) ?? null,
      is_overdue: (ev.scheduled_date as string) < today,
    }))
    .sort((a, b) =>
      a.scheduled_date.localeCompare(b.scheduled_date) ||
      (a.send_hour ?? 9) - (b.send_hour ?? 9) ||
      a.company_name.localeCompare(b.company_name)
    );

  return tasks;
}

export async function getTodaysTaskCount(): Promise<number> {
  const tasks = await getTodaysEmailTasks();
  return tasks.length;
}
