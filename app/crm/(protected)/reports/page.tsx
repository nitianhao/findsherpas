import Link from "next/link";
import { readFile } from "fs/promises";
import { resolve } from "path";
import { ExternalLink } from "lucide-react";
import { getCompanies } from "@/lib/crm/queries/companies";
import { Badge } from "@/components/crm/ui/badge";
import { buttonVariants } from "@/components/crm/ui/button";

interface ReportSlugEntry {
  slug?: string;
  url?: string;
}

async function getReportRegistry(): Promise<Array<{ companyKey: string; url: string }>> {
  try {
    const file = await readFile(resolve(process.cwd(), "reports/report_slugs.json"), "utf-8");
    const data = JSON.parse(file) as Record<string, ReportSlugEntry>;
    return Object.entries(data)
      .filter(([, entry]) => entry.url)
      .map(([companyKey, entry]) => ({
        companyKey,
        url: entry.url as string,
      }));
  } catch {
    return [];
  }
}

function normalizeName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function titleizeReportKey(value: string): string {
  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default async function ReportsPage() {
  const [{ companies }, registry] = await Promise.all([
    getCompanies({
      limit: 1000,
      sort_by: "updated_at",
      sort_dir: "desc",
    }),
    getReportRegistry(),
  ]);
  const companiesByReportKey = new Map(
    companies.map((company) => [normalizeName(company.name), company])
  );
  const reportsByKey = new Map<
    string,
    {
      key: string;
      name: string;
      company: (typeof companies)[number] | undefined;
      reportUrl: string;
    }
  >();

  for (const company of companies.filter((company) => company.report_url)) {
    reportsByKey.set(normalizeName(company.name), {
      key: company.id,
      name: company.name,
      company,
      reportUrl: company.report_url as string,
    });
  }

  for (const entry of registry) {
    const key = normalizeName(entry.companyKey);
    if (reportsByKey.has(key)) continue;
    const company = companiesByReportKey.get(key);
    reportsByKey.set(key, {
      key: entry.companyKey,
      name: company?.name ?? titleizeReportKey(entry.companyKey),
      company,
      reportUrl: company?.report_url ?? entry.url,
    });
  }

  const reports = Array.from(reportsByKey.values()).sort((a, b) =>
    a.name.localeCompare(b.name)
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Reports</h1>
        <p className="text-sm text-muted-foreground">{reports.length} unlisted report pages</p>
      </div>

      <div className="overflow-hidden rounded-lg border border-border/60">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Company</th>
              <th className="px-4 py-3 font-medium">Report URL</th>
              <th className="px-4 py-3 font-medium">Search</th>
              <th className="px-4 py-3 font-medium">Audit</th>
              <th className="px-4 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {reports.map((report) => (
              <tr key={report.key}>
                <td className="px-4 py-3">
                  {report.company ? (
                    <Link href={`/crm/companies/${report.company.id}`} className="font-medium hover:underline">
                      {report.name}
                    </Link>
                  ) : (
                    <span className="font-medium">{report.name}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <a
                    href={report.reportUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex max-w-md items-center gap-1 truncate text-blue-600 hover:underline"
                  >
                    {report.reportUrl.replace(/^https?:\/\//, "")}
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {report.company?.search_solution || "-"}
                </td>
                <td className="px-4 py-3">
                  {report.company?.audit_score ? (
                    <Badge variant="secondary">{report.company.audit_score}/100</Badge>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {report.company ? (
                    <Link
                      href={`/crm/companies/${report.company.id}`}
                      className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                      View
                    </Link>
                  ) : (
                    <a
                      href={report.reportUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={buttonVariants({ variant: "outline", size: "sm" })}
                    >
                      Open
                    </a>
                  )}
                </td>
              </tr>
            ))}
            {reports.length === 0 && (
              <tr>
                <td className="px-4 py-8 text-center text-muted-foreground" colSpan={5}>
                  No reports found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
