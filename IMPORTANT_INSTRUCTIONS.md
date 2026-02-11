# Find Sherpas — Important Instructions (Living Doc)

**Purpose**: A single place to keep the “stuff we always forget” (setup, commands, conventions, links, decisions).

**How to use this doc**
- Add/update notes as soon as something becomes “tribal knowledge”.
- Prefer short, copy/pasteable commands.
- When something changes, update the relevant section and add a dated entry to **Decision log** (if applicable).

---

## Table of contents
- [Project snapshot](#project-snapshot)
- [Local setup](#local-setup)
- [How to run](#how-to-run)
- [Testing](#testing)
- [Environment & secrets](#environment--secrets)
- [Repo conventions](#repo-conventions)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Decision log](#decision-log)
- [Links](#links)

---

## Project snapshot
- **What this is**: Find Sherpas agency website (on-site search optimization services).
- **Primary user**: Ecommerce / marketplace / content teams responsible for on-site search.
- **Tech stack**: Tailwind CSS + shadcn/ui (design system)
- **Key folders**:
  - `app/` — Next.js App Router pages + API routes
  - `content/` — MDX content for Blog and Case Studies
  - `components/` — shared UI components
  - `lib/` — content + pricing + Stripe helpers
- **Status**: MVP

---

## Local setup
### Prerequisites
- **Runtime(s)**: Node.js 20+
- **Package manager(s)**: npm
- **Datastores**: none

### First-time setup (copy/paste)
```bash
npm install
cp .env.example .env.local
npm run dev
```

### Optional tools
- **Formatting/linting**:
- **Git hooks**:

---

## How to run
### Development
```bash
npm run dev
```

### Production-like
```bash
npm run build && npm run start
```

---

## Testing
```bash
# Example:
# npm test
# pytest
```

- **Where tests live**:
- **How to run a single test**:

---

## Environment & secrets
### Environment variables
- **Source of truth**: `.env.local` (local) and Vercel project env vars (prod). Use `.env.example` as the checked-in template.
- **Rules**:
  - Never commit real secrets.
  - Prefer documenting required vars in a checked-in example file.

### Required variables (document here)
- `NEXT_PUBLIC_SITE_URL` — base URL (e.g. `http://localhost:3000`, `https://findsherpas.com`)
- `STRIPE_SECRET_KEY` — Stripe secret key
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret (optional but recommended)
- `STRIPE_PRICE_STARTER` — Stripe Price ID for Starter tier
- `STRIPE_PRICE_GROWTH` — Stripe Price ID for Growth tier
- `STRIPE_PRICE_ENTERPRISE` — Stripe Price ID for Enterprise tier
- `RESEND_API_KEY` — Resend API key (optional; without it contact submissions are logged)
- `CONTACT_TO_EMAIL` — recipient email for contact form submissions
- `CONTACT_FROM_EMAIL` — verified sender email for Resend

---

## Repo conventions
### Branching & commits
- **Branch naming**: (e.g. `feature/...`, `fix/...`)
- **Commit message style**:

### Code style
- **Formatter**:
- **Linting**:
- **Naming conventions**:

### Documentation rules
- Any setup change must update this file.
- Any non-obvious decision should add an entry in **Decision log**.

---

## Deployment
- **Environments**: dev (local) / prod (Vercel)
- **Where hosted**: Vercel
- **CI/CD**: Vercel GitHub integration

### Deploy steps (copy/paste)
```bash
# 1) Push to GitHub
# 2) Import the repo in Vercel
# 3) Add env vars from .env.example in Vercel Project Settings
# 4) Deploy
```

### Rollback steps
```bash
# Put rollback steps here.
```

---

## Troubleshooting
### Common issues
- **Problem**:
  - **Symptoms**:
  - **Fix**:

### Reset local environment
```bash
# Put “nuke and pave” steps here (safe + explicit).
```

---

## Decision log
Add short entries when you choose an approach/tool that future-you might question.

- **2026-02-10** — Stack + content + payments decisions
  - **Context**: Build a Vercel-deployable marketing site quickly with SEO-friendly content and payments.
  - **Decision**: Next.js App Router + Tailwind + shadcn/ui, MDX content in-repo, Stripe Checkout for one-time tier purchases.
  - **Alternatives considered**: CMS for content; subscriptions; embedded Stripe Elements.
  - **Consequences**: Simple MVP, easy GitHub/Vercel deploy; can migrate content to CMS later if needed.

---

## Links
- **Product/spec**:
- **Design**: Design system = shadcn/ui + Tailwind CSS
- **Project board**:
- **Staging**:
- **Production**:
- **Monitoring/logs**:

