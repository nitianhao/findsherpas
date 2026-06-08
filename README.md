## Find Sherpas

Agency website for **Find Sherpas** — on-site search optimization (UX audits, relevance tuning, and search analytics design).

Built with **Next.js (App Router)**, **Tailwind CSS**, and **shadcn/ui**. Deployable to **Vercel**.

## Local development

1) Install dependencies

```bash
npm install
```

2) Configure environment

```bash
cp .env.example .env.local
```

3) Run dev server

```bash
npm run dev
```

Open `http://localhost:3000`.

## Environment variables

Source of truth: `.env.local` (local) and Vercel project env vars (prod). Use `.env.example` as the checked-in template. Never commit real secrets.

- `NEXT_PUBLIC_SITE_URL` — base URL (e.g. `http://localhost:3000`, `https://findsherpas.com`)
- `STRIPE_SECRET_KEY` — Stripe secret key
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret (optional but recommended)
- `STRIPE_PRICE_STARTER` — Stripe Price ID for Starter tier
- `STRIPE_PRICE_GROWTH` — Stripe Price ID for Growth tier
- `STRIPE_PRICE_ENTERPRISE` — Stripe Price ID for Enterprise tier
- `RESEND_API_KEY` — Resend API key (optional; without it contact submissions are logged)
- `CONTACT_TO_EMAIL` — recipient email for contact form submissions
- `CONTACT_FROM_EMAIL` — verified sender email for Resend

## Content (MDX)
- Blog posts: `content/blog/*.mdx`
- Case studies: `content/case-studies/*.mdx`

## Search audit pipeline

The audit pipeline is a self-contained project under `src/audit/`. Its documentation lives there, not in this website README.

- Report publishing, CRM writeback, and report presentation rules: `src/audit/docs/REPORT-PUBLISHING-AND-CRM-NOTES.md`
- Pipeline run instructions and architecture: see `src/audit/` (skill: `synthetic-search-audit`)

## Stripe (Checkout)
- API route: `app/api/stripe/checkout/route.ts`
- Success page: `app/stripe/success`
- Cancel page: `app/stripe/cancel`

Set these env vars (see `.env.example`): `STRIPE_SECRET_KEY` + tier `STRIPE_PRICE_*`.

## Contact form
- API route: `app/api/contact/route.ts`
- UI: `components/site/reach-out-form.tsx` (rendered on `app/(site)/book-a-call`)

Uses Resend if `RESEND_API_KEY` is set; otherwise it logs submissions in dev.

## Deploy (Vercel)
- Push to GitHub
- Import repo in Vercel
- Add env vars from `.env.example` to Vercel Project Settings

## Decision log

- **2026-02-10** — Stack + content + payments
  - **Context**: Build a Vercel-deployable marketing site quickly with SEO-friendly content and payments.
  - **Decision**: Next.js App Router + Tailwind + shadcn/ui, MDX content in-repo, Stripe Checkout for one-time tier purchases.
  - **Alternatives considered**: CMS for content; subscriptions; embedded Stripe Elements.
  - **Consequences**: Simple MVP, easy GitHub/Vercel deploy; can migrate content to CMS later if needed.
