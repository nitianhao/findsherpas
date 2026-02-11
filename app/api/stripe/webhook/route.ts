import { headers } from "next/headers";
import { NextResponse } from "next/server";

import type Stripe from "stripe";

import { getStripe } from "@/lib/stripe";

export async function POST(req: Request) {
  let stripe: ReturnType<typeof getStripe>;
  try {
    stripe = getStripe();
  } catch (err) {
    const message = err instanceof Error ? err.message : "Stripe not configured";
    return NextResponse.json({ error: message }, { status: 500 });
  }

  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret) {
    return NextResponse.json(
      { error: "Missing STRIPE_WEBHOOK_SECRET" },
      { status: 500 },
    );
  }

  const body = await req.text();
  const signature = (await headers()).get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ error: "Missing signature" }, { status: 400 });
  }

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch {
    return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    // Placeholder: later we can email you, create a lead record, etc.
    console.log("Stripe checkout.session.completed", {
      id: session.id,
      customerEmail: session.customer_details?.email,
      tierId: session.metadata?.tierId,
    });
  }

  return NextResponse.json({ received: true });
}

