export type Region = "US" | "EU";

export type TargetRole =
  | "CEO"
  | "HEAD_OF_PRODUCT"
  | "HEAD_OF_ECOMMERCE"
  | "HEAD_OF_GROWTH";

export interface ProspectRowNormalized {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  region: Region;
  companyName: string;
  websiteUrl: string;
  country: string;
  category: string;
  estimatedRevenue: string;
  linkedinCompanyPage: string;
  ceoName: string;
  ceoLinkedin: string;
  ceoEmail: string;
  headOfProductName: string;
  headOfProductEmail: string;
  headOfEcommerceName: string;
  headOfEcommerceEmail: string;
  headOfGrowthName: string;
  headOfGrowthEmail: string;
  notes: string;
  originalRow: Record<string, string>;
}

/**
 * Maps a normalized field name to the exact column header in a workbook.
 */
export interface ColumnMapping {
  companyName: string;
  websiteUrl: string;
  country?: string; // absent in US file
  category: string;
  estimatedRevenue: string;
  linkedinCompanyPage: string;
  ceoName: string;
  ceoLinkedin: string;
  ceoEmail: string;
  headOfProductName: string;
  headOfProductEmail: string;
  headOfEcommerceName: string;
  headOfEcommerceEmail: string;
  headOfGrowthName: string;
  headOfGrowthEmail: string;
  notes: string;
}

export interface WorkbookConfig {
  filename: string;
  region: Region;
  primarySheet: string;
  defaultCountry: string;
  columns: ColumnMapping;
}
