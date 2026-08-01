import type { Keyword } from '../types';

// ---------------------------------------------------------------------------
// Cheap string-similarity pre-filter. Deliberately NOT the final clustering —
// string similarity gets intent wrong (it splits `algolia cost` from
// `algolia kosten` and merges terms Google treats separately). Its only job is
// to collapse obvious variants so Stage 3 fetches fewer SERPs.
// ---------------------------------------------------------------------------

const STOPWORDS = new Set([
  'a', 'an', 'the', 'for', 'to', 'of', 'in', 'on', 'is', 'are', 'and', 'or',
  'my', 'your', 'with', 'what', 'how', 'best',
]);

function singularize(token: string): string {
  if (token.endsWith('ies') && token.length > 4) return `${token.slice(0, -3)}y`;
  // Only strip "es" after a sibilant (boxes, matches). A blanket "es" rule
  // over-strips: "alternatives" would become "alternativ", which no longer
  // matches the singular "alternative".
  if (/(s|x|z|ch|sh)es$/.test(token) && token.length > 4) return token.slice(0, -2);
  if (token.endsWith('s') && !token.endsWith('ss') && token.length > 3) return token.slice(0, -1);
  return token;
}

export function normalizeTerm(term: string): string {
  return term
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t !== '' && !STOPWORDS.has(t))
    .map(singularize)
    .sort()
    .join(' ');
}

export function groupCandidates(keywords: Keyword[]): Keyword[][] {
  const groups = new Map<string, Keyword[]>();
  for (const k of keywords) {
    const key = normalizeTerm(k.term);
    const existing = groups.get(key);
    if (existing) existing.push(k);
    else groups.set(key, [k]);
  }
  return [...groups.values()];
}
