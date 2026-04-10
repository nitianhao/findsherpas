import { NextRequest, NextResponse } from 'next/server';
import { createHmac } from 'node:crypto';

const PUBLIC_PATHS = ['/crm/login', '/crm/unsubscribe', '/api/crm/auth', '/api/crm/webhooks/resend', '/api/crm/unsubscribe'];

function computeHmac(secret: string): string {
  return createHmac('sha256', secret).update('crm-session').digest('hex');
}

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  const isCrm = pathname.startsWith('/crm') || pathname.startsWith('/api/crm');
  if (!isCrm) return NextResponse.next();
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) return NextResponse.next();

  const cookie = req.cookies.get('crm_session')?.value;
  const expected = computeHmac(process.env.AUTH_SECRET!);

  if (cookie && cookie === expected) return NextResponse.next();

  const loginUrl = req.nextUrl.clone();
  loginUrl.pathname = '/crm/login';
  loginUrl.search = '';
  return NextResponse.redirect(loginUrl);
}

export const proxyConfig = {
  matcher: ['/crm/:path*', '/api/crm/:path*'],
};
