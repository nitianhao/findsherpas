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

## Content (MDX)
- Blog posts: `content/blog/*.mdx`
- Case studies: `content/case-studies/*.mdx`

## Stripe (Checkout)
- API route: `app/api/stripe/checkout/route.ts`
- Success page: `app/stripe/success`
- Cancel page: `app/stripe/cancel`

Set these env vars (see `.env.example`): `STRIPE_SECRET_KEY` + tier `STRIPE_PRICE_*`.

## Contact form
- API route: `app/api/contact/route.ts`
- UI: `components/site/contact-form.tsx`

Uses Resend if `RESEND_API_KEY` is set; otherwise it logs submissions in dev.

## Deploy (Vercel)
- Push to GitHub
- Import repo in Vercel
- Add env vars from `.env.example` to Vercel Project Settings

