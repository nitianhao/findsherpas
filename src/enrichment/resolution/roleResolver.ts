import type { PlannedRoleTask, PlannedRowTask } from "../types/tasks";
import type { CompanyDiscoveryResult } from "../types/discovery";
import type {
  RoleSearchCompositeResult,
  RankedIdentityCandidate,
} from "../types/search";
import type { TargetRole } from "../types/prospect";
import type {
  ResolvedRoleDecision,
  ResolvedRoleCandidate,
  ResolvedRoleStatus,
  ResolvedRowDecision,
  ConfidenceLabel,
} from "../types/resolution";

// ---------------------------------------------------------------------------
// Name matching
// ---------------------------------------------------------------------------

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, " ").toLowerCase();
}

function tokenOverlap(a: string, b: string): number {
  const tokA = new Set(normalizeName(a).split(" "));
  const tokB = new Set(normalizeName(b).split(" "));
  let overlap = 0;
  for (const t of tokA) {
    if (tokB.has(t) && t.length > 1) overlap++;
  }
  const minSize = Math.min(tokA.size, tokB.size);
  return minSize > 0 ? overlap / minSize : 0;
}

function namesMatch(a: string, b: string): boolean {
  if (normalizeName(a) === normalizeName(b)) return true;
  return tokenOverlap(a, b) >= 0.66;
}

// ---------------------------------------------------------------------------
// Role evidence keywords
// ---------------------------------------------------------------------------

const CEO_EVIDENCE = [
  "ceo", "chief executive", "founder", "co-founder", "cofounder",
  "managing director", "geschäftsführer", "geschaeftsfuehrer",
];

const ROLE_EVIDENCE: Record<string, string[]> = {
  CEO: CEO_EVIDENCE,
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
    "director of marketing",
  ],
};

function hasExplicitRoleEvidence(role: TargetRole, text: string): boolean {
  const lower = text.toLowerCase();
  const keywords = ROLE_EVIDENCE[role] ?? [];
  return keywords.some((kw) => lower.includes(kw));
}

// ---------------------------------------------------------------------------
// Negative patterns
// ---------------------------------------------------------------------------

const CAREERS_PATTERNS = [/\bcareer/i, /\bjobs?\b/i, /\bhiring/i, /\brecruit/i];
const ARTICLE_PATTERNS = [/\barticle\b/i, /\bpost\b/i, /\bnews\b/i, /\bblog\b/i, /\bpodcast\b/i];
const DIRECTORY_PATTERNS = [
  /\bzoominfo/i, /\brocketreach/i, /\bapollo\.io/i,
  /\bsignalhire/i, /\bcontactout/i, /\blusha/i,
  /\bpeople\s+directory/i, /\bdnb\.com/i,
];

const HIGH_VALUE_PAGE_TYPES = new Set(["ABOUT", "TEAM", "LEADERSHIP", "LEGAL", "HOMEPAGE"]);

// ---------------------------------------------------------------------------
// Merged candidate cluster
// ---------------------------------------------------------------------------

interface MergedCluster {
  primaryName: string;
  normalizedName: string;
  linkedinUrl: string;
  role: TargetRole;
  searchCandidates: RankedIdentityCandidate[];
  websitePersonMatches: { fullName: string; titleText: string; pageType: string; roleHints: string[] }[];
  websiteLinkedinMatches: string[];
  evidence: string[];
  baseScore: number;
}

// ---------------------------------------------------------------------------
// Core resolution
// ---------------------------------------------------------------------------

