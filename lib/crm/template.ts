import type { EmailTask } from '@/lib/crm/queries/tasks';

export function resolveTemplate(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => vars[key] ?? `{{${key}}}`);
}

export function buildVars(task: Pick<EmailTask, 'contact_name' | 'contact_email' | 'company_name'>): Record<string, string> {
  const nameParts = task.contact_name.trim().split(/\s+/);
  return {
    first_name: nameParts[0] ?? '',
    last_name: nameParts.length > 1 ? nameParts[nameParts.length - 1] : '',
    full_name: task.contact_name,
    company_name: task.company_name,
    email: task.contact_email,
  };
}
