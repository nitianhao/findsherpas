import * as cheerio from "cheerio";
import type {
  PageType,
  ExtractedPersonCandidate,
  ExtractedEmailCandidate,
  ExtractedLinkedinCandidate,
  EmailSourceType,
  LinkedinProfileType,
} from "../types/discovery";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PERSONAL_DOMAINS = new Set([
  "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
  "hotmail.com", "outlook.com", "live.com", "aol.com",
  "icloud.com", "me.com", "mac.com", "protonmail.com",
  "proton.me", "mail.com", "gmx.com", "gmx.de", "web.de",
  "ymail.com", "msn.com",
]);

const ROLE_HINTS: Record<string, string[]> = {
  CEO: [
    "ceo", "chief executive officer", "founder", "co-founder",
    "cofounder", "managing director", "geschäftsführer",
    "geschaeftsfuehrer", "general manager", "gründer", "gründerin",
  ],
  HEAD_OF_PRODUCT: [
    "head of product", "vp product", "vp of product",
    "product director", "chief product officer", "cpo",
    "director of product",
  ],
  HEAD_OF_ECOMMERCE: [
    "head of ecommerce", "head of e-commerce",
    "ecommerce director", "e-commerce director",
    "director of ecommerce", "director of e-commerce",
    "digital commerce", "vp ecommerce", "vp e-commerce",
  ],
  HEAD_OF_GROWTH: [
    "head of growth", "cmo", "chief marketing officer",
    "growth lead", "marketing director", "vp marketing",
    "vp of marketing", "director of marketing",
  ],
};

// ---------------------------------------------------------------------------
// Email extraction
// ---------------------------------------------------------------------------

