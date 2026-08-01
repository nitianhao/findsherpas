import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

function escapeField(value: unknown): string {
  if (value === null || value === undefined) return '';
  const s = String(value);
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

/**
 * Serialise rows to CSV.
 *
 * Headers are the UNION of keys across every row, not just the first row's.
 * Taking them from `rows[0]` silently drops any column that row happens to
 * lack — and several producers here populate fields conditionally. `joinGscData`
 * only sets `gscPosition`/`gscImpressions` on terms that actually rank, and
 * findsherpas ranks for almost nothing, so the first row would nearly always
 * miss and the columns would vanish from the entire file without an error.
 */
export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return '';
  const headers: string[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    for (const k of Object.keys(row)) {
      if (!seen.has(k)) {
        seen.add(k);
        headers.push(k);
      }
    }
  }
  const lines = [headers.join(',')];
  for (const row of rows) {
    lines.push(headers.map((h) => escapeField(row[h])).join(','));
  }
  return lines.join('\n');
}

/**
 * Parses the whole CSV text into rows of raw string fields in a single pass,
 * tracking quote state across line boundaries. This must not split on line
 * terminators before parsing quotes: a quoted field can legitimately contain
 * a literal newline, and splitting first would break it apart. It also
 * handles both `\n` and `\r\n` line terminators (Google Keyword Planner and
 * Search Console CSV exports are CRLF-terminated), and skips lines that are
 * entirely blank rather than emitting a phantom all-empty row.
 */
function parseRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let inQuotes = false;

  const endLine = () => {
    row.push(field);
    field = '';
    // A genuinely blank line parses to a single empty field; drop it instead
    // of emitting a phantom row of empty values.
    if (!(row.length === 1 && row[0] === '')) rows.push(row);
    row = [];
  };

  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\r') {
      if (text[i + 1] === '\n') i++;
      endLine();
    } else if (c === '\n') {
      endLine();
    } else {
      field += c;
    }
  }
  if (field !== '' || row.length > 0) endLine();

  return rows;
}

export function fromCsv(text: string): Record<string, string>[] {
  const rows = parseRows(text);
  if (rows.length === 0) return [];
  const [headers, ...dataRows] = rows;
  return dataRows.map((values) =>
    Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ''])) as Record<string, string>
  );
}

export function writeCsv(path: string, rows: Record<string, unknown>[]): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, toCsv(rows), 'utf8');
}

export function readCsv(path: string): Record<string, string>[] {
  return fromCsv(readFileSync(path, 'utf8'));
}

/**
 * Read a Google export, which is not the CSV its extension claims.
 *
 * A real Keyword Planner download is UTF-16 little-endian with a BOM and is
 * TAB-delimited despite the .csv name. Read as UTF-8 and split on commas, it
 * yields one garbage column and every downstream lookup silently misses.
 *
 * Detects the BOM for encoding and picks the delimiter by counting occurrences
 * in the header line, so a genuinely comma-separated export still works.
 */
export function readGoogleExport(path: string): string {
  const buf = readFileSync(path);

  let text: string;
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    text = buf.toString('utf16le').slice(1); // slice off the BOM code unit
  } else if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    // UTF-16 big-endian: swap byte pairs, then decode as little-endian.
    const swapped = Buffer.from(buf);
    for (let i = 0; i + 1 < swapped.length; i += 2) {
      const t = swapped[i];
      swapped[i] = swapped[i + 1];
      swapped[i + 1] = t;
    }
    text = swapped.toString('utf16le').slice(1);
  } else {
    text = buf.toString('utf8').replace(/^\uFEFF/, '');
  }

  return text;
}

/** Convert a tab-delimited body to comma-delimited so `fromCsv` can read it. */
export function tabsToCommas(text: string): string {
  return text
    .split(/\r\n|\n/)
    .map((line) =>
      line
        .split('\t')
        .map((cell) => (/[",\n]/.test(cell) ? `"${cell.replace(/"/g, '""')}"` : cell))
        .join(','),
    )
    .join('\n');
}

/** True when the header line has more tabs than commas. */
export function isTabDelimited(text: string): boolean {
  const firstReal = text.split(/\r\n|\n/).find((l) => l.trim() !== '') ?? '';
  const sample = text.split(/\r\n|\n/).slice(0, 6).join('\n') || firstReal;
  return (sample.match(/\t/g) ?? []).length > (sample.match(/,/g) ?? []).length;
}
