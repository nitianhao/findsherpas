import { NextRequest, NextResponse } from 'next/server';
import { Webhook } from 'svix';
import { getEventByResendId, markEventBounced, markEventOpened, markEventClicked } from '@/lib/crm/queries/events';

export async function POST(req: NextRequest) {
  const secret = process.env.RESEND_WEBHOOK_SECRET;
  if (!secret) {
    return NextResponse.json({ error: 'Webhook secret not configured' }, { status: 500 });
  }

  const rawBody = await req.text();
  const headers = {
    'svix-id': req.headers.get('svix-id') ?? '',
    'svix-timestamp': req.headers.get('svix-timestamp') ?? '',
    'svix-signature': req.headers.get('svix-signature') ?? '',
  };

  let payload: { type: string; data: { email_id?: string } };
  try {
    const wh = new Webhook(secret);
    payload = wh.verify(rawBody, headers) as typeof payload;
  } catch {
    return NextResponse.json({ error: 'Invalid webhook signature' }, { status: 401 });
  }

  const { type, data } = payload;
  const resendEmailId = data?.email_id;

  if (resendEmailId) {
    const eventId = await getEventByResendId(resendEmailId);
    if (eventId) {
      if (type === 'email.bounced' || type === 'email.complained') {
        await markEventBounced(eventId);
      } else if (type === 'email.opened') {
        await markEventOpened(eventId);
      } else if (type === 'email.link_clicked' || type === 'email.clicked') {
        await markEventClicked(eventId);
      }
    }
  }

  return NextResponse.json({ received: true });
}
