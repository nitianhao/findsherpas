import { adminDb, id } from '@/lib/crm/instant-db';
import type { Sequence, SequenceStep } from '@/lib/crm/types';

function now() {
  return new Date().toISOString();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapSequence(s: any): Sequence {
  return {
    id: s.id as string,
    name: s.name ?? '',
    description: s.description ?? null,
    is_active: s.is_active ?? 1,
    created_at: s.created_at ?? now(),
    updated_at: s.updated_at ?? now(),
    steps_count: (s.steps ?? []).length,
    enrolled_count: (s.enrollments ?? []).length,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapStep(s: any): SequenceStep {
  return {
    id: s.id as string,
    sequence_id: s.sequence?.id ?? '',
    step_order: s.step_order ?? 0,
    subject_template: s.subject_template ?? null,
    body_template: s.body_template ?? null,
    delay_days: s.delay_days ?? 0,
    created_at: s.created_at ?? now(),
  };
}

export async function getSequences(): Promise<Sequence[]> {
  const data = await adminDb.query({
    sequences: { steps: {}, enrollments: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.sequences as any[]).map(mapSequence)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function getSequenceById(sequenceId: string): Promise<Sequence | null> {
  const data = await adminDb.query({
    sequences: { $: { where: { id: sequenceId } }, steps: {}, enrollments: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const s = (data.sequences as any[])[0];
  return s ? mapSequence(s) : null;
}

export async function createSequence(data: {
  name: string;
  description?: string | null;
  is_active?: number;
}): Promise<Sequence> {
  const seqId = id();
  const ts = now();
  await adminDb.transact(
    adminDb.tx.sequences[seqId].update({
      name: data.name,
      description: data.description ?? null,
      is_active: data.is_active ?? 1,
      created_at: ts,
      updated_at: ts,
    })
  );
  return getSequenceById(seqId) as Promise<Sequence>;
}

export async function updateSequence(sequenceId: string, data: Record<string, unknown>): Promise<Sequence> {
  const attrs: Record<string, unknown> = { updated_at: now() };
  for (const [k, v] of Object.entries(data)) {
    if (['name', 'description', 'is_active'].includes(k) && v !== undefined) attrs[k] = v;
  }
  await adminDb.transact(adminDb.tx.sequences[sequenceId].update(attrs));
  return getSequenceById(sequenceId) as Promise<Sequence>;
}

export async function deleteSequence(sequenceId: string): Promise<void> {
  await adminDb.transact(adminDb.tx.sequences[sequenceId].delete());
}

export async function getStepsBySequenceId(sequenceId: string): Promise<SequenceStep[]> {
  const data = await adminDb.query({
    sequenceSteps: { $: { where: { 'sequence.id': sequenceId } }, sequence: {} },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.sequenceSteps as any[]).map(mapStep)
    .sort((a, b) => a.step_order - b.step_order);
}

export async function saveSteps(
  sequenceId: string,
  steps: Array<{
    id?: string;
    step_order: number;
    subject_template?: string | null;
    body_template?: string | null;
    delay_days: number;
  }>
): Promise<SequenceStep[]> {
  const existingSteps = await getStepsBySequenceId(sequenceId);
  const ts = now();
  const txns = [];

  // Delete existing steps
  for (const step of existingSteps) {
    txns.push(adminDb.tx.sequenceSteps[step.id].delete());
  }

  // Create new steps
  for (const step of steps) {
    const stepId = id();
    txns.push(
      adminDb.tx.sequenceSteps[stepId].update({
        step_order: step.step_order,
        subject_template: step.subject_template ?? null,
        body_template: step.body_template ?? null,
        delay_days: step.delay_days,
        created_at: ts,
      })
    );
    txns.push(adminDb.tx.sequenceSteps[stepId].link({ sequence: sequenceId }));
  }

  await adminDb.transact(txns);
  return getStepsBySequenceId(sequenceId);
}
