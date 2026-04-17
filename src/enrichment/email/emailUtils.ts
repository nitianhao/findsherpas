// ---------------------------------------------------------------------------
// Personal / free email domains — reject as work emails
// ---------------------------------------------------------------------------

const PERSONAL_DOMAINS = new Set([
  "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
  "hotmail.com", "outlook.com", "live.com", "aol.com",
  "icloud.com", "me.com", "mac.com", "protonmail.com",
  "proton.me", "mail.com", "gmx.com", "gmx.de", "web.de",
  "ymail.com", "msn.com",
]);

export function isPersonalDomain(domain: string): boolean {
  return PERSONAL_DOMAINS.has(domain.toLowerCase());
}

// ---------------------------------------------------------------------------
// Generic inbox prefixes — not person-specific
// ---------------------------------------------------------------------------

const GENERIC_PREFIXES = new Set([
  "info", "hello", "contact", "support", "service", "help",
  "kontakt", "shop", "sales", "careers", "jobs", "hiring",
  "press", "pr", "legal", "privacy", "datenschutz",
  "presse", "media", "marketing", "team", "admin",
  "office", "billing", "orders", "customercare",
  "customerservice", "wholesale", "general", "enquiries",
  "dialog", "kundenservice", "bestellungen",
  "produktanfragen", "behoerdenkontakt", "produktsicherheit",
  "hr", "recruitment",
]);

export function isGenericInbox(localPart: string): boolean {
  return GENERIC_PREFIXES.has(localPart.toLowerCase());
}

export function isPersonSpecificEmail(localPart: string): boolean {
  return !isGenericInbox(localPart);
}

// ---------------------------------------------------------------------------
// Email normalization
// ---------------------------------------------------------------------------

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function splitEmail(email: string): { localPart: string; domain: string } | null {
  const parts = normalizeEmail(email).split("@");
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null;
  return { localPart: parts[0], domain: parts[1] };
}

export function isValidWorkEmail(email: string): boolean {
  const parts = splitEmail(email);
  if (!parts) return false;
  if (isPersonalDomain(parts.domain)) return false;
  if (parts.localPart.length < 1) return false;
  if (!parts.domain.includes(".")) return false;
  // Reject malformed extractions (common scraping artifacts)
  if (parts.localPart.includes("u003e")) return false;
  if (parts.domain.includes("u003e")) return false;
  if (parts.localPart.length > 64) return false;
  if (parts.domain.length > 100) return false;
  // Reject domains that are clearly not company domains
  if (parts.domain.endsWith(".png") || parts.domain.endsWith(".jpg")) return false;
  return true;
}

// ---------------------------------------------------------------------------
// Name normalization for email generation
// ---------------------------------------------------------------------------

const ACCENT_MAP: Record<string, string> = {
  "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
  "à": "a", "á": "a", "â": "a", "ã": "a", "å": "a",
  "è": "e", "é": "e", "ê": "e", "ë": "e",
  "ì": "i", "í": "i", "î": "i", "ï": "i",
  "ò": "o", "ó": "o", "ô": "o", "õ": "o",
  "ù": "u", "ú": "u", "û": "u",
  "ñ": "n", "ç": "c", "ð": "d", "ø": "o",
  "ý": "y", "ÿ": "y", "ž": "z", "š": "s", "č": "c",
  "ř": "r", "ď": "d", "ť": "t", "ň": "n", "ě": "e",
  "ů": "u", "ł": "l", "ą": "a", "ę": "e", "ć": "c",
  "ź": "z", "ś": "s", "ő": "o", "ű": "u",
};

const HONORIFICS = new Set([
  "mr", "mrs", "ms", "dr", "prof", "sir", "dame",
  "herr", "frau",
]);

export function stripAccents(text: string): string {
  let result = "";
  for (const ch of text.toLowerCase()) {
    result += ACCENT_MAP[ch] ?? ch;
  }
  return result;
}

export interface NormalizedNameParts {
  first: string;
  last: string;
  firstInitial: string;
  allTokens: string[];
}

export function normalizeNameForEmail(fullName: string): NormalizedNameParts | null {
  const cleaned = stripAccents(fullName.trim());
  let tokens = cleaned
    .replace(/['']/g, "")
    .split(/[\s]+/)
    .map((t) => t.replace(/[^a-z\-]/g, ""))
    .filter((t) => t.length > 0);

  // Remove honorifics
  tokens = tokens.filter((t) => !HONORIFICS.has(t));

  if (tokens.length < 2) return null;

  const first = tokens[0];
  const last = tokens[tokens.length - 1];

  // Handle hyphenated last names: keep them joined
  const lastNormalized = last.replace(/-/g, "");

  return {
    first,
    last: lastNormalized,
    firstInitial: first.charAt(0),
    allTokens: tokens,
  };
}

// ---------------------------------------------------------------------------
// Domain extraction
// ---------------------------------------------------------------------------

export function extractDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}
