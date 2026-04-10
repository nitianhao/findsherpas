import { NextRequest, NextResponse } from 'next/server';
import { getEnrollmentsByContactId, getEventsByEnrollmentId } from '@/lib/crm/queries/enrollments';
import { getContactById } from '@/lib/crm/queries/contacts';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const contactId = id;

    const contact = await getContactById(contactId);
    if (!contact) {
      return NextResponse.json({ error: 'Contact not found' }, { status: 404 });
    }

    const enrollments = await getEnrollmentsByContactId(contactId);

    // Attach events and total step count to each enrollment
    const enriched = await Promise.all(enrollments.map(async (enrollment) => {
      const events = await getEventsByEnrollmentId(enrollment.id);
      return {
        ...enrollment,
        events,
        totalSteps: events.length,
      };
    }));

    return NextResponse.json(enriched);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch enrollments' },
      { status: 500 }
    );
  }
}
