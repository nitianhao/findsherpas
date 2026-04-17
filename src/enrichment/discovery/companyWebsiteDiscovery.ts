import type { Page } from "playwright";
import { newPage, closeBrowser } from "../browser/browserPool";
import {
  discoverInternalPages,
  toDiscoveredPageStubs,
} from "./internalPageDiscovery";
import {
  extractVisibleEmails,
  extractLinkedinUrls,
  extractPersonLikeBlocks,
} from "../extract/pageExtractors";
import type { PlannedRowTask } from "../types/tasks";
import type {
  CompanyDiscoveryResult,
  DiscoveredPage,
  ExtractedPersonCandidate,
  ExtractedEmailCandidate,
  ExtractedLinkedinCandidate,
} from "../types/discovery";

const MAX_PAGES_TO_VISIT = 6;
const DELAY_BETWEEN_MS = 1500;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function ensureProtocol(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

async function visitPage(
  page: Page,
  url: string,
): Promise<{ html: string; status: number; title: string; finalUrl: string }> {
  const response = await page.goto(url, { waitUntil: "domcontentloaded" });
  const status = response?.status() ?? 0;
  const title = await page.title();
  const html = await page.content();
  const finalUrl = page.url();
  return { html, status, title, finalUrl };
}

export async function discoverCompanyWebsiteData(
  task: PlannedRowTask,
): Promise<CompanyDiscoveryResult> {
  const result: CompanyDiscoveryResult = {
    sourceFile: task.sourceFile,
    sheetName: task.sheetName,
    rowIndex: task.rowIndex,
    companyName: task.companyName,
    websiteUrl: task.websiteUrl,
    region: task.region,
    country: "",
    homepageFinalUrl: "",
    discoveredPages: [],
    personCandidates: [],
    emailCandidates: [],
    linkedinCandidates: [],
    notes: [],
    errors: [],
  };

  const url = ensureProtocol(task.websiteUrl);
  let page: Page | null = null;

  try {
    page = await newPage();

    // 1. Visit homepage
    let homepageHtml: string;
    let homepageStatus: number;
    let homepageTitle: string;

    try {
      const hp = await visitPage(page, url);
      homepageHtml = hp.html;
      homepageStatus = hp.status;
      homepageTitle = hp.title;
      result.homepageFinalUrl = hp.finalUrl;
    } catch (err: any) {
      result.errors.push(`Homepage failed: ${err.message}`);
      return result;
    }

    // Record homepage
    const homepageDiscovered: DiscoveredPage = {
      url: result.homepageFinalUrl,
      pageType: "HOMEPAGE",
      httpStatus: homepageStatus,
      title: homepageTitle,
      discoveredFrom: "entry",
      sameDomain: true,
    };
    result.discoveredPages.push(homepageDiscovered);

    // Extract from homepage
    collectExtractions(result, homepageHtml, result.homepageFinalUrl, "HOMEPAGE");

    // 2. Discover internal pages
    const candidates = discoverInternalPages(
      homepageHtml,
      result.homepageFinalUrl,
      MAX_PAGES_TO_VISIT - 1,
    );
    const stubs = toDiscoveredPageStubs(candidates, result.homepageFinalUrl);
    // stubs[0] is homepage (already visited), skip it
    const toVisit = stubs.slice(1).slice(0, MAX_PAGES_TO_VISIT - 1);

    // 3. Visit internal pages sequentially
    for (const stub of toVisit) {
      await sleep(DELAY_BETWEEN_MS);

      try {
        const visited = await visitPage(page, stub.url);
        stub.httpStatus = visited.status;
        stub.title = visited.title;
        result.discoveredPages.push(stub);

        collectExtractions(result, visited.html, stub.url, stub.pageType);
      } catch (err: any) {
        stub.httpStatus = 0;
        result.discoveredPages.push(stub);
        result.errors.push(`Page ${stub.url}: ${err.message}`);
      }
    }
  } catch (err: any) {
    result.errors.push(`Browser error: ${err.message}`);
  } finally {
    if (page) {
      try {
        await page.context().close();
      } catch {
        // ignore
      }
    }
  }

  return result;
}

function collectExtractions(
  result: CompanyDiscoveryResult,
  html: string,
  pageUrl: string,
  pageType: import("../types/discovery").PageType,
) {
  try {
    const emails = extractVisibleEmails(html, pageUrl, pageType);
    result.emailCandidates.push(...dedupeEmails(result.emailCandidates, emails));
  } catch (err: any) {
    result.errors.push(`Email extraction failed on ${pageUrl}: ${err.message}`);
  }

  try {
    const linkedin = extractLinkedinUrls(html, pageUrl, pageType);
    result.linkedinCandidates.push(
      ...dedupeLinkedin(result.linkedinCandidates, linkedin),
    );
  } catch (err: any) {
    result.errors.push(
      `LinkedIn extraction failed on ${pageUrl}: ${err.message}`,
    );
  }

  try {
    const persons = extractPersonLikeBlocks(html, pageUrl, pageType);
    result.personCandidates.push(
      ...dedupePersons(result.personCandidates, persons),
    );
  } catch (err: any) {
    result.errors.push(
      `Person extraction failed on ${pageUrl}: ${err.message}`,
    );
  }
}

function dedupeEmails(
  existing: ExtractedEmailCandidate[],
  incoming: ExtractedEmailCandidate[],
): ExtractedEmailCandidate[] {
  const seen = new Set(existing.map((e) => e.email));
  return incoming.filter((e) => !seen.has(e.email));
}

function dedupeLinkedin(
  existing: ExtractedLinkedinCandidate[],
  incoming: ExtractedLinkedinCandidate[],
): ExtractedLinkedinCandidate[] {
  const seen = new Set(existing.map((e) => e.url));
  return incoming.filter((e) => !seen.has(e.url));
}

function dedupePersons(
  existing: ExtractedPersonCandidate[],
  incoming: ExtractedPersonCandidate[],
): ExtractedPersonCandidate[] {
  const seen = new Set(existing.map((e) => e.normalizedName));
  return incoming.filter((e) => !seen.has(e.normalizedName));
}
