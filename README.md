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

## Search audit reports
- Audit engine: `src/audit/`
- Default report output: `reports/`
- Legacy audit utilities migrated from the discontinued audit workspace: `src/audit/scripts/`

New audit runs should be created from this repo. The audit orchestrator defaults to the top-level `reports/` directory.

When an audit is published, the orchestrator uploads the unlisted HTML report to a non-guessable URL like `https://findsherpas.com/report/{company}-1234/`. Report slugs are stored in `reports/report_slugs.json` so future republishes keep the same URL. The orchestrator also writes a `{slug}_access.json` file next to the report artifacts with:
- `report_url`
- `published_at`

If the audited company already exists in CRM, pass its InstantDB company id so the report URL and audit personalization variables are written immediately:

```bash
python3 src/audit/src/orchestrator.py "https://example.com/search?q=shoes" \
  --crm-company-id <instantdb-company-id>
```

For an existing report artifact, write the same fields manually with:

```bash
npx tsx --tsconfig tsconfig.json src/enrichment/scripts/writeAuditToCRM.ts \
  --company-id <instantdb-company-id> \
  --report reports/example/example_YYYYMMDD_HHMMSS_data.json \
  --report-url https://findsherpas.com/report/example/
```

CRM email sequences use company-level audit variables from this writeback, including `{{score}}`, `{{query_count}}`, `{{top_3_rate}}`, `{{outside_3_rate}}`, `{{worst_query}}`, `{{worst_pos}}`, `{{wrong_product}}`, `{{search_platform_sentence}}`, and `{{report_url}}`. `{{query_count}}` is derived from the actual number of query judgments in the report, so sequence copy can vary by audit size. `{{search_platform_sentence}}` is intentionally cautious and currently renders as `Looks fixable without replatforming.`

Generated HTML audit reports must show the Find Sherpas logo and wordmark on the cover. Keep the cover logo block in `src/audit/templates/master_report.html`, and keep the SVG asset at `src/audit/assets/logo.svg`; reports should not be shipped if that branding is missing.

Current report presentation rules:
- The reusable HTML template is `src/audit/templates/master_report.html`.
- The cover should feel like a boutique agency presentation: large Find Sherpas logo/wordmark, clean client name line, and a separate `Prepared by` block with `Name`, `Agency`, and `Contact`.
- Do not put `findsherpas.com` inside the logo/wordmark lockup. Put it in the `Prepared by` block as the agency link.
- Do not include a methodology/process section in client-facing reports. Avoid exposing automation, scoring pipeline, scraper, LLM, or implementation details in the rendered report.
- Keep the short-version summary, revenue-risk hero, tier cards, coverage heatmap, revenue-risk failure cards, deep dives, appendix, scope/boundaries section, and final CTA.
- The final CTA must link to the live Find Sherpas booking flow: `https://findsherpas.com/book-a-call`.

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
