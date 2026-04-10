import { adminDb } from '@/lib/crm/instant-db';

function now() {
  return new Date().toISOString();
}

export async function getEventByResendId(resendEmailId: string): Promise<string | null> {
  const data = await adminDb.query({
    events: { $: { where: { resend_email_id: resendEmailId } } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev = (data.events as any[])[0];
  return ev ? (ev.id as string) : null;
}

export async function markEventSent(eventId: string, resendEmailId?: string): Promise<void> {
  const attrs: Record<string, unknown> = { status: 'sent', sent_at: now() };
  if (resendEmailId) attrs.resend_email_id = resendEmailId;
  await adminDb.transact(adminDb.tx.events[eventId].update(attrs));

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
    adminDb.tx.enrollments[enrollmentId].update({ status: 'replied', completed_at: ts, deal_stage: 'replied' }),
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

export async function markEventOpened(eventId: string): Promise<void> {
  const data = await adminDb.query({ events: { $: { where: { id: eventId } } } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev = (data.events as any[])[0];
  if (!ev) return;
  const currentCount = (ev.open_count as number | undefined) ?? 0;
  const attrs: Record<string, unknown> = { open_count: currentCount + 1 };
  if (!ev.opened_at) attrs.opened_at = now();
  await adminDb.transact(adminDb.tx.events[eventId].update(attrs));
}

export async function markEventClicked(eventId: string): Promise<void> {
  const data = await adminDb.query({ events: { $: { where: { id: eventId } } } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ev = (data.events as any[])[0];
  if (!ev) return;
  const currentCount = (ev.click_count as number | undefined) ?? 0;
  const attrs: Record<string, unknown> = { click_count: currentCount + 1 };
  if (!ev.clicked_at) attrs.clicked_at = now();
  await adminDb.transact(adminDb.tx.events[eventId].update(attrs));
}
