/**
 * enrichCrmHunter.ts
 *
 * Enrich CRM contacts (InstantDB) with emails from Hunter.io, spending the
 * free-plan search credits efficiently.
 *
 * Phase 1 — Email Finder for existing contacts that have a NAME but NO EMAIL.
 *           (highest value: named decision-makers, ~1 credit each)
 * Phase 2 — Domain Search for companies that have ZERO contacts. Discovered
 *           PERSONAL emails are added as new contacts (generic role mailboxes
 *           are skipped). Companies are processed in --companies order, else
 *           by missing-contact priority. Blacks is forced first.
 *
 * Every written email is verified via Hunter Email Verifier (separate credit
 * pool, 100/mo) and the deliverability status stored in the contact notes.
 *
 * Stops automatically when search credits are (nearly) exhausted.
 *
 * Usage:
 *   npx tsx src/enrichment/scripts/enrichCrmHunter.ts --phase 1
 *   npx tsx src/enrichment/scripts/enrichCrmHunter.ts --phase 2 --max 10
 *   npx tsx src/enrichment/scripts/enrichCrmHunter.ts --phase 2 --companies Blacks
 *   add --dry-run to avoid writing to the CRM
 */

import { init, id } from '@instantdb/admin';
import * as dotenv from 'dotenv';
import * as path from 'path';
import {
  findEmail,
  searchDomain,
  parseName,
} from '../email/hunterAdapter';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const db = init({
  appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
  adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
});

const HUNTER_KEY = process.env.HUNTER_API_KEY!;
const RESERVE = 1; // leave a small buffer of search credits

// ---- args -----------------------------------------------------------------
const args = process.argv.slice(2);
function arg(name: string): string | undefined {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : undefined;
}
const PHASE = arg('phase') ?? '1';
const MAX = arg('max') ? parseInt(arg('max')!, 10) : Infinity;
const DRY = args.includes('--dry-run');
const COMPANIES = arg('companies')?.split(',').map((s) => s.trim().toLowerCase());

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }
function nowIso() { return new Date().toISOString(); }
function domainOf(url?: string | null): string | null {
  if (!url) return null;
  try {
    const u = new URL(url.startsWith('http') ? url : `https://${url}`);
    return u.hostname.replace(/^www\./, '').toLowerCase();
  } catch { return null; }
}

async function creditsLeft(): Promise<number> {
  const r = await fetch(`https://api.hunter.io/v2/account?api_key=${HUNTER_KEY}`);
  const j: any = await r.json();
  return j?.data?.requests?.searches?.available - j?.data?.requests?.searches?.used;
}

async function verify(email: string): Promise<string> {
  try {
    const r = await fetch(`https://api.hunter.io/v2/email-verifier?email=${encodeURIComponent(email)}&api_key=${HUNTER_KEY}`);
    const j: any = await r.json();
    return j?.data?.status ?? 'unknown';
  } catch { return 'unknown'; }
}

// ---------------------------------------------------------------------------
async function phase1() {
  const { contacts } = await db.query({ contacts: { company: {} } });
  const targets = contacts.filter(
    (c: any) => (!c.email || String(c.email).trim() === '') && c.name && c.name.trim()
  );
  console.log(`Phase 1 — ${targets.length} contacts with name but no email\n`);

  let used = 0, found = 0;
  for (const c of targets as any[]) {
    if (used >= MAX) { console.log('Reached --max'); break; }
    const left = await creditsLeft();
    if (left <= RESERVE) { console.log(`Stopping — ${left} search credits left`); break; }

    const comp = c.company?.[0];
    const domain = domainOf(comp?.website);
    if (!domain) { console.log(`SKIP  ${c.name} (${comp?.name ?? '?'}) — no domain`); continue; }

    const { firstName, lastName } = parseName(c.name);
    process.stdout.write(`[${left} left] ${c.name} @ ${domain} → `);
    const res = await findEmail(domain, firstName, lastName);
    used++;
    await sleep(1200);

    if (res.status === 'found' && res.email) {
      const vstatus = await verify(res.email);
      await sleep(800);
      console.log(`${res.email} (score ${res.score}, verify ${vstatus})`);
      found++;
      if (!DRY) {
        await db.transact(
          db.tx.contacts[c.id].update({
            email: res.email,
            updated_at: nowIso(),
            notes: `${c.notes ? c.notes + ' | ' : ''}Hunter email-finder score ${res.score}, verify=${vstatus} (${nowIso().slice(0,10)})`,
          })
        );
      }
    } else {
      console.log(res.status === 'not_found' ? 'not found' : `error: ${res.errorMessage}`);
    }
  }
  console.log(`\nPhase 1 done. Searches used: ${used}, emails written: ${found}`);
}

