/**
 * writeAuditToCRM.ts
 *
 * Reads a Find Sherpas _data.json audit report and writes the key
 * personalization variables to the matching CRM company record.
 *
 * Audit variables live at the COMPANY level (one audit per company, shared
 * across all contacts at that company) and are merged into email templates
 * via lib/crm/template.ts at send time.
 *
 * Usage:
 *   npx tsx src/enrichment/scripts/writeAuditToCRM.ts \
 *     --company-id <instantdb-company-id> \
 *     --report <path/to/_data.json> \
 *     --report-url <https://findsherpas.com/report/company/>
 *
 * Dry-run (print extracted vars without writing):
 *   npx tsx src/enrichment/scripts/writeAuditToCRM.ts \
 *     --report <path/to/_data.json> \
 *     --dry-run
 *
 * Fields written to the company:
 *   audit_score         — Search Quality Score, 0-100                  → {{score}}
 *   audit_query_count   — number of tested customer queries             → {{query_count}}
 *   audit_cap_count     — number of CRITICAL capability failures       → {{cap_count}}
 *   audit_outside3rate  — % of queries where best result is NOT top 3  → {{outside3rate}}
 *   audit_top3rate      — % of queries where best result IS top 3      → {{top3rate}}
 *   audit_worst_query   — query string with the highest displacement   → {{worst_query}}
 *   audit_worst_pos     — 1-indexed pos of best result for worst query → {{worst_pos}}
 *   audit_wrong_product — title of result at position #1 for that q    → {{wrong_product}}
 *   report_url          — live unlisted report URL                      → {{report_url}}
 *   audit_run_at        — ISO timestamp of when this write happened
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
  severity: string;
  evidence: string;
  recommended_fix: string;
  displacement: number;
  max_relevance_score: number;
}

interface CapabilityScore {
  capability: string;
  severity: string;
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
// Extraction
// ---------------------------------------------------------------------------

interface AuditVars {
  score: string;
  query_count: string;
  cap_count: string;
  outside3rate: string;
  top3rate: string;
  worst_query: string;
  worst_pos: string;
  wrong_product: string;
}

function extractVars(report: AuditReport): AuditVars {
  const capabilities = report.capability_scores;

  const critical = capabilities.filter(c =>
    c.severity.toLowerCase().startsWith('critical')
  ).length;

  const allJudgments: Judgment[] = capabilities.flatMap(c => c.judgments);
  if (allJudgments.length === 0) {
    throw new Error('No judgments found in report — is this a complete audit?');
  }

  const outsideTop3 = allJudgments.filter(j => j.displacement > 2).length;
  const outside3rate = Math.round((outsideTop3 / allJudgments.length) * 100);
  const top3rate = 100 - outside3rate;

  const withResults = allJudgments.filter(j => j.results.length > 0);
  const pool = withResults.length > 0 ? withResults : allJudgments;
  const worst = pool.reduce((a, b) => (b.displacement > a.displacement ? b : a));

  const worstPos = worst.displacement + 1;

  const sortedByOriginal = [...worst.results].sort(
    (a, b) => a.original_rank - b.original_rank
  );
  const wrongProduct = sortedByOriginal[0]?.title ?? 'n/a';

  return {
    score: String(computeSearchQualityScore(allJudgments)),
    query_count: String(allJudgments.length),
    cap_count: String(critical),
    outside3rate: String(outside3rate),
    top3rate: String(top3rate),
    worst_query: worst.test_query.query,
    worst_pos: String(worstPos),
    wrong_product: wrongProduct,
  };
}

function byOriginalRank(judgment: Judgment): ScoredResult[] {
  return [...judgment.results].sort((a, b) => a.original_rank - b.original_rank);
}

function computeSearchQualityScore(judgments: Judgment[]): number {
  if (judgments.length === 0) return 0;

  const withResults = judgments.filter(j => j.results.length > 0);

  const trustFailures = judgments.filter(j => {
    const rankedResults = byOriginalRank(j);
    if (rankedResults.length === 0) return true;

    const topResult = rankedResults[0];
    const bestScore = Math.max(...rankedResults.map(r => r.relevance_score));

    return (
      topResult.relevance_score < 0.6 ||
      (bestScore - topResult.relevance_score >= 0.2 && j.displacement > 2)
    );
  }).length;

  const topResultTrust = (1 - trustFailures / judgments.length) * 100;
  const top3Findability =
    withResults.length > 0
      ? (withResults.filter(j => j.displacement <= 2).length / withResults.length) * 100
      : 0;

  const top3Rows = withResults.flatMap(j => byOriginalRank(j).slice(0, 3));
  const resultSetPurity =
    top3Rows.length > 0
      ? (top3Rows.filter(r => r.relevance_score >= 0.6).length / top3Rows.length) * 100
      : 0;

  return Math.round(
    topResultTrust * 0.45 + top3Findability * 0.35 + resultSetPurity * 0.2
  );
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
    companyId: get('--company-id'),
    reportPath: get('--report'),
    reportUrl: get('--report-url'),
    dryRun: args.includes('--dry-run'),
  };
}

async function main() {
  const { companyId, reportPath, reportUrl, dryRun } = parseArgs();

  if (!reportPath) {
    console.error(
      'Usage: npx tsx writeAuditToCRM.ts --report <path> [--company-id <id>] [--dry-run]'
    );
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
  console.log(`  {{score}}         = ${vars.score} / 100 Search Quality Score`);
  console.log(`  {{query_count}}   = ${vars.query_count} tested customer queries`);
  console.log(`  {{cap_count}}     = ${vars.cap_count} critical capability failures`);
  console.log(`  {{top3rate}}      = ${vars.top3rate}%`);
  console.log(`  {{outside3rate}}  = ${vars.outside3rate}%`);
  console.log(`  {{worst_query}}   = "${vars.worst_query}"`);
  console.log(`  {{worst_pos}}     = #${vars.worst_pos}`);
  console.log(`  {{wrong_product}} = "${vars.wrong_product}"`);
  if (reportUrl) console.log(`  {{report_url}}    = ${reportUrl}`);

  if (dryRun || !companyId) {
    if (!companyId) {
      console.log('\n--company-id not provided. Use --dry-run to suppress this message.');
    }
    console.log('\nDry run — nothing written to CRM.');
    return;
  }

  const db = init({
    appId: process.env.NEXT_PUBLIC_INSTANT_APP_ID!,
    adminToken: process.env.INSTANT_APP_ADMIN_TOKEN!,
  });

  const data = await db.query({ companies: { $: { where: { id: companyId } } } });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const company = (data.companies as any[])[0];
  if (!company) {
    console.error(`Company not found: ${companyId}`);
    process.exit(1);
  }

  const now = new Date().toISOString();
  await db.transact(
    db.tx.companies[companyId].update({
      audit_score: vars.score,
      audit_query_count: vars.query_count,
      audit_cap_count: vars.cap_count,
      audit_top3rate: vars.top3rate,
      audit_outside3rate: vars.outside3rate,
      audit_worst_query: vars.worst_query,
      audit_worst_pos: vars.worst_pos,
      audit_wrong_product: vars.wrong_product,
      ...(reportUrl ? { report_url: reportUrl } : {}),
      audit_run_at: now,
      updated_at: now,
    })
  );

  console.log(`\nWritten to company: ${company.name ?? companyId}`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
