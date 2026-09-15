import { NextResponse } from "next/server";

import { Resend } from "resend";

type ContactPayload = {
  name: string;
  email: string;
  company?: string;
  message: string;
  interestedIn?: "ux" | "relevance" | "analytics" | "other";
  website?: string; // honeypot
};

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export async function POST(req: Request) {
  let body: ContactPayload | null = null;
  try {
    body = (await req.json()) as ContactPayload;
  } catch {
    body = null;
  }

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  // Basic spam protection: honeypot must stay empty
  if (typeof body.website === "string" && body.website.trim().length > 0) {
    return NextResponse.json({ ok: true });
  }

  const name = typeof body.name === "string" ? body.name.trim() : "";
  const email = typeof body.email === "string" ? body.email.trim() : "";
  const company = typeof body.company === "string" ? body.company.trim() : "";
  const message = typeof body.message === "string" ? body.message.trim() : "";
  const interestedIn = body.interestedIn ?? "other";

  if (!name || !email || !message) {
    return NextResponse.json(
      { error: "Missing required fields" },
      { status: 400 },
    );
  }
  if (!isEmail(email)) {
    return NextResponse.json({ error: "Invalid email" }, { status: 400 });
  }
  if (
    name.length > 200 ||
    email.length > 254 ||
    company.length > 500 ||
    message.length > 10000
  ) {
    return NextResponse.json(
      { error: "Please shorten your message and try again." },
      { status: 400 },
    );
  }

  const toEmail = process.env.CONTACT_TO_EMAIL ?? "michal.pekarcik@gmail.com";

  // A successful response must mean the provider accepted the message.
  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey || resendKey === "re_...") {
    return NextResponse.json(
      {
        error:
          "The form is temporarily unavailable. Please email michal@findsherpas.com directly.",
      },
      { status: 503 },
    );
  }

  const resend = new Resend(resendKey);

  const subject = `Find Sherpas inquiry: ${interestedIn}`;
  const text = [
    `Name: ${name}`,
    `Email: ${email}`,
    `Company: ${company || "-"}`,
    `Interested in: ${interestedIn}`,
    "",
    message,
  ].join("\n");

  try {
    const { data, error } = await resend.emails.send({
      from:
        process.env.CONTACT_FROM_EMAIL ??
        "Find Sherpas <onboarding@resend.dev>",
      to: [toEmail],
      replyTo: email,
      subject,
      text,
    });

    if (error) {
      console.error("Resend error:", error);
      return NextResponse.json(
        {
          error:
            "Your message could not be sent. Please try again or email michal@findsherpas.com.",
        },
        { status: 502 },
      );
    }

    return NextResponse.json({ ok: true, delivery: "email", id: data?.id });
  } catch (err: unknown) {
    console.error("Unexpected error sending email:", err);
    return NextResponse.json(
      { error: "Failed to send email. Please try again later." },
      { status: 500 },
    );
  }
}
