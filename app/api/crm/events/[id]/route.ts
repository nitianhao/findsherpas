import { NextRequest, NextResponse } from 'next/server';
import { markEventSent, markEventReplied, markEventBounced, markEventSkipped } from '@/lib/crm/queries/events';

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const eventId = id;

    const body = await request.json();
    const action = body.action as string;

    switch (action) {
      case 'sent':
        markEventSent(eventId);
        break;
      case 'replied':
        markEventReplied(eventId);
        break;
      case 'bounced':
        markEventBounced(eventId);
        break;
      case 'skipped':
        markEventSkipped(eventId);
        break;
      default:
        return NextResponse.json(
          { error: 'Invalid action. Use "sent", "replied", "bounced", or "skipped".' },
          { status: 400 }
        );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to update event' },
      { status: 500 }
    );
  }
}
