import type { WorkbookConfig } from "../types/prospect";

/**
 * Canonical output email column names -- these must be added
 * to the workbook if they don't already exist.
 */
export const OUTPUT_EMAIL_COLUMNS = [
  "CEO Email",
  "Head of Product Email",
  "Head of Ecommerce Email",
  "Head of Growth / CMO Email",
] as const;

const sharedEmailAndPeopleColumns = {
  ceoLinkedin: "CEO LinkedIn Profile",
  ceoEmail: "CEO Email",
  headOfProductName: "Head of Product (Name)",
  headOfProductEmail: "Head of Product Email",
  headOfEcommerceName: "Head of Ecommerce (Name)",
  headOfEcommerceEmail: "Head of Ecommerce Email",
  headOfGrowthName: "Head of Growth / CMO (Name)",
  headOfGrowthEmail: "Head of Growth / CMO Email",
  notes: "Notes (Search Relevance)",
} as const;

export const EU_CONFIG: WorkbookConfig = {
  filename: "EU_Ecommerce_Prospects_SiteSearch.xlsx",
  region: "EU",
  primarySheet: "EU Ecommerce Prospects",
  defaultCountry: "",
  columns: {
    companyName: "Company Name",
    websiteUrl: "Website URL",
    country: "Country",
    category: "Category",
    estimatedRevenue: "Est. Revenue (EUR)",
    linkedinCompanyPage: "LinkedIn Company Page",
    ceoName: "CEO / MD Name",
    ...sharedEmailAndPeopleColumns,
  },
};

export const US_CONFIG: WorkbookConfig = {
  filename: "US_Ecommerce_Prospects_SiteSearch.xlsx",
  region: "US",
  primarySheet: "US Ecommerce Prospects",
  defaultCountry: "United States",
  columns: {
    companyName: "Company Name",
    websiteUrl: "Website URL",
    // no country column in the US file
    category: "Category",
    estimatedRevenue: "Est. Revenue (USD)",
    linkedinCompanyPage: "LinkedIn Company Page",
    ceoName: "CEO / Founder Name",
    ...sharedEmailAndPeopleColumns,
  },
};

export const ALL_CONFIGS: WorkbookConfig[] = [US_CONFIG, EU_CONFIG];
