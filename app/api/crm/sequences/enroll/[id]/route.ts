import { NextRequest, NextResponse } from 'next/server';
import { getEnrollmentById, pauseEnrollment, resumeEnrollment } from '@/lib/crm/queries/enrollments';

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const enrollmentId = id;

    const existing = await getEnrollmentById(enrollmentId);
    if (!existing) {
      return NextResponse.json({ error: 'Enrollment not found' }, { status: 404 });
    }

    const body = await request.json();
    const action = body.action as string;

    if (action === 'pause') {
      pauseEnrollment(enrollmentId);
    } else if (action === 'resume') {
      resumeEnrollment(enrollmentId);
    } else {
      return NextResponse.json({ error: 'Invalid action. Use "pause" or "resume".' }, { status: 400 });
    }

    const updated = await getEnrollmentById(enrollmentId);
    return NextResponse.json(updated);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to update enrollment' },
      { status: 500 }
    );
  }
}
