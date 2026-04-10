import { NextRequest, NextResponse } from 'next/server';
import { getContacts, createContact } from '@/lib/crm/queries/contacts';
import { contactCreateSchema } from '@/lib/crm/validations';
import type { ContactStatus } from '@/lib/crm/types';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;

    const filters = {
      search: searchParams.get('search') ?? undefined,
      status: (searchParams.get('status') as ContactStatus) ?? undefined,
      company_id: searchParams.get('company_id') ? searchParams.get('company_id')! : undefined,
      role: searchParams.get('role') ?? undefined,
      limit: searchParams.get('limit') ? Number(searchParams.get('limit')) : undefined,
      offset: searchParams.get('offset') ? Number(searchParams.get('offset')) : undefined,
    };

    const result = await getContacts(filters);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch contacts' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = contactCreateSchema.parse(body);
    const contact = await createContact(parsed);
    return NextResponse.json(contact, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to create contact' },
      { status: 500 }
    );
  }
}
