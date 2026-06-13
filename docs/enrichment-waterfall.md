# Email enrichment waterfall

How Find Sherpas finds, verifies, and stores contact emails — safely, cheaply,
and without hard-coding Hunter as the only source.

## TL;DR

- Email sources are **pluggable providers** behind one interface. Hunter is
  just one of them.
- Enrichment runs as a **waterfall**: existing CRM email → Hunter → Prospeo →
  Findymail → Dropcontact → Apollo. Order is env-configurable.
- Every email gets a **status**: `verified | risky | guessed | invalid | unavailable`.
  **Only `verified` is sent.** Guessed/risky emails are stored but never auto-emailed.
- A **send-time guard** blocks opted-out, bounced, and non-verified contacts —
  even on a direct send.

## Recommended provider waterfall

```
existing CRM email (valid) → Hunter → Prospeo / Findymail → Dropcontact → Apollo → manual review
```

1. **Existing CRM email** — if present and passes the quality gate, keep it.
   No credits spent. (If it's already `verified`, we short-circuit immediately.)
2. **Hunter** — domain pattern discovery + email-finder + verifier. Free tier
   friendly. Used as a source, not the source.
3. **Prospeo / Findymail** — live alternative finders. Good cheap second opinions.
4. **Dropcontact** — EU/GDPR-friendly enrichment (async: posts then polls).
5. **Apollo** — limited free reveals.
6. **Inference** — **credit-free last resort.** If no paid provider has credits
   (or none verified), guess the address from the company's known email pattern.
   Always produces `guessed` → never auto-sent.

### Credit-aware behaviour

This is the rule you asked for, enforced in [waterfall.ts](../src/enrichment/providers/waterfall.ts):

- The waterfall **stops at the first provider that returns a `verified` email** —
  so once one finds the contact, the others are **not called** and their credits
  are not spent.
- If a provider is **out of credits/quota** (Prospeo `INSUFFICIENT_CREDITS`,
  Findymail `402`, Dropcontact `403`), it returns an error and the waterfall
  **moves on to the next provider** automatically.
- If **every paid provider is exhausted or finds nothing**, the **inference**
  step runs (free) and returns a `guessed` address — visible in the CRM but
  blocked from outreach until verified.
- A provider returning a `not found` (it has credits, just no result) does not
  stop the chain — we keep trying so the contact can still be found elsewhere.

## Configuration (env)

| Variable | Purpose | Default |
|---|---|---|
| `HUNTER_API_KEY` | Enable Hunter | — |
| `PROSPEO_API_KEY` | Enable Prospeo (stub) | — |
| `FINDYMAIL_API_KEY` | Enable Findymail (stub) | — |
| `DROPCONTACT_API_KEY` | Enable Dropcontact (stub) | — |
| `APOLLO_API_KEY` | Enable Apollo | — |
| `ENRICHMENT_PROVIDER_ORDER` | Waterfall order, comma list | `hunter,prospeo,findymail,dropcontact,apollo` |
| `ENRICHMENT_ALLOW_ROLE_INBOXES` | Allow `info@`/`sales@`/`support@` | `false` |
| `ENRICHMENT_ACCEPT_STATUSES` | Statuses that stop the waterfall | `verified` |
| `ENRICHMENT_REVERIFY_EXISTING` | Re-verify existing CRM emails | `false` |

**A provider with no API key is disabled** and silently skipped (the comparison
tool reports it as `disabled`). Hunter, Prospeo, Findymail, Dropcontact and
Apollo are all live adapters — add a key to enable each. The `inference`
provider needs no key and is always available as the final fallback.

## Email quality rules

Defined once in [`src/enrichment/email/emailQuality.ts`](../src/enrichment/email/emailQuality.ts)
and [`emailUtils.ts`](../src/enrichment/email/emailUtils.ts):

- **Free/personal domains rejected** — Gmail, Yahoo, Outlook, iCloud, Proton,
  and regional providers including **Seznam, email.cz, centrum.cz, atlas.cz,
  zoznam.sk**, etc. → `invalid`.
- **Role inboxes rejected by default** — `info@`, `sales@`, `support@`,
  `kontakt@`, … Allow them only with `ENRICHMENT_ALLOW_ROLE_INBOXES=true`.
- **Verification beats guessing** — a verifier "valid" → `verified`;
  accept-all/unknown → `risky`; undeliverable → `invalid`.
- **Guessed emails are never `verified`** unless a verifier explicitly confirms
  them. A pattern-inferred address stays `guessed` and is not sent.
- **High provider confidence alone is still `risky`** — we never auto-send an
  address we didn't confirm.

### Status → outreach eligibility

| Status | Meaning | Auto-send? |
|---|---|---|
| `verified` | Verifier confirmed deliverable | ✅ yes |
| `risky` | Found but unconfirmed (accept-all/unverified) | ❌ no — manual review |
| `guessed` | Pattern-inferred, never confirmed | ❌ no |
| `invalid` | Undeliverable / personal / role inbox | ❌ no |
| `unavailable` | No email found | ❌ no |

## GDPR & opt-out rules

Enforced in [`lib/crm/outreach-guard.ts`](../lib/crm/outreach-guard.ts) and the
enrichment script:

- **Business relevance required.** `enrichCrmWaterfall` skips any contact with no
  `business_relevance_reason` (pass `--reason "<why>"` to apply one to a run).
  We do not enrich irrelevant contacts "just in case."
- **Opt-out is global.** Unsubscribing sets `status = unsubscribed`, `opt_out = 1`,
  `opt_out_at`, and pauses active enrollments. The send guard and the daily task
  query both refuse opted-out/bounced contacts.
- **No sending unverified addresses.** The send route and task queue both call
  the outreach guard; only `verified` (or legacy pre-field) contacts pass.
- **Defense in depth.** The guard runs at the actual send point, so even a
  direct "send event by id" cannot leak past opt-out / quality rules.

### Provenance stored on each contact

`email_status`, `email_source`, `email_provider`, `email_confidence`,
`email_verified_at`, `enriched_at`, `enrichment_source_url`, `company_domain`,
`business_relevance_reason`, `opt_out`, `opt_out_at`, `last_contacted_at`.
(Schema: [`instant.schema.ts`](../instant.schema.ts), all additive/optional.)

## Running a 100-contact provider test

Compare providers **before** paying for any of them:

```bash
# 100 contacts that currently have no email, each run through every enabled provider
npm run enrichment:compare-providers

# smaller sample / specific providers / include contacts that already have an email
npm run enrichment:compare-providers -- --limit 50
npm run enrichment:compare-providers -- --providers hunter,apollo
npm run enrichment:compare-providers -- --all --limit 25
```

Output (saved to `reports/provider-comparison-<timestamp>.{csv,md}`):

| provider | attempted | found | verified | risky | invalid | personal_rejected | role_rejected | errors | credits_used | usable_rate |
|---|---|---|---|---|---|---|---|---|---|---|

`usable_rate = verified / attempted`.

### When to pay for Hunter (or any provider)

Pay **only after** a ~100-contact test shows the provider gives a meaningfully
higher **usable_rate** (verified coverage) than the alternatives for *your*
prospect list — not on reputation. If two providers tie on usable rate, prefer
the cheaper / more GDPR-friendly one (Dropcontact is EU-based).

## Writing enriched emails into the CRM

```bash
npm run enrichment:crm-waterfall -- --dry-run                 # preview, no writes
npm run enrichment:crm-waterfall -- --limit 25
npm run enrichment:crm-waterfall -- --reason "Ecommerce site-search prospect"
npm run enrichment:crm-waterfall -- --reverify                # re-check existing emails
```

This stores the chosen email **with its true status**. A `guessed`/`risky`
result is saved for visibility but the outreach guard will not send it.

## Tests

```bash
npm test
```

Covers: personal/role domain filtering, the status taxonomy, waterfall ordering
& stop conditions, existing-email short-circuit, guessed-email exclusion,
provenance capture, and opt-out / non-verified send exclusion.

## What was intentionally left alone

- The **workbook enrichment pipeline** (`src/enrichment/{discovery,search,
  resolution,quality,writeback}`) still works as before. It already has its own
  conservative confidence model; we did not reroute it through the waterfall.
- Existing Hunter/Apollo scripts (`enrichCrmHunter`, `runApolloEnrichment`)
  remain for backward compatibility. New work should prefer the waterfall.
- Legacy contacts with an email but no `email_status` are still allowed to send
  (so current sequences don't break); they're reported as `OK_LEGACY_UNVERIFIED`.
```
