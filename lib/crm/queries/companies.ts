import { adminDb, id } from '@/lib/crm/instant-db';
import type { Company, CompanyStatus, Tag } from '@/lib/crm/types';

interface CompanyFilters {
  search?: string;
  status?: CompanyStatus;
  platform?: string;
  search_solution?: string;
  tag_id?: string;
  limit?: number;
  offset?: number;
}

function now() {
  return new Date().toISOString();
}

function mapCompany(c: Record<string, unknown> & { tags?: Array<Record<string, unknown>>; contacts?: Array<unknown> }): Company {
  return {
    id: c.id as string,
    name: (c.name as string) ?? '',
    website: (c.website as string | null) ?? null,
    industry: (c.industry as string | null) ?? null,
    size_estimate: (c.size_estimate as string | null) ?? null,
    revenue_estimate: (c.revenue_estimate as string | null) ?? null,
    platform: (c.platform as string | null) ?? null,
    search_solution: (c.search_solution as string | null) ?? null,
    social_linkedin: (c.social_linkedin as string | null) ?? null,
    social_twitter: (c.social_twitter as string | null) ?? null,
    social_facebook: (c.social_facebook as string | null) ?? null,
    social_other: (c.social_other as string | null) ?? null,
    tech_stack_notes: (c.tech_stack_notes as string | null) ?? null,
    notes: (c.notes as string | null) ?? null,
    status: (c.status as CompanyStatus) ?? 'prospect',
    report_url: (c.report_url as string | null) ?? null,
    country: (c.country as string | null) ?? null,
    language: (c.language as string | null) ?? null,
    pdf_url: (c.pdf_url as string | null) ?? null,
    pdf_name: (c.pdf_name as string | null) ?? null,
    created_at: (c.created_at as string) ?? now(),
    updated_at: (c.updated_at as string) ?? now(),
    contacts_count: (c.contacts ?? []).length,
    tags: (c.tags ?? []).map(mapTag),
  };
}

function mapTag(t: Record<string, unknown>): Tag {
  return {
    id: t.id as string,
    name: (t.name as string) ?? '',
    color: (t.color as string | null) ?? null,
    created_at: (t.created_at as string) ?? now(),
  };
}

export async function getCompanies(filters: CompanyFilters = {}): Promise<{ companies: Company[]; total: number }> {
  const { search, status, platform, search_solution, tag_id, limit = 50, offset = 0 } = filters;

  const data = await adminDb.query({ companies: { tags: {}, contacts: {} } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let results = (data.companies as any[]).map(mapCompany);

  if (search) {
    const q = search.toLowerCase();
    results = results.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.website && c.website.toLowerCase().includes(q))
    );
  }
  if (status) results = results.filter(c => c.status === status);
  if (platform) results = results.filter(c => c.platform === platform);
  if (search_solution) results = results.filter(c => c.search_solution === search_solution);
  if (tag_id) results = results.filter(c => c.tags?.some((t: Tag) => t.id === tag_id));

  results.sort((a, b) => b.updated_at.localeCompare(a.updated_at));

  return { companies: results.slice(offset, offset + limit), total: results.length };
}

export async function getCompanyById(companyId: string): Promise<(Company & { tags: Tag[] }) | null> {
  const data = await adminDb.query({
    companies: { $: { where: { id: companyId } }, tags: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const c = (data.companies as any[])[0];
  if (!c) return null;
  return mapCompany(c) as Company & { tags: Tag[] };
}

interface CompanyCreateData {
  name: string;
  website?: string | null;
  industry?: string | null;
  size_estimate?: string | null;
  revenue_estimate?: string | null;
  platform?: string | null;
  social_linkedin?: string | null;
  social_twitter?: string | null;
  social_facebook?: string | null;
  social_other?: string | null;
  tech_stack_notes?: string | null;
  search_solution?: string | null;
  notes?: string | null;
  status?: CompanyStatus;
  tag_ids?: string[];
  report_url?: string | null;
  country?: string | null;
  language?: string | null;
}

export async function createCompany(data: CompanyCreateData): Promise<Company> {
  const { tag_ids, ...fields } = data;
  const companyId = id();
  const ts = now();

  const txns = [
    adminDb.tx.companies[companyId].update({
      name: fields.name,
      website: fields.website ?? null,
      industry: fields.industry ?? null,
      size_estimate: fields.size_estimate ?? null,
      revenue_estimate: fields.revenue_estimate ?? null,
      platform: fields.platform ?? null,
      search_solution: fields.search_solution ?? null,
      social_linkedin: fields.social_linkedin ?? null,
      social_twitter: fields.social_twitter ?? null,
      social_facebook: fields.social_facebook ?? null,
      social_other: fields.social_other ?? null,
      tech_stack_notes: fields.tech_stack_notes ?? null,
      notes: fields.notes ?? null,
      status: fields.status ?? 'prospect',
      report_url: fields.report_url ?? null,
      country: fields.country ?? null,
      language: fields.language ?? null,
      created_at: ts,
      updated_at: ts,
    }),
  ];

  if (tag_ids && tag_ids.length > 0) {
    txns.push(adminDb.tx.companies[companyId].link({ tags: tag_ids }));
  }

  await adminDb.transact(txns);
  return getCompanyById(companyId) as Promise<Company>;
}

interface CompanyUpdateData {
  name?: string;
  website?: string | null;
  industry?: string | null;
  size_estimate?: string | null;
  revenue_estimate?: string | null;
  platform?: string | null;
  social_linkedin?: string | null;
  social_twitter?: string | null;
  social_facebook?: string | null;
  social_other?: string | null;
  tech_stack_notes?: string | null;
  search_solution?: string | null;
  notes?: string | null;
  status?: CompanyStatus;
  tag_ids?: string[];
  report_url?: string | null;
  country?: string | null;
  language?: string | null;
}

export async function updateCompany(companyId: string, data: CompanyUpdateData): Promise<Company> {
  const { tag_ids, ...fields } = data;

  const attrs: Record<string, unknown> = { updated_at: now() };
  for (const [k, v] of Object.entries(fields)) {
    if (v !== undefined) attrs[k] = v;
  }

  const txns = [adminDb.tx.companies[companyId].update(attrs)];

  if (tag_ids !== undefined) {
    const current = await getCompanyById(companyId);
    const currentTagIds = (current?.tags ?? []).map((t: Tag) => t.id);
    if (currentTagIds.length > 0) {
      txns.push(adminDb.tx.companies[companyId].unlink({ tags: currentTagIds }));
    }
    if (tag_ids.length > 0) {
      txns.push(adminDb.tx.companies[companyId].link({ tags: tag_ids }));
    }
  }

  await adminDb.transact(txns);
  return getCompanyById(companyId) as Promise<Company>;
}

export async function deleteCompany(companyId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.companies[companyId].delete());
}

export async function bulkUpdateStatus(ids: string[], status: CompanyStatus): Promise<void> {
  const ts = now();
  await adminDb.transact(ids.map(cid => adminDb.tx.companies[cid].update({ status, updated_at: ts })));
}

export async function getCompanyCount(): Promise<number> {
  const data = await adminDb.query({ companies: { $: { fields: ['id'] } } });
  return (data.companies as unknown[]).length;
}
