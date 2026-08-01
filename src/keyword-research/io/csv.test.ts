import { describe, it, expect } from 'vitest';
import { toCsv, fromCsv } from './csv';

describe('toCsv', () => {
  it('writes a header row from the first object keys', () => {
    expect(toCsv([{ term: 'algolia pricing', source: 'autocomplete' }]))
      .toBe('term,source\nalgolia pricing,autocomplete');
  });

  it('quotes fields containing commas', () => {
    expect(toCsv([{ term: 'algolia, coveo' }])).toBe('term\n"algolia, coveo"');
  });

  it('escapes embedded double quotes by doubling them', () => {
    expect(toCsv([{ term: 'the "best" search' }])).toBe('term\n"the ""best"" search"');
  });

  it('renders null and undefined as empty fields', () => {
    expect(toCsv([{ a: null, b: undefined }])).toBe('a,b\n,');
  });

  it('returns an empty string for no rows', () => {
    expect(toCsv([])).toBe('');
  });
});

describe('fromCsv', () => {
  it('parses a simple table', () => {
    expect(fromCsv('term,source\nalgolia pricing,autocomplete'))
      .toEqual([{ term: 'algolia pricing', source: 'autocomplete' }]);
  });

  it('parses quoted fields containing commas', () => {
    expect(fromCsv('term\n"algolia, coveo"')).toEqual([{ term: 'algolia, coveo' }]);
  });

  it('parses doubled quotes back into a single quote', () => {
    expect(fromCsv('term\n"the ""best"" search"')).toEqual([{ term: 'the "best" search' }]);
  });

  it('returns an empty array for an empty string', () => {
    expect(fromCsv('')).toEqual([]);
  });

  it('round-trips through toCsv', () => {
    const rows = [{ term: 'a,b', note: 'say "hi"' }];
    expect(fromCsv(toCsv(rows))).toEqual(rows);
  });

  it('parses a CRLF-terminated document without leaking \\r into fields', () => {
    expect(fromCsv('term,volume\r\nalgolia pricing,100\r\n'))
      .toEqual([{ term: 'algolia pricing', volume: '100' }]);
  });

  it('round-trips a field containing an embedded newline', () => {
    const rows = [{ term: 'line1\nline2', source: 'x' }];
    expect(fromCsv(toCsv(rows))).toEqual(rows);
  });

  it('skips a blank line in the middle of a document instead of emitting a phantom row', () => {
    expect(fromCsv('term\na\n\nb')).toEqual([{ term: 'a' }, { term: 'b' }]);
  });
});
