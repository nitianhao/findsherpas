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
  /** Self-contained sentence describing the single most damning failure. */
  worst_example: string;
  /** Diagnostic label for the chosen example (not written to CRM). */
  worst_failure_type: string;
}

// ---------------------------------------------------------------------------
// "Most damning example" selection
//
// Reusable across every audit. Instead of always picking the largest
// displacement (which can surface a trivially-weak example when many results
// have near-identical relevance), we rank each judgment by how self-evidently
// bad AND costly its failure is, then build a ready-to-drop-in sentence.
// ---------------------------------------------------------------------------

/** Buyer-intent categories — a dead end here directly loses a ready-to-buy customer. */
const HIGH_INTENT_CATEGORIES = new Set([
  'PRICE_ANCHORED',
  'MULTI_ATTRIBUTE',
  'SKU_MODEL_NUMBER',
  'BRAND_SEARCH',
  'TYPO',
  'SPLIT_WORD',
  'PLURAL_SINGULAR',
  'DIRECT_MATCH',
]);

/** Filler removed before deriving brand/product tokens from a query. */
const STOPWORDS = new Set([
  // English filler / intent words
  'the', 'a', 'an', 'and', 'or', 'for', 'with', 'some', 'any', 'me', 'my', 'i',
  'want', 'need', 'buy', 'find', 'looking', 'look', 'show', 'help', 'best',
  'nice', 'really', 'high', 'quality', 'good', 'great', 'perfect', 'stylish',
  'comfortable', 'trendy', 'fashionable', 'available', 'store', 'both', 'that',
  'would', 'work', 'casual', 'formal', 'occasions', 'occasion', 'where', 'can',
  'from', 'like', 'brands', 'brand', 'women', 'men', 'under', 'over', 'kr', 'dkk',
  'size', 'pair', 'of', 'to', 'in', 'on', 'is', 'are', 'this', 'your', 'you',
  // category nouns (keep brand tokens, drop the product type)
  'clothing', 'clothes', 'jacket', 'jackets', 'dress', 'dresses', 'shoes',
  'shoe', 'sneakers', 'sneaker', 'boots', 'boot', 'bag', 'bags', 'handbag',
  'handbags', 'sport', 'sports', 'outfit', 'wardrobe', 'essentials',
  // Danish filler / common category nouns
  'til', 'og', 'en', 'et', 'med', 'jeg', 'vil', 'have', 'kjole', 'sko',
  'sportstøj', 'løbetur', 'bryllup', 'dame', 'herre',
]);

const normalize = (s: string): string => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const queryTokens = (q: string): string[] =>
  q.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);

/** Candidate brand/product phrases from a query, longest-first. */
function candidatePhrases(query: string): string[] {
  const words = queryTokens(query).filter(w => w.length >= 3 && !STOPWORDS.has(w));
  const phrases = new Set<string>();
  for (let i = 0; i < words.length - 1; i++) phrases.add(`${words[i]} ${words[i + 1]}`);
  for (const w of words) phrases.add(w);
  return [...phrases]
    .filter(p => normalize(p).length >= 5)
    .sort((a, b) => normalize(b).length - normalize(a).length);
}

interface StockProof {
  brand: string;
  workingVariant: string;
  exampleTitle: string;
}

/**
 * Prove a zero-result query SHOULD have matched. Fully generic — no per-company
 * hardcoding. We only claim "you carry it" when a *direct search* for the term
 * works: some other query whose own text contains the term returns a product
 * whose title also contains it. This rejects coincidental matches on generic
 * words (e.g. "trail" appearing in an unrelated shirt) and incoherent working
 * variants (e.g. citing a "bestsellers" query that merely happened to surface
 * the product).
 */
function findProofOfStock(query: string, allJudgments: Judgment[]): StockProof | null {
  const others = allJudgments.filter(
    j => j.test_query.query !== query && j.results.length > 0
  );

  for (const phrase of candidatePhrases(query)) {
    const needle = normalize(phrase);

    // Generic-word guard: a specific brand/product clusters in a few queries;
    // a generic word bleeds across many. Skip terms that aren't distinctive.
    const documentFreq = others.filter(j =>
      j.results.some(r => normalize(r.title).includes(needle))
    ).length;
    if (documentFreq === 0 || documentFreq > 6) continue;

    // Credible proof: a query that DIRECTLY searches this term returns it.
    // Prefer the shortest such query (usually the cleanest brand search).
    const direct = others
      .filter(
        j =>
          normalize(j.test_query.query).includes(needle) &&
          j.results.some(r => normalize(r.title).includes(needle))
      )
      .sort((a, b) => a.test_query.query.length - b.test_query.query.length)[0];

    if (direct) {
      const match = direct.results.find(r => normalize(r.title).includes(needle))!;
      return {
        brand: phrase,
        workingVariant: direct.test_query.query,
        exampleTitle: match.title,
      };
    }
  }
  return null;
}

