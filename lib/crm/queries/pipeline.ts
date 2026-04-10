import { adminDb } from '@/lib/crm/instant-db';

export const DEAL_STAGES = ['replied', 'meeting-booked', 'proposal-sent', 'won', 'lost', 'not-interested'] as const;
export type DealStage = typeof DEAL_STAGES[number];

export interface PipelineContact {
  enrollment_id: string;
  contact_id: string;
  contact_name: string;
  contact_email: string;
  company_id: string | null;
  company_name: string | null;
  sequence_id: string;
  sequence_name: string;
  deal_stage: DealStage;
  started_at: string;
  last_sent_at: string | null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapPipelineContact(e: any): PipelineContact | null {
  if (!e.contact?.id || !e.sequence?.id) return null;
  const stage = e.deal_stage as DealStage | undefined;
  if (!stage || !DEAL_STAGES.includes(stage)) return null;
  return {
    enrollment_id: e.id as string,
    contact_id: e.contact.id as string,
    contact_name: e.contact.name ?? '',
    contact_email: e.contact.email ?? '',
    company_id: e.contact.company?.id ?? null,
    company_name: e.contact.company?.name ?? null,
    sequence_id: e.sequence.id as string,
    sequence_name: e.sequence.name ?? '',
    deal_stage: stage,
    started_at: e.started_at ?? '',
    last_sent_at: null, // not needed for kanban view
  };
}

export async function getPipelineContacts(): Promise<PipelineContact[]> {
  const data = await adminDb.query({
    enrollments: {
      contact: { company: {} },
      sequence: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.enrollments as any[])
    .map(mapPipelineContact)
    .filter((x): x is PipelineContact => x !== null)
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
}

export async function updateEnrollmentDealStage(enrollmentId: string, dealStage: DealStage | null): Promise<void> {
  await adminDb.transact(
    adminDb.tx.enrollments[enrollmentId].update({ deal_stage: dealStage })
  );
}
