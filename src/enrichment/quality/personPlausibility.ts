import type { TargetRole } from "../types/prospect";
import type { PersonPlausibilityStatus, PersonPlausibilityDecision } from "../types/quality";
import { stripAccents } from "../email/emailUtils";

// ---------------------------------------------------------------------------
// Strong negative signals — likely not a real person name
// ---------------------------------------------------------------------------

const COMPANY_SUFFIX_PATTERNS = [
  /\b(inc|llc|ltd|gmbh|corp|ag|se|bv|sa|srl|pty|plc|co)\b/i,
  /\b(brand|brands|group|holding|holdings|company|enterprises)\b/i,
  /\b(store|stores|shop|boutique|outlet|marketplace)\b/i,
];

const ECOMMERCE_WORD_PATTERNS = [
  /\b(dress|dresses|shoes|boots|jacket|jackets|clothing|apparel|fashion)\b/i,
  /\b(sustainable|eco-friendly|organic|handmade|artisan|vintage)\b/i,
  /\b(collection|lookbook|catalog|sale|clearance|deals)\b/i,
  /\b(shipping|returns|warranty|customer service)\b/i,
  /\b(onlineshop|webshop|online shop|web shop)\b/i,
];

const MARKETING_PHRASE_PATTERNS = [
  /\b(preisgekr[öo]n|award[\s-]?winning|best[\s-]?selling|top[\s-]?rated)\b/i,
  /\b(beitrag von|post by|posted by|shared by|article by)\b/i,
  /\b(official site|official page|home page|landing page)\b/i,
  /\b(community|resources|support|help center)\b/i,
  /\b(management team|leadership team|executive team|our team|meet the team)\b/i,
  /\b(the reformation|the company|the brand|the store)\b/i,
];

