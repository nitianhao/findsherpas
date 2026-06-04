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
    brand: task.company_name,
    email: task.contact_email,
  };
}

/**
 * Lead stat sentence for sequence openers. Leads with the zero-result rate when
 * it's material (>= 10%) — the most visceral, report-aligned signal — otherwise
 * falls back to the outside-top-3 rate. Avoids opening with "0% returned zero
 * results" for sites whose failures are ranking/irrelevance rather than retrieval.
 */
export function buildHeadlineStat(
  zeroResultRate?: string | null,
  outsideTop3Rate?: string | null
): string {
  const zr = parseFloat(zeroResultRate ?? '');
  const o3 = parseFloat(outsideTop3Rate ?? '');
  if (!Number.isNaN(zr) && zr >= 10) {
    return `${Math.round(zr)}% of searches returned zero results — a blank page — for products you stock.`;
  }
  if (!Number.isNaN(o3)) {
    return `${Math.round(o3)}% of searches surfaced the best match outside the top 3 — relevant products pushed out of view.`;
  }
  return 'Relevant products you stock are not surfacing on the first page of search.';
}

export function buildSearchPlatformSentence(searchSolution?: string | null): string {
  const sol = (searchSolution ?? '').trim();
  if (sol) {
    return `This is a configuration and tuning gap on ${sol} — fixable without replatforming.`;
  }
  return 'This is a configuration gap on your current search stack — fixable without replatforming.';
}
