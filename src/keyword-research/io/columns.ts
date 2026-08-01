// ---------------------------------------------------------------------------
// Matching CSV columns whose names Google spells inconsistently.
//
// Keyword Planner and Search Console both vary their header names between
// exports, and both pad them with stray whitespace. This was independently
// solved in `planner/keywordPlanner.ts` and `gsc/gscJoin.ts` with byte-identical
// code; it lives here now so a fix lands once rather than twice.
//
// `pick` returns '' for a missing column, which is indistinguishable from a
// present-but-empty cell. That ambiguity is fine for optional metrics and NOT
// fine for a join key — a header Google renamed or localised then silently
// yields zero matches instead of an error. Use `pickOrThrow` for join keys.
// ---------------------------------------------------------------------------

function normalizedIndex(row: Record<string, string>): Map<string, string> {
  const index = new Map<string, string>();
  for (const [k, v] of Object.entries(row)) index.set(k.trim(), v);
  return index;
}

/** First matching column's value, or '' if none match. */
export function pick(row: Record<string, string>, candidates: string[]): string {
  const index = normalizedIndex(row);
  for (const c of candidates) {
    const v = index.get(c.trim());
    if (v !== undefined) return v;
  }
  return '';
}

/**
 * Like `pick`, but throws when no candidate column exists at all.
 *
 * For a join key this converts a silent zero-match run into a clear failure.
 * A localised export (`Mot clé` rather than `Keyword`) previously produced an
 * all-zero merge whose own diagnostic then blamed the bid signal.
 */
export function pickOrThrow(
  row: Record<string, string>,
  candidates: string[],
  what: string,
): string {
  const index = normalizedIndex(row);
  for (const c of candidates) {
    const v = index.get(c.trim());
    if (v !== undefined) return v;
  }
  throw new Error(
    `No ${what} column found. Looked for: ${candidates.join(', ')}. ` +
      `Found: ${[...index.keys()].join(', ') || '(none)'}. ` +
      `If this export is not in English, re-export it in English — ` +
      `localised column names are not supported.`,
  );
}