interface ExamplePick {
  tier: number;
  failureType: string;
  query: string;
  worstPos: number;
  wrongProduct: string;
  sentence: string;
}

function pickWorstExample(allJudgments: Judgment[]): ExamplePick {
  const candidates = allJudgments.map((j): ExamplePick => {
    const q = j.test_query.query;

    if (j.results.length === 0) {
      const proof = findProofOfStock(q, allJudgments);
      if (proof) {
        return {
          tier: 1,
          failureType: 'ZERO_RESULTS_STOCKED',
          query: q,
          worstPos: 0,
          wrongProduct: '',
          sentence:
            `A customer searching "${q}" gets zero results — a blank page — ` +
            `even though you carry it (e.g. "${proof.exampleTitle}" shows up when ` +
            `they instead search "${proof.workingVariant}").`,
        };
      }
      const highIntent = HIGH_INTENT_CATEGORIES.has(j.test_query.category);
      return {
        tier: highIntent ? 2 : 3,
        failureType: highIntent ? 'ZERO_RESULTS_HIGH_INTENT' : 'ZERO_RESULTS',
        query: q,
        worstPos: 0,
        wrongProduct: '',
        sentence:
          `A customer searching "${q}" gets zero results — a blank page, ` +
          `nothing at all.`,
      };
    }

    const byOrig = byOriginalRank(j);
    const top = byOrig[0];
    const best = Math.max(...j.results.map(r => r.relevance_score));

    if (top.relevance_score < 0.6) {
      return {
        tier: 4,
        failureType: 'IRRELEVANT_TOP',
        query: q,
        worstPos: 1,
        wrongProduct: top.title,
        sentence:
          `A customer searching "${q}" sees "${top.title}" at the #1 spot — ` +
          `not what they asked for.`,
      };
    }

    if (j.displacement > 2 && best - top.relevance_score >= 0.15) {
      const pos = j.displacement + 1;
      return {
        tier: 5,
        failureType: 'BURIED_BEST',
        query: q,
        worstPos: pos,
        wrongProduct: top.title,
        sentence:
          `A customer searching "${q}" has to scroll to position ${pos} to reach ` +
          `the best-matching product — below ${j.displacement} weaker results.`,
      };
    }

    // Not a compelling example.
    return {
      tier: 99,
      failureType: 'NONE',
      query: q,
      worstPos: j.displacement + 1,
      wrongProduct: top.title,
      sentence: '',
    };
  });

  const queryLen = (q: string) => q.length;
  candidates.sort((a, b) => {
    if (a.tier !== b.tier) return a.tier - b.tier;
    // Within a tier, prefer the cleanest / most concrete example.
    if (a.tier <= 3) return queryLen(a.query) - queryLen(b.query); // shorter zero-result query reads cleaner
    return b.worstPos - a.worstPos; // deeper burial / more egregious first
  });

  const best = candidates[0];
  if (best.tier === 99) {
    // No self-evident failure — fall back to the largest displacement (legacy behavior).
    const fallback = allJudgments
      .filter(j => j.results.length > 0)
      .reduce((a, b) => (b.displacement > a.displacement ? b : a), allJudgments[0]);
    const pos = fallback.displacement + 1;
    const top = byOriginalRank(fallback)[0];
    return {
      tier: 5,
      failureType: 'BURIED_BEST_FALLBACK',
      query: fallback.test_query.query,
      worstPos: pos,
      wrongProduct: top?.title ?? 'n/a',
      sentence:
        `A customer searching "${fallback.test_query.query}" has to scroll to ` +
        `position ${pos} to reach the best-matching product.`,
    };
  }
  return best;
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

  const pick = pickWorstExample(allJudgments);

  return {
    score: String(computeSearchQualityScore(allJudgments)),
    query_count: String(allJudgments.length),
    cap_count: String(critical),
    outside3rate: String(outside3rate),
    top3rate: String(top3rate),
    worst_query: pick.query,
    worst_pos: String(pick.worstPos),
    wrong_product: pick.wrongProduct,
    worst_example: pick.sentence,
    worst_failure_type: pick.failureType,
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
  console.log(`  [failure type]    = ${vars.worst_failure_type}`);
  console.log(`  {{worst_example}} = ${vars.worst_example}`);
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
      audit_worst_example: vars.worst_example,
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
