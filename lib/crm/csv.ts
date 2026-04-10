import Papa from 'papaparse';

export function parseCSV(content: string): { headers: string[]; rows: Record<string, string>[] } {
  const result = Papa.parse<Record<string, string>>(content, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header) => header.trim(),
  });
  return {
    headers: result.meta.fields || [],
    rows: result.data,
  };
}

export function generateCSV(rows: Record<string, unknown>[], columns: string[]): string {
  return Papa.unparse(rows, { columns });
}

// Fuzzy match CSV headers to company fields
export function suggestMapping(csvHeaders: string[]): Record<string, string> {
  const fieldMap: Record<string, string[]> = {
    name: ['company', 'company name', 'company_name', 'name', 'organization', 'org'],
    website: ['website', 'url', 'domain', 'web', 'site', 'homepage'],
    industry: ['industry', 'vertical', 'niche', 'sector', 'category'],
    platform: ['platform', 'ecommerce platform', 'cms', 'shop platform'],
    search_solution: ['search', 'search solution', 'search engine', 'search provider'],
    size_estimate: ['size', 'employees', 'company size', 'headcount', 'employee count'],
    revenue_estimate: ['revenue', 'annual revenue', 'arr', 'turnover'],
    social_linkedin: ['linkedin', 'linkedin url', 'li'],
    social_twitter: ['twitter', 'twitter url', 'x', 'x url'],
    social_facebook: ['facebook', 'facebook url', 'fb'],
    notes: ['notes', 'comments', 'description', 'memo'],
    status: ['status', 'stage', 'pipeline stage'],
  };

  const mapping: Record<string, string> = {};
  for (const header of csvHeaders) {
    const lower = header.toLowerCase().trim();
    for (const [field, aliases] of Object.entries(fieldMap)) {
      if (aliases.includes(lower)) {
        mapping[header] = field;
        break;
      }
    }
  }
  return mapping;
}
