import { adminDb } from '@/lib/crm/instant-db';
import { buildSearchPlatformSentence } from '@/lib/crm/template';
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
  audit_vars: Record<string, string> | null;
  report_url: string | null;
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
    .map(ev => {
      const co = ev.enrollment?.contact?.company ?? {};
      const auditKeys = [
        'score',
        'query_count',
        'cap_count',
        'top3rate',
        'outside3rate',
        'worst_query',
        'worst_pos',
        'wrong_product',
      ] as const;
      const audit_vars: Record<string, string> = {};
      for (const k of auditKeys) {
        const v = co[`audit_${k}`];
        if (typeof v === 'string' && v.length > 0) {
          audit_vars[k] = v;
          // Provide underscore aliases used by some sequence templates
          if (k === 'top3rate') audit_vars['top_3_rate'] = v;
          if (k === 'outside3rate') audit_vars['outside_3_rate'] = v;
        }
      }
      audit_vars['search_platform_sentence'] = buildSearchPlatformSentence(
        (co.search_solution as string | null) ?? null
      );
      return {
        event_id: ev.id as string,
        contact_name: ev.enrollment?.contact?.name ?? '',
        contact_email: ev.enrollment?.contact?.email ?? '',
        contact_id: ev.enrollment?.contact?.id ?? '',
        company_name: co.name ?? '',
        company_id: co.id ?? '',
        sequence_name: ev.enrollment?.sequence?.name ?? '',
        step_order: ev.step?.step_order ?? 0,
        subject_template: ev.step?.subject_template ?? null,
        body_template: ev.step?.body_template ?? null,
        scheduled_date: ev.scheduled_date as string,
        send_hour: (ev.enrollment?.send_hour as number | undefined) ?? null,
        is_overdue: (ev.scheduled_date as string) < today,
        audit_vars: Object.keys(audit_vars).length > 0 ? audit_vars : null,
        report_url: (co.report_url as string | null) ?? null,
      };
    })
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
