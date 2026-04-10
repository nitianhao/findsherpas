import { NextRequest, NextResponse } from 'next/server';
import { getDb } from '@/lib/crm/db';
import type { CompanyStatus } from '@/lib/crm/types';

const VALID_STATUSES: CompanyStatus[] = [
  'prospect', 'contacted', 'in-sequence', 'replied',
  'meeting-booked', 'won', 'lost', 'not-interested',
];

const COMPANY_FIELDS = [
  'name', 'website', 'industry', 'size_estimate', 'revenue_estimate',
  'platform', 'social_linkedin', 'social_twitter', 'social_facebook',
  'social_other', 'tech_stack_notes', 'search_solution', 'notes', 'status',
];

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { rows, mapping } = body as {
      rows: Record<string, string>[];
      mapping: Record<string, string>;
    };

    if (!rows || !Array.isArray(rows) || !mapping || typeof mapping !== 'object') {
      return NextResponse.json(
        { error: 'Invalid request body. Expected { rows, mapping }.' },
        { status: 400 }
      );
    }

    const db = getDb();
    let imported = 0;
    let skipped = 0;
    const errors: string[] = [];

    const insertStmt = db.prepare(
      `INSERT INTO companies (name, website, industry, size_estimate, revenue_estimate, platform, social_linkedin, social_twitter, social_facebook, social_other, tech_stack_notes, search_solution, notes, status)
       VALUES (@name, @website, @industry, @size_estimate, @revenue_estimate, @platform, @social_linkedin, @social_twitter, @social_facebook, @social_other, @tech_stack_notes, @search_solution, @notes, @status)`
    );

    const importAll = db.transaction(() => {
      for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const mapped: Record<string, string | null> = {};

        // Initialize all fields to null
        for (const field of COMPANY_FIELDS) {
          mapped[field] = null;
        }
        mapped['status'] = 'prospect';

        // Apply mapping
        for (const [csvHeader, companyField] of Object.entries(mapping)) {
          if (COMPANY_FIELDS.includes(companyField) && row[csvHeader] !== undefined) {
            const value = row[csvHeader]?.trim() || null;
            mapped[companyField] = value;
          }
        }

        // Validate: name is required
        if (!mapped['name']) {
          errors.push(`Row ${i + 1}: Missing required field "name". Skipped.`);
          skipped++;
          continue;
        }

        // Validate status
        if (mapped['status'] && !VALID_STATUSES.includes(mapped['status'] as CompanyStatus)) {
          mapped['status'] = 'prospect';
        }

        try {
          insertStmt.run(mapped);
          imported++;
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Unknown error';
          errors.push(`Row ${i + 1} ("${mapped['name']}"): ${message}`);
          skipped++;
        }
      }
    });

    importAll();

    return NextResponse.json({ imported, skipped, errors });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to import companies' },
      { status: 500 }
    );
  }
}
