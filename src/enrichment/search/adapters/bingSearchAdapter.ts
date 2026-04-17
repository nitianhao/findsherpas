import type { BrowserContext, Page } from "playwright";
import { newContext } from "../../browser/browserPool";
import { classifySearchResult } from "./googleSearchAdapter";
import type { SearchResultCandidate, SearchEngineAdapter } from "../../types/search";

const MAX_RESULTS = 8;

// ---------------------------------------------------------------------------
// Persistent Bing page
// ---------------------------------------------------------------------------

let _ctx: BrowserContext | null = null;
let _page: Page | null = null;
let _queryCount = 0;

async function getPage(): Promise<Page> {
  if (_queryCount > 0 && _queryCount % 20 === 0) {
    await releaseBingPage();
  }

  if (!_page || _page.isClosed()) {
    _ctx = await newContext();
    _page = await _ctx.newPage();
    await _page.addInitScript(() => {
      Object.defineProperty(navigator, "webdriver", { get: () => false });
    });
    await _page.route("**/*", (route) => {
      const type = route.request().resourceType();
      if (["image", "media"].includes(type)) return route.abort();
      return route.continue();
    });
    _page.setDefaultNavigationTimeout(20_000);
    _page.setDefaultTimeout(12_000);
  }
  return _page;
}

export async function releaseBingPage(): Promise<void> {
  if (_ctx) {
    try { await _ctx.close(); } catch {}
    _ctx = null;
    _page = null;
    _homepageVisited = false;
  }
}

// ---------------------------------------------------------------------------
// Bing URL resolution
// ---------------------------------------------------------------------------

function resolveBingUrl(rawHref: string): string {
  // Bing wraps URLs via /ck/a?... with a base64-encoded destination
  if (rawHref.includes("bing.com/ck/a")) {
    try {
      const url = new URL(rawHref);
      const u = url.searchParams.get("u");
      if (u) {
        // Bing uses a1<base64url> format
        const b64 = u.startsWith("a1") ? u.slice(2) : u;
        const decoded = Buffer.from(b64, "base64").toString("utf-8");
        if (decoded.startsWith("http")) return decoded;
      }
    } catch {
      // fall through
    }
  }
  return rawHref;
}

// ---------------------------------------------------------------------------
// Result extraction
// ---------------------------------------------------------------------------

async function extractBingResults(
  page: Page,
  query: string,
): Promise<SearchResultCandidate[]> {
  const raw = await page.evaluate(
    ({ max }: { max: number }) => {
      const items: { title: string; snippet: string; url: string }[] = [];
      const lis = document.querySelectorAll("#b_results > li.b_algo");

      for (let i = 0; i < lis.length && items.length < max; i++) {
        const li = lis[i];
        const a = li.querySelector("h2 a");
        if (!a) continue;
        const url = a.getAttribute("href") || "";
        if (!url.startsWith("http")) continue;
        const title = a.textContent?.trim() || "";

        // Snippet from various Bing caption elements
        const snippetEl = li.querySelector(
          ".b_caption p, .b_caption .b_algoSlug, .b_caption .b_paractl, .b_lineclamp2"
        );
        const snippet = snippetEl?.textContent?.trim() || "";

        items.push({ title, snippet: snippet.slice(0, 300), url });
      }
      return items;
    },
    { max: MAX_RESULTS },
  );

  return raw.map((r, i) => {
    const resolvedUrl = resolveBingUrl(r.url);
    return classifySearchResult(
      { title: r.title, snippet: r.snippet, url: resolvedUrl },
      i,
      query,
      "BING",
    );
  });
}

// ---------------------------------------------------------------------------
// Public search function
// ---------------------------------------------------------------------------

let _homepageVisited = false;

export async function runBingSearch(
  query: string,
): Promise<SearchResultCandidate[]> {
  const page = await getPage();
  _queryCount++;

  // Visit homepage first to establish session (avoids bot-detection on direct URL)
  if (!_homepageVisited) {
    await page.goto("https://www.bing.com/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    _homepageVisited = true;
  }

  // Use form-based search for first query, URL-based for subsequent (session established)
  const searchBox = page.locator("#sb_form_q");
  const searchBoxVisible = await searchBox.isVisible({ timeout: 3000 }).catch(() => false);

  if (searchBoxVisible) {
    await searchBox.fill("");
    await searchBox.fill(query);
    await searchBox.press("Enter");
  } else {
    // Fallback to URL navigation
    const encoded = encodeURIComponent(query);
    await page.goto(
      `https://www.bing.com/search?q=${encoded}&setlang=en&cc=US`,
      { waitUntil: "domcontentloaded" },
    );
  }

  // Wait for results to load
  try {
    await page.waitForSelector("#b_results > li.b_algo", { timeout: 8000 });
  } catch {
    // May have no results -- continue to extract what we can
  }

  await page.waitForTimeout(1500);

  return extractBingResults(page, query);
}

export const bingAdapter: SearchEngineAdapter = {
  name: "BING",
  runSearch: runBingSearch,
};