const NON_NAME_STRUCTURAL_PATTERNS = [
  /^\d/,                           // starts with digit
  /[@#$%^&*(){}[\]<>]/,           // special chars
  /^[a-z]/,                        // starts lowercase
  /^(www\.|http)/i,                // URL fragment
  /\.(com|org|net|de|co\.uk)\b/i,  // domain fragment
];

// Words that should never appear in a person name
const TOXIC_TOKENS = new Set([
  "shop", "store", "brand", "online", "onlineshop", "webshop",
  "fashion", "clothing", "apparel", "boutique", "outlet",
  "official", "site", "page", "home", "team", "company",
  "service", "support", "management", "leadership",
  "collection", "catalog", "lookbook", "sale",
  "preisgekroenter", "preisgekrönter", "award-winning",
  "inc", "llc", "gmbh",
]);

// ---------------------------------------------------------------------------
// Positive signals — looks like a real person
// ---------------------------------------------------------------------------

const PERSON_NAME_PATTERN =
  /^[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+(?:de|van|von|der|den|la|le|el|al|di|del|da|dos|das|du|mc|mac|o')?)?(?:\s+[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+){1,3}$/;

// ---------------------------------------------------------------------------
// Company name overlap detection
// ---------------------------------------------------------------------------

function companyNameOverlap(personName: string, companyName: string): boolean {
  const personTokens = stripAccents(personName.toLowerCase()).split(/\s+/);
  const companyTokens = stripAccents(companyName.toLowerCase())
    .replace(/['']/g, "")
    .split(/[\s\-&+,]+/)
    .filter((t) => t.length >= 3);

  if (companyTokens.length === 0) return false;

  // If the entire person name matches the company name closely
  const personFull = personTokens.join(" ");
  const companyFull = companyTokens.join(" ");
  if (personFull === companyFull) return true;

  // Filter out articles/prepositions for matching
  const FILLER_WORDS = new Set(["the", "a", "an", "of", "for", "and", "by", "von", "de", "der", "die", "das"]);
  const personContentTokens = personTokens.filter((t) => !FILLER_WORDS.has(t));
  const companyContentTokens = companyTokens.filter((t) => !FILLER_WORDS.has(t));

  // If most person content tokens appear in the company name
  const matchCount = personContentTokens.filter((pt) =>
    companyContentTokens.some((ct) => ct === pt || ct.includes(pt) || pt.includes(ct)),
  ).length;

  // If all content tokens match company tokens, very suspicious
  if (matchCount >= personContentTokens.length && personContentTokens.length >= 1) return true;

  // If the company name is a single word and it's the person's "last name"
  if (
    companyContentTokens.length === 1 &&
    personTokens.length === 2 &&
    personTokens[1] === companyContentTokens[0]
  ) {
    // This is tricky — "Alex Faherty" at "Faherty" is a real person
    // Only flag if first token also looks like a company word
    return COMPANY_SUFFIX_PATTERNS.some((p) => p.test(personTokens[0]));
  }

  return false;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function evaluatePersonPlausibility(
  personName: string,
  companyName: string,
  role: TargetRole,
  linkedinUrl: string,
  roleConfidenceLabel: string | null,
): PersonPlausibilityDecision {
  const positiveSignals: string[] = [];
  const negativeSignals: string[] = [];
  const notes: string[] = [];
  let score = 50; // neutral baseline

  const trimmedName = personName.trim();
  if (!trimmedName) {
    return {
      personName,
      companyName,
      role,
      status: "IMPLAUSIBLE",
      score: 0,
      positiveSignals: [],
      negativeSignals: ["empty name"],
      notes: [],
    };
  }

  // --- Negative signals ---

  // Structural checks
  for (const pattern of NON_NAME_STRUCTURAL_PATTERNS) {
    if (pattern.test(trimmedName)) {
      score -= 40;
      negativeSignals.push(`structural: matches ${pattern.source}`);
    }
  }

  // Company suffix in name
  for (const pattern of COMPANY_SUFFIX_PATTERNS) {
    if (pattern.test(trimmedName)) {
      score -= 35;
      negativeSignals.push(`company suffix: matches ${pattern.source}`);
    }
  }

  // Ecommerce words
  for (const pattern of ECOMMERCE_WORD_PATTERNS) {
    if (pattern.test(trimmedName)) {
      score -= 40;
      negativeSignals.push(`ecommerce word: matches ${pattern.source}`);
    }
  }

  // Marketing phrases — these are strong signals of non-person text
  for (const pattern of MARKETING_PHRASE_PATTERNS) {
    if (pattern.test(trimmedName)) {
      score -= 50;
      negativeSignals.push(`marketing phrase: matches ${pattern.source}`);
    }
  }

  // Toxic tokens
  const nameTokens = stripAccents(trimmedName.toLowerCase()).split(/\s+/);
  for (const token of nameTokens) {
    if (TOXIC_TOKENS.has(token)) {
      score -= 30;
      negativeSignals.push(`toxic token: "${token}"`);
    }
  }

  // Company name overlap
  if (companyNameOverlap(trimmedName, companyName)) {
    score -= 35;
    negativeSignals.push(
      `name overlaps company name "${companyName}" — likely company/brand, not person`,
    );
  }

  // Token count: single word or 5+ words
  if (nameTokens.length < 2) {
    score -= 30;
    negativeSignals.push("single-word name");
  }
  if (nameTokens.length > 4) {
    score -= 15;
    negativeSignals.push(`${nameTokens.length} tokens — unusually long`);
  }

  // All-uppercase or all-lowercase
  if (trimmedName === trimmedName.toUpperCase()) {
    score -= 20;
    negativeSignals.push("all uppercase");
  }
  if (trimmedName === trimmedName.toLowerCase()) {
    score -= 25;
    negativeSignals.push("all lowercase");
  }

  // --- Positive signals ---

  // Standard person name pattern (2-3 tokens, title case)
  if (PERSON_NAME_PATTERN.test(trimmedName)) {
    score += 25;
    positiveSignals.push("matches standard person name pattern");
  }

  // Reasonable token count
  if (nameTokens.length >= 2 && nameTokens.length <= 3) {
    score += 10;
    positiveSignals.push(`${nameTokens.length} name tokens — typical`);
  }

  // Has a LinkedIn profile URL
  if (linkedinUrl && linkedinUrl.includes("linkedin.com/in/")) {
    score += 20;
    positiveSignals.push("has LinkedIn person profile URL");

    // Slug consistency check
    const slugMatch = linkedinUrl.match(/linkedin\.com\/in\/([^/?#]+)/i);
    if (slugMatch) {
      const slug = decodeURIComponent(slugMatch[1]).replace(/[-_]/g, " ").toLowerCase();
      const nameNorm = stripAccents(trimmedName.toLowerCase());
      const nameTokensNorm = nameNorm.split(/\s+/);
      const slugContainsName = nameTokensNorm.some(
        (t) => t.length >= 3 && slug.includes(t),
      );
      if (slugContainsName) {
        score += 15;
        positiveSignals.push("LinkedIn slug contains name tokens");
      } else {
        score -= 10;
        negativeSignals.push("LinkedIn slug does not match name");
        notes.push(`slug "${slugMatch[1]}" vs name "${trimmedName}"`);
      }
    }
  }

  // Role confidence boost
  if (roleConfidenceLabel === "STRONG") {
    score += 10;
    positiveSignals.push("role resolution is STRONG");
  } else if (roleConfidenceLabel === "PROBABLE") {
    score += 5;
    positiveSignals.push("role resolution is PROBABLE");
  }

  // --- Determine status ---
  let status: PersonPlausibilityStatus;
  if (score >= 60) {
    status = "PLAUSIBLE";
  } else if (score >= 30) {
    status = "SUSPICIOUS";
  } else {
    status = "IMPLAUSIBLE";
  }

  return {
    personName: trimmedName,
    companyName,
    role,
    status,
    score,
    positiveSignals,
    negativeSignals,
    notes,
  };
}
