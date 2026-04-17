/**
 * writeAuditToCRM.ts
 *
 * Reads a Synthetic Search _data.json audit report and writes the 6 key
 * personalization variables to the matching CRM contact's custom_fields.
 *
 * Usage:
 *   npx tsx src/enrichment/scripts/writeAuditToCRM.ts \
 *     --contact-id <instantdb-contact-id> \
 *     --report <path/to/_data.json>
 *
 * Or to dry-run (print extracted vars without writing to CRM):
 *   npx tsx src/enrichment/scripts/writeAuditToCRM.ts \
 *     --report <path/to/_data.json> \
 *     --dry-run
 *
 * Variables written to custom_fields:
 *   score         — number of capabilities passing (e.g. "2")          → used as {{score}} in emails
 *   cap_count     — number of CRITICAL capability failures               → {{cap_count}}
 *   outside3rate  — % of queries where best result is NOT in top 3      → {{outside3rate}}
 *   top3rate      — % of queries where best result IS in top 3          → {{top3rate}}
 *   worst_query   — query string with the highest displacement           → {{worst_query}}
 *   worst_pos     — 1-indexed position of best result for worst query   → {{worst_pos}}
 *   wrong_product — title of result at position #1 for worst query      → {{wrong_product}}
 */

import * as fs from 'fs';
import * as path from 'path';
import { init } from '@instantdb/admin';
import * as dotenv from 'dotenv';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

// ---------------------------------------------------------------------------
// Types (mirroring the Python Pydantic models)
// ---------------------------------------------------------------------------

interface ScoredResult {
  rank: number;
  title: string;
  price: string | null;
  snippet: string | null;
  url: string;
  relevance_score: number;
  original_rank: number;
}

interface Judgment {
  test_query: { category: string; query: string; rationale: string };
  results: ScoredResult[];
  failure_mode: string;
  severity: string;         // e.g. "Critical — ...", "Moderate — ...", "Pass"
  evidence: string;
  recommended_fix: string;
  displacement: number;
  max_relevance_score: number;
}

interface CapabilityScore {
  capability: string;
  severity: string;         // same format as judgment severity
  summary: string;
  judgments: Judgment[];
}

interface AuditReport {
  site_context: { url: string; site_name: string };
  selected_categories: string[];
  queries: unknown[];
  capability_scores: CapabilityScore[];
}

// ---------------------------------------------------------------------------
// Extraction logic
// ---------------------------------------------------------------------------

interface AuditVars {
  score: string;        // "2" (capabilities passing out of 6)
  cap_count: string;    // "3" (critical capability failures)
  outside3rate: string; // "62" (% as integer string, no % sign)
  top3rate: string;     // "38"
  worst_query: string;  // "waterproof jacket"
  worst_pos: string;    // "15"
  wrong_product: string; // "Adidas Performance ULTRABOOST 5"
}

function extractVars(report: AuditReport): AuditVars {
  const capabilities = report.capability_scores;

  // score: capabilities where severity starts with "Pass" (case-insensitive)
  const passing = capabilities.filter(c =>
    c.severity.toLowerCase().startsWith('pass')
  ).length;

  // cap_count: capabilities where severity starts with "Critical"
  const critical = capabilities.filter(c =>
    c.severity.toLowerCase().startsWith('critical')
  ).length;

  // Flatten all judgments across all capabilities
  const allJudgments: Judgment[] = capabilities.flatMap(c => c.judgments);

  if (allJudgments.length === 0) {
    throw new Error('No judgments found in report — is this a complete audit?');
  }

  // outside3rate / top3rate: displacement > 2 means best result is NOT in top 3
  const outsideTop3 = allJudgments.filter(j => j.displacement > 2).length;
  const outside3rate = Math.round((outsideTop3 / allJudgments.length) * 100);
  const top3rate = 100 - outside3rate;

  // worst_query: judgment with highest displacement that has actual results
  // (some queries produce zero results — skip those for wrong_product extraction)
  const withResults = allJudgments.filter(j => j.results.length > 0);
  const pool = withResults.length > 0 ? withResults : allJudgments;
  const worst = pool.reduce((a, b) =>
    b.displacement > a.displacement ? b : a
  );

  const worstPos = worst.displacement + 1; // displacement is 0-indexed from position 1

  // wrong_product: title of result at position #1 in the original SERP for worst query
  // Results are stored by relevance order so we pick the one with lowest original_rank
  const sortedByOriginal = [...worst.results].sort((a, b) => a.original_rank - b.original_rank);
  const wrongProduct = sortedByOriginal[0]?.title ?? 'n/a';

  return {
    score: String(passing),
    cap_count: String(critical),
    outside3rate: String(outside3rate),
    top3rate: String(top3rate),
    worst_query: worst.test_query.query,
    worst_pos: String(worstPos),
    wrong_product: wrongProduct,
  };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const get = (flag: string) => {
    const i = args.indexOf(flag);
    return i !== -1 ? args[i + 1] : undefined;
  };
  return {
    contactId: get('--contact-id'),
    reportPath: get('--report'),
    dryRun: args.includes('--dry-run'),
  };
}

async function main() {
  const { contactId, reportPath, dryRun } = parseArgs();

  if (!reportPath) {
    console.error('Usage: npx tsx writeAuditToCRM.ts --report <path> [--contact-id <id>] [--dry-run]');
    process.exit(1);
  }

  const fullPath = path.resolve(reportPath);
  if (!fs.existsSync(fullPath)) {
    console.error(`File not found: ${fullPath}`);
    process.exit(1);
  }

  const raw = JSON.parse(fs.readFileSync(fullPath, 'utf-8')) as AuditReport;
  const vars = extractVars(raw);

  console.log('\nExtracted audit variables:');
  console.log(`  {{score}}         = ${vars.score} / 6 capabilities passing`);
  console.log(`  {{cap_count}}     = ${vars.cap_count} critical capability failures`);
  console.log(`  {{top3rate}}      = ${vars.top3rate}%`);
  console.log(`  {{outside3rate}}  = ${vars.outside3rate}%`);
  console.log(`  {{worst_query}}   = "${vars.worst_query}"`);
  console.log(`  {{worst_pos}}     = #${vars.worst_pos}`);
  console.log(`  {{wrong_product}} = "${vars.wrong_product}"`);

  if (dryRun || !contactId) {
    if (!contactId) console.log('\n--contact-id not provided. Use --dry-run to suppress this message.');
    console.log('\nDry run — nothing written to CRM.');
    return;
  }

  const db = init({
    appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
    adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
  });

  // Read existing custom_fields first so we don't overwrite unrelated keys
  const data = await db.query({ contacts: { $: { where: { id: contactId } } } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const contact = (data.contacts as any[])[0];
  if (!contact) {
    console.error(`Contact not found: ${contactId}`);
    process.exit(1);
  }

  const existing = (contact.custom_fields as Record<string, string> | null) ?? {};
  const merged = { ...existing, ...vars };

  await db.transact(
    db.tx.contacts[contactId].update({
      custom_fields: merged,
      updated_at: new Date().toISOString(),
    })
  );

  console.log(`\nWritten to contact: ${contact.name ?? contactId}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
