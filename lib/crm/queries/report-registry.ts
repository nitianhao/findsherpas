import { readFile } from 'fs/promises';
import { resolve } from 'path';

/** Lowercase + strip everything but a-z0-9, matching the Reports page key logic. */
export function normalizeKey(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, '');
}

/** Derive a registry-comparable key from a website URL (first domain label). */
function websiteKey(website: string): string {
  const host = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
  const firstLabel = host.split('.')[0];
  return normalizeKey(firstLabel);
}

/**
 * Normalized keys of every report in reports/report_slugs.json (with a url).
 * Used to decide whether a company has a generated report.
 */
export async function getReportRegistryKeySet(): Promise<Set<string>> {
  try {
    const file = await readFile(resolve(process.cwd(), 'reports/report_slugs.json'), 'utf-8');
    const data = JSON.parse(file) as Record<string, { url?: string }>;
    return new Set(
      Object.entries(data)
        .filter(([, entry]) => entry && entry.url)
        .map(([key]) => normalizeKey(key))
    );
  } catch {
    return new Set();
  }
}

/**
 * A company has a report when its report_url is set, or its name/website domain
 * matches a registry entry — the same union the CRM Reports page uses to list
 * the 12 generated reports (website match also catches diacritic names like
 * "Åhlens" and "Bächli Bergsport" that normalized-name matching misses).
 */
export function companyHasReport(
  company: { report_url?: string | null; name: string; website?: string | null },
  keys: Set<string>
): boolean {
  if (company.report_url) return true;
  if (keys.has(normalizeKey(company.name))) return true;
  if (company.website && keys.has(websiteKey(company.website))) return true;
  return false;
}
