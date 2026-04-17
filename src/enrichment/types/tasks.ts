import type { Region, TargetRole } from "./prospect";

export type EnrichmentField =
  | "CEO_NAME"
  | "CEO_LINKEDIN"
  | "CEO_EMAIL"
  | "HEAD_OF_PRODUCT_NAME"
  | "HEAD_OF_PRODUCT_EMAIL"
  | "HEAD_OF_ECOMMERCE_NAME"
  | "HEAD_OF_ECOMMERCE_EMAIL"
  | "HEAD_OF_GROWTH_NAME"
  | "HEAD_OF_GROWTH_EMAIL";

export type RoleTaskStatus =
  | "READY"
  | "SKIP_COMPLETE"
  | "SKIP_NO_WEBSITE"
  | "SKIP_NO_COMPANY_NAME";

export interface PlannedRoleTask {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  region: Region;
  companyName: string;
  websiteUrl: string;
  country: string;
  role: TargetRole;
  missingFields: EnrichmentField[];
  existingSignals: {
    existingName: string;
    existingLinkedin: string;
    existingEmail: string;
  };
  priorityScore: number;
  status: RoleTaskStatus;
  statusReason: string;
}

export interface PlannedRowTask {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  websiteUrl: string;
  region: Region;
  roleTasks: PlannedRoleTask[];
  totalPriorityScore: number;
}