// ---------------------------------------------------------------------------
const GENERIC_PREFIXES = ['info','contact','hello','support','sales','customercare','customer.service','customerservice','help','admin','office','enquiries','press','marketing','team','service','care','orders'];
function isGeneric(value: string, type: string): boolean {
  if (type === 'generic') return true;
  const local = value.split('@')[0].toLowerCase();
  return GENERIC_PREFIXES.some((p) => local === p || local.startsWith(p));
}

async function phase2() {
  const { companies } = await db.query({ companies: { contacts: {} } });
  let pool = companies.filter((c: any) => c.contacts.length === 0 && domainOf(c.website));

  if (COMPANIES) {
    pool = pool.filter((c: any) => COMPANIES.includes(c.name.toLowerCase()));
  } else {
    // Blacks first, then alphabetical
    pool.sort((a: any, b: any) => {
      if (a.name === 'Blacks') return -1;
      if (b.name === 'Blacks') return 1;
      return a.name.localeCompare(b.name);
    });
  }
  console.log(`Phase 2 — ${pool.length} companies without contacts (domain known)\n`);

  let used = 0, added = 0, companiesDone = 0;
  for (const comp of pool as any[]) {
    if (companiesDone >= MAX) { console.log('Reached --max companies'); break; }
    const left = await creditsLeft();
    if (left <= RESERVE) { console.log(`Stopping — ${left} search credits left`); break; }

    const domain = domainOf(comp.website)!;
    process.stdout.write(`[${left} left] ${comp.name} @ ${domain} → `);
    const ds = await searchDomain(domain, 10);
    used++; companiesDone++;
    await sleep(1200);

    if (ds.status !== 'found') { console.log(ds.status); continue; }
    const personal = ds.emails.filter((e) => !isGeneric(e.value, e.type) && e.firstName);
    console.log(`${ds.emails.length} emails, ${personal.length} personal`);

    for (const e of personal) {
      const vstatus = await verify(e.value);
      await sleep(800);
      const fullName = [e.firstName, e.lastName].filter(Boolean).join(' ').trim() || e.value.split('@')[0];
      console.log(`    + ${fullName} <${e.value}> ${e.position ?? '(role?)'} conf ${e.confidence} verify ${vstatus}`);
      added++;
      if (!DRY) {
        const cid = id();
        await db.transact([
          db.tx.contacts[cid].update({
            name: fullName,
            email: e.value,
            role: e.position ?? '',
            linkedin_url: e.linkedinUrl ?? '',
            phone: '',
            status: 'prospect',
            notes: `Hunter domain-search conf ${e.confidence}, verify=${vstatus} (${nowIso().slice(0,10)})`,
            created_at: nowIso(),
            updated_at: nowIso(),
          }).link({ company: comp.id }),
        ]);
      }
    }
  }
  console.log(`\nPhase 2 done. Searches used: ${used}, companies: ${companiesDone}, contacts added: ${added}`);
}

async function main() {
  const left = await creditsLeft();
  console.log(`Hunter search credits available: ${left}\n`);
  if (PHASE === '1') await phase1();
  else if (PHASE === '2') await phase2();
  const after = await creditsLeft();
  console.log(`\nSearch credits remaining: ${after}`);
}
main().catch((e) => { console.error(e); process.exit(1); });
