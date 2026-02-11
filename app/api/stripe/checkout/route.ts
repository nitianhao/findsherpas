import { NextResponse } from "next/server";

import { getStripe } from "@/lib/stripe";
import { tierStripePriceEnv, type TierId } from "@/lib/pricing";

export async function POST(req: Request) {
  let stripe: ReturnType<typeof getStripe>;
  try {
    stripe = getStripe();
  } catch (err) {
    const message = err instanceof Error ? err.message : "Stripe not configured";
    return NextResponse.json({ error: message }, { status: 500 });
  }

  let tierId: TierId | null = null;
  try {
    const body = (await req.json()) as { tierId?: TierId };
    tierId = body.tierId ?? null;
  } catch {
    tierId = null;
  }

  if (!tierId || !(tierId in tierStripePriceEnv)) {
    return NextResponse.json(
      { error: "Invalid tierId" },
      { status: 400 },
    );
  }

  const priceEnvKey = tierStripePriceEnv[tierId];
  const priceId = process.env[priceEnvKey];
  if (!priceId) {
    return NextResponse.json(
      { error: `Missing ${priceEnvKey}` },
      { status: 500 },
    );
  }

  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ??
    "http://localhost:3000";

  try {
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${siteUrl}/stripe/success?tier=${tierId}&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${siteUrl}/stripe/cancel?tier=${tierId}`,
      allow_promotion_codes: true,
      metadata: { tierId },
    });

    return NextResponse.json({ url: session.url });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to create Checkout session";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

