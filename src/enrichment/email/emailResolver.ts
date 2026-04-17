import type { CompanyDiscoveryResult } from "../types/discovery";
import type { ResolvedRoleDecision } from "../types/resolution";
import type {
  ResolvedEmailDecision,
  EmailConfidenceLabel,
  ObservedWorkEmail,
  InferredDomainPattern,
} from "../types/email";
import {
  extractDomain,
  isValidWorkEmail,
  isGenericInbox,
  isPersonalDomain,
  splitEmail,
  normalizeNameForEmail,
  stripAccents,
} from "./emailUtils";
import { classifyEmailPattern, inferDomainPatternFromObservedEmails } from "./emailPatternInference";
import { generateEmailCandidatesForPerson } from "./emailGenerator";

// ---------------------------------------------------------------------------
// Extract observed work emails from discovery
// ---------------------------------------------------------------------------

function extractObservedWorkEmails(
  discovery: CompanyDiscoveryResult | null,
): ObservedWorkEmail[] {
  if (!discovery) return [];

  return discovery.emailCandidates
    .filter((e) => isValidWorkEmail(e.email))
    .map((e) => ({
      email: e.email,
      domain: e.domain,
      localPart: e.localPart,
      sourceFile: discovery.sourceFile,
      sheetName: discovery.sheetName,
      rowIndex: discovery.rowIndex,
      companyName: discovery.companyName,
      pageUrl: e.pageUrl,
      pageType: e.pageType,
      sourceType: e.sourceType,
      confidenceSignals: e.confidenceSignals,
    }));
}

// ---------------------------------------------------------------------------
// Check if an observed email matches a person name
// ---------------------------------------------------------------------------

function emailMatchesPerson(
  email: ObservedWorkEmail,
  personName: string,
): boolean {
  if (isGenericInbox(email.localPart)) return false;

  const pattern = classifyEmailPattern(email.localPart, personName);
  if (pattern !== "UNKNOWN") return true;

  // Fuzzy: check if local part contains significant name tokens
  const parts = normalizeNameForEmail(personName);
  if (!parts) return false;

  const local = email.localPart.toLowerCase();
  const { first, last } = parts;

  // If local part contains last name (3+ chars) — likely match
  if (last.length >= 3 && local.includes(last)) return true;

  return false;
}

// ---------------------------------------------------------------------------
// Resolve email for a role decision
// ---------------------------------------------------------------------------

