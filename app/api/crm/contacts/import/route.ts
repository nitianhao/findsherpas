import { NextRequest, NextResponse } from 'next/server';
import { adminDb, id } from '@/lib/crm/instant-db';
import type { ContactStatus } from '@/lib/crm/types';

const VALID_STATUSES: ContactStatus[] = ['active', 'bounced', 'unsubscribed', 'replied'];

const CONTACT_FIELDS = ['name', 'email', 'role', 'phone', 'linkedin_url', 'notes', 'status', 'company_name'];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { rows, mapping } = body as {
      rows: Record<string, string>[];
      mapping: Record<string, string>;
    };

    if (!rows || !Array.isArray(rows) || !mapping || typeof mapping !== 'object') {
      return NextResponse.json({ error: 'Invalid request body. Expected { rows, mapping }.' }, { status: 400 });
    }

    // Pre-load all companies for name lookup
    const companiesData = await adminDb.query({ companies: {} });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const companiesByName = new Map<string, string>((companiesData.companies as any[]).map((c) => [
      (c.name as string).toLowerCase().trim(),
      c.id as string,
    ]));

    let imported = 0;
    let skipped = 0;
    const errors: string[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const txns: any[] = [];

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const mapped: Record<string, string | null> = {};

      for (const field of CONTACT_FIELDS) {
        mapped[field] = null;
      }
      mapped['status'] = 'active';

      for (const [csvHeader, contactField] of Object.entries(mapping)) {
        if (CONTACT_FIELDS.includes(contactField) && row[csvHeader] !== undefined) {
          mapped[contactField] = row[csvHeader]?.trim() || null;
        }
      }

      if (!mapped['name']) {
        errors.push(`Row ${i + 1}: Missing required field "name". Skipped.`);
        skipped++;
        continue;
      }
      if (!mapped['email']) {
        errors.push(`Row ${i + 1} ("${mapped['name']}"): Missing required field "email". Skipped.`);
        skipped++;
        continue;
      }

      if (mapped['status'] && !VALID_STATUSES.includes(mapped['status'] as ContactStatus)) {
        mapped['status'] = 'active';
      }

      const companyName = mapped['company_name']?.toLowerCase().trim() ?? '';
      const companyId = companyName ? companiesByName.get(companyName) : undefined;
      if (mapped['company_name'] && !companyId) {
        errors.push(`Row ${i + 1} ("${mapped['name']}"): Company "${mapped['company_name']}" not found — contact imported without company link.`);
      }

      const contactId = id();
      const ts = new Date().toISOString();
      txns.push(
        adminDb.tx.contacts[contactId].update({
          name: mapped['name']!,
          email: mapped['email']!,
          role: mapped['role'] ?? null,
          phone: mapped['phone'] ?? null,
          linkedin_url: mapped['linkedin_url'] ?? null,
          notes: mapped['notes'] ?? null,
          status: mapped['status'] ?? 'active',
          created_at: ts,
          updated_at: ts,
        })
      );
      if (companyId) {
        txns.push(adminDb.tx.contacts[contactId].link({ company: companyId }));
      }
      imported++;
    }

    if (txns.length > 0) {
      // InstantDB transact has a limit per call — batch in chunks of 100 ops
      for (let i = 0; i < txns.length; i += 100) {
        await adminDb.transact(txns.slice(i, i + 100));
      }
    }

    return NextResponse.json({ imported, skipped, errors });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to import contacts' },
      { status: 500 }
    );
  }
}
