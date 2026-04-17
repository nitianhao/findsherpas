import { chromium, type Browser, type BrowserContext, type Page } from "playwright";

let _browser: Browser | null = null;

const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

export async function getBrowser(): Promise<Browser> {
  if (!_browser || !_browser.isConnected()) {
    _browser = await chromium.launch({
      headless: false,
      args: [
        "--disable-blink-features=AutomationControlled",
        "--window-size=1440,900",
      ],
    });
  }
  return _browser;
}

export async function newContext(): Promise<BrowserContext> {
  const browser = await getBrowser();
  return browser.newContext({
    userAgent: USER_AGENT,
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    javaScriptEnabled: true,
  });
}

/**
 * Page for crawling company websites -- blocks heavy resources.
 */
export async function newPage(): Promise<Page> {
  const ctx = await newContext();
  const page = await ctx.newPage();
  await addAntiDetection(page);

  // Block heavy resources to speed things up
  await page.route("**/*", (route) => {
    const type = route.request().resourceType();
    if (["image", "font", "media"].includes(type)) {
      return route.abort();
    }
    return route.continue();
  });

  page.setDefaultNavigationTimeout(18_000);
  page.setDefaultTimeout(10_000);

  return page;
}

/**
 * Page for search engines -- keeps stylesheets, blocks only images/media.
 */
export async function newSearchPage(): Promise<Page> {
  const ctx = await newContext();
  const page = await ctx.newPage();
  await addAntiDetection(page);

  await page.route("**/*", (route) => {
    const type = route.request().resourceType();
    if (["image", "font", "media"].includes(type)) {
      return route.abort();
    }
    return route.continue();
  });

  page.setDefaultNavigationTimeout(20_000);
  page.setDefaultTimeout(12_000);

  return page;
}

async function addAntiDetection(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => false });
  });
}

export async function closeBrowser(): Promise<void> {
  if (_browser) {
    await _browser.close();
    _browser = null;
  }
}
