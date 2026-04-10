import { NextRequest, NextResponse } from 'next/server';
import { createHmac } from 'node:crypto';

function computeHmac(secret: string): string {
  return createHmac('sha256', secret).update('crm-session').digest('hex');
}

const COOKIE_OPTIONS = {
  httpOnly: true,
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
  maxAge: 60 * 60 * 24 * 30, // 30 days
};

export async function POST(request: NextRequest) {
  const { password } = await request.json();

  if (!password || password !== process.env.CRM_PASSWORD) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const token = computeHmac(process.env.AUTH_SECRET!);
  const response = NextResponse.json({ ok: true });
  response.cookies.set('crm_session', token, COOKIE_OPTIONS);
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set('crm_session', '', { ...COOKIE_OPTIONS, maxAge: 0 });
  return response;
}
