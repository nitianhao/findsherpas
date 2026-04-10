import { adminDb } from '@/lib/crm/instant-db';

function now() {
  return new Date().toISOString();
}

export async function markEventSent(eventId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.events[eventId].update({ status: 'sent', sent_at: now() }));

  // Look up the enrollment to advance current_step and check completion
  const evData = await adminDb.query({
    events: { $: { where: { id: eventId } }, enrollment: { events: {} }, step: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev = (evData.events as any[])[0];
  if (!ev?.enrollment) return;

  const enrollment = ev.enrollment;
  const stepOrder = ev.step?.step_order ?? 0;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const txns: any[] = [adminDb.tx.enrollments[enrollment.id as string].update({ current_step: stepOrder + 1 })];

  // Check if all events are done
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pending = (enrollment.events as any[]).filter(
    (e: { id: string; status: string }) => e.id !== eventId && (e.status === 'pending' || e.status === 'scheduled')
  );
  if (pending.length === 0) {
    txns.push(adminDb.tx.enrollments[enrollment.id as string].update({ status: 'completed', completed_at: now() }));
  }

  await adminDb.transact(txns);
}

export async function markEventReplied(eventId: string): Promise<void> {
  const ts = now();
  await adminDb.transact(adminDb.tx.events[eventId].update({ status: 'replied', replied_at: ts }));

  const evData = await adminDb.query({
    events: { $: { where: { id: eventId } }, enrollment: { events: {}, contact: {} } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev = (evData.events as any[])[0];
  if (!ev?.enrollment) return;

  const enrollment = ev.enrollment;
  const enrollmentId = enrollment.id as string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingEvents = (enrollment.events as any[]).filter(
    (e: { id: string; status: string }) => e.id !== eventId && e.status === 'pending'
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const txns: any[] = [
    adminDb.tx.enrollments[enrollmentId].update({ status: 'replied', completed_at: ts }),
    ...pendingEvents.map((e: { id: string }) => adminDb.tx.events[e.id].update({ status: 'skipped' })),
  ];

  if (enrollment.contact?.id) {
    txns.push(adminDb.tx.contacts[enrollment.contact.id as string].update({ status: 'replied', updated_at: ts }));
  }

  await adminDb.transact(txns);
}

export async function markEventBounced(eventId: string): Promise<void> {
  const ts = now();
  await adminDb.transact(adminDb.tx.events[eventId].update({ status: 'bounced' }));

  const evData = await adminDb.query({
    events: { $: { where: { id: eventId } }, enrollment: { events: {}, contact: {} } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev = (evData.events as any[])[0];
  if (!ev?.enrollment) return;

  const enrollment = ev.enrollment;
  const enrollmentId = enrollment.id as string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingEvents = (enrollment.events as any[]).filter(
    (e: { id: string; status: string }) => e.id !== eventId && e.status === 'pending'
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const txns: any[] = [
    adminDb.tx.enrollments[enrollmentId].update({ status: 'bounced' }),
    ...pendingEvents.map((e: { id: string }) => adminDb.tx.events[e.id].update({ status: 'skipped' })),
  ];

  if (enrollment.contact?.id) {
    txns.push(adminDb.tx.contacts[enrollment.contact.id as string].update({ status: 'bounced', updated_at: ts }));
  }

  await adminDb.transact(txns);
}

export async function markEventSkipped(eventId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.events[eventId].update({ status: 'skipped' }));
}
