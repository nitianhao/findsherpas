/**
 * enrichCrmWaterfall.ts
 *
 * Enrich CRM contacts using the configurable provider WATERFALL
 * (existing CRM email → Hunter → Prospeo → Findymail → Dropcontact → Apollo).
 * Writes the chosen email AND full provenance into structured contact fields:
 *   email_status, email_source, email_provider, email_confidence,
 *   email_verified_at, enriched_at, enrichment_source_url, company_domain.
 *
 * CONSERVATIVE GDPR RULES (enforced here):
 *   - A contact is only enriched if it has a business_relevance_reason
 *     (or you pass --reason "<text>" to apply one to the whole run).
 *   - Opted-out / unsubscribed contacts are skipped.
 *   - Guessed/risky emails are stored with their true status — they are NOT
 *     marked verified and the outreach guard will refuse to send them.
 *
 * Usage:
 *   npm run enrichment:crm-waterfall -- --dry-run
 *   npm run enrichment:crm-waterfall -- --limit 25
 *   npm run enrichment:crm-waterfall -- --reason "Ecommerce search prospect" --limit 50
 *   npm run enrichment:crm-waterfall -- --reverify   # re-check existing emails
 */

import { init } from '@instantdb/admin';
import * as dotenv from 'dotenv';
import * as path from 'path';
import { runEmailWaterfall } from '../providers/waterfall';
import { resolveProviders } from '../providers/registry';
import { extractDomain } from '../email/emailUtils';
import type { EmailStatus } from '../email/emailQuality';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
});

const args = process.argv.slice(2);
function arg(name: string): string | undefined {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
}
const DRY = args.includes('--dry-run');
const REVERIFY = args.includes('--reverify');
const LIMIT = arg('limit') ? parseInt(arg('limit')!, 10) : Infinity;
const RUN_REASON = arg('reason');

function nowIso() { return new Date().toISOString(); }

async function main() {
  const providers = resolveProviders();
  if (providers.length === 0) {
    console.error('No enabled providers. Set at least one provider API key (e.g. HUNTER_API_KEY).');
    process.exit(1);
  }
  console.log(`Waterfall order: ${providers.map((p) => p.name).join(' → ')}`);
  console.log(`${DRY ? 'DRY RUN — no writes. ' : ''}${REVERIFY ? 'Re-verifying existing emails. ' : ''}\n`);

  const { contacts } = await db.query({ contacts: { company: {} } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const all = contacts as any[];

  // Build a credit-free pool of known emails per company domain (from existing
  // CRM contacts). The inference fallback uses these to learn the domain's
  // pattern when no paid provider has credits.
  const knownByDomain = new Map<string, Set<string>>();
  for (const c of all) {
    const email = c.email && String(c.email).trim().toLowerCase();
    if (!email || !email.includes('@')) continue;
    const dom = email.split('@')[1];
    if (!knownByDomain.has(dom)) knownByDomain.set(dom, new Set());
    knownByDomain.get(dom)!.add(email);
  }

  let processed = 0, written = 0, skipped = 0;
  for (const c of all) {
    if (processed >= LIMIT) { console.log('Reached --limit'); break; }

    // GDPR: skip opted-out / unsubscribed.
    if (c.opt_out === 1 || c.status === 'unsubscribed' || c.status === 'bounced') {
      continue;
    }
    // GDPR: require a business relevance reason.
    const relevance = c.business_relevance_reason ?? RUN_REASON;
    if (!relevance) {
      skipped++;
      continue;
    }
    // Skip if already has a verified email and we're not re-verifying.
    const hasEmail = c.email && String(c.email).trim();
    if (hasEmail && c.email_status === 'verified' && !REVERIFY) continue;
    if (hasEmail && !REVERIFY && !c.email_status) continue; // legacy email, leave alone

    const company = c.company?.[0];
    const domain = company?.website ? extractDomain(company.website) : (c.company_domain ?? '');
    if (!domain) { continue; }

    processed++;
    process.stdout.write(`[${processed}] ${c.name} @ ${domain} → `);

    // Known emails on this domain, excluding the contact's own (if any).
    const known = [...(knownByDomain.get(domain) ?? [])].filter(
      (e) => !hasEmail || e !== String(c.email).trim().toLowerCase(),
    );

    const result = await runEmailWaterfall({
      fullName: c.name,
      role: c.role ?? undefined,
      companyName: company?.name,
      companyDomain: domain,
      existingEmail: hasEmail ? c.email : null,
      existingStatus: (c.email_status as EmailStatus | undefined) ?? null,
      knownDomainEmails: known,
    });

    console.log(`${result.email ?? '(none)'} [${result.status}] via ${result.source}`);

    if (!result.email) { continue; }

    written++;
    if (!DRY) {
      await db.transact(
        db.tx.contacts[c.id].update({
          email: result.email,
          email_status: result.status,
          email_source: result.source,
          email_provider: result.provider ?? '',
          email_confidence: result.confidence ?? 0,
          email_verified_at: result.verifiedAt ?? '',
          enriched_at: nowIso(),
          enrichment_source_url: result.sourceUrl ?? '',
          company_domain: domain,
          business_relevance_reason: relevance,
          updated_at: nowIso(),
        })
      );
    }
  }

  console.log(`\nDone. Processed: ${processed}, emails written: ${written}, skipped (no relevance reason): ${skipped}`);
  if (skipped > 0) {
    console.log('Tip: set business_relevance_reason per contact, or pass --reason "<why>" to enrich the run.');
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
