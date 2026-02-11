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

  if (!body) {
    return NextResponse.json({ error: "Invalid payload" }, { status: 400 });
  }

  // Basic spam protection: honeypot must stay empty
  if (body.website && body.website.trim().length > 0) {
    return NextResponse.json({ ok: true });
  }

  const name = (body.name ?? "").trim();
  const email = (body.email ?? "").trim();
  const company = (body.company ?? "").trim();
  const message = (body.message ?? "").trim();
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

  const toEmail = process.env.CONTACT_TO_EMAIL ?? "hello@findsherpas.com";

  // If Resend is not configured yet, fall back to logging.
  const resendKey = process.env.RESEND_API_KEY;
  if (!resendKey) {
    console.log("Contact form submission (no RESEND_API_KEY configured)", {
      name,
      email,
      company,
      interestedIn,
      message,
    });
    return NextResponse.json({ ok: true, delivery: "log" });
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

  await resend.emails.send({
    from: process.env.CONTACT_FROM_EMAIL ?? "Find Sherpas <onboarding@resend.dev>",
    to: [toEmail],
    replyTo: email,
    subject,
    text,
  });

  return NextResponse.json({ ok: true, delivery: "email" });
}

