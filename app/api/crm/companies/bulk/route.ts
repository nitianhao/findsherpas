import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { bulkUpdateStatus } from '@/lib/crm/queries/companies';
import type { CompanyStatus } from '@/lib/crm/types';

const bulkUpdateSchema = z.object({
  ids: z.array(z.string().min(1)).min(1),
  status: z.enum([
    'prospect', 'contacted', 'in-sequence', 'replied',
    'meeting-booked', 'won', 'lost', 'not-interested',
  ]),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = bulkUpdateSchema.parse(body);
    bulkUpdateStatus(parsed.ids, parsed.status as CompanyStatus);
    return NextResponse.json({ success: true });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to bulk update status' },
      { status: 500 }
    );
  }
}
