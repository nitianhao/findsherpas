import type { PlannedRoleTask } from "../types/tasks";
import type { CompanyDiscoveryResult } from "../types/discovery";
import type { SearchQueryPlan } from "../types/search";

// ---------------------------------------------------------------------------
// Role-specific query templates
// ---------------------------------------------------------------------------

type QueryTemplate = (company: string, domain: string, country: string) => string[];

const ROLE_QUERIES: Record<string, QueryTemplate> = {
  CEO: (company, _domain, _country) => [
    `"${company}" CEO LinkedIn`,
    `site:linkedin.com/in "${company}" CEO`,
    `"${company}" founder LinkedIn`,
  ],
  HEAD_OF_PRODUCT: (company, _domain, _country) => [
    `site:linkedin.com/in "${company}" "Head of Product"`,
    `"${company}" "Head of Product" LinkedIn`,
    `"${company}" "VP Product" LinkedIn`,
  ],
  HEAD_OF_ECOMMERCE: (company, _domain, _country) => [
    `site:linkedin.com/in "${company}" "Head of Ecommerce"`,
    `"${company}" "Director of Ecommerce" LinkedIn`,
    `"${company}" ecommerce LinkedIn`,
  ],
  HEAD_OF_GROWTH: (company, _domain, _country) => [
    `site:linkedin.com/in "${company}" "Head of Growth"`,
    `"${company}" CMO LinkedIn`,
    `"${company}" "Marketing Director" LinkedIn`,
  ],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function dedupe(queries: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const q of queries) {
    const key = q.toLowerCase().replace(/\s+/g, " ").trim();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(q);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Query builder
// ---------------------------------------------------------------------------

export function buildRoleSearchQueryPlan(
  task: PlannedRoleTask,
  discoveryResult?: CompanyDiscoveryResult | null,
): SearchQueryPlan {
  const domain = extractDomain(task.websiteUrl);
  const company = task.companyName;

  const templateFn = ROLE_QUERIES[task.role];
  const queries: string[] = templateFn
    ? templateFn(company, domain, task.country)
    : [
        `"${company}" ${task.role} LinkedIn`,
        `site:linkedin.com/in "${company}" ${task.role}`,
      ];

  // Optional: country-hinted query for EU companies (only if adds specificity)
  if (task.region === "EU" && task.country && task.role === "CEO") {
    queries.push(`"${company}" CEO ${task.country} LinkedIn`);
  }

  // Optional: confirm existing name from website discovery
  if (discoveryResult) {
    const existingName = task.existingSignals.existingName;
    if (existingName) {
      queries.push(`"${existingName}" "${company}" LinkedIn`);
    }
  }

  return {
    companyName: company,
    websiteUrl: task.websiteUrl,
    domain,
    role: task.role,
    region: task.region,
    country: task.country,
    queries: dedupe(queries).slice(0, 4),
  };
}
