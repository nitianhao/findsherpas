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

## Article CMS

Open `/crm/articles` after signing in to the CRM. The editor supports headings, fonts, colors, alignment, lists, checklists, quotes, code, tables, links, and images, video, audio, YouTube, Vimeo, and PDF attachments. Media can be inserted from a URL or uploaded to the existing Vercel Blob store; supported files can also be pasted or dropped into the editor. Uploads are limited to 100 MB. It supports drafts, a site-styled preview, and publishing. Published articles appear at `/blog/[slug]` and in the sitemap. Saving edits to an existing article keeps its published version live until Publish is clicked again. Existing MDX blog posts remain available.

Article data is stored in the existing InstantDB app. The CRM needs `NEXT_PUBLIC_INSTANT_APP_ID`, `INSTANT_APP_ADMIN_TOKEN`, `AUTH_SECRET`, and `CRM_PASSWORD`. Apply the checked-in schema and permissions to a new InstantDB app with `npx instant-cli@latest push schema` and `npx instant-cli@latest push perms`. The article namespace denies client SDK access; the protected server routes use the Admin SDK.

## Search audit pipeline

The audit pipeline is a self-contained project under `src/audit/`. Its documentation lives there, not in this website README.

- Report publishing, CRM writeback, and report presentation rules: `src/audit/docs/REPORT-PUBLISHING-AND-CRM-NOTES.md`
- Pipeline run instructions and architecture: see `src/audit/` (skill: `synthetic-search-audit`)

## Lead-gen: Search Scanner & Teardown Flow

The lead-gen system lives under `src/scanner/` (Python) and several new Next.js routes/components.

### Components

1. **Scanner** (`src/scanner/`) — Python module with deterministic search probes
2. **Benchmark page** (`/benchmark`) — anonymized capability stats across stores
3. **Teardown request** (`/teardown`) — public form to request a free search teardown
4. **CRM queue** (`/crm/audit-requests`) — approve/reject teardown requests, trigger emails
5. **Teardown report** (`/teardown-report/[slug]`) — private noindexed report page

### Scanner Setup (Mac local)

```bash
cd src/scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Environment variables (`.env` in `src/scanner/`):

```env
INSTANT_APP_ID=...           # InstantDB app ID
INSTANT_ADMIN_TOKEN=...      # InstantDB admin token
```

### Scanner CLI

**Single scan:**
```bash
python -m scanner.cli https://example-store.com --vertical fashion --country DK --headed
```

**Batch mode (CSV):**
```bash
python -m scanner.cli --batch domains.csv --output-dir ./output --headed
```

CSV format: `domain,vertical,country`

**Push to InstantDB:**
```bash
python -m scanner.cli https://example-store.com --push-benchmark
```

### Teardown Worker

Polls InstantDB for new teardown requests and runs scans:

```bash
python -m scanner.worker --interval 60 --headed --output-dir ./output
```

Flags:
- `--once` — process pending requests and exit
- `--dry-run` — don't push results to InstantDB
- `--headless` — run browser headless (default: headed)

### Teardown Flow

1. User submits form at `/teardown` with store URL and email
2. Rate limiting checks (2 per domain/week, 5 per email domain/day)
3. Request saved to InstantDB (`auditRequests`) with status `new`
4. CRM shows request at `/crm/audit-requests`
5. Worker picks up request, runs scanner, pushes results, sets status `ready_for_review`
6. CRM reviewer can approve (sends email via Resend) or reject
7. Approved requests link to private report at `/teardown-report/[slug]`

### Tests

**Python scanner tests:**
```bash
cd src/scanner
source .venv/bin/activate
pytest test_scorer.py -v
```

**TypeScript API tests:**
```bash
npm test -- lib/teardown-route.test.ts
```

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
