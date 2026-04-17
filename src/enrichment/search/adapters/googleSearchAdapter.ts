import type { Page, BrowserContext } from "playwright";
import { newContext } from "../../browser/browserPool";
import type { SearchResultCandidate, SearchEngineAdapter } from "../../types/search";

const MAX_RESULTS = 8;

// ---------------------------------------------------------------------------
// Persistent page management
// ---------------------------------------------------------------------------

let _ctx: BrowserContext | null = null;
let _page: Page | null = null;
let _consentHandled = false;
let _queryCount = 0;
let _captchaBackoffUntil = 0; // query count after which Google is re-enabled

async function getPage(): Promise<Page> {
  if (_queryCount > 0 && _queryCount % 12 === 0) {
    await releaseGooglePage();
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
    _consentHandled = false;
  }
  return _page;
}

export async function releaseGooglePage(): Promise<void> {
  if (_ctx) {
    try { await _ctx.close(); } catch {}
    _ctx = null;
    _page = null;
    _consentHandled = false;
    _homepageVisited = false;
  }
}

// ---------------------------------------------------------------------------
// CAPTCHA state
// ---------------------------------------------------------------------------

let _totalQueryCounter = 0;

export function isGoogleInCaptchaBackoff(): boolean {
  return _totalQueryCounter < _captchaBackoffUntil;
}

function triggerCaptchaBackoff(): void {
  _captchaBackoffUntil = _totalQueryCounter + 10;
}

// ---------------------------------------------------------------------------
// Consent
// ---------------------------------------------------------------------------

async function handleConsent(page: Page): Promise<void> {
  if (_consentHandled) return;
  try {
    for (const sel of [
      "button#L2AGLb",
      'button:has-text("Accept all")',
      'button:has-text("Reject all")',
    ]) {
      const btn = page.locator(sel).first();
      if (await btn.isVisible({ timeout: 2000 })) {
        await btn.click();
        await page.waitForTimeout(1500);
        _consentHandled = true;
        return;
      }
    }
    _consentHandled = true;
  } catch {
    _consentHandled = true;
  }
}

// ---------------------------------------------------------------------------
// CAPTCHA detection
// ---------------------------------------------------------------------------

async function detectCaptcha(page: Page): Promise<boolean> {
  const text = await page.evaluate(
    () => document.body?.innerText?.slice(0, 500) || "",
  );
  if (text.includes("unusual traffic") || text.includes("not a robot") || text.includes("detected unusual traffic")) {
    return true;
  }
  // Check for reCAPTCHA iframe
  const hasRecaptcha = await page.evaluate(
    () => !!document.querySelector('iframe[src*="recaptcha"]'),
  );
  return hasRecaptcha;
}

// ---------------------------------------------------------------------------
// Result extraction
// ---------------------------------------------------------------------------

async function extractResults(
  page: Page,
  query: string,
): Promise<SearchResultCandidate[]> {
  const raw = await page.evaluate(
    ({ max }: { max: number }) => {
      const items: { title: string; snippet: string; url: string }[] = [];
      const h3s = document.querySelectorAll("h3");
      for (let i = 0; i < h3s.length && items.length < max; i++) {
        const h3 = h3s[i];
        const a = h3.closest("a") || h3.parentElement?.closest("a");
        if (!a) continue;
        const url = a.getAttribute("href") || "";
        if (!url.startsWith("http")) continue;
        const title = h3.textContent?.trim() || "";

        const container =
          h3.closest("[data-sokoban-container]") ||
          h3.closest(".g") ||
          h3.parentElement?.parentElement?.parentElement?.parentElement;

        let snippet = "";
        if (container) {
          container.querySelectorAll("div, span").forEach((el) => {
            const t = el.textContent?.trim() || "";
            if (t.length > snippet.length && t.length < 500 && t !== title && !t.includes(title)) {
              snippet = t;
            }
          });
        }
        items.push({ title, snippet: snippet.slice(0, 300), url });
      }
      return items;
    },
    { max: MAX_RESULTS },
  );

  return raw.map((r, i) => classify(r, i, query, "GOOGLE"));
}

// ---------------------------------------------------------------------------
// LinkedIn classification (shared)
// ---------------------------------------------------------------------------

export function classifyLinkedin(url: string): {
  isLinkedin: boolean;
  linkedinType: "PERSON_PROFILE" | "COMPANY_PAGE" | "OTHER" | null;
} {
  const lower = url.toLowerCase();
  if (!lower.includes("linkedin.com")) return { isLinkedin: false, linkedinType: null };
  if (lower.includes("/in/")) return { isLinkedin: true, linkedinType: "PERSON_PROFILE" };
  if (lower.includes("/company/")) return { isLinkedin: true, linkedinType: "COMPANY_PAGE" };
  return { isLinkedin: true, linkedinType: "OTHER" };
}

function classify(
  r: { title: string; snippet: string; url: string },
  rank: number,
  query: string,
  engine: "GOOGLE" | "BING",
): SearchResultCandidate {
  const li = classifyLinkedin(r.url);
  const signals: string[] = [];
  if (li.isLinkedin) signals.push("linkedin-url");
  if (li.linkedinType === "PERSON_PROFILE") signals.push("linkedin-person");
  return {
    query,
    engine,
    title: r.title,
    snippet: r.snippet,
    url: r.url,
    displayUrl: r.url,
    rank: rank + 1,
    isLinkedin: li.isLinkedin,
    linkedinType: li.linkedinType,
    evidenceSignals: signals,
  };
}

// Also export classify for Bing adapter reuse
export { classify as classifySearchResult };

// ---------------------------------------------------------------------------
// Public search function
// ---------------------------------------------------------------------------

let _homepageVisited = false;

export async function runGoogleSearch(
  query: string,
): Promise<SearchResultCandidate[]> {
  _totalQueryCounter++;

  if (isGoogleInCaptchaBackoff()) {
    throw new Error("Google CAPTCHA backoff active");
  }

  const page = await getPage();
  _queryCount++;

  // Visit homepage first to establish session and handle consent
  if (!_homepageVisited) {
    await page.goto("https://www.google.com/", { waitUntil: "domcontentloaded" });
    await handleConsent(page);
    await page.waitForTimeout(1000);
    _homepageVisited = true;
  }

  // Use form-based search
  const searchBox = page.locator('textarea[name="q"], input[name="q"]').first();
  const searchBoxVisible = await searchBox.isVisible({ timeout: 3000 }).catch(() => false);

  if (searchBoxVisible) {
    await searchBox.fill("");
    await searchBox.fill(query);
    await searchBox.press("Enter");
  } else {
    // Fallback to URL navigation
    const encoded = encodeURIComponent(query);
    await page.goto(
      `https://www.google.com/search?q=${encoded}&hl=en&gl=us&num=10`,
      { waitUntil: "domcontentloaded" },
    );
    await handleConsent(page);
  }

  await page.waitForTimeout(1200);

  if (await detectCaptcha(page)) {
    await releaseGooglePage();
    triggerCaptchaBackoff();
    throw new Error("Google CAPTCHA -- rate limited");
  }

  return extractResults(page, query);
}

export const googleAdapter: SearchEngineAdapter = {
  name: "GOOGLE",
  runSearch: runGoogleSearch,
};
