import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/crm/db';
import { generateCSV } from '@/lib/crm/csv';

const COMPANY_COLUMNS = [
  'id', 'name', 'website', 'industry', 'size_estimate', 'revenue_estimate',
  'platform', 'social_linkedin', 'social_twitter', 'social_facebook',
  'social_other', 'tech_stack_notes', 'search_solution', 'notes', 'status',
  'created_at', 'updated_at',
];

const CONTACT_COLUMNS = [
  'id', 'company_id', 'name', 'email', 'role', 'phone',
  'linkedin_url', 'status', 'notes', 'created_at', 'updated_at',
];

export async function GET(request: NextRequest) {
  try {
    const type = request.nextUrl.searchParams.get('type') ?? 'companies';
    const db = getDb();

    let csv = '';
    let filename = '';

    if (type === 'companies' || type === 'all') {
      const companies = db.prepare('SELECT * FROM companies ORDER BY id').all() as Record<string, unknown>[];
      csv += generateCSV(companies, COMPANY_COLUMNS);
      filename = 'companies-export.csv';
    }

    if (type === 'contacts' || type === 'all') {
      const contacts = db.prepare(
        `SELECT c.*, comp.name as company_name
         FROM contacts c
         LEFT JOIN companies comp ON c.company_id = comp.id
         ORDER BY c.id`
      ).all() as Record<string, unknown>[];
      const contactCols = [...CONTACT_COLUMNS, 'company_name'];

      if (type === 'all') {
        // Separate with a blank line for combined export
        csv += '\n\n';
        csv += generateCSV(contacts, contactCols);
        filename = 'crm-export.csv';
      } else {
        csv = generateCSV(contacts, contactCols);
        filename = 'contacts-export.csv';
      }
    }

    if (!csv) {
      return NextResponse.json(
        { error: 'Invalid export type. Use "companies", "contacts", or "all".' },
        { status: 400 }
      );
    }

    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to export' },
      { status: 500 }
    );
  }
}
