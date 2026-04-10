import { NextRequest, NextResponse } from 'next/server';
import { getCompanies, createCompany } from '@/lib/crm/queries/companies';
import { companyCreateSchema } from '@/lib/crm/validations';
import type { CompanyStatus } from '@/lib/crm/types';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;

    const filters = {
      search: searchParams.get('search') ?? undefined,
      status: (searchParams.get('status') as CompanyStatus) ?? undefined,
      platform: searchParams.get('platform') ?? undefined,
      tag_id: searchParams.get('tag_id') ?? undefined,
      limit: searchParams.get('limit') ? Number(searchParams.get('limit')) : undefined,
      offset: searchParams.get('offset') ? Number(searchParams.get('offset')) : undefined,
    };

    const result = await getCompanies(filters);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch companies' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = companyCreateSchema.parse(body);
    const company = await createCompany(parsed);
    return NextResponse.json(company, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to create company' },
      { status: 500 }
    );
  }
}