export function resolveRoleDecision(
  task: PlannedRoleTask,
  discovery: CompanyDiscoveryResult | null,
  search: RoleSearchCompositeResult | null,
): ResolvedRoleDecision {
  const decision: ResolvedRoleDecision = {
    sourceFile: task.sourceFile,
    sheetName: task.sheetName,
    rowIndex: task.rowIndex,
    region: task.region,
    companyName: task.companyName,
    websiteUrl: task.websiteUrl,
    country: task.country,
    role: task.role,
    status: "UNRESOLVED_NONE",
    chosenCandidate: null,
    alternateCandidates: [],
    blockingIssues: [],
    notes: [],
    rawSummary: {
      websitePersonCandidates: discovery?.personCandidates.length ?? 0,
      websiteLinkedinCandidates: discovery?.linkedinCandidates.length ?? 0,
      searchResultCount: search?.rawSearchResults.length ?? 0,
      parsedSearchCandidateCount: search?.parsedCandidates.length ?? 0,
      rankedSearchCandidateCount: search?.rankedCandidates.length ?? 0,
    },
  };

  // Build merged clusters
  const clusters = buildMergedClusters(task.role, discovery, search);

  if (clusters.length === 0) {
    decision.status = "UNRESOLVED_NONE";
    decision.notes.push("No viable candidates from any source");
    return decision;
  }

  // Score each cluster
  const scored = clusters.map((c) => scoreCluster(c, task));
  scored.sort((a, b) => b.finalScore - a.finalScore);

  // Convert to resolved candidates
  const resolved = scored.map((s) => toResolvedCandidate(s, task.role));

  // Apply status thresholds
  const top = resolved[0];
  decision.chosenCandidate = top;
  decision.alternateCandidates = resolved.slice(1, 4);

  if (top.confidenceScore >= 90 && top.fullName && (top.linkedinUrl || hasStrongWebsiteLeadershipEvidence(scored[0]))) {
    // For head-of roles, require explicit role evidence for STRONG
    if (task.role !== "CEO" && !scored[0].hasExplicitRole) {
      decision.status = "RESOLVED_PROBABLE";
      decision.notes.push("Strong score but no explicit role evidence for non-CEO role");
    } else {
      decision.status = "RESOLVED_STRONG";
    }
  } else if (top.confidenceScore >= 65 && top.fullName) {
    decision.status = "RESOLVED_PROBABLE";
  } else if (top.confidenceScore > 0) {
    decision.status = "UNRESOLVED_WEAK";
  } else {
    decision.status = "UNRESOLVED_NONE";
    decision.chosenCandidate = null;
    decision.alternateCandidates = resolved.slice(0, 3);
  }

  return decision;
}

// ---------------------------------------------------------------------------
// Cluster building
// ---------------------------------------------------------------------------

function buildMergedClusters(
  role: TargetRole,
  discovery: CompanyDiscoveryResult | null,
  search: RoleSearchCompositeResult | null,
): MergedCluster[] {
  const clusters: MergedCluster[] = [];
  const clusterByName = new Map<string, MergedCluster>();

  function getOrCreate(name: string, linkedinUrl: string): MergedCluster {
    const norm = normalizeName(name);
    // Try exact match first
    if (clusterByName.has(norm)) return clusterByName.get(norm)!;
    // Try fuzzy match
    for (const [key, cluster] of clusterByName) {
      if (namesMatch(name, cluster.primaryName)) return cluster;
    }
    const cluster: MergedCluster = {
      primaryName: name,
      normalizedName: norm,
      linkedinUrl,
      role,
      searchCandidates: [],
      websitePersonMatches: [],
      websiteLinkedinMatches: [],
      evidence: [],
      baseScore: 0,
    };
    clusterByName.set(norm, cluster);
    clusters.push(cluster);
    return cluster;
  }

  // Add search candidates (primary source)
  if (search) {
    for (const sc of search.rankedCandidates) {
      if (!sc.fullName || sc.fullName.trim().length < 3) continue;
      const cluster = getOrCreate(sc.fullName, sc.linkedinUrl);
      cluster.searchCandidates.push(sc);
      if (sc.linkedinUrl && !cluster.linkedinUrl) {
        cluster.linkedinUrl = sc.linkedinUrl;
      }
      cluster.baseScore = Math.max(cluster.baseScore, sc.rankScore);
    }
  }

  // Add website person candidates (supportive)
  if (discovery) {
    for (const wp of discovery.personCandidates) {
      if (!wp.fullName || wp.fullName.trim().length < 3) continue;
      // Only add website persons that have role hints relevant to this role
      const roleRelevant = wp.matchedRoleHints.includes(role) ||
        wp.matchedRoleHints.some((h) => h === role);
      const hasAnyRoleHint = wp.matchedRoleHints.length > 0;

      // If this person matches an existing search cluster, add as support
      let matched = false;
      for (const cluster of clusters) {
        if (namesMatch(wp.fullName, cluster.primaryName)) {
          cluster.websitePersonMatches.push({
            fullName: wp.fullName,
            titleText: wp.titleText,
            pageType: wp.pageType,
            roleHints: wp.matchedRoleHints,
          });
          matched = true;
          break;
        }
      }

      // Only create new cluster from website if it has a strong role hint
      if (!matched && roleRelevant && hasAnyRoleHint) {
        const cluster = getOrCreate(wp.fullName, "");
        cluster.websitePersonMatches.push({
          fullName: wp.fullName,
          titleText: wp.titleText,
          pageType: wp.pageType,
          roleHints: wp.matchedRoleHints,
        });
      }
    }

    // Associate website LinkedIn URLs with clusters if possible
    for (const li of discovery.linkedinCandidates) {
      if (li.sourceType !== "PERSON_PROFILE") continue;
      for (const cluster of clusters) {
        if (cluster.linkedinUrl === li.url) {
          cluster.websiteLinkedinMatches.push(li.url);
          break;
        }
      }
    }
  }

  return clusters;
}

