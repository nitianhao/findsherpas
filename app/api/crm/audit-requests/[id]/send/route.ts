import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { Resend } from "resend";
import { updateAuditRequestStatus, getAuditRequestById } from "@/lib/crm/queries/audit-requests";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const cookieStore = await cookies();
  const auth = cookieStore.get("crm-auth");
  if (!auth) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  
  const request = await getAuditRequestById(id);
  if (!request) {
    return NextResponse.json({ error: "Request not found" }, { status: 404 });
  }

  if (request.status !== "approved") {
    return NextResponse.json(
      { error: "Request must be approved before sending" },
      { status: 400 }
    );
  }

  if (!request.report_slug) {
    return NextResponse.json(
      { error: "No report generated for this request" },
      { status: 400 }
    );
  }

  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey || resendKey === "re_...") {
    // Dry run mode
    console.log("DRY RUN: Would send teardown report email to:", request.email);
    console.log("Report URL:", `${process.env.NEXT_PUBLIC_SITE_URL}/teardown-report/${request.report_slug}`);
    
    await updateAuditRequestStatus(id, "sent");
    return NextResponse.json({ ok: true, dryRun: true });
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://findsherpas.com";
  const reportUrl = `${siteUrl}/teardown-report/${request.report_slug}`;

  const resend = new Resend(resendKey);

  const emailSubject = "Your search teardown report is ready";
  const emailBody = `Hi ${request.name},

Your search teardown report for ${request.store_url} is ready.

View your report:
${reportUrl}

This report shows how your store's search performs across key capabilities like typo tolerance, synonyms, constraints, and more. Each section includes specific examples of queries that work and queries that don't.

The report link is private and not indexed by search engines.

If you'd like to discuss the findings or explore how to address the issues found, reply to this email.

Best,
Michal
Find Sherpas

---
You requested this report at findsherpas.com/teardown.`;

  try {
    const { data, error } = await resend.emails.send({
      from: process.env.CONTACT_FROM_EMAIL ?? "Find Sherpas <hello@findsherpas.com>",
      to: request.email,
      replyTo: "michal@findsherpas.com",
      subject: emailSubject,
      text: emailBody,
    });

    if (error) {
      console.error("Failed to send email:", error);
      return NextResponse.json(
        { error: "Failed to send email" },
        { status: 500 }
      );
    }

    await updateAuditRequestStatus(id, "sent");

    return NextResponse.json({ ok: true, emailId: data?.id });
  } catch (error) {
    console.error("Failed to send email:", error);
    return NextResponse.json(
      { error: "Failed to send email" },
      { status: 500 }
    );
  }
}
