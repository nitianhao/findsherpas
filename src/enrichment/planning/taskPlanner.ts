import type { ProspectRowNormalized, TargetRole } from "../types/prospect";
import type {
  EnrichmentField,
  PlannedRoleTask,
  PlannedRowTask,
  RoleTaskStatus,
} from "../types/tasks";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isEmpty(value: string): boolean {
  return value.trim() === "";
}

function hasValue(value: string): boolean {
  return value.trim() !== "";
}

const ECOMMERCE_CATEGORY_KEYWORDS = [
  "fashion",
  "electronics",
  "home",
  "beauty",
  "marketplace",
];

function categoryBoost(category: string): number {
  const lower = category.toLowerCase();
  return ECOMMERCE_CATEGORY_KEYWORDS.some((kw) => lower.includes(kw)) ? 4 : 0;
}

// ---------------------------------------------------------------------------
// Per-role field detection
// ---------------------------------------------------------------------------

interface RoleFieldSet {
  name: string;
  linkedin: string; // empty string if not tracked for this role
  email: string;
  nameField: EnrichmentField;
  linkedinField: EnrichmentField | null;
  emailField: EnrichmentField;
}

function getRoleFields(
  row: ProspectRowNormalized,
  role: TargetRole,
): RoleFieldSet {
  switch (role) {
    case "CEO":
      return {
        name: row.ceoName,
        linkedin: row.ceoLinkedin,
        email: row.ceoEmail,
        nameField: "CEO_NAME",
        linkedinField: "CEO_LINKEDIN",
        emailField: "CEO_EMAIL",
      };
    case "HEAD_OF_PRODUCT":
      return {
        name: row.headOfProductName,
        linkedin: "",
        email: row.headOfProductEmail,
        nameField: "HEAD_OF_PRODUCT_NAME",
        linkedinField: null,
        emailField: "HEAD_OF_PRODUCT_EMAIL",
      };
    case "HEAD_OF_ECOMMERCE":
      return {
        name: row.headOfEcommerceName,
        linkedin: "",
        email: row.headOfEcommerceEmail,
        nameField: "HEAD_OF_ECOMMERCE_NAME",
        linkedinField: null,
        emailField: "HEAD_OF_ECOMMERCE_EMAIL",
      };
    case "HEAD_OF_GROWTH":
      return {
        name: row.headOfGrowthName,
        linkedin: "",
        email: row.headOfGrowthEmail,
        nameField: "HEAD_OF_GROWTH_NAME",
        linkedinField: null,
        emailField: "HEAD_OF_GROWTH_EMAIL",
      };
  }
}

// ---------------------------------------------------------------------------
// Priority scoring
// ---------------------------------------------------------------------------

const ROLE_BASE_SCORE: Record<TargetRole, number> = {
  CEO: 25,
  HEAD_OF_ECOMMERCE: 20,
  HEAD_OF_PRODUCT: 12,
  HEAD_OF_GROWTH: 8,
};

function computePriority(
  row: ProspectRowNormalized,
  role: TargetRole,
  missingFields: EnrichmentField[],
  fields: RoleFieldSet,
): number {
  let score = 0;

  // Base signals
  if (hasValue(row.websiteUrl)) score += 50;
  else score -= 1000;

  if (hasValue(row.companyName)) score += 20;
  else score -= 1000;

  // Role weight
  score += ROLE_BASE_SCORE[role];

  // Missing field urgency
  if (missingFields.some((f) => f.endsWith("_NAME"))) score += 15;
  if (
    role === "CEO" &&
    missingFields.includes("CEO_LINKEDIN")
  )
    score += 10;
  if (missingFields.some((f) => f.endsWith("_EMAIL"))) score += 15;

  // Partial data bonus -- easier to finish
  if (hasValue(fields.name) && isEmpty(fields.email)) score += 8;
  if (
    role === "CEO" &&
    hasValue(fields.linkedin) &&
    isEmpty(fields.email)
  )
    score += 8;

  // Country bonus
  if (hasValue(row.country)) score += 5;

  // Category boost
  score += categoryBoost(row.category);

  return score;
}

// ---------------------------------------------------------------------------
// Plan a single role task
// ---------------------------------------------------------------------------