// ---------------------------------------------------------------------------
// Cluster scoring
// ---------------------------------------------------------------------------

interface ScoredCluster {
  cluster: MergedCluster;
  finalScore: number;
  hasExplicitRole: boolean;
  evidence: string[];
}

function scoreCluster(cluster: MergedCluster, task: PlannedRoleTask): ScoredCluster {
  let score = cluster.baseScore;
  const evidence: string[] = [];
  let hasExplicitRole = false;

  // +20 if same person in 2+ independent search results
  if (cluster.searchCandidates.length >= 2) {
    score += 20;
    evidence.push(`+20 appears in ${cluster.searchCandidates.length} search results`);
  }

  // Check role evidence across all search candidates
  const allSearchText = cluster.searchCandidates
    .map((c) => `${c.sourceTitle} ${c.sourceSnippet}`)
    .join(" ");
  if (hasExplicitRoleEvidence(task.role, allSearchText)) {
    hasExplicitRole = true;
    evidence.push("explicit-role-evidence-in-search");
  }

  // +15 if website person with role hint supports
  const websiteRoleMatches = cluster.websitePersonMatches.filter(
    (wp) => wp.roleHints.length > 0,
  );
  if (websiteRoleMatches.length > 0) {
    score += 15;
    evidence.push(`+15 website person with role hint (${websiteRoleMatches[0].titleText.slice(0, 50)})`);
    if (!hasExplicitRole) {
      // Check website evidence for role too
      const websiteText = cluster.websitePersonMatches
        .map((wp) => `${wp.titleText} ${wp.roleHints.join(" ")}`)
        .join(" ");
      if (hasExplicitRoleEvidence(task.role, websiteText)) {
        hasExplicitRole = true;
        evidence.push("explicit-role-evidence-in-website");
      }
    }
  }

  // +10 if website LinkedIn evidence matches
  if (cluster.websiteLinkedinMatches.length > 0) {
    score += 10;
    evidence.push("+10 website LinkedIn URL corroboration");
  }

  // +8 if person appears on high-value page
  const highValuePages = cluster.websitePersonMatches.filter(
    (wp) => HIGH_VALUE_PAGE_TYPES.has(wp.pageType),
  );
  if (highValuePages.length > 0) {
    score += 8;
    evidence.push(`+8 found on ${highValuePages[0].pageType} page`);
  }

  // Penalties

  // -20 if support only from careers context
  const allText = `${allSearchText} ${cluster.websitePersonMatches.map((wp) => wp.titleText).join(" ")}`;
  const isCareersOnly = CAREERS_PATTERNS.some((p) => p.test(allText)) &&
    !cluster.linkedinUrl &&
    cluster.searchCandidates.length <= 1;
  if (isCareersOnly) {
    score -= 20;
    evidence.push("-20 careers/job-posting context only");
  }

  // -15 if only weak name parse and no LinkedIn
  if (!cluster.linkedinUrl && cluster.searchCandidates.length <= 1) {
    score -= 15;
    evidence.push("-15 weak name parse, no LinkedIn URL");
  }

  // -25 if evidence suggests article mention
  if (ARTICLE_PATTERNS.some((p) => p.test(allText)) &&
    !cluster.linkedinUrl &&
    cluster.searchCandidates.length <= 1) {
    score -= 25;
    evidence.push("-25 likely article/post mention, not actual profile");
  }

  // -30 if only from directory source
  if (DIRECTORY_PATTERNS.some((p) => p.test(allText)) &&
    cluster.searchCandidates.length <= 1 &&
    cluster.websitePersonMatches.length === 0) {
    score -= 30;
    evidence.push("-30 people-directory source only");
  }

  // -20 if role evidence is ambiguous for non-CEO
  if (task.role !== "CEO" && !hasExplicitRole && cluster.searchCandidates.length > 0) {
    score -= 20;
    evidence.push("-20 no explicit role evidence for non-CEO role");
  }

  return { cluster, finalScore: score, hasExplicitRole, evidence };
}

