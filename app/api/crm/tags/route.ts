import { NextRequest, NextResponse } from 'next/server';
import { getTags, createTag } from '@/lib/crm/queries/tags';
import { tagCreateSchema } from '@/lib/crm/validations';

export async function GET() {
  try {
    const tags = await getTags();
    return NextResponse.json(tags);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to fetch tags' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = tagCreateSchema.parse(body);
    const tag = await createTag(parsed.name, parsed.color ?? null);
    return NextResponse.json(tag, { status: 201 });
  } catch (error) {
    if (error instanceof Error && error.name === 'ZodError') {
      return NextResponse.json({ error: (error as any).errors }, { status: 400 });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to create tag' },
      { status: 500 }
    );
  }
}
