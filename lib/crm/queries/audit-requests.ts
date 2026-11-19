import { adminDb, id } from '@/lib/crm/instant-db';

export type AuditRequestStatus = 
  | 'new'
  | 'scanning'
  | 'ready_for_review'
  | 'approved'
  | 'sent'
  | 'rejected';

export interface AuditRequest {
  id: string;
  store_url: string;
  email: string;
  name: string;
  problem_queries: string | null;
  status: AuditRequestStatus;
  rate_limit_key: string;
  created_at: string;
  updated_at: string | null;
  scanned_at: string | null;
  approved_at: string | null;
  sent_at: string | null;
  rejected_at: string | null;
  report_slug: string | null;
  notes: string | null;
  company_id?: string;
  company_name?: string;
  contact_id?: string;
  teardown_scan?: TeardownScan | null;
}

export interface TeardownScan {
  id: string;
  domain: string;
  site_name: string | null;
  vertical: string | null;
  country: string | null;
  overall_score: string;
  capabilities: string;
  probes: string;
  blocked: boolean;
  llm_cost_usd: number | null;
  execution_time_ms: number | null;
  scanned_at: string;
  created_at: string;
}

function now() {
  return new Date().toISOString();
}

function mapAuditRequest(r: Record<string, unknown>): AuditRequest {
  return {
    id: r.id as string,
    store_url: (r.store_url as string) ?? '',
    email: (r.email as string) ?? '',
    name: (r.name as string) ?? '',
    problem_queries: (r.problem_queries as string | null) ?? null,
    status: (r.status as AuditRequestStatus) ?? 'new',
    rate_limit_key: (r.rate_limit_key as string) ?? '',
    created_at: (r.created_at as string) ?? now(),
    updated_at: (r.updated_at as string | null) ?? null,
    scanned_at: (r.scanned_at as string | null) ?? null,
    approved_at: (r.approved_at as string | null) ?? null,
    sent_at: (r.sent_at as string | null) ?? null,
    rejected_at: (r.rejected_at as string | null) ?? null,
    report_slug: (r.report_slug as string | null) ?? null,
    notes: (r.notes as string | null) ?? null,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    company_id: (r as any).company?.id ?? undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    company_name: (r as any).company?.name ?? undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    contact_id: (r as any).contact?.id ?? undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    teardown_scan: (r as any).teardownScan ? mapTeardownScan((r as any).teardownScan) : null,
  };
}

function mapTeardownScan(s: Record<string, unknown>): TeardownScan {
  return {
    id: s.id as string,
    domain: (s.domain as string) ?? '',
    site_name: (s.site_name as string | null) ?? null,
    vertical: (s.vertical as string | null) ?? null,
    country: (s.country as string | null) ?? null,
    overall_score: (s.overall_score as string) ?? 'error',
    capabilities: (s.capabilities as string) ?? '{}',
    probes: (s.probes as string) ?? '[]',
    blocked: Boolean(s.blocked),
    llm_cost_usd: (s.llm_cost_usd as number | null) ?? null,
    execution_time_ms: (s.execution_time_ms as number | null) ?? null,
    scanned_at: (s.scanned_at as string) ?? now(),
    created_at: (s.created_at as string) ?? now(),
  };
}

interface AuditRequestFilters {
  status?: AuditRequestStatus;
  search?: string;
  limit?: number;
  offset?: number;
}

export async function getAuditRequests(
  filters: AuditRequestFilters = {}
): Promise<{ requests: AuditRequest[]; total: number }> {
  const { status, search, limit = 50, offset = 0 } = filters;

  const data = await adminDb.query({
    auditRequests: {
      company: {},
      contact: {},
      teardownScan: {},
    },
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let results = (data.auditRequests as any[]).map(mapAuditRequest);

  if (status) {
    results = results.filter((r) => r.status === status);
  }

  if (search) {
    const q = search.toLowerCase();
    results = results.filter(
      (r) =>
        r.store_url.toLowerCase().includes(q) ||
        r.email.toLowerCase().includes(q) ||
        r.name.toLowerCase().includes(q)
    );
  }

  // Sort by created_at descending (newest first)
  results.sort((a, b) => b.created_at.localeCompare(a.created_at));

  return {
    requests: results.slice(offset, offset + limit),
    total: results.length,
  };
}

export async function getAuditRequestById(requestId: string): Promise<AuditRequest | null> {
  const data = await adminDb.query({
    auditRequests: {
      $: { where: { id: requestId } },
      company: {},
      contact: {},
      teardownScan: {},
    },
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const r = (data.auditRequests as any[])[0];
  return r ? mapAuditRequest(r) : null;
}

export async function getNewAuditRequests(): Promise<AuditRequest[]> {
  const { requests } = await getAuditRequests({ status: 'new' });
  return requests;
}

export async function updateAuditRequestStatus(
  requestId: string,
  status: AuditRequestStatus,
  extraFields?: Record<string, unknown>
): Promise<void> {
  const attrs: Record<string, unknown> = {
    status,
    updated_at: now(),
  };

  if (status === 'scanning') {
    // No extra fields needed
  } else if (status === 'ready_for_review') {
    attrs.scanned_at = now();
  } else if (status === 'approved') {
    attrs.approved_at = now();
  } else if (status === 'sent') {
    attrs.sent_at = now();
  } else if (status === 'rejected') {
    attrs.rejected_at = now();
  }

  if (extraFields) {
    Object.assign(attrs, extraFields);
  }

  await adminDb.transact([adminDb.tx.auditRequests[requestId].update(attrs)]);
}

export async function setAuditRequestReportSlug(
  requestId: string,
  reportSlug: string
): Promise<void> {
  await adminDb.transact([
    adminDb.tx.auditRequests[requestId].update({
      report_slug: reportSlug,
      updated_at: now(),
    }),
  ]);
}

export async function addAuditRequestNote(
  requestId: string,
  note: string
): Promise<void> {
  const request = await getAuditRequestById(requestId);
  const existingNotes = request?.notes || '';
  const timestamp = new Date().toISOString().split('T')[0];
  const newNotes = existingNotes
    ? `${existingNotes}\n\n[${timestamp}] ${note}`
    : `[${timestamp}] ${note}`;

  await adminDb.transact([
    adminDb.tx.auditRequests[requestId].update({
      notes: newNotes,
      updated_at: now(),
    }),
  ]);
}

export async function getAuditRequestStats(): Promise<{
  total: number;
  byStatus: Record<AuditRequestStatus, number>;
}> {
  const data = await adminDb.query({
    auditRequests: { $: { fields: ['id', 'status'] } },
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const requests = data.auditRequests as any[];
  
  const byStatus: Record<AuditRequestStatus, number> = {
    new: 0,
    scanning: 0,
    ready_for_review: 0,
    approved: 0,
    sent: 0,
    rejected: 0,
  };

  for (const r of requests) {
    const status = r.status as AuditRequestStatus;
    if (status in byStatus) {
      byStatus[status]++;
    }
  }

  return {
    total: requests.length,
    byStatus,
  };
}