function hasStrongWebsiteLeadershipEvidence(scored: ScoredCluster): boolean {
  return scored.cluster.websitePersonMatches.some(
    (wp) => wp.roleHints.length > 0 && HIGH_VALUE_PAGE_TYPES.has(wp.pageType),
  );
}

// ---------------------------------------------------------------------------
// Convert to output types
// ---------------------------------------------------------------------------

function toResolvedCandidate(
  scored: ScoredCluster,
  role: TargetRole,
): ResolvedRoleCandidate {
  const c = scored.cluster;
  const sourceKinds: ("SEARCH" | "WEBSITE")[] = [];
  if (c.searchCandidates.length > 0) sourceKinds.push("SEARCH");
  if (c.websitePersonMatches.length > 0 || c.websiteLinkedinMatches.length > 0) {
    sourceKinds.push("WEBSITE");
  }

  let label: ConfidenceLabel;
  if (scored.finalScore >= 90) label = "STRONG";
  else if (scored.finalScore >= 65) label = "PROBABLE";
  else label = "WEAK";

  return {
    fullName: c.primaryName,
    normalizedName: c.normalizedName,
    role,
    linkedinUrl: c.linkedinUrl,
    sourceKinds,
    evidence: scored.evidence,
    confidenceScore: scored.finalScore,
    confidenceLabel: label,
    supportingSearchCandidatesCount: c.searchCandidates.length,
    supportingWebsiteCandidatesCount: c.websitePersonMatches.length,
  };
}

// ---------------------------------------------------------------------------
// Row-level resolution
// ---------------------------------------------------------------------------

export function resolveRowDecision(
  rowTask: PlannedRowTask,
  discoveryResult: CompanyDiscoveryResult | null,
  searchByRole: Map<TargetRole, RoleSearchCompositeResult | null>,
): ResolvedRowDecision {
  const roleDecisions = rowTask.roleTasks.map((rt) =>
    resolveRoleDecision(rt, discoveryResult, searchByRole.get(rt.role) ?? null),
  );

  return {
    sourceFile: rowTask.sourceFile,
    sheetName: rowTask.sheetName,
    rowIndex: rowTask.rowIndex,
    companyName: rowTask.companyName,
    websiteUrl: rowTask.websiteUrl,
    region: rowTask.region,
    roleDecisions,
  };
}
