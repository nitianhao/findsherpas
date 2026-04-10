import { adminDb, id } from '@/lib/crm/instant-db';
import type { Contact, ContactStatus } from '@/lib/crm/types';

function now() {
  return new Date().toISOString();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapContact(c: any): Contact {
  return {
    id: c.id as string,
    company_id: c.company?.id ?? '',
    name: c.name ?? '',
    email: c.email ?? '',
    role: c.role ?? null,
    phone: c.phone ?? null,
    linkedin_url: c.linkedin_url ?? null,
    status: (c.status as ContactStatus) ?? 'active',
    notes: c.notes ?? null,
    created_at: c.created_at ?? now(),
    updated_at: c.updated_at ?? now(),
    company_name: c.company?.name ?? undefined,
  };
}

interface ContactFilters {
  search?: string;
  status?: ContactStatus;
  company_id?: string;
  role?: string;
  limit?: number;
  offset?: number;
}

export async function getContacts(filters: ContactFilters = {}): Promise<{ contacts: Contact[]; total: number }> {
  const { search, status, company_id, role, limit = 50, offset = 0 } = filters;

  const data = await adminDb.query({ contacts: { company: {} } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let results = (data.contacts as any[]).map(mapContact);

  if (search) {
    const q = search.toLowerCase();
    results = results.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.email && c.email.toLowerCase().includes(q))
    );
  }
  if (status) results = results.filter(c => c.status === status);
  if (company_id) results = results.filter(c => c.company_id === company_id);
  if (role) results = results.filter(c => c.role === role);

  results.sort((a, b) => b.created_at.localeCompare(a.created_at));

  return { contacts: results.slice(offset, offset + limit), total: results.length };
}

export async function getContactsByCompanyId(companyId: string): Promise<Contact[]> {
  const data = await adminDb.query({
    contacts: { $: { where: { 'company.id': companyId } }, company: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.contacts as any[]).map(mapContact).sort((a: Contact, b: Contact) => a.name.localeCompare(b.name));
}

export async function getContactById(contactId: string): Promise<Contact | null> {
  const data = await adminDb.query({
    contacts: { $: { where: { id: contactId } }, company: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const c = (data.contacts as any[])[0];
  return c ? mapContact(c) : null;
}

export async function createContact(data: {
  company_id: string;
  name: string;
  email: string;
  role?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  status?: string;
  notes?: string | null;
}): Promise<Contact> {
  const contactId = id();
  const ts = now();
  await adminDb.transact([
    adminDb.tx.contacts[contactId].update({
      name: data.name,
      email: data.email,
      role: data.role ?? null,
      phone: data.phone ?? null,
      linkedin_url: data.linkedin_url ?? null,
      status: data.status ?? 'active',
      notes: data.notes ?? null,
      created_at: ts,
      updated_at: ts,
    }),
    adminDb.tx.contacts[contactId].link({ company: data.company_id }),
  ]);
  return getContactById(contactId) as Promise<Contact>;
}

export async function updateContact(contactId: string, data: Record<string, unknown>): Promise<Contact> {
  const allowedFields = ['name', 'email', 'role', 'phone', 'linkedin_url', 'status', 'notes'];
  const attrs: Record<string, unknown> = { updated_at: now() };
  const txns = [];

  for (const [k, v] of Object.entries(data)) {
    if (allowedFields.includes(k) && v !== undefined) attrs[k] = v;
  }
  txns.push(adminDb.tx.contacts[contactId].update(attrs));

  if (data.company_id && typeof data.company_id === 'string') {
    const current = await getContactById(contactId);
    if (current?.company_id) {
      txns.push(adminDb.tx.contacts[contactId].unlink({ company: current.company_id }));
    }
    txns.push(adminDb.tx.contacts[contactId].link({ company: data.company_id }));
  }

  await adminDb.transact(txns);
  return getContactById(contactId) as Promise<Contact>;
}

export async function deleteContact(contactId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.contacts[contactId].delete());
}

export async function getContactCount(): Promise<number> {
  const data = await adminDb.query({ contacts: { $: { fields: ['id'] } } });
  return (data.contacts as unknown[]).length;
}
