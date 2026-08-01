import type { SerpOwnerType } from '../types';

// ---------------------------------------------------------------------------
// SERP owner classification
//
// Buckets a result URL by who owns the domain, so Stage 3 can judge how
// winnable a SERP is for an independent voice. Order matters: forum and
// listicle domains are checked BEFORE vendor domains, because a domain like
// github.com is forum-class (community-hosted content) and would otherwise
// be misread as a vendor property if vendor domains were checked first.
//
// `independent` is a POSITIVE list, not the fallback. That distinction is the
// whole point of this module, and getting it wrong inverts the pipeline's
// output. When `independent` was the default, 64.5% of 820 real results landed
// in it, and because `serpWeakness` scores independent 0.15 (hardest to beat),
// every unrecognised domain was treated as a formidable incumbent. The query
// `best algolia alternatives` scored 0.15 — least winnable — when its actual
// page one was ten alternatives-directories, AI content farms, and two search
// vendors, with no credible expert anywhere. It is one of the MOST winnable
// SERPs in the set.
//
// So: an unrecognised domain is `unknown` (neutral, 0.5). Only domains we can
// name as genuine independent authorities score as hard to displace.
// ---------------------------------------------------------------------------

const VENDOR_DOMAINS = [
  'algolia.com', 'coveo.com', 'bloomreach.com', 'constructor.io', 'klevu.com',
  'searchspring.com', 'elastic.co', 'opensearch.org', 'typesense.org',
  'meilisearch.com', 'attraqt.com', 'lucidworks.com', 'nosto.com',
  'luigisbox.com', 'aws.amazon.com',
  // Found sitting in the `independent` bucket on real SERPs — all of them sell
  // search or discovery products, so their "alternatives" posts are marketing.
  'addsearch.com', 'shaped.ai', 'expertrec.com', 'experro.com',
];

/**
 * Genuine independent authorities. Deliberately short: a domain earns a place
 * here by being one, not by being unrecognised. Grow it as real ones turn up in
 * `stage3-serps.json` — an over-long list here makes every SERP look unwinnable.
 */
const INDEPENDENT_DOMAINS = [
  'baymard.com', 'nngroup.com', 'smashingmagazine.com', 'alistapart.com',
];

const FORUM_DOMAINS = [
  'stackoverflow.com', 'reddit.com', 'news.ycombinator.com', 'quora.com',
  'discuss.elastic.co', 'stackexchange.com', 'github.com',
  // Community publishing platforms: anyone can post, so a result here
  // reflects the platform's moderation and SEO weight, not one author's
  // independent expertise — the same reasoning that puts stackoverflow.com
  // and reddit.com in this bucket rather than being read as independent.
  'dev.to', 'medium.com',
  // Video, not a competing article. A YouTube result is one fewer article slot
  // on the page, so it makes a SERP more winnable, not less.
  'youtube.com',
];

const LISTICLE_DOMAINS = [
  'g2.com', 'capterra.com', 'trustradius.com', 'getapp.com',
  'softwareadvice.com', 'sourceforge.net', 'slashdot.org',
  // Review aggregators and alternatives directories. Same content shape as the
  // above: roundups assembled from vendor marketing and user submissions rather
  // than first-hand expertise. gartner.com alone was 45 of 820 real results.
  'gartner.com', 'peerspot.com', 'itqlick.com', 'alternativeto.net',
  'openalternative.co', 'saasworthy.com', 'softwaresuggest.com', 'research.com',
  'comparably.com', 'vendr.com', 'glassdoor.com',
];

const DOCS_PATH = /\/(doc|docs|documentation|api|reference|guides?)(\/|$)/;

function hostOf(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

export function classifyOwner(url: string): SerpOwnerType {
  const host = hostOf(url);
  if (host === null) return 'unknown';

  const matches = (list: string[]) => list.some((d) => host === d || host.endsWith(`.${d}`));

  if (matches(FORUM_DOMAINS)) return 'forum';
  if (matches(LISTICLE_DOMAINS)) return 'listicle';
  if (matches(VENDOR_DOMAINS)) {
    let path = '';
    try { path = new URL(url).pathname; } catch { path = ''; }
    return DOCS_PATH.test(path) || host.startsWith('docs.') ? 'vendor-docs' : 'vendor-blog';
  }
  if (matches(INDEPENDENT_DOMAINS)) return 'independent';
  // Unrecognised. NOT independent — see the banner comment.
  return 'unknown';
}
