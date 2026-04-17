import { Resend } from 'resend';
import type { EmailTask } from '@/lib/crm/queries/tasks';
import { resolveTemplate, buildVars } from '@/lib/crm/template';

export { resolveTemplate, buildVars };

let _resend: Resend | null = null;
function getResend(): Resend {
  if (!_resend) {
    if (!process.env.RESEND_API_KEY) throw new Error('RESEND_API_KEY env var not set');
    _resend = new Resend(process.env.RESEND_API_KEY);
  }
  return _resend;
}

export async function validateEmailDomain(email: string): Promise<boolean> {
  const domain = email.split('@')[1];
  if (!domain) return false;
  try {
    const dns = await import('dns');
    const records = await dns.promises.resolveMx(domain);
    return records.length > 0;
  } catch {
    return false;
  }
}

export async function sendCrmEmail(task: EmailTask & { custom_fields?: Record<string, string> | null }, fromEmail?: string): Promise<string> {
  if (!task.contact_email) throw new Error('Contact has no email address');

  const vars = buildVars(task);
  if (task.custom_fields) Object.assign(vars, task.custom_fields);

  if (process.env.UNSUBSCRIBE_SECRET && task.contact_id) {
    const { buildUnsubscribeUrl } = await import('@/lib/crm/unsubscribe');
    vars['unsubscribe_url'] = buildUnsubscribeUrl(task.contact_id);
  }

  const subject = task.subject_template ? resolveTemplate(task.subject_template, vars) : '(no subject)';
  const body = task.body_template ? resolveTemplate(task.body_template, vars) : '';

  const from = fromEmail ?? process.env.RESEND_FROM_EMAIL;
  if (!from) throw new Error('RESEND_FROM_EMAIL env var not set');

  const resend = getResend();
  const sendOpts: Parameters<typeof resend.emails.send>[0] = {
    from,
    to: task.contact_email,
    replyTo: 'michal@findsherpas.com',
    subject,
    text: body,
  };
  if (vars['unsubscribe_url']) {
    sendOpts.headers = { 'List-Unsubscribe': `<${vars['unsubscribe_url']}>` };
  }
  const { data, error } = await resend.emails.send(sendOpts);

  if (error || !data) throw new Error(error?.message ?? 'Failed to send email');

  return data.id;
}
