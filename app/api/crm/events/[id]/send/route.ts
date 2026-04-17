import { NextRequest, NextResponse } from 'next/server';
import { adminDb } from '@/lib/crm/instant-db';
import { sendCrmEmail, buildVars, resolveTemplate, validateEmailDomain } from '@/lib/crm/email';
import { markEventSent } from '@/lib/crm/queries/events';
import type { EmailTask } from '@/lib/crm/queries/tasks';

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: eventId } = await params;

    const data = await adminDb.query({
      events: {
        $: { where: { id: eventId } },
        enrollment: {
          contact: { company: {} },
          sequence: {},
        },
        step: {},
      },
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const ev = (data.events as any[])[0];
    if (!ev) return NextResponse.json({ error: 'Event not found' }, { status: 404 });

    const contact = ev.enrollment?.contact;
    const company = ev.enrollment?.contact?.company;
    const sequence = ev.enrollment?.sequence;

    if (!contact?.email) {
      return NextResponse.json({ error: 'Contact has no email address' }, { status: 400 });
    }

    // Email domain validation
    const domainValid = await validateEmailDomain(contact.email as string);
    if (!domainValid) {
      return NextResponse.json(
        { error: 'Invalid email domain — no MX records found', code: 'INVALID_EMAIL' },
        { status: 422 }
      );
    }

    // Parse custom fields from contact
    let customFields: Record<string, string> | null = null;
    if (contact.custom_fields) {
      try { customFields = JSON.parse(contact.custom_fields as string); } catch { /* ignore */ }
    }

    // Pull audit vars from the company record
    const auditKeys = [
      'score', 'cap_count', 'top3rate', 'outside3rate',
      'worst_query', 'worst_pos', 'wrong_product',
    ] as const;
    const auditVars: Record<string, string> = {};
    for (const k of auditKeys) {
      const v = company?.[`audit_${k}`];
      if (typeof v === 'string' && v.length > 0) auditVars[k] = v;
    }

    const task: EmailTask & { custom_fields?: Record<string, string> | null } = {
      event_id: eventId,
      contact_name: contact.name ?? '',
      contact_email: contact.email ?? '',
      contact_id: contact.id ?? '',
      company_name: company?.name ?? '',
      company_id: company?.id ?? '',
      sequence_name: sequence?.name ?? '',
      step_order: ev.step?.step_order ?? 0,
      subject_template: ev.step?.subject_template ?? null,
      body_template: ev.step?.body_template ?? null,
      scheduled_date: ev.scheduled_date ?? '',
      is_overdue: false,
      send_hour: null,
      audit_vars: Object.keys(auditVars).length > 0 ? auditVars : null,
      custom_fields: customFields,
    };

    const fromEmail = sequence?.from_email ?? undefined;
    const resendId = await sendCrmEmail(task, fromEmail);
    await markEventSent(eventId, resendId);

    return NextResponse.json({ success: true, resend_id: resendId });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to send email' },
      { status: 500 }
    );
  }
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: eventId } = await params;

    const data = await adminDb.query({
      events: {
        $: { where: { id: eventId } },
        enrollment: { contact: { company: {} } },
        step: {},
      },
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const ev = (data.events as any[])[0];
    if (!ev) return NextResponse.json({ error: 'Event not found' }, { status: 404 });

    const contact = ev.enrollment?.contact;
    const company = ev.enrollment?.contact?.company;

    // Parse custom fields for preview
    let customFields: Record<string, string> | null = null;
    if (contact?.custom_fields) {
      try { customFields = JSON.parse(contact.custom_fields as string); } catch { /* ignore */ }
    }

    const task = {
      contact_name: contact?.name ?? '',
      contact_email: contact?.email ?? '',
      company_name: company?.name ?? '',
    };

    const vars = buildVars(task);
    const auditKeys = [
      'score', 'cap_count', 'top3rate', 'outside3rate',
      'worst_query', 'worst_pos', 'wrong_product',
    ] as const;
    for (const k of auditKeys) {
      const v = company?.[`audit_${k}`];
      if (typeof v === 'string' && v.length > 0) vars[k] = v;
    }
    if (customFields) Object.assign(vars, customFields);

    const subject = ev.step?.subject_template
      ? resolveTemplate(ev.step.subject_template, vars)
      : '(no subject)';
    const body = ev.step?.body_template
      ? resolveTemplate(ev.step.body_template, vars)
      : '';

    return NextResponse.json({ subject, body, to: contact?.email ?? '' });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to preview email' },
      { status: 500 }
    );
  }
}
