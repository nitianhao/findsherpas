/**
 * compareProviders.ts
 *
 * Provider comparison / test mode. Runs EACH enabled provider INDEPENDENTLY
 * (not as a waterfall) against a sample of CRM contacts, then reports a table
 * so you can decide — with data — which provider gives the best usable verified
 * coverage before paying for any of them.
 *
 * Sampling: contacts that have a NAME and a resolvable company DOMAIN. By
 * default it samples contacts WITHOUT an email (the realistic enrichment
 * target); pass --all to include everyone.
 *
 * Usage:
 *   npm run enrichment:compare-providers                 # 100 contacts, no-email
 *   npm run enrichment:compare-providers -- --limit 50
 *   npm run enrichment:compare-providers -- --all --limit 25
 *   npm run enrichment:compare-providers -- --providers hunter,apollo
 *   add --allow-role-inboxes to permit info@/sales@ in the gate
 *
 * Output: reports/provider-comparison-<timestamp>.csv and .md
 */

import { init } from '@instantdb/admin';
import * as dotenv from 'dotenv';
import * as path from 'path';
import * as fs from 'fs';
import { PROVIDER_REGISTRY, resolveProviders } from '../providers/registry';
import type { EmailEnrichmentProvider, EnrichmentInput, ProviderName, ProviderEmailResult } from '../providers/types';
import { extractDomain } from '../email/emailUtils';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
});

// ---- args -----------------------------------------------------------------
const args = process.argv.slice(2);
function arg(name: string): string | undefined {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
}
const LIMIT = arg('limit') ? parseInt(arg('limit')!, 10) : 100;
const INCLUDE_ALL = args.includes('--all');
const ALLOW_ROLE = args.includes('--allow-role-inboxes');
const ONLY = arg('providers')?.split(',').map((s) => s.trim().toLowerCase()) as ProviderName[] | undefined;

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

interface Tally {
  attempted: number;
  found: number;
  verified: number;
  risky: number;
  invalid: number;
  personalRejected: number;
  roleRejected: number;
  errors: number;
  creditsUsed: number;
}

function newTally(): Tally {
  return { attempted: 0, found: 0, verified: 0, risky: 0, invalid: 0, personalRejected: 0, roleRejected: 0, errors: 0, creditsUsed: 0 };
}

function record(t: Tally, r: ProviderEmailResult) {
  t.attempted++;
  t.creditsUsed += r.creditsUsed;
  if (r.outcome === 'error') t.errors++;
  if (r.outcome === 'found') t.found++;
  if (r.status === 'verified') t.verified++;
  if (r.status === 'risky') t.risky++;
  if (r.status === 'invalid') t.invalid++;
  if (r.reasons.some((x) => x.includes('PERSONAL_DOMAIN'))) t.personalRejected++;
  if (r.reasons.some((x) => x.includes('ROLE_INBOX'))) t.roleRejected++;
}

function usableRate(t: Tally): string {
  if (t.attempted === 0) return '0.0%';
  return ((t.verified / t.attempted) * 100).toFixed(1) + '%';
}

async function main() {
  // Resolve providers to compare.
  let providers: EmailEnrichmentProvider[];
  if (ONLY) {
    providers = ONLY.map((n) => PROVIDER_REGISTRY[n]).filter(Boolean).filter((p) => p.isEnabled());
  } else {
    providers = resolveProviders();
  }

  if (providers.length === 0) {
    console.error('No enabled providers. Set at least one provider API key (e.g. HUNTER_API_KEY).');
    process.exit(1);
  }
  console.log(`Comparing providers: ${providers.map((p) => p.name).join(', ')}`);
  console.log(`Role inboxes ${ALLOW_ROLE ? 'ALLOWED' : 'rejected'} | sample mode: ${INCLUDE_ALL ? 'all' : 'no-email only'}\n`);

  // Build the sample.
  const { contacts } = await db.query({ contacts: { company: {} } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sample = (contacts as any[])
    .filter((c) => c.name && String(c.name).trim())
    .filter((c) => INCLUDE_ALL || !c.email || String(c.email).trim() === '')
    .map((c) => {
      const company = c.company?.[0];
      const domain = company?.website ? extractDomain(company.website) : (c.company_domain ?? '');
      return { contact: c, companyName: company?.name ?? '', domain };
    })
    .filter((x) => x.domain)
    .slice(0, LIMIT);

  console.log(`Sample size: ${sample.length} contacts\n`);
  if (sample.length === 0) { console.log('Nothing to compare.'); return; }

  const tallies: Record<string, Tally> = {};
  for (const p of providers) tallies[p.name] = newTally();

  let i = 0;
  for (const row of sample) {
    i++;
    const input: EnrichmentInput = {
      fullName: row.contact.name,
      role: row.contact.role ?? undefined,
      companyName: row.companyName,
      companyDomain: row.domain,
    };
    process.stdout.write(`[${i}/${sample.length}] ${row.contact.name} @ ${row.domain}\n`);
    for (const p of providers) {
      const r = await p.findEmail(input, { allowRoleInboxes: ALLOW_ROLE });
      record(tallies[p.name], r);
      console.log(`    ${p.name.padEnd(12)} ${r.outcome.padEnd(10)} ${r.status.padEnd(11)} ${r.email ?? ''}`);
      await sleep(400); // be gentle with rate limits
    }
  }

  // ---- build report -------------------------------------------------------
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const header = ['provider', 'attempted', 'found', 'verified', 'risky', 'invalid', 'personal_rejected', 'role_rejected', 'errors', 'credits_used', 'usable_rate'];
  const rows = providers.map((p) => {
    const t = tallies[p.name];
    return [p.name, t.attempted, t.found, t.verified, t.risky, t.invalid, t.personalRejected, t.roleRejected, t.errors, t.creditsUsed, usableRate(t)];
  });

  const reportsDir = path.resolve(process.cwd(), 'reports');
  fs.mkdirSync(reportsDir, { recursive: true });

  const csv = [header.join(','), ...rows.map((r) => r.join(','))].join('\n');
  const csvPath = path.join(reportsDir, `provider-comparison-${ts}.csv`);
  fs.writeFileSync(csvPath, csv);

  const md = [
    `# Provider comparison — ${new Date().toISOString().slice(0, 10)}`,
    '',
    `Sample: **${sample.length}** contacts (${INCLUDE_ALL ? 'all' : 'no-email only'}). Role inboxes: ${ALLOW_ROLE ? 'allowed' : 'rejected'}.`,
    '',
    '| ' + header.join(' | ') + ' |',
    '| ' + header.map(() => '---').join(' | ') + ' |',
    ...rows.map((r) => '| ' + r.join(' | ') + ' |'),
    '',
    '**usable_rate = verified / attempted.** Only `verified` emails are eligible for outreach.',
    '',
    '> Pay for a provider only when this table shows it beats the alternatives on usable verified coverage for your sample.',
  ].join('\n');
  const mdPath = path.join(reportsDir, `provider-comparison-${ts}.md`);
  fs.writeFileSync(mdPath, md);

  console.log('\n' + md);
  console.log(`\nSaved:\n  ${csvPath}\n  ${mdPath}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
