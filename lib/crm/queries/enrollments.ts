import { adminDb, id } from '@/lib/crm/instant-db';
import type { ContactSequence, ContactSequenceEvent } from '@/lib/crm/types';
import { format, addDays } from 'date-fns';

function now() {
  return new Date().toISOString();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapEnrollment(e: any): ContactSequence {
  return {
    id: e.id as string,
    contact_id: e.contact?.id ?? '',
    sequence_id: e.sequence?.id ?? '',
    current_step: e.current_step ?? 1,
    status: e.status ?? 'active',
    started_at: e.started_at ?? now(),
    paused_at: e.paused_at ?? null,
    completed_at: e.completed_at ?? null,
    contact_name: e.contact?.name ?? undefined,
    contact_email: e.contact?.email ?? undefined,
    company_name: e.contact?.company?.name ?? undefined,
    sequence_name: e.sequence?.name ?? undefined,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapEvent(ev: any): ContactSequenceEvent {
  return {
    id: ev.id as string,
    contact_sequence_id: ev.enrollment?.id ?? '',
    step_id: ev.step?.id ?? '',
    status: ev.status ?? 'pending',
    scheduled_date: ev.scheduled_date ?? null,
    sent_at: ev.sent_at ?? null,
    replied_at: ev.replied_at ?? null,
    notes: ev.notes ?? null,
    step_order: ev.step?.step_order ?? undefined,
    subject_template: ev.step?.subject_template ?? undefined,
    body_template: ev.step?.body_template ?? undefined,
  };
}

export async function enrollContact(contactId: string, sequenceId: string): Promise<ContactSequence> {
  // Get all steps for the sequence, ordered by step_order
  const stepsData = await adminDb.query({
    sequenceSteps: {
      $: { where: { 'sequence.id': sequenceId } },
      sequence: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const steps = (stepsData.sequenceSteps as any[])
    .sort((a, b) => (a.step_order ?? 0) - (b.step_order ?? 0));

  const enrollmentId = id();
  const ts = now();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const txns: any[] = [
    adminDb.tx.enrollments[enrollmentId].update({
      current_step: 1,
      status: 'active',
      started_at: ts,
    }),
    adminDb.tx.enrollments[enrollmentId].link({ contact: contactId }),
    adminDb.tx.enrollments[enrollmentId].link({ sequence: sequenceId }),
  ];

  // Pre-generate all events with scheduled dates
  let currentDate = new Date();
  for (const step of steps) {
    currentDate = addDays(currentDate, step.delay_days ?? 0);
    const eventId = id();
    txns.push(
      adminDb.tx.events[eventId].update({
        status: 'pending',
        scheduled_date: format(currentDate, 'yyyy-MM-dd'),
      })
    );
    txns.push(adminDb.tx.events[eventId].link({ enrollment: enrollmentId }));
    txns.push(adminDb.tx.events[eventId].link({ step: step.id }));
  }

  await adminDb.transact(txns);
  return getEnrollmentById(enrollmentId) as Promise<ContactSequence>;
}

export async function enrollContacts(contactIds: string[], sequenceId: string): Promise<ContactSequence[]> {
  const results = [];
  for (const contactId of contactIds) {
    results.push(await enrollContact(contactId, sequenceId));
  }
  return results;
}

export async function getEnrollmentById(enrollmentId: string): Promise<ContactSequence | null> {
  const data = await adminDb.query({
    enrollments: {
      $: { where: { id: enrollmentId } },
      contact: { company: {} },
      sequence: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const e = (data.enrollments as any[])[0];
  return e ? mapEnrollment(e) : null;
}

export async function getEnrollmentsBySequenceId(sequenceId: string): Promise<ContactSequence[]> {
  const data = await adminDb.query({
    enrollments: {
      $: { where: { 'sequence.id': sequenceId } },
      contact: { company: {} },
      sequence: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.enrollments as any[]).map(mapEnrollment)
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
}

export async function getEnrollmentsByContactId(contactId: string): Promise<ContactSequence[]> {
  const data = await adminDb.query({
    enrollments: {
      $: { where: { 'contact.id': contactId } },
      contact: { company: {} },
      sequence: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.enrollments as any[]).map(mapEnrollment)
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
}

export async function pauseEnrollment(enrollmentId: string): Promise<void> {
  await adminDb.transact(
    adminDb.tx.enrollments[enrollmentId].update({ status: 'paused', paused_at: now() })
  );
}

export async function resumeEnrollment(enrollmentId: string): Promise<void> {
  const data = await adminDb.query({
    enrollments: { $: { where: { id: enrollmentId } } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const enrollment = (data.enrollments as any[])[0];
  if (!enrollment?.paused_at) return;

  const pausedAt = new Date(enrollment.paused_at);
  const pauseDays = Math.ceil((Date.now() - pausedAt.getTime()) / (1000 * 60 * 60 * 24));

  // Fetch pending events and shift their scheduled dates
  const eventsData = await adminDb.query({
    events: {
      $: { where: { status: 'pending', 'enrollment.id': enrollmentId } },
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pendingEvents = eventsData.events as any[];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const txns: any[] = pendingEvents.map(ev => {
    const newDate = addDays(new Date(ev.scheduled_date), pauseDays);
    return adminDb.tx.events[ev.id as string].update({
      scheduled_date: format(newDate, 'yyyy-MM-dd'),
    });
  });

  txns.push(adminDb.tx.enrollments[enrollmentId].update({ status: 'active', paused_at: null }));
  await adminDb.transact(txns);
}

export async function getEventsByEnrollmentId(enrollmentId: string): Promise<ContactSequenceEvent[]> {
  const data = await adminDb.query({
    events: {
      $: { where: { 'enrollment.id': enrollmentId } },
      enrollment: {},
      step: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.events as any[]).map(mapEvent)
    .sort((a, b) => (a.step_order ?? 0) - (b.step_order ?? 0));
}
