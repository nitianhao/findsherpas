import type { PlannedRoleTask } from "../types/tasks";
import type { ResolvedRoleDecision } from "../types/resolution";
import type { ResolvedEmailDecision } from "../types/email";
import type { WritebackEligibilityDecision } from "../types/quality";
import type { WriteAction } from "../types/writeback";
import type { CompanyDiscoveryResult } from "../types/discovery";
import type { RoleSearchCompositeResult } from "../types/search";
import type {
  ReviewQueueItem,
  ReviewQueueSummary,
  ReviewBucket,
  ReviewPriority,
} from "../types/review";
import { extractDomain } from "../email/emailUtils";

// ---------------------------------------------------------------------------
// Input for a single role decision
// ---------------------------------------------------------------------------

export interface ReviewInput {
  task: PlannedRoleTask;
  roleDecision: ResolvedRoleDecision;
  emailDecision: ResolvedEmailDecision | null;
  eligibility: WritebackEligibilityDecision;
  writeActions: WriteAction[];
  discovery: CompanyDiscoveryResult | null;
  search: RoleSearchCompositeResult | null;
}

// ---------------------------------------------------------------------------
// Bucket assignment
// ---------------------------------------------------------------------------

function assignBuckets(input: ReviewInput): ReviewQueueItem[] {
  const items: ReviewQueueItem[] = [];
  const {
    task,
    roleDecision,
    emailDecision,
    eligibility,
    writeActions,
    discovery,
    search,
  } = input;

  const roleStatus = roleDecision.status;
  const candidate = roleDecision.chosenCandidate;
  const plausibility = eligibility.plausibility;
  const emailStatus = emailDecision?.status ?? "UNRESOLVED";
  const wbStatus = eligibility.overallStatus;

  // Skip if nothing to review
  if (!candidate && roleStatus === "UNRESOLVED_NONE") return items;

  // Helper to build base item
  function base(bucket: ReviewBucket, priority: ReviewPriority): ReviewQueueItem {
    return {
      sourceFile: task.sourceFile,
      sheetName: task.sheetName,
      rowIndex: task.rowIndex,
      region: task.region,
      companyName: task.companyName,
      websiteUrl: task.websiteUrl,
      country: task.country,
      role: task.role,
      bucket,
      priority,
      currentWorkbookValues: {
        existingName: task.existingSignals.existingName,
        existingLinkedin: task.existingSignals.existingLinkedin,
        existingEmail: task.existingSignals.existingEmail,
      },
      candidateValues: {
        candidateName: candidate?.fullName ?? null,
        candidateLinkedin: candidate?.linkedinUrl ?? null,
        candidateEmail: emailDecision?.chosenEmail ?? null,
      },
      statusSummary: {
        roleStatus,
        emailStatus,
        plausibilityStatus: plausibility.status,
        writebackEligibility: wbStatus,
      },
      scores: {
        roleScore: candidate?.confidenceScore ?? 0,
        emailScore: emailDecision?.confidenceScore ?? 0,
        plausibilityScore: plausibility.score,
      },
      evidenceSummary: [],
      blockerSummary: [],
      suggestedHumanAction: "",
      rawReferences: {
        topSearchQueries: search?.queryPlans?.map((q) => q.query).slice(0, 3) ?? [],
        topSearchUrls: search?.rawSearchResults?.map((r) => r.url).slice(0, 5) ?? [],
        topWebsitePages: discovery?.discoveredPages?.map((p) => p.url).slice(0, 3) ?? [],
      },
    };
  }

  // Check which write actions were applied vs skipped
  const hasWriteCell = writeActions.some((a) => a.actionType === "WRITE_CELL");
  const hasSkipExisting = writeActions.some((a) => a.actionType === "SKIP_EXISTING_VALUE");
  const hasSkipNotApproved = writeActions.some((a) => a.actionType === "SKIP_NOT_APPROVED");

  // A: ROLE_PROBABLE_NOT_WRITTEN
  // Check if name was already written (existing matches candidate — prior run)
  const nameAlreadyPresent =
    candidate &&
    task.existingSignals.existingName.trim().toLowerCase() ===
      candidate.fullName.trim().toLowerCase();

  if (
    roleStatus === "RESOLVED_PROBABLE" &&
    plausibility.status === "PLAUSIBLE" &&
    !hasWriteCell &&
    !nameAlreadyPresent
  ) {
    const item = base("ROLE_PROBABLE_NOT_WRITTEN", "HIGH");
    item.evidenceSummary = candidate?.evidence.slice(0, 5) ?? [];
    item.blockerSummary = writeActions
      .filter((a) => a.actionType !== "WRITE_CELL" && a.actionType !== "SKIP_EMPTY_VALUE")
      .map((a) => `${a.actionType}: ${a.reason}`)
      .slice(0, 3);
    item.suggestedHumanAction = candidate?.linkedinUrl
      ? "Check candidate LinkedIn manually and confirm role"
      : "Search for this person on LinkedIn to verify role";
    items.push(item);
  }

  // B: ROLE_WEAK_WITH_CANDIDATE
  if (
    roleStatus === "UNRESOLVED_WEAK" &&
    candidate &&
    (plausibility.status === "PLAUSIBLE" || plausibility.status === "SUSPICIOUS")
  ) {
    const priority: ReviewPriority = plausibility.status === "PLAUSIBLE" ? "MEDIUM" : "LOW";
    const item = base("ROLE_WEAK_WITH_CANDIDATE", priority);
    item.evidenceSummary = candidate.evidence.slice(0, 5);
    item.blockerSummary = [`Role score ${candidate.confidenceScore} below threshold`];
    item.suggestedHumanAction = candidate.linkedinUrl
      ? "Check candidate LinkedIn manually and confirm role"
      : "Search company team page or LinkedIn for this person";
    items.push(item);
  }

  // C: INVALID_PERSON_BUT_HIGH_SIGNAL
  if (
    plausibility.status === "IMPLAUSIBLE" &&
    candidate &&
    candidate.confidenceScore >= 60
  ) {
    const item = base("INVALID_PERSON_BUT_HIGH_SIGNAL", "LOW");
    item.evidenceSummary = candidate.evidence.slice(0, 5);
    item.blockerSummary = [
      `Plausibility: ${plausibility.status} (${plausibility.score})`,
      ...plausibility.negativeSignals.slice(0, 3),
    ];
    item.suggestedHumanAction = "Discard likely false positive, or investigate if name was misextracted";
    items.push(item);
  }

  // D: EMAIL_INFERRED_WEAK — only for plausible persons with resolved roles
  if (
    plausibility.status === "PLAUSIBLE" &&
    emailDecision?.status === "RESOLVED_INFERRED" &&
    emailDecision.confidenceLabel === "WEAK" &&
    emailDecision.chosenEmail &&
    (roleStatus === "RESOLVED_STRONG" || roleStatus === "RESOLVED_PROBABLE")
  ) {
    const domain = extractDomain(task.websiteUrl);
    const priority: ReviewPriority =
      roleStatus === "RESOLVED_STRONG" ? "HIGH" : "MEDIUM";
    const item = base("EMAIL_INFERRED_WEAK", priority);
    item.evidenceSummary = emailDecision.evidence.slice(0, 5);
    item.blockerSummary = emailDecision.blockingIssues.slice(0, 3);
    if (emailDecision.inferredPattern) {
      item.evidenceSummary.push(
        `Pattern: ${emailDecision.inferredPattern.patternType} (${emailDecision.inferredPattern.confidenceScore})`,
      );
    }
    item.suggestedHumanAction = `Use Hunter.io or manual search to verify ${emailDecision.chosenEmail} on ${domain}`;
    items.push(item);
  }

  // E: EMAIL_UNRESOLVED_BUT_DOMAIN_KNOWN
  if (
    plausibility.status === "PLAUSIBLE" &&
    candidate &&
    (roleStatus === "RESOLVED_STRONG" || roleStatus === "RESOLVED_PROBABLE") &&
    emailStatus === "UNRESOLVED" &&
    discovery
  ) {
    const domain = extractDomain(task.websiteUrl);
    const hasGenericEmails = discovery.emailCandidates.some(
      (e) => e.domain === domain,
    );
    if (hasGenericEmails) {
      const item = base("EMAIL_UNRESOLVED_BUT_DOMAIN_KNOWN", "MEDIUM");
      item.evidenceSummary = [
        `Domain ${domain} has ${discovery.emailCandidates.filter((e) => e.domain === domain).length} email(s) found`,
        ...emailDecision?.blockingIssues.slice(0, 3) ?? [],
      ];
      item.blockerSummary = emailDecision?.blockingIssues.slice(0, 3) ?? [];
      item.suggestedHumanAction = `Search company/team page manually for email pattern on ${domain}`;
      items.push(item);
    }
  }

  // F: SEARCH_GOOD_LINKEDIN_BUT_ROLE_UNCLEAR
  if (
    candidate &&
    candidate.linkedinUrl &&
    candidate.linkedinUrl.includes("/in/") &&
    plausibility.status === "PLAUSIBLE" &&
    (roleStatus === "UNRESOLVED_WEAK" || roleStatus === "RESOLVED_PROBABLE") &&
    candidate.confidenceScore >= 40
  ) {
    // Only add if not already covered by bucket A or B
    const alreadyCovered = items.some(
      (i) =>
        i.bucket === "ROLE_PROBABLE_NOT_WRITTEN" ||
        i.bucket === "ROLE_WEAK_WITH_CANDIDATE",
    );
    if (!alreadyCovered) {
      const item = base("SEARCH_GOOD_LINKEDIN_BUT_ROLE_UNCLEAR", "HIGH");
      item.evidenceSummary = candidate.evidence.slice(0, 5);
      item.blockerSummary = ["Explicit role evidence was insufficient"];
      item.suggestedHumanAction =
        "Check candidate LinkedIn profile to verify current role at this company";
      items.push(item);
    }
  }

  // G: EXISTING_CELL_BLOCKED_NEW_VALUE
  if (hasSkipExisting && candidate) {
    const skippedExisting = writeActions.filter(
      (a) => a.actionType === "SKIP_EXISTING_VALUE",
    );
    for (const action of skippedExisting) {
      // Skip if existing value matches new value (already written in prior run)
      if (
        action.oldValue.trim().toLowerCase() ===
        (action.newValue ?? "").trim().toLowerCase()
      ) {
        continue;
      }

      const priority: ReviewPriority =
        roleStatus === "RESOLVED_STRONG" ? "HIGH" : "MEDIUM";
      const item = base("EXISTING_CELL_BLOCKED_NEW_VALUE", priority);
      item.evidenceSummary = [
        `Column: ${action.columnName}`,
        `Existing: "${action.oldValue}"`,
        `New candidate: "${action.newValue}"`,
        ...candidate.evidence.slice(0, 3),
      ];
      item.blockerSummary = [action.reason];
      item.suggestedHumanAction = `Verify if existing workbook value "${action.oldValue}" should be replaced with "${action.newValue}"`;
      items.push(item);
    }
  }

  return items;
}

