import { NextRequest, NextResponse } from 'next/server';
import { getCompanyById, updateCompany, deleteCompany } from '@/lib/crm/queries/companies';
import { companyUpdateSchema } from '@/lib/crm/validations';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const company = await getCompanyById(id);
    if (!company) {
      return NextResponse.json({ error: 'Company not found' }, { status: 404 });
    }
    return NextResponse.json(company);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch company' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const companyId = id;

    const existing = await getCompanyById(companyId);
    if (!existing) {
      return NextResponse.json({ error: 'Company not found' }, { status: 404 });
    }

    const body = await request.json();
    const parsed = companyUpdateSchema.parse(body);
    const company = await updateCompany(companyId, parsed);
    return NextResponse.json(company);
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to update company' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const companyId = id;

    const existing = await getCompanyById(companyId);
    if (!existing) {
      return NextResponse.json({ error: 'Company not found' }, { status: 404 });
    }

    deleteCompany(companyId);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to delete company' },
      { status: 500 }
    );
  }
}
