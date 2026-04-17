import type {
  EmailPatternType,
  InferredDomainPattern,
  GeneratedEmailCandidate,
  EmailConfidenceLabel,
} from "../types/email";
import type { TargetRole } from "../types/prospect";
import { normalizeNameForEmail, isPersonalDomain } from "./emailUtils";

// ---------------------------------------------------------------------------
// Pattern-based email generation
// ---------------------------------------------------------------------------

function buildEmail(
  parts: { first: string; last: string; firstInitial: string },
  pattern: EmailPatternType,
): string | null {
  switch (pattern) {
    case "FIRST_LAST":
    case "FIRST.DOT.LAST":
      return `${parts.first}.${parts.last}`;
    case "FIRSTLAST":
      return `${parts.first}${parts.last}`;
    case "F_LAST":
      return `${parts.firstInitial}${parts.last}`;
    case "F.DOT.LAST":
      return `${parts.firstInitial}.${parts.last}`;
    case "FIRST":
      return parts.first;
    case "LAST":
      return parts.last;
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Standard fallback set (when no pattern known)
// ---------------------------------------------------------------------------

const FALLBACK_PATTERNS: EmailPatternType[] = [
  "FIRST_LAST",
  "FIRSTLAST",
  "FIRST",
  "F.DOT.LAST",
  "F_LAST",
];

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function generateEmailCandidatesForPerson(
  personName: string,
  domain: string,
  inferredPattern: InferredDomainPattern | null,
  role: TargetRole,
): GeneratedEmailCandidate[] {
  if (isPersonalDomain(domain)) return [];

  const nameParts = normalizeNameForEmail(personName);
  if (!nameParts) return [];

  const candidates: GeneratedEmailCandidate[] = [];
  const seen = new Set<string>();

  function add(
    localPart: string,
    pattern: EmailPatternType,
    score: number,
    evidence: string[],
  ) {
    const email = `${localPart}@${domain}`;
    if (seen.has(email)) return;
    seen.add(email);

    let label: EmailConfidenceLabel;
    if (score >= 90) label = "STRONG";
    else if (score >= 70) label = "PROBABLE";
    else label = "WEAK";

    candidates.push({
      email,
      domain,
      patternType: pattern,
      personName,
      role,
      evidence,
      confidenceScore: score,
      confidenceLabel: label,
    });
  }

  // If we have an inferred pattern with decent confidence, prioritize it
  if (
    inferredPattern &&
    inferredPattern.patternType !== "UNKNOWN" &&
    inferredPattern.confidenceScore >= 40
  ) {
    const local = buildEmail(nameParts, inferredPattern.patternType);
    if (local) {
      add(local, inferredPattern.patternType, inferredPattern.confidenceScore, [
        `pattern ${inferredPattern.patternType} inferred from: ${inferredPattern.evidenceEmails.join(", ")}`,
        ...inferredPattern.notes,
      ]);
    }
  }

  // Generate fallback candidates at lower confidence
  const fallbackScore = inferredPattern
    ? Math.max(inferredPattern.confidenceScore - 20, 20)
    : 30;

  for (const pattern of FALLBACK_PATTERNS) {
    if (candidates.length >= 5) break;
    const local = buildEmail(nameParts, pattern);
    if (local) {
      add(local, pattern, fallbackScore, [`fallback pattern: ${pattern}`]);
    }
  }

  return candidates.slice(0, 5);
}

export function generateFallbackEmailCandidates(
  personName: string,
  domain: string,
  role: TargetRole,
): GeneratedEmailCandidate[] {
  return generateEmailCandidatesForPerson(personName, domain, null, role);
}