// ---------------------------------------------------------------------------
// Build full review queue
// ---------------------------------------------------------------------------

export function buildReviewQueue(inputs: ReviewInput[]): ReviewQueueItem[] {
  const allItems: ReviewQueueItem[] = [];

  for (const input of inputs) {
    const items = assignBuckets(input);
    allItems.push(...items);
  }

  // Dedupe: one item per (sourceFile, rowIndex, role, bucket)
  const seen = new Set<string>();
  const deduped: ReviewQueueItem[] = [];
  for (const item of allItems) {
    const key = `${item.sourceFile}|${item.rowIndex}|${item.role}|${item.bucket}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(item);
  }

  // Sort: priority (HIGH > MEDIUM > LOW), then bucket, then descending role score
  const priorityOrder: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };
  deduped.sort((a, b) => {
    const pDiff = (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3);
    if (pDiff !== 0) return pDiff;
    const bDiff = a.bucket.localeCompare(b.bucket);
    if (bDiff !== 0) return bDiff;
    return b.scores.roleScore - a.scores.roleScore;
  });

  return deduped;
}

// ---------------------------------------------------------------------------
// Summarize
// ---------------------------------------------------------------------------

export function summarizeReviewQueue(items: ReviewQueueItem[]): ReviewQueueSummary {
  const byBucket: Record<string, number> = {};
  const byPriority: Record<string, number> = {};
  const byRole: Record<string, number> = {};
  const byWorkbook: Record<string, number> = {};

  for (const item of items) {
    byBucket[item.bucket] = (byBucket[item.bucket] ?? 0) + 1;
    byPriority[item.priority] = (byPriority[item.priority] ?? 0) + 1;
    byRole[item.role] = (byRole[item.role] ?? 0) + 1;
    byWorkbook[item.sourceFile] = (byWorkbook[item.sourceFile] ?? 0) + 1;
  }

  return {
    totalItems: items.length,
    byBucket,
    byPriority,
    byRole,
    byWorkbook,
  };
}
