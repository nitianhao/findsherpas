import type { Region } from "./prospect";

export type PageType =
  | "HOMEPAGE"
  | "ABOUT"
  | "TEAM"
  | "LEADERSHIP"
  | "CONTACT"
  | "LEGAL"
  | "CAREERS"
  | "OTHER";

export interface DiscoveredPage {
  url: string;
  pageType: PageType;
  httpStatus: number;
  title: string;
  discoveredFrom: string;
  sameDomain: boolean;
}

export interface ExtractedPersonCandidate {
  fullName: string;
  normalizedName: string;
  titleText: string;
  matchedRoleHints: string[];
  pageUrl: string;
  pageType: PageType;
  evidenceText: string;
  confidenceSignals: string[];
}

export type EmailSourceType = "MAILTO" | "VISIBLE_TEXT" | "OBFUSCATED_TEXT";

export interface ExtractedEmailCandidate {
  email: string;
  domain: string;
  localPart: string;
  sourceType: EmailSourceType;
  pageUrl: string;
  pageType: PageType;
  confidenceSignals: string[];
}

export type LinkedinProfileType =
  | "PERSON_PROFILE"
  | "COMPANY_PAGE"
  | "UNKNOWN";

export interface ExtractedLinkedinCandidate {
  url: string;
  sourceType: LinkedinProfileType;
  pageUrl: string;
  pageType: PageType;
}

export interface CompanyDiscoveryResult {
  sourceFile: string;
  sheetName: string;
  rowIndex: number;
  companyName: string;
  websiteUrl: string;
  region: Region;
  country: string;
  homepageFinalUrl: string;
  discoveredPages: DiscoveredPage[];
  personCandidates: ExtractedPersonCandidate[];
  emailCandidates: ExtractedEmailCandidate[];
  linkedinCandidates: ExtractedLinkedinCandidate[];
  notes: string[];
  errors: string[];
}
