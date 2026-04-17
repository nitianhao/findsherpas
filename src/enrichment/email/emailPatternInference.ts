import type { EmailPatternType, InferredDomainPattern } from "../types/email";
import {
  isGenericInbox,
  isValidWorkEmail,
  splitEmail,
  normalizeNameForEmail,
  type NormalizedNameParts,
} from "./emailUtils";

// ---------------------------------------------------------------------------
// Classify a single email against a known person name
// ---------------------------------------------------------------------------

export function classifyEmailPattern(
  emailLocalPart: string,
  personName: string,
): EmailPatternType {
  const parts = normalizeNameForEmail(personName);
  if (!parts) return "UNKNOWN";

  const local = emailLocalPart.toLowerCase();
  const { first, last, firstInitial } = parts;

  // first.last
  if (local === `${first}.${last}`) return "FIRST_LAST";
  // firstlast
  if (local === `${first}${last}`) return "FIRSTLAST";
  // flast
  if (local === `${firstInitial}${last}`) return "F_LAST";
  // f.last
  if (local === `${firstInitial}.${last}`) return "F.DOT.LAST";
  // first only
  if (local === first) return "FIRST";
  // last only
  if (local === last) return "LAST";

  // Fuzzy: handle middle-name variations (e.g. "lstansberry" for "L Stansberry")
  if (local.startsWith(firstInitial) && local.endsWith(last) && local.length > last.length) {
    return "F_LAST";
  }

  return "UNKNOWN";
}

// ---------------------------------------------------------------------------
// Try to classify an email without a known name (structural heuristic)
// ---------------------------------------------------------------------------

function guessStructuralPattern(localPart: string): EmailPatternType {
  if (isGenericInbox(localPart)) return "UNKNOWN";

  // first.last pattern: contains a dot, both parts alpha, 2+ chars each
  const dotParts = localPart.split(".");
  if (
    dotParts.length === 2 &&
    dotParts[0].length >= 2 &&
    dotParts[1].length >= 2 &&
    /^[a-z]+$/.test(dotParts[0]) &&
    /^[a-z]+$/.test(dotParts[1])
  ) {
    return "FIRST_LAST";
  }

  // f.last: single char + dot + 2+ chars
  if (
    dotParts.length === 2 &&
    dotParts[0].length === 1 &&
    dotParts[1].length >= 2 &&
    /^[a-z]$/.test(dotParts[0]) &&
    /^[a-z]+$/.test(dotParts[1])
  ) {
    return "F.DOT.LAST";
  }

  // flast: single lowercase letter followed by longer word, no dots
  if (/^[a-z][a-z]{3,}$/.test(localPart) && !localPart.includes(".")) {
    // Could be firstlast or flast — ambiguous without a name
    return "UNKNOWN";
  }

  return "UNKNOWN";
}

// ---------------------------------------------------------------------------
// Infer domain-level pattern from observed emails
// ---------------------------------------------------------------------------

export function inferDomainPatternFromObservedEmails(
  domain: string,
  observedEmails: Array<{ email: string; localPart: string; domain: string }>,
  resolvedPeopleNames?: string[],
): InferredDomainPattern | null {
  // Filter to same-domain, valid, work emails
  const domainEmails = observedEmails.filter(
    (e) => e.domain === domain && isValidWorkEmail(e.email),
  );

  if (domainEmails.length === 0) return null;

  const personSpecific = domainEmails.filter((e) => !isGenericInbox(e.localPart));
  const patternVotes = new Map<EmailPatternType, string[]>();

  // Try matching against known people names
  if (resolvedPeopleNames && resolvedPeopleNames.length > 0) {
    for (const email of personSpecific) {
      for (const name of resolvedPeopleNames) {
        const pattern = classifyEmailPattern(email.localPart, name);
        if (pattern !== "UNKNOWN") {
          const list = patternVotes.get(pattern) ?? [];
          list.push(email.email);
          patternVotes.set(pattern, list);
        }
      }
    }
  }

  // If no name-based matches, try structural heuristics
  if (patternVotes.size === 0) {
    for (const email of personSpecific) {
      const pattern = guessStructuralPattern(email.localPart);
      if (pattern !== "UNKNOWN") {
        const list = patternVotes.get(pattern) ?? [];
        list.push(email.email);
        patternVotes.set(pattern, list);
      }
    }
  }

  // Pick the pattern with most votes
  let bestPattern: EmailPatternType = "UNKNOWN";
  let bestEmails: string[] = [];
  let bestCount = 0;

  for (const [pattern, emails] of patternVotes) {
    if (emails.length > bestCount) {
      bestCount = emails.length;
      bestPattern = pattern;
      bestEmails = emails;
    }
  }

  // Score confidence
  const notes: string[] = [];
  let confidence = 0;

  if (bestPattern !== "UNKNOWN") {
    confidence = 50; // base for having any pattern

    if (bestCount >= 2) {
      confidence += 25;
      notes.push(`${bestCount} emails match pattern`);
    } else {
      notes.push("single email evidence");
    }

    if (personSpecific.length >= 2) {
      confidence += 10;
      notes.push(`${personSpecific.length} person-specific emails on domain`);
    }

    // Name-matched evidence is stronger
    if (resolvedPeopleNames && resolvedPeopleNames.length > 0) {
      const nameMatched = personSpecific.some((e) =>
        resolvedPeopleNames.some(
          (n) => classifyEmailPattern(e.localPart, n) !== "UNKNOWN",
        ),
      );
      if (nameMatched) {
        confidence += 15;
        notes.push("pattern confirmed against known name");
      }
    }
  } else if (personSpecific.length > 0) {
    // Have person-specific emails but couldn't classify pattern
    confidence = 30;
    notes.push("person-specific emails found but pattern unclear");
  } else if (domainEmails.length > 0) {
    // Only generic inboxes
    confidence = 10;
    notes.push("only generic inboxes found");
  }

  return {
    domain,
    patternType: bestPattern,
    confidenceScore: confidence,
    evidenceEmails: bestEmails.length > 0
      ? bestEmails
      : domainEmails.slice(0, 3).map((e) => e.email),
    notes,
  };
}
