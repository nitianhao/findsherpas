import type { SerpOwnerType } from '../types';

// ---------------------------------------------------------------------------
// SERP owner classification
//
// Buckets a result URL by who owns the domain, so Stage 3 can judge how
// winnable a SERP is for an independent voice. Order matters: forum and
// listicle domains are checked BEFORE vendor domains, because a domain like
// github.com is forum-class (community-hosted content) and would otherwise
// be misread as a vendor property if vendor domains were checked first.
// ---------------------------------------------------------------------------

const VENDOR_DOMAINS = [
  'algolia.com', 'coveo.com', 'bloomreach.com', 'constructor.io', 'klevu.com',
  'searchspring.com', 'elastic.co', 'opensearch.org', 'typesense.org',
  'meilisearch.com', 'attraqt.com', 'lucidworks.com', 'nosto.com',
  'luigisbox.com', 'aws.amazon.com',
];

const FORUM_DOMAINS = [
  'stackoverflow.com', 'reddit.com', 'news.ycombinator.com', 'quora.com',
  'discuss.elastic.co', 'stackexchange.com', 'github.com',
  // Community publishing platforms: anyone can post, so a result here
  // reflects the platform's moderation and SEO weight, not one author's
  // independent expertise — the same reasoning that puts stackoverflow.com
  // and reddit.com in this bucket rather than being read as independent.
  'dev.to', 'medium.com',
];

const LISTICLE_DOMAINS = [
  'g2.com', 'capterra.com', 'trustradius.com', 'getapp.com',
  'softwareadvice.com', 'sourceforge.net', 'slashdot.org',
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
  return 'independent';
}
