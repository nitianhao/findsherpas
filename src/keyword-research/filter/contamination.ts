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
 *
 * SEARCH_OPERATOR was narrowed after a manual review of real Stage 1 output
 * found the original bare `operator`/`boolean`/`extension`/browser-name
 * tokens catching unrelated senses of the same words: `elasticsearch
 * operator` / `opensearch operator` (Kubernetes operators — some of the
 * most valuable practitioner keywords in the set), `typesense boolean`
 * (a real filter-syntax feature), and `coveo explorer extension` (a
 * product feature, not a browser extension). `boolean` was dropped
 * entirely — it has a legitimate search-syntax sense and no
 * operator-specific one. The operator/command and browser/extension senses
 * now require adjacent context instead of matching bare anywhere in the
 * term.
 */
const RULES: { reason: string; pattern: RegExp }[] = [
  // "operator" and "command" are only contamination in the Google/site
  // search-operator sense (e.g. "search operator", "google command").
  // Bare, they also mean a real Kubernetes/Elasticsearch "operator" or a
  // shell "command" — both legitimate practitioner terms — so they must
  // co-occur with search/site/google, not match anywhere in the term.
  { reason: 'SEARCH_OPERATOR', pattern: /\b(search|site|google) operator\b/ },
  { reason: 'SEARCH_OPERATOR', pattern: /\b(search|google) command\b/ },
  { reason: 'SEARCH_OPERATOR', pattern: /\bsearch q site\b|\bsite search (google|bing|command)\b/ },
  // These have no legitimate sense in this domain — safe as bare tokens.
  { reason: 'SEARCH_OPERATOR', pattern: /\b(dork|shortcut|keybind)\b/ },
  // "extension" alone also means a real vendor product feature (e.g.
  // "coveo explorer extension"), so require a browser name to co-occur,
  // in either order.
  { reason: 'SEARCH_OPERATOR', pattern: /(?=.*\bextension\b)(?=.*\b(chrome|firefox|edge|brave|safari|duckduckgo)\b)/ },
  // These browser names have no other common sense in this domain, so
  // they're safe as bare tokens.
  { reason: 'SEARCH_OPERATOR', pattern: /\b(chrome|firefox|brave|safari|duckduckgo)\b/ },
  // "edge" alone also means edge computing/edge cases — require an
  // explicit browser context (the extension rule above already covers
  // "edge extension"; this catches bare browser mentions like "microsoft
  // edge" or "edge browser").
  { reason: 'SEARCH_OPERATOR', pattern: /\bmicrosoft edge\b|\bedge browser\b/ },
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
