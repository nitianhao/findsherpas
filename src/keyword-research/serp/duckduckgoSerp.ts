import { chromium, type Browser, type Page } from 'playwright';

import type { SerpResult, SerpSnapshot } from '../types';
import { classifyOwner } from './ownerClassifier';
import { buildSnapshot } from './serpRecon';

// ---------------------------------------------------------------------------
// SERP fetching via DuckDuckGo, driven by a real browser.
//
// Why DuckDuckGo and why headful, both measured rather than assumed:
//
//   - Brave's API works but burns a paid quota shared with the enrichment
//     pipeline, so it is reserved for that.
//   - `html.duckduckgo.com` over plain HTTP returns an anti-bot challenge
//     (HTTP 202, no results).
//   - Bing returns an empty shell both headless AND headful (body ~105 bytes).
//   - DuckDuckGo headless returns an empty shell too.
//   - DuckDuckGo HEADFUL returns real results. That is the only free path that
//     works, which is also why the sibling enrichment adapters run headful.
//
// Consequence worth stating plainly: these are DuckDuckGo results, not Google
// results. For the question this pipeline actually asks — "is page one owned by
// vendors grading their own homework?" — that is a sound proxy, and a spot
// check against Brave showed substantial URL overlap. For precise rank
// positions it is NOT a proxy, and nothing downstream should read these as
// Google rankings.
//
// Two fields the pipeline wants and this source cannot supply:
//   - Page word count. Search engines return a snippet, not a page body.
//     `SerpResult.wordCount` is therefore left undefined, and `serpWeakness`
//     skips its depth adjustment. Estimating depth from snippet length would
//     invent a signal the source does not carry.
//   - People Also Ask. DuckDuckGo exposes no PAA equivalent. `peopleAlsoAsk`
//     is an empty array. DuckDuckGo's "discussions" block is a different thing
//     (Reddit threads) and is deliberately NOT substituted for it.
// ---------------------------------------------------------------------------

/**
 * Delay between searches. DuckDuckGo is being scraped rather than API-served,
 * so this is politeness, not a documented rate limit. Do not parallelise.
 */
export const DDG_REQUEST_DELAY_MS = 2500;

const RESULTS_PER_SERP = 10;

/** Raised when DuckDuckGo starts serving challenge pages instead of results. */
export class DdgBlockedError extends Error {
  constructor(term: string) {
    super(
      `DuckDuckGo returned no results for "${term}" — likely an anti-bot ` +
        `challenge. Stop, wait, and resume later rather than hammering it.`,
    );
    this.name = 'DdgBlockedError';
  }
}

/** Hosts that are DuckDuckGo's own chrome rather than organic results. */
const CHROME_HOSTS =
  /duckduckgo\.com|duck\.co|spreadprivacy\.com|microsofttranslator\.com/;

function toSerpResult(raw: { url: string; title: string }): SerpResult {
  return {
    url: raw.url,
    title: raw.title,
    ownerType: classifyOwner(raw.url),
    // wordCount deliberately omitted — see the banner comment.
  };
}

/**
 * Reduce raw page anchors to organic results.
 *
 * Extracted from the page-evaluation callback so it is testable without a
 * browser. The extraction is deliberately structure-agnostic — it takes every
 * anchor rather than depending on a DuckDuckGo class name that will change —
 * which means this filter is the only thing standing between the pipeline and
 * DuckDuckGo's own navigation appearing as search results.
 */
export function selectOrganicResults(
  raw: { url: string; title: string }[],
): SerpResult[] {
  const seen = new Set<string>();
  const results: SerpResult[] = [];
  for (const r of raw) {
    if (CHROME_HOSTS.test(r.url)) continue;
    if (seen.has(r.url)) continue;
    seen.add(r.url);
    results.push(toSerpResult(r));
    if (results.length >= RESULTS_PER_SERP) break;
  }
  return results;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function extractResults(
  page: Page,
): Promise<{ url: string; title: string }[]> {
  return page.evaluate(() => {
    // DuckDuckGo's result markup changes; take anchors and filter, rather than
    // depending on one class name that will silently break.
    const anchors = Array.from(
      document.querySelectorAll('a[href^="http"]'),
    ) as HTMLAnchorElement[];
    return anchors.map((a) => ({ url: a.href, title: (a.innerText || '').trim() }));
  });
}

/**
 * Fetch one SERP. The caller owns the browser so a run can reuse one instance
 * across hundreds of terms rather than paying browser startup each time.
 */
export async function fetchDdgSerp(page: Page, term: string): Promise<SerpSnapshot> {
  const url = `https://duckduckgo.com/?q=${encodeURIComponent(term)}&ia=web`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2500);

  const raw = await extractResults(page);

  const results = selectOrganicResults(raw);
  if (results.length === 0) throw new DdgBlockedError(term);
  return buildSnapshot(term, results, []);
}

/**
 * Fetch SERPs for many terms in sequence, invoking `onResult` after each so the
 * caller can persist incrementally. Never parallelised: concurrent scraping is
 * the fastest way to get blocked.
 */
export async function fetchSerpsSequentially(
  terms: string[],
  onResult: (term: string, snapshot: SerpSnapshot) => void,
): Promise<void> {
  let browser: Browser | undefined;
  try {
    // Headful is required — see the banner comment. Headless returns a shell.
    browser = await chromium.launch({ headless: false });
    const context = await browser.newContext({ locale: 'en-US' });
    const page = await context.newPage();

    for (let i = 0; i < terms.length; i++) {
      const snapshot = await fetchDdgSerp(page, terms[i]);
      onResult(terms[i], snapshot);
      if (i < terms.length - 1) await sleep(DDG_REQUEST_DELAY_MS);
    }
  } finally {
    await browser?.close();
  }
}
