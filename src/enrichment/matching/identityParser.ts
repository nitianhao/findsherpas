import type {
  RoleSearchDiscoveryResult,
  ParsedIdentityCandidate,
} from "../types/search";
import type { TargetRole } from "../types/prospect";

// ---------------------------------------------------------------------------
// Role keyword detection
// ---------------------------------------------------------------------------

const ROLE_EVIDENCE_KEYWORDS: Record<string, string[]> = {
  CEO: [
    "ceo", "chief executive", "founder", "co-founder", "cofounder",
    "managing director", "geschäftsführer", "geschaeftsfuehrer",
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
    "digital commerce",
  ],
  HEAD_OF_GROWTH: [
    "head of growth", "cmo", "chief marketing officer",
    "marketing director", "vp marketing", "vp of marketing",
    "director of marketing", "growth lead",
  ],
};

// ---------------------------------------------------------------------------
// LinkedIn post / non-profile detection
// ---------------------------------------------------------------------------

const LINKEDIN_POST_PATTERNS = [
  /^beitrag von\b/i,
  /^post by\b/i,
  /^post von\b/i,
  /\bactivity-\d+/i,
  /\/posts?\//i,
  /^#\w+/,
];

function isLinkedinPostResult(title: string, url: string): boolean {
  return LINKEDIN_POST_PATTERNS.some((p) => p.test(title) || p.test(url));
}

// ---------------------------------------------------------------------------
// Ecommerce / product false-positive rejection
// ---------------------------------------------------------------------------

const ECOMMERCE_NOISE_PATTERNS = [
  /\b(dresses|shoes|boots|jackets|coats|pants|jeans|shirts|tops|blouses)\b/i,
  /\b(sale|clearance|new arrivals|collection|lookbook|catalog)\b/i,
  /\b(sustainable clothing|sustainable fashion|eco-friendly)\b/i,
  /\b(shop now|add to cart|buy now|free shipping|official site|official store)\b/i,
  /\b(wedding guest|bridesmaid|prom|homecoming)\b/i,
  /\b(gift card|promo code|coupon|discount)\b/i,
  /\b(customer service|return policy|shipping info|size guide)\b/i,
  /\b(webmail|login|sign in|my account|forgot password)\b/i,
];

function isEcommerceNoise(title: string, snippet: string): boolean {
  const combined = `${title} ${snippet}`;
  return ECOMMERCE_NOISE_PATTERNS.some((p) => p.test(combined));
}

// ---------------------------------------------------------------------------
// Name heuristics
// ---------------------------------------------------------------------------

