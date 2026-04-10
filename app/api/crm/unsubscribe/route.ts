import { NextRequest, NextResponse } from 'next/server';
import { verifyContactToken } from '@/lib/crm/unsubscribe';
import { adminDb } from '@/lib/crm/instant-db';

export async function GET(req: NextRequest) {
  const contactId = req.nextUrl.searchParams.get('contact_id');
  const token = req.nextUrl.searchParams.get('token');

  if (!contactId || !token) {
    return NextResponse.json({ error: 'Invalid unsubscribe link' }, { status: 400 });
  }

  if (!verifyContactToken(contactId, token)) {
    return NextResponse.json({ error: 'Invalid or expired unsubscribe link' }, { status: 401 });
  }

  const ts = new Date().toISOString();

  // Mark contact as unsubscribed
  await adminDb.transact(
    adminDb.tx.contacts[contactId].update({ status: 'unsubscribed', updated_at: ts })
  );

  // Pause all active enrollments for this contact
  const enrollmentData = await adminDb.query({
    enrollments: { $: { where: { 'contact.id': contactId, status: 'active' } } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const activeEnrollments = enrollmentData.enrollments as any[];
  if (activeEnrollments.length > 0) {
    await adminDb.transact(
      activeEnrollments.map((e) =>
        adminDb.tx.enrollments[e.id as string].update({ status: 'paused', paused_at: ts })
      )
    );
  }

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL ?? '';
  return NextResponse.redirect(`${baseUrl}/crm/unsubscribe/confirmed`);
}
