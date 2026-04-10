import { NextRequest, NextResponse } from 'next/server';
import { enrollContacts } from '@/lib/crm/queries/enrollments';
import { enrollContactSchema } from '@/lib/crm/validations';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = enrollContactSchema.parse(body);
    const enrollments = await enrollContacts(parsed.contact_ids, parsed.sequence_id);
    return NextResponse.json(enrollments, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to enroll contacts' },
      { status: 500 }
    );
  }
}
