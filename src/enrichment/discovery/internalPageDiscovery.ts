import * as cheerio from "cheerio";
import type { DiscoveredPage, PageType } from "../types/discovery";

// ---------------------------------------------------------------------------
// Page-type classification keywords
// ---------------------------------------------------------------------------

const PAGE_TYPE_KEYWORDS: { type: PageType; keywords: string[] }[] = [
  {
    type: "TEAM",
    keywords: ["team", "people", "our-team", "ourteam", "meet-the-team"],
  },
  {
    type: "LEADERSHIP",
    keywords: [
      "leadership",
      "management",
      "executives",
      "board",
      "directors",
      "fuhrung",
      "führung",
    ],
  },
  {
    type: "ABOUT",
    keywords: [
      "about",
      "about-us",
      "aboutus",
      "who-we-are",
      "our-story",
      "company",
      "uber-uns",
      "über-uns",
    ],
  },
  {
    type: "CONTACT",
    keywords: [
      "contact",
      "kontakt",
      "kontakte",
      "get-in-touch",
      "reach-us",
    ],
  },
  {
    type: "LEGAL",
    keywords: ["impressum", "imprint", "legal", "datenschutz", "privacy"],
  },
  {
    type: "CAREERS",
    keywords: ["careers", "jobs", "join-us", "work-with-us", "karriere"],
  },
];

const SKIP_EXTENSIONS = new Set([
  ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif",
  ".pdf", ".zip", ".gz", ".tar", ".mp3", ".mp4", ".webm",
  ".woff", ".woff2", ".ttf", ".eot", ".ico", ".css", ".js",
]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeUrl(href: string, baseUrl: string): string | null {
  try {
    const url = new URL(href, baseUrl);
    // Strip fragment and trailing slash for dedup
    url.hash = "";
    let path = url.pathname.replace(/\/+$/, "") || "/";
    url.pathname = path;
    return url.toString();
  } catch {
    return null;
  }
}

function isSameDomain(url: string, baseUrl: string): boolean {
  try {
    const a = new URL(url);
    const b = new URL(baseUrl);
    // Compare root domain (allow www vs non-www)
    const norm = (h: string) => h.replace(/^www\./, "").toLowerCase();
    return norm(a.hostname) === norm(b.hostname);
  } catch {
    return false;
  }
}

function shouldSkipHref(href: string): boolean {
  const lower = href.toLowerCase().trim();
  if (!lower || lower === "#") return true;
  if (lower.startsWith("mailto:")) return true;
  if (lower.startsWith("tel:")) return true;
  if (lower.startsWith("javascript:")) return true;
  if (lower.startsWith("data:")) return true;

  try {
    const ext = new URL(href, "https://x.com").pathname
      .split(".")
      .pop()
      ?.toLowerCase();
    if (ext && SKIP_EXTENSIONS.has(`.${ext}`)) return true;
  } catch {
    // ignore
  }

  return false;
}

function classifyPageType(url: string, anchorText: string): PageType {
  const combined = (url + " " + anchorText).toLowerCase();
  for (const { type, keywords } of PAGE_TYPE_KEYWORDS) {
    if (keywords.some((kw) => combined.includes(kw))) return type;
  }
  return "OTHER";
}

function scoreRelevance(url: string, anchorText: string): number {
  const combined = (url + " " + anchorText).toLowerCase();
  const PRIORITY_KEYWORDS = [
    "about", "team", "leadership", "management", "company",
    "contact", "kontakte", "kontakt", "impressum", "legal",
    "about-us", "aboutus", "who-we-are", "our-story",
    "careers", "jobs", "people", "executives", "board",
  ];
  let score = 0;
  for (const kw of PRIORITY_KEYWORDS) {
    if (combined.includes(kw)) score += 10;
  }
  // Penalize deep paths
  const pathDepth = (new URL(url).pathname.match(/\//g) || []).length;
  score -= pathDepth * 2;
  return score;
}

// ---------------------------------------------------------------------------
// Main discovery
// ---------------------------------------------------------------------------

export interface InternalPageCandidate {
  url: string;
  pageType: PageType;
  anchorText: string;
  relevanceScore: number;
}

export function discoverInternalPages(
  homepageHtml: string,
  homepageUrl: string,
  maxPages: number = 9,
): InternalPageCandidate[] {
  const $ = cheerio.load(homepageHtml);
  const seen = new Set<string>();
  const candidates: InternalPageCandidate[] = [];

  // Always include homepage
  seen.add(normalizeUrl(homepageUrl, homepageUrl)!);

  $("a[href]").each((_, el) => {
    const href = $(el).attr("href");
    if (!href || shouldSkipHref(href)) return;

    const resolved = normalizeUrl(href, homepageUrl);
    if (!resolved) return;
    if (!isSameDomain(resolved, homepageUrl)) return;
    if (seen.has(resolved)) return;
    seen.add(resolved);

    const anchorText = $(el).text().trim().slice(0, 200);
    const pageType = classifyPageType(resolved, anchorText);
    const relevanceScore = scoreRelevance(resolved, anchorText);

    candidates.push({ url: resolved, pageType, anchorText, relevanceScore });
  });

  // Sort by relevance, keep top N, prefer non-OTHER types
  candidates.sort((a, b) => {
    const typeA = a.pageType !== "OTHER" ? 1 : 0;
    const typeB = b.pageType !== "OTHER" ? 1 : 0;
    if (typeB !== typeA) return typeB - typeA;
    return b.relevanceScore - a.relevanceScore;
  });

  return candidates.slice(0, maxPages);
}

/**
 * Convert internal page candidates into DiscoveredPage stubs
 * (httpStatus and title will be filled after visiting).
 */
export function toDiscoveredPageStubs(
  candidates: InternalPageCandidate[],
  homepageUrl: string,
): DiscoveredPage[] {
  const homepage: DiscoveredPage = {
    url: homepageUrl,
    pageType: "HOMEPAGE",
    httpStatus: 0,
    title: "",
    discoveredFrom: "entry",
    sameDomain: true,
  };

  const pages = candidates.map(
    (c): DiscoveredPage => ({
      url: c.url,
      pageType: c.pageType,
      httpStatus: 0,
      title: "",
      discoveredFrom: homepageUrl,
      sameDomain: true,
    }),
  );

  return [homepage, ...pages];
}