function planRoleTask(
  row: ProspectRowNormalized,
  role: TargetRole,
): PlannedRoleTask {
  const fields = getRoleFields(row, role);

  // Determine status
  let status: RoleTaskStatus;
  let statusReason: string;

  if (isEmpty(row.companyName)) {
    status = "SKIP_NO_COMPANY_NAME";
    statusReason = "Row has no company name";
  } else if (isEmpty(row.websiteUrl)) {
    status = "SKIP_NO_WEBSITE";
    statusReason = "Row has no website URL";
  } else {
    // Detect missing fields
    const missing: EnrichmentField[] = [];
    if (isEmpty(fields.name)) missing.push(fields.nameField);
    if (fields.linkedinField && isEmpty(fields.linkedin))
      missing.push(fields.linkedinField);
    if (isEmpty(fields.email)) missing.push(fields.emailField);

    if (missing.length === 0) {
      status = "SKIP_COMPLETE";
      statusReason = `All ${role} fields already filled`;
    } else {
      status = "READY";
      statusReason = `Missing: ${missing.join(", ")}`;
    }
  }

  const missingFields: EnrichmentField[] = [];
  if (status === "READY") {
    if (isEmpty(fields.name)) missingFields.push(fields.nameField);
    if (fields.linkedinField && isEmpty(fields.linkedin))
      missingFields.push(fields.linkedinField);
    if (isEmpty(fields.email)) missingFields.push(fields.emailField);
  }

  const priorityScore =
    status === "READY" ? computePriority(row, role, missingFields, fields) : 0;

  return {
    sourceFile: row.sourceFile,
    sheetName: row.sheetName,
    rowIndex: row.rowIndex,
    region: row.region,
    companyName: row.companyName,
    websiteUrl: row.websiteUrl,
    country: row.country,
    role,
    missingFields,
    existingSignals: {
      existingName: fields.name,
      existingLinkedin: fields.linkedin,
      existingEmail: fields.email,
    },
    priorityScore,
    status,
    statusReason,
  };
}

// ---------------------------------------------------------------------------
// Row-level planning
// ---------------------------------------------------------------------------

const ALL_ROLES: TargetRole[] = [
  "CEO",
  "HEAD_OF_PRODUCT",
  "HEAD_OF_ECOMMERCE",
  "HEAD_OF_GROWTH",
];

export function planRowTasks(row: ProspectRowNormalized): PlannedRowTask {
  const roleTasks = ALL_ROLES.map((role) => planRoleTask(row, role));
  const totalPriorityScore = roleTasks.reduce(
    (sum, t) => sum + t.priorityScore,
    0,
  );

  return {
    sourceFile: row.sourceFile,
    sheetName: row.sheetName,
    rowIndex: row.rowIndex,
    companyName: row.companyName,
    websiteUrl: row.websiteUrl,
    region: row.region,
    roleTasks,
    totalPriorityScore,
  };
}

export function planAllRows(
  rows: ProspectRowNormalized[],
): PlannedRowTask[] {
  return rows.map(planRowTasks);
}

// ---------------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------------

export function getReadyRoleTasks(
  plannedRows: PlannedRowTask[],
): PlannedRoleTask[] {
  return plannedRows
    .flatMap((r) => r.roleTasks)
    .filter((t) => t.status === "READY")
    .sort((a, b) => b.priorityScore - a.priorityScore);
}

export function groupTasksByWorkbook(
  plannedRows: PlannedRowTask[],
): Map<string, PlannedRowTask[]> {
  const map = new Map<string, PlannedRowTask[]>();
  for (const row of plannedRows) {
    const list = map.get(row.sourceFile) ?? [];
    list.push(row);
    map.set(row.sourceFile, list);
  }
  return map;
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export interface TaskSummary {
  totalRows: number;
  totalPlannedRowTasks: number;
  totalReadyRoleTasks: number;
  readyByWorkbook: Record<string, number>;
  readyByRole: Record<string, number>;
  skipComplete: number;
  skipNoWebsite: number;
  skipNoCompanyName: number;
}

export function summarizePlannedTasks(
  plannedRows: PlannedRowTask[],
): TaskSummary {
  const allRoleTasks = plannedRows.flatMap((r) => r.roleTasks);
  const ready = allRoleTasks.filter((t) => t.status === "READY");

  const readyByWorkbook: Record<string, number> = {};
  const readyByRole: Record<string, number> = {};

  for (const t of ready) {
    readyByWorkbook[t.sourceFile] = (readyByWorkbook[t.sourceFile] ?? 0) + 1;
    readyByRole[t.role] = (readyByRole[t.role] ?? 0) + 1;
  }

  return {
    totalRows: plannedRows.length,
    totalPlannedRowTasks: plannedRows.length,
    totalReadyRoleTasks: ready.length,
    readyByWorkbook,
    readyByRole,
    skipComplete: allRoleTasks.filter((t) => t.status === "SKIP_COMPLETE")
      .length,
    skipNoWebsite: allRoleTasks.filter((t) => t.status === "SKIP_NO_WEBSITE")
      .length,
    skipNoCompanyName: allRoleTasks.filter(
      (t) => t.status === "SKIP_NO_COMPANY_NAME",
    ).length,
  };
}
