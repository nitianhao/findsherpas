import { NextRequest, NextResponse } from 'next/server';
import { put, del } from '@vercel/blob';
import { adminDb } from '@/lib/crm/instant-db';
import { getCompanyById } from '@/lib/crm/queries/companies';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: companyId } = await params;
    const company = await getCompanyById(companyId);
    if (!company) return NextResponse.json({ error: 'Company not found' }, { status: 404 });

    const formData = await req.formData();
    const file = formData.get('file') as File | null;
    if (!file) return NextResponse.json({ error: 'No file provided' }, { status: 400 });
    if (file.type !== 'application/pdf') {
      return NextResponse.json({ error: 'Only PDF files are accepted' }, { status: 400 });
    }

    // Delete old blob if one exists
    if (company.pdf_url) {
      try { await del(company.pdf_url); } catch { /* ignore if already gone */ }
    }

    const blob = await put(`crm/companies/${companyId}/${file.name}`, file, {
      access: 'public',
      contentType: 'application/pdf',
    });

    await adminDb.transact(
      adminDb.tx.companies[companyId].update({
        pdf_url: blob.url,
        pdf_name: file.name,
        updated_at: new Date().toISOString(),
      })
    );

    return NextResponse.json({ pdf_url: blob.url, pdf_name: file.name });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Upload failed' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: companyId } = await params;
    const company = await getCompanyById(companyId);
    if (!company) return NextResponse.json({ error: 'Company not found' }, { status: 404 });

    if (company.pdf_url) {
      await del(company.pdf_url);
    }

    await adminDb.transact(
      adminDb.tx.companies[companyId].update({
        pdf_url: null,
        pdf_name: null,
        updated_at: new Date().toISOString(),
      })
    );

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Delete failed' },
      { status: 500 }
    );
  }
}
