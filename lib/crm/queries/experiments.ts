import { adminDb, id } from '@/lib/crm/instant-db';
import type { Experiment, ExperimentVariant } from '@/lib/crm/types';
import { enrollContact } from '@/lib/crm/queries/enrollments';

function now() {
  return new Date().toISOString();
}

// Build per-variant stats from a flat list of enrollments tagged with ab_variant
function computeVariantStats(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  variants: any[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  enrollments: any[],
): ExperimentVariant[] {
  return variants.map((v) => {
    const varEnrollments = enrollments.filter((e) => e.ab_variant === v.label);
    const sent = varEnrollments.reduce((n: number, enr: { events?: { status: string }[] }) => {
      return n + (enr.events ?? []).filter((ev) => ev.status === 'sent' || ev.status === 'replied').length;
    }, 0);
    const replied = varEnrollments.reduce((n: number, enr: { events?: { status: string }[] }) => {
      return n + (enr.events ?? []).filter((ev) => ev.status === 'replied').length;
    }, 0);
    return {
      id: v.id as string,
      label: v.label as 'A' | 'B',
      sequence_id: v.sequence?.id ?? '',
      sequence_name: v.sequence?.name ?? '',
      enrolled: varEnrollments.length,
      sent,
      replied,
    };
  });
}

export async function getExperiments(): Promise<Experiment[]> {
  const data = await adminDb.query({
    experiments: {
      variants: { sequence: {} },
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const experiments = data.experiments as any[];

  // Fetch enrollment counts per experiment (stats without events for list view)
  const enrollmentData = await adminDb.query({
    enrollments: { $: { where: {} } },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const allEnrollments = enrollmentData.enrollments as any[];

  return experiments
    .map((exp) => {
      const expEnrollments = allEnrollments.filter((e) => e.experiment_id === exp.id);
      const variants = computeVariantStats(exp.variants ?? [], expEnrollments);
      return {
        id: exp.id as string,
        name: exp.name ?? '',
        status: exp.status ?? 'active',
        created_at: exp.created_at ?? now(),
        updated_at: exp.updated_at ?? now(),
        variants,
      };
    })
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function getExperimentById(experimentId: string): Promise<Experiment | null> {
  const [expData, enrollmentData] = await Promise.all([
    adminDb.query({
      experiments: {
        $: { where: { id: experimentId } },
        variants: { sequence: {} },
      },
    }),
    adminDb.query({
      enrollments: {
        $: { where: { experiment_id: experimentId } },
        events: {},
      },
    }),
  ]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const exp = (expData.experiments as any[])[0];
  if (!exp) return null;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const enrollments = enrollmentData.enrollments as any[];
  const variants = computeVariantStats(exp.variants ?? [], enrollments);

  return {
    id: exp.id as string,
    name: exp.name ?? '',
    status: exp.status ?? 'active',
    created_at: exp.created_at ?? now(),
    updated_at: exp.updated_at ?? now(),
    variants,
  };
}

export async function createExperiment(
  name: string,
  sequenceAId: string,
  sequenceBId: string,
): Promise<Experiment> {
  const experimentId = id();
  const variantAId = id();
  const variantBId = id();
  const ts = now();

  await adminDb.transact([
    adminDb.tx.experiments[experimentId].update({ name, status: 'active', created_at: ts, updated_at: ts }),
    adminDb.tx.experimentVariants[variantAId].update({ label: 'A', created_at: ts }),
    adminDb.tx.experimentVariants[variantAId].link({ experiment: experimentId }),
    adminDb.tx.experimentVariants[variantAId].link({ sequence: sequenceAId }),
    adminDb.tx.experimentVariants[variantBId].update({ label: 'B', created_at: ts }),
    adminDb.tx.experimentVariants[variantBId].link({ experiment: experimentId }),
    adminDb.tx.experimentVariants[variantBId].link({ sequence: sequenceBId }),
  ]);

  return getExperimentById(experimentId) as Promise<Experiment>;
}

export async function endExperiment(experimentId: string): Promise<void> {
  await adminDb.transact(
    adminDb.tx.experiments[experimentId].update({ status: 'ended', updated_at: now() })
  );
}

export async function enrollInExperiment(
  experimentId: string,
  contactIds: string[],
): Promise<void> {
  const data = await adminDb.query({
    experiments: {
      $: { where: { id: experimentId } },
      variants: { sequence: {} },
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const exp = (data.experiments as any[])[0];
  if (!exp) throw new Error('Experiment not found');

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const variants: any[] = (exp.variants ?? []).sort((a: any, b: any) =>
    (a.label as string).localeCompare(b.label as string)
  );
  if (variants.length !== 2) throw new Error('Experiment must have exactly 2 variants');

  // Fisher-Yates shuffle for random split
  const shuffled = [...contactIds];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }

  const half = Math.ceil(shuffled.length / 2);
  const groupA = shuffled.slice(0, half);
  const groupB = shuffled.slice(half);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const variantA = variants.find((v: any) => v.label === 'A');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const variantB = variants.find((v: any) => v.label === 'B');

  async function enrollGroup(contactGroup: string[], variant: { sequence: { id: string } }, abLabel: string) {
    for (const contactId of contactGroup) {
      const enrollment = await enrollContact(contactId, variant.sequence.id);
      await adminDb.transact(
        adminDb.tx.enrollments[enrollment.id].update({
          experiment_id: experimentId,
          ab_variant: abLabel,
        })
      );
    }
  }

  await Promise.all([
    enrollGroup(groupA, variantA, 'A'),
    enrollGroup(groupB, variantB, 'B'),
  ]);
}

export async function getEnrollmentsByExperimentId(
  experimentId: string,
): Promise<{
  id: string;
  contact_name: string;
  contact_email: string;
  ab_variant: string;
  status: string;
  started_at: string;
  sequence_name: string;
}[]> {
  const data = await adminDb.query({
    enrollments: {
      $: { where: { experiment_id: experimentId } },
      contact: {},
      sequence: {},
    },
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (data.enrollments as any[])
    .map((e) => ({
      id: e.id as string,
      contact_name: e.contact?.name ?? '',
      contact_email: e.contact?.email ?? '',
      ab_variant: e.ab_variant ?? '',
      status: e.status ?? 'active',
      started_at: e.started_at ?? '',
      sequence_name: e.sequence?.name ?? '',
    }))
    .sort((a, b) => b.started_at.localeCompare(a.started_at));
}