const NAME_PATTERN =
  /^[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+(?:de|van|von|der|den|la|le|el|al|di|del|da|dos|das|du|mc|mac|o')?)?(?:\s+[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+){1,3}$/;

const REJECT_PATTERNS = [
  /^(shop|buy|order|sale|official|site|page|home|new|free)\b/i,
  /\b(shop now|official site|sign up|log in|contact us|read more)\b/i,
  /^\d/,
  /[@#$%^&*(){}[\]]/,
  // Common non-name phrases that look like Title Case
  /^(Your Account|My Account|Google Help|Amazon Stores)\b/i,
  /^(Customer Service|Trading Post|New Arrivals|Top Picks)\b/i,
  /^(Free Shipping|Gift Cards|About Us|Contact Us)\b/i,
  /^(Community Resources|Forbes Advisor|Microsoft Support)\b/i,
  /^(Cheap Flights|Best Deals|Top Rated)\b/i,
  /^(Online Shop|Official Site|Web Store)\b/i,
  /^(Comprehensive Identity|Sustainable Dresses|Cowboy Boots)\b/i,
  /\b(Management Team|Org Chart|Company Profile|Employee List)\b/i,
  /\b(Inc\.|LLC|Ltd\.|GmbH|Corp\.)\b/i,
];

function isLikelyPersonName(text: string): boolean {
  const trimmed = text.trim();
  if (trimmed.length < 4 || trimmed.length > 60) return false;
  const tokens = trimmed.split(/\s+/);
  if (tokens.length < 2 || tokens.length > 5) return false;
  if (trimmed === trimmed.toUpperCase()) return false;
  if (trimmed === trimmed.toLowerCase()) return false;
  if (REJECT_PATTERNS.some((p) => p.test(trimmed))) return false;
  return NAME_PATTERN.test(trimmed);
}

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, " ").toLowerCase();
}

// ---------------------------------------------------------------------------
// LinkedIn slug name extraction
// ---------------------------------------------------------------------------

function nameFromLinkedinSlug(url: string): string | null {
  const match = url.match(/linkedin\.com\/in\/([^/?#]+)/i);
  if (!match) return null;
  const slug = decodeURIComponent(match[1]).replace(/[-_]/g, " ").trim();
  // Remove trailing numbers (e.g. "john-smith-12345")
  const cleaned = slug.replace(/\s+\d+$/, "");
  const tokens = cleaned.split(/\s+/);
  if (tokens.length < 2 || tokens.length > 4) return null;
  const name = tokens
    .map((t) => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase())
    .join(" ");
  if (!isLikelyPersonName(name)) return null;
  return name;
}

// ---------------------------------------------------------------------------
// LinkedIn title parsing: "Name – Role – Company | LinkedIn"
// ---------------------------------------------------------------------------

interface LinkedinTitleParsed {
  name: string | null;
  roleSegment: string;
  companySegment: string;
  hasRoleKeyword: boolean;
  matchedRole: string | null;
}

function extractLinkedinTitlePattern(
  title: string,
  targetRole: TargetRole,
): LinkedinTitleParsed {
  const result: LinkedinTitleParsed = {
    name: null,
    roleSegment: "",
    companySegment: "",
    hasRoleKeyword: false,
    matchedRole: null,
  };

  // Remove trailing "| LinkedIn" or "- LinkedIn"
  const cleaned = title.replace(/\s*[|\-–—]\s*LinkedIn\s*$/i, "").trim();

  // Split by common delimiters: en-dash, em-dash, pipe, hyphen surrounded by spaces
  const segments = cleaned
    .split(/\s*[–—|]\s*|\s+-\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

  if (segments.length === 0) return result;

  // First segment is typically the name
  if (segments.length >= 1 && isLikelyPersonName(segments[0])) {
    result.name = segments[0];
  }

  // Second segment is typically the role/title
  if (segments.length >= 2) {
    result.roleSegment = segments[1];
  }

  // Third segment is typically the company
  if (segments.length >= 3) {
    result.companySegment = segments[2];
  }

  // Also check " at " pattern: "Name - Role at Company"
  if (segments.length === 2 && segments[1].includes(" at ")) {
    const [rolePart, companyPart] = segments[1].split(/\s+at\s+/);
    result.roleSegment = rolePart?.trim() ?? "";
    result.companySegment = companyPart?.trim() ?? "";
  }

  // Check role keywords across non-name text
  const nonNameText = segments.slice(1).join(" ").toLowerCase();
  const allText = cleaned.toLowerCase();

  // Check target role specifically
  const targetKeywords = ROLE_EVIDENCE_KEYWORDS[targetRole] ?? [];
  if (targetKeywords.some((kw) => nonNameText.includes(kw) || allText.includes(kw))) {
    result.hasRoleKeyword = true;
    result.matchedRole = targetRole;
  }

  // Also check all roles for general detection
  if (!result.hasRoleKeyword) {
    for (const [role, keywords] of Object.entries(ROLE_EVIDENCE_KEYWORDS)) {
      if (keywords.some((kw) => nonNameText.includes(kw))) {
        result.hasRoleKeyword = true;
        result.matchedRole = role;
        break;
      }
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Title-based name extraction
// ---------------------------------------------------------------------------

function extractNameFromTitle(title: string): string | null {
  const dashParts = title.split(/\s*[-–—|]\s*/);
  for (const part of dashParts) {
    const cleaned = part.trim();
    if (isLikelyPersonName(cleaned)) return cleaned;
  }
  const commaParts = title.split(/,\s*/);
  if (commaParts.length >= 1) {
    const first = commaParts[0].trim();
    if (isLikelyPersonName(first)) return first;
  }
  return null;
}

function extractNameFromSnippet(snippet: string): string | null {
  const clauses = snippet.split(/[.;–—|]/);
  for (const clause of clauses.slice(0, 3)) {
    const trimmed = clause.trim();
    const isMatch = trimmed.match(
      /^([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+){1,3})\s+(?:is|,|\u2013)/,
    );
    if (isMatch && isLikelyPersonName(isMatch[1])) return isMatch[1];
  }
  return null;
}

// ---------------------------------------------------------------------------
// Role evidence check
// ---------------------------------------------------------------------------

function hasRoleEvidence(
  role: TargetRole,
  title: string,
  snippet: string,
): boolean {
  const combined = `${title} ${snippet}`.toLowerCase();
  const keywords = ROLE_EVIDENCE_KEYWORDS[role] ?? [];
  return keywords.some((kw) => combined.includes(kw));
}

// ---------------------------------------------------------------------------
// Slug-name matching
// ---------------------------------------------------------------------------

function slugMatchesName(url: string, name: string): boolean {
  const slugName = nameFromLinkedinSlug(url);
  if (!slugName) return false;
  return normalizeName(slugName) === normalizeName(name);
}

// ---------------------------------------------------------------------------
// Main extraction
// ---------------------------------------------------------------------------

export function extractIdentityCandidatesFromSearchResults(
  roleSearch: RoleSearchDiscoveryResult,
): ParsedIdentityCandidate[] {
  const candidates: ParsedIdentityCandidate[] = [];
  const seen = new Set<string>();

  for (const result of roleSearch.searchResults) {
    // Hard-reject ecommerce noise
    if (isEcommerceNoise(result.title, result.snippet)) continue;

    // Skip LinkedIn post/activity results
    if (isLinkedinPostResult(result.title, result.url)) continue;

    const signals: string[] = [...result.evidenceSignals];
    let fullName: string | null = null;
    let linkedinUrl = "";

    // Priority 1: LinkedIn person profile URL
    if (result.isLinkedin && result.linkedinType === "PERSON_PROFILE") {
      linkedinUrl = cleanLinkedinUrl(result.url);

      // Parse LinkedIn title pattern for role evidence
      const liParsed = extractLinkedinTitlePattern(result.title, roleSearch.role);

      if (liParsed.name) {
        fullName = liParsed.name;
        signals.push("linkedin-profile-name");
      } else {
        fullName = extractNameFromTitle(result.title);
        if (!fullName) fullName = nameFromLinkedinSlug(result.url);
        if (fullName) signals.push("linkedin-profile-name");
      }

      // Add LinkedIn title role match signal
      if (liParsed.hasRoleKeyword && liParsed.matchedRole === roleSearch.role) {
        signals.push("LINKEDIN_TITLE_ROLE_MATCH");
      }

      // Add company match from title signal
      if (
        liParsed.companySegment &&
        liParsed.companySegment
          .toLowerCase()
          .includes(
            roleSearch.companyName.toLowerCase().split(" ")[0].toLowerCase(),
          )
      ) {
        signals.push("COMPANY_MATCH_FROM_TITLE");
      }

      // Check slug matches parsed name
      if (fullName && slugMatchesName(result.url, fullName)) {
        signals.push("LINKEDIN_PROFILE_SLUG_MATCHES_NAME");
      }
    }

    // Priority 2: Name from title/snippet for non-LinkedIn results
    if (!fullName) {
      fullName = extractNameFromTitle(result.title);
      if (fullName) signals.push("title-name");
    }
    if (!fullName) {
      fullName = extractNameFromSnippet(result.snippet);
      if (fullName) signals.push("snippet-name");
    }

    if (!fullName) continue;

    // Role evidence check
    if (hasRoleEvidence(roleSearch.role, result.title, result.snippet)) {
      signals.push("role-evidence");
    }

    // Dedupe
    const key = `${normalizeName(fullName)}|${linkedinUrl}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const inferredCompany = inferCompanyFromContext(
      result.title,
      result.snippet,
      roleSearch.companyName,
    );

    candidates.push({
      fullName,
      normalizedName: normalizeName(fullName),
      role: roleSearch.role,
      inferredCompany,
      sourceUrl: result.url,
      sourceTitle: result.title,
      sourceSnippet: result.snippet,
      linkedinUrl,
      evidenceSignals: signals,
      confidenceScore: 0,
    });
  }

  return candidates;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cleanLinkedinUrl(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return url;
  }
}

function inferCompanyFromContext(
  title: string,
  snippet: string,
  targetCompany: string,
): string {
  const combined = `${title} ${snippet}`.toLowerCase();
  if (combined.includes(targetCompany.toLowerCase())) return targetCompany;
  return "";
}
