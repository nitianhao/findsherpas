import type { PlannedRoleTask } from "../types/tasks";
import type { CompanyDiscoveryResult } from "../types/discovery";
import type {
  ParsedIdentityCandidate,
  RankedIdentityCandidate,
} from "../types/search";

// ---------------------------------------------------------------------------
// Penalty patterns
// ---------------------------------------------------------------------------

const RECRUITER_PATTERNS = [
  /\brecruit/i, /\bjob\s+post/i, /\bhiring\b/i,
  /\bcareer/i, /\bglassdoor/i, /\bindeed\.com/i, /\bapply\s+now/i,
];

const DIRECTORY_PATTERNS = [
  /\bzoominfo/i, /\brocketreach/i, /\bapollo\.io/i,
  /\bsignalhire/i, /\bcontactout/i, /\blusha/i,
  /\bpeople\s+directory/i, /\bdnb\.com/i, /\bbloomberg\.com\/profile/i,
];

const FORMER_PATTERNS = [
  /\bformer\b/i, /\bex-\b/i, /\bpreviously\b/i,
  /\bformerly\b/i, /\bleft\b.*\bcompany/i,
];

const LINKEDIN_POST_PATTERNS = [
  /^beitrag von\b/i, /^post by\b/i, /^post von\b/i,
  /\bactivity-\d+/i, /\/posts?\//i,
];

// ---------------------------------------------------------------------------
// Ranker
// ---------------------------------------------------------------------------

export function rankIdentityCandidates(
  task: PlannedRoleTask,
  parsedCandidates: ParsedIdentityCandidate[],
  discoveryResult?: CompanyDiscoveryResult | null,
): RankedIdentityCandidate[] {
  const ranked = parsedCandidates.map((c) =>
    scoreSingle(task, c, discoveryResult),
  );
  ranked.sort((a, b) => b.rankScore - a.rankScore);
  return ranked;
}

function scoreSingle(
  task: PlannedRoleTask,
  candidate: ParsedIdentityCandidate,
  discoveryResult?: CompanyDiscoveryResult | null,
): RankedIdentityCandidate {
  let score = 0;
  const reasons: string[] = [];
  const context = `${candidate.sourceTitle} ${candidate.sourceSnippet} ${candidate.sourceUrl}`;

  // +40 LinkedIn person profile URL
  if (candidate.linkedinUrl && candidate.linkedinUrl.includes("/in/")) {
    score += 40;
    reasons.push("+40 linkedin-person-profile");
  }

  // +25 LINKEDIN_TITLE_ROLE_MATCH (new)
  if (candidate.evidenceSignals.includes("LINKEDIN_TITLE_ROLE_MATCH")) {
    score += 25;
    reasons.push("+25 linkedin-title-role-match");
  }

  // +25 exact company name in title/snippet
  if (context.toLowerCase().includes(task.companyName.toLowerCase())) {
    score += 25;
    reasons.push("+25 company-name-match");
  }

  // +20 domain/company token match
  const domain = extractDomain(task.websiteUrl);
  if (domain && context.toLowerCase().includes(domain.split(".")[0])) {
    score += 20;
    reasons.push("+20 domain-token-match");
  }

  // +20 role keyword in title/snippet (from identity parser)
  if (candidate.evidenceSignals.includes("role-evidence")) {
    score += 20;
    reasons.push("+20 role-keyword-match");
  }

  // +15 LINKEDIN_PROFILE_SLUG_MATCHES_NAME (new)
  if (candidate.evidenceSignals.includes("LINKEDIN_PROFILE_SLUG_MATCHES_NAME")) {
    score += 15;
    reasons.push("+15 linkedin-slug-matches-name");
  }

  // +10 COMPANY_MATCH_FROM_TITLE (new)
  if (candidate.evidenceSignals.includes("COMPANY_MATCH_FROM_TITLE")) {
    score += 10;
    reasons.push("+10 company-match-from-title");
  }

  // +10 country match for EU
  if (task.region === "EU" && task.country) {
    if (context.toLowerCase().includes(task.country.toLowerCase())) {
      score += 10;
      reasons.push("+10 country-match");
    }
  }

  // +8 website discovery matching evidence
  if (discoveryResult) {
    const nameInDiscovery = discoveryResult.personCandidates.some(
      (p) => p.normalizedName === candidate.normalizedName,
    );
    if (nameInDiscovery) {
      score += 8;
      reasons.push("+8 name-in-website-evidence");
    }

    const linkedinInDiscovery =
      candidate.linkedinUrl &&
      discoveryResult.linkedinCandidates.some(
        (l) => l.url === candidate.linkedinUrl,
      );
    if (linkedinInDiscovery) {
      score += 8;
      reasons.push("+8 linkedin-in-website-evidence");
    }
  }

  // Penalties

  // -20 LinkedIn post/activity (not actual profile)
  if (LINKEDIN_POST_PATTERNS.some((p) => p.test(candidate.sourceTitle) || p.test(candidate.sourceUrl))) {
    score -= 20;
    reasons.push("-20 linkedin-post-not-profile");
  }

  if (RECRUITER_PATTERNS.some((p) => p.test(context))) {
    score -= 25;
    reasons.push("-25 recruiter-job-posting");
  }

  if (DIRECTORY_PATTERNS.some((p) => p.test(context))) {
    score -= 20;
    reasons.push("-20 people-directory");
  }

  if (FORMER_PATTERNS.some((p) => p.test(context))) {
    score -= 15;
    reasons.push("-15 former-employee");
  }

  // -30 if no reliable name
  if (!candidate.fullName || candidate.fullName.split(/\s+/).length < 2) {
    score -= 30;
    reasons.push("-30 unreliable-name");
  }

  return {
    ...candidate,
    confidenceScore: score,
    rankScore: score,
    rankReasons: reasons,
  };
}

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}