const EMAIL_REGEX = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
const OBFUSCATED_AT = /[a-zA-Z0-9._%+\-]+\s*[\[\(]\s*at\s*[\]\)]\s*[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/gi;
const OBFUSCATED_AT_SPACED = /[a-zA-Z0-9._%+\-]+\s+@\s+[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;

function deobfuscateEmail(text: string): string {
  return text
    .replace(/\s*[\[\(]\s*at\s*[\]\)]\s*/gi, "@")
    .replace(/\s+@\s+/g, "@")
    .trim();
}

export function extractVisibleEmails(
  html: string,
  pageUrl: string,
  pageType: PageType,
): ExtractedEmailCandidate[] {
  const $ = cheerio.load(html);
  const results: ExtractedEmailCandidate[] = [];
  const seen = new Set<string>();

  function addEmail(email: string, sourceType: EmailSourceType) {
    const lower = email.toLowerCase().trim();
    if (seen.has(lower)) return;
    if (lower.length < 5 || lower.length > 100) return;
    const [localPart, domain] = lower.split("@");
    if (!domain || !localPart) return;
    if (PERSONAL_DOMAINS.has(domain)) return;
    seen.add(lower);

    const signals: string[] = [];
    if (sourceType === "MAILTO") signals.push("mailto-link");
    if (!PERSONAL_DOMAINS.has(domain)) signals.push("likely-work-domain");

    results.push({
      email: lower,
      domain,
      localPart,
      sourceType,
      pageUrl,
      pageType,
      confidenceSignals: signals,
    });
  }

  // mailto links
  $("a[href^='mailto:']").each((_, el) => {
    const href = $(el).attr("href") || "";
    const match = href.replace("mailto:", "").split("?")[0].trim();
    if (match.includes("@")) addEmail(match, "MAILTO");
  });

  // Visible text
  const text = $("body").text();
  const plainMatches = text.match(EMAIL_REGEX) || [];
  for (const m of plainMatches) addEmail(m, "VISIBLE_TEXT");

  // Obfuscated
  const obfMatches = [
    ...(text.match(OBFUSCATED_AT) || []),
    ...(text.match(OBFUSCATED_AT_SPACED) || []),
  ];
  for (const m of obfMatches) {
    const clean = deobfuscateEmail(m);
    if (clean.includes("@")) addEmail(clean, "OBFUSCATED_TEXT");
  }

  return results;
}

// ---------------------------------------------------------------------------
// LinkedIn extraction
// ---------------------------------------------------------------------------

const LINKEDIN_REGEX = /https?:\/\/(?:www\.)?linkedin\.com\/(?:in|company)\/[a-zA-Z0-9\-_.%/]+/g;

export function extractLinkedinUrls(
  html: string,
  pageUrl: string,
  pageType: PageType,
): ExtractedLinkedinCandidate[] {
  const $ = cheerio.load(html);
  const seen = new Set<string>();
  const results: ExtractedLinkedinCandidate[] = [];

  function addUrl(raw: string) {
    // Normalize: strip trailing slash, query, fragment
    let url: string;
    try {
      const parsed = new URL(raw);
      parsed.search = "";
      parsed.hash = "";
      parsed.pathname = parsed.pathname.replace(/\/+$/, "");
      url = parsed.toString();
    } catch {
      return;
    }
    if (seen.has(url)) return;
    seen.add(url);

    let sourceType: LinkedinProfileType = "UNKNOWN";
    if (url.includes("/in/")) sourceType = "PERSON_PROFILE";
    else if (url.includes("/company/")) sourceType = "COMPANY_PAGE";

    results.push({ url, sourceType, pageUrl, pageType });
  }

  // From href attributes
  $("a[href*='linkedin.com']").each((_, el) => {
    const href = $(el).attr("href") || "";
    addUrl(href);
  });

  // From visible text / other attributes
  const fullHtml = $.html();
  const textMatches = fullHtml.match(LINKEDIN_REGEX) || [];
  for (const m of textMatches) addUrl(m);

  return results;
}

// ---------------------------------------------------------------------------
// Person candidate extraction
// ---------------------------------------------------------------------------

const NAME_REGEX = /^[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+(?:de|van|von|der|den|la|le|el|al|di|del|da|dos|das|du|mc|mac|o')?)?(?:\s+[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+){1,3}$/;

function isLikelyName(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 4 || trimmed.length > 60) return false;
  const tokens = trimmed.split(/\s+/);
  if (tokens.length < 2 || tokens.length > 5) return false;
  // Reject all caps
  if (trimmed === trimmed.toUpperCase()) return false;
  // Reject all lowercase
  if (trimmed === trimmed.toLowerCase()) return false;
  return NAME_REGEX.test(trimmed);
}

function matchRoleHints(text: string): string[] {
  const lower = text.toLowerCase();
  const matched: string[] = [];
  for (const [role, hints] of Object.entries(ROLE_HINTS)) {
    if (hints.some((h) => lower.includes(h))) {
      matched.push(role);
    }
  }
  return matched;
}

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, " ").toLowerCase();
}

export function extractPersonLikeBlocks(
  html: string,
  pageUrl: string,
  pageType: PageType,
): ExtractedPersonCandidate[] {
  const $ = cheerio.load(html);
  const results: ExtractedPersonCandidate[] = [];
  const seen = new Set<string>();

  function tryAddCandidate(
    nameText: string,
    surroundingText: string,
    confidenceSignals: string[],
  ) {
    const name = nameText.trim().replace(/\s+/g, " ");
    if (!isLikelyName(name)) return;
    const key = `${normalizeName(name)}|${pageUrl}`;
    if (seen.has(key)) return;
    seen.add(key);

    const roleHints = matchRoleHints(surroundingText);
    const titleText = extractTitleFromContext(surroundingText, name);

    results.push({
      fullName: name,
      normalizedName: normalizeName(name),
      titleText,
      matchedRoleHints: roleHints,
      pageUrl,
      pageType,
      evidenceText: surroundingText.slice(0, 300),
      confidenceSignals: [
        ...confidenceSignals,
        ...(roleHints.length > 0 ? ["has-role-hint"] : []),
      ],
    });
  }

  // Strategy 1: headings (h1-h4) that look like names
  $("h1, h2, h3, h4").each((_, el) => {
    const text = $(el).text().trim();
    const surrounding = $(el).parent().text().trim();
    tryAddCandidate(text, surrounding, ["heading-element"]);
  });

  // Strategy 2: common team card patterns
  const cardSelectors = [
    ".team-member", ".team-card", ".staff-member", ".person",
    ".member", ".bio", ".leader", "[class*='team']",
    "[class*='person']", "[class*='staff']", "[class*='leader']",
    "[class*='member']", "[class*='bio']",
  ];

  for (const sel of cardSelectors) {
    $(sel).each((_, el) => {
      const block = $(el);
      const blockText = block.text().trim();
      // Look for name in strong, h-tags, or first text node
      const nameEl = block.find("h2, h3, h4, h5, strong, b, .name, [class*='name']").first();
      const name = nameEl.length ? nameEl.text().trim() : "";
      if (name) {
        tryAddCandidate(name, blockText, ["team-card-pattern"]);
      }
    });
  }

  // Strategy 3: structured data / list items with name + title patterns
  $("li, dt, dd, p").each((_, el) => {
    const text = $(el).text().trim();
    if (text.length < 10 || text.length > 300) return;
    // Pattern: "Name – Title" or "Name, Title" or "Name | Title"
    const parts = text.split(/\s*[–—\-|,]\s*/);
    if (parts.length >= 2) {
      const candidate = parts[0].trim();
      const rest = parts.slice(1).join(" ");
      if (isLikelyName(candidate) && matchRoleHints(rest).length > 0) {
        tryAddCandidate(candidate, text, ["name-title-pattern"]);
      }
    }
  });

  return results;
}

function extractTitleFromContext(text: string, name: string): string {
  // Remove the name from the text to isolate title
  const without = text.replace(name, "").trim();
  // Take first meaningful chunk
  const parts = without.split(/[\n\r]+/).map((s) => s.trim()).filter(Boolean);
  const titleLine = parts.find((p) => p.length > 2 && p.length < 120) || "";
  return titleLine.replace(/^[,\-–—|:]\s*/, "").trim().slice(0, 120);
}
