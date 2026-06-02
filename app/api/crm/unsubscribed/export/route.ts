import { NextResponse } from 'next/server';
import { getUnsubscribedContacts } from '@/lib/crm/queries/contacts';
import { generateCSV } from '@/lib/crm/csv';

const COLUMNS = ['email', 'name', 'company_name', 'role', 'status', 'updated_at'];

export async function GET() {
  try {
    // No pagination — export the full unsubscribed list
    const { contacts } = await getUnsubscribedContacts({ limit: Number.MAX_SAFE_INTEGER });

    const rows = contacts.map((c) => ({
      email: c.email,
      name: c.name,
      company_name: c.company_name ?? '',
      role: c.role ?? '',
      status: c.status,
      updated_at: c.updated_at,
    }));

    const csv = generateCSV(rows, COLUMNS);

    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="unsubscribed-export.csv"',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to export' },
      { status: 500 }
    );
  }
}