export function resolveEmailForRole(
  roleDecision: ResolvedRoleDecision,
  discovery: CompanyDiscoveryResult | null,
): ResolvedEmailDecision {
  const personName = roleDecision.chosenCandidate?.fullName ?? "";
  const companyDomain = extractDomain(roleDecision.websiteUrl);

  const decision: ResolvedEmailDecision = {
    sourceFile: roleDecision.sourceFile,
    sheetName: roleDecision.sheetName,
    rowIndex: roleDecision.rowIndex,
    companyName: roleDecision.companyName,
    websiteUrl: roleDecision.websiteUrl,
    role: roleDecision.role,
    personName,
    status: "UNRESOLVED",
    chosenEmail: null,
    alternateEmails: [],
    inferredPattern: null,
    evidence: [],
    confidenceScore: 0,
    confidenceLabel: null,
    blockingIssues: [],
  };

  // Bail if no resolved person
  if (!roleDecision.chosenCandidate || !personName) {
    decision.blockingIssues.push("No resolved person for this role");
    return decision;
  }

  if (!companyDomain) {
    decision.blockingIssues.push("Cannot determine company domain from URL");
    return decision;
  }

  if (isPersonalDomain(companyDomain)) {
    decision.blockingIssues.push(`Domain ${companyDomain} is a personal email provider`);
    return decision;
  }

  const roleStatus = roleDecision.status;
  const observedEmails = extractObservedWorkEmails(discovery);

  // Find observed emails on the company domain
  const domainEmails = observedEmails.filter((e) => e.domain === companyDomain);
  const personSpecificEmails = domainEmails.filter((e) => !isGenericInbox(e.localPart));

  // -------------------------------------------------------------------
  // Resolution path 1: Public work email matching the person
  // -------------------------------------------------------------------

  for (const email of personSpecificEmails) {
    if (emailMatchesPerson(email, personName)) {
      const pattern = classifyEmailPattern(email.localPart, personName);
      decision.status = "RESOLVED_PUBLIC";
      decision.chosenEmail = email.email;
      decision.confidenceScore = 95;
      decision.confidenceLabel = "STRONG";
      decision.evidence.push(
        `Public email ${email.email} found on ${email.pageType} page`,
        `Pattern: ${pattern}`,
        `Source: ${email.sourceType} on ${email.pageUrl}`,
      );
      return decision;
    }
  }

  // -------------------------------------------------------------------
  // Resolution path 2: Infer pattern + generate email
  // -------------------------------------------------------------------

  // Collect known person names for pattern inference
  const knownNames: string[] = [personName];
  if (discovery) {
    for (const p of discovery.personCandidates) {
      if (p.fullName && !knownNames.includes(p.fullName)) {
        knownNames.push(p.fullName);
      }
    }
  }

  const pattern = inferDomainPatternFromObservedEmails(
    companyDomain,
    domainEmails.map((e) => ({ email: e.email, localPart: e.localPart, domain: e.domain })),
    knownNames,
  );

  decision.inferredPattern = pattern;

  if (pattern) {
    decision.evidence.push(
      `Domain ${companyDomain}: ${domainEmails.length} emails found, ${personSpecificEmails.length} person-specific`,
      `Inferred pattern: ${pattern.patternType} (confidence: ${pattern.confidenceScore})`,
      ...pattern.notes,
    );
  }

  // Generate candidates
  const candidates = generateEmailCandidatesForPerson(
    personName,
    companyDomain,
    pattern,
    roleDecision.role,
  );

  if (candidates.length === 0) {
    decision.blockingIssues.push("Could not generate email candidates for this name/domain");
    return decision;
  }

  // Score adjustments based on role resolution strength
  const topCandidate = candidates[0];
  let adjustedScore = topCandidate.confidenceScore;
  const adjustReasons: string[] = [];

  if (roleStatus === "RESOLVED_STRONG") {
    adjustedScore += 20;
    adjustReasons.push("+20 person resolved STRONG");
  } else if (roleStatus === "RESOLVED_PROBABLE") {
    adjustedScore += 10;
    adjustReasons.push("+10 person resolved PROBABLE");
  }

  if (personSpecificEmails.length >= 2) {
    adjustedScore += 15;
    adjustReasons.push(`+15 ${personSpecificEmails.length} person-specific emails support pattern`);
  }

  // Penalties
  if (pattern && pattern.patternType === "UNKNOWN" && personSpecificEmails.length === 0) {
    adjustedScore -= 25;
    adjustReasons.push("-25 pattern based only on generic inboxes");
  }

  if (personSpecificEmails.length === 0 && domainEmails.length > 0) {
    adjustedScore -= 20;
    adjustReasons.push("-20 no person-specific email evidence on domain");
  }

  if (personSpecificEmails.length === 0 && domainEmails.length === 0) {
    adjustedScore -= 15;
    adjustReasons.push("-15 no email evidence at all on domain");
  }

  const nameParts = normalizeNameForEmail(personName);
  if (!nameParts || nameParts.allTokens.length > 3) {
    adjustedScore -= 15;
    adjustReasons.push("-15 name normalization ambiguous");
  }

  // Determine final label
  let label: EmailConfidenceLabel;
  if (adjustedScore >= 90) label = "STRONG";
  else if (adjustedScore >= 70) label = "PROBABLE";
  else label = "WEAK";

  // Conservative: never mark inferred as STRONG without person-email evidence
  if (label === "STRONG" && personSpecificEmails.length === 0) {
    label = "PROBABLE";
    adjustReasons.push("Downgraded from STRONG: no person-specific email evidence");
  }

  decision.status = "RESOLVED_INFERRED";
  decision.chosenEmail = topCandidate.email;
  decision.alternateEmails = candidates.slice(1);
  decision.confidenceScore = adjustedScore;
  decision.confidenceLabel = label;
  decision.evidence.push(
    `Generated: ${topCandidate.email} (pattern: ${topCandidate.patternType})`,
    ...adjustReasons,
  );

  // If score is too low, mark as unresolved instead
  if (adjustedScore <= 0) {
    decision.status = "UNRESOLVED";
    decision.chosenEmail = null;
    decision.confidenceLabel = null;
    decision.blockingIssues.push("Confidence too low to assign email");
  }

  return decision;
}
