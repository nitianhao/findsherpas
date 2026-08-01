import type { Keyword } from '../types';

/**
 * Stage 2. This is the stage that justifies building a script at all.
 *
 * Evidence: the seed `site search` returns 256 autocomplete suggestions, and
 * the majority are the Google `site:` operator or job boards. Without this
 * filter, a naive expander hands that back as a top cluster.
 *
 * Order matters — the first matching rule wins, so specific patterns must
 * precede general ones.
 */
const RULES: { reason: string; pattern: RegExp }[] = [
  { reason: 'SEARCH_OPERATOR', pattern: /\b(dork|operator|command|shortcut|keybind|boolean|extension|chrome|firefox|edge|brave|duckduckgo)\b/ },
  { reason: 'SEARCH_OPERATOR', pattern: /\bsearch q site\b|\bsite search (google|bing|command)\b/ },
  { reason: 'JOBS', pattern: /\b(job|jobs|career|careers|hiring|salary|recruit|vacanc|glassdoor|internship)\b/ },
  { reason: 'CORPORATE', pattern: /\b(valuation|revenue|funding|investor|crunchbase|ipo|stock|market cap|net worth|ceo|founder|headquarters|employees|layoffs|board of directors|acquisition)\b/ },
  { reason: 'BRAND_ASSET', pattern: /\b(logo|icon|png|svg|wallpaper|font)\b/ },
  { reason: 'NAVIGATIONAL', pattern: /\b(login|log in|sign in|dashboard|status|outage|down|support|contact|phone number|address|office)\b/ },
  { reason: 'TRIVIA', pattern: /\b(meaning|pronunciation|pronounce|wiki|wikipedia|que es|ne demek|definition|psychiatry)\b/ },
  // Business-registry contamination: "tennessee ecommerce filing search",
  // "site search llc". These carry topic tokens, so the TOPIC_TOKEN check
  // below will not catch them — they need an explicit rule.
  { reason: 'REGISTRY', pattern: /\b(filing|registry|incorporation|llc|business entity|secretary of state|tngov|mstc|find a grave|dns|ip lookup)\b/ },
];

export const BLOCKLIST_PATTERNS: RegExp[] = RULES.map((r) => r.pattern);

/**
 * A term must contain at least one of these to be plausibly on-topic.
 * Deliberately broad — the blocklist does the precision work.
 */
export const TOPIC_TOKENS = [
  'search', 'relevance', 'ranking', 'query', 'queries', 'index', 'indexing',
  'facet', 'filter', 'synonym', 'autocomplete', 'discovery', 'merchandis',
  'ecommerce', 'e-commerce', 'catalog', 'product', 'zero result', 'no result',
  'algolia', 'coveo', 'bloomreach', 'constructor', 'klevu', 'searchspring',
  'elasticsearch', 'opensearch', 'typesense', 'meilisearch', 'attraqt',
  'lucidworks', 'nosto', 'luigi', 'solr', 'vector', 'semantic', 'embedding',
  'typo', 'relevancy', 'conversion', 'boost',
];

export function rejectionReason(term: string): string | null {
  const t = term.toLowerCase();
  for (const { reason, pattern } of RULES) {
    if (pattern.test(t)) return reason;
  }
  if (!TOPIC_TOKENS.some((tok) => t.includes(tok))) return 'NO_TOPIC_TOKEN';
  return null;
}

export function filterKeywords(keywords: Keyword[]): {
  kept: Keyword[];
  rejected: { term: string; reason: string }[];
} {
  const kept: Keyword[] = [];
  const rejected: { term: string; reason: string }[] = [];
  const seen = new Set<string>();

  for (const k of keywords) {
    if (seen.has(k.term)) continue;
    seen.add(k.term);
    const reason = rejectionReason(k.term);
    if (reason) rejected.push({ term: k.term, reason });
    else kept.push(k);
  }

  return { kept, rejected };
}
