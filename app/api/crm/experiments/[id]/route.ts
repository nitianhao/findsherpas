import { NextRequest, NextResponse } from 'next/server';
import { getExperimentById, endExperiment } from '@/lib/crm/queries/experiments';

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const experiment = await getExperimentById(id);
  if (!experiment) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  return NextResponse.json(experiment);
}

export async function PUT(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  await endExperiment(id);
  return NextResponse.json({ ok: true });
}
