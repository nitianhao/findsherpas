import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { CompanyTable } from "@/components/crm/companies/company-table";
import { CompanyFilters } from "@/components/crm/companies/company-filters";
import { ExportButton } from "@/components/crm/shared/export-button";
import { getCompanies } from "@/lib/crm/queries/companies";
import { Plus, Upload } from "lucide-react";
import { CompanyStatus } from "@/lib/crm/types";
import { Suspense } from "react";

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string; status?: string; platform?: string; tag_id?: string }>;
}) {
  const params = await searchParams;
  const { companies, total } = await getCompanies({
    search: params.search,
    status: params.status as CompanyStatus | undefined,
    platform: params.platform,
    tag_id: params.tag_id ? params.tag_id : undefined,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Companies</h1>
          <p className="text-sm text-muted-foreground">{total} companies total</p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton type="companies" />
          <Link href="/crm/companies/import" className={buttonVariants({ variant: "outline" })}>
            <Upload className="mr-2 h-4 w-4" />
            Import CSV
          </Link>
          <Link href="/crm/companies/new" className={buttonVariants()}>
            <Plus className="mr-2 h-4 w-4" />
            Add Company
          </Link>
        </div>
      </div>
      <Suspense fallback={<div>Loading filters...</div>}>
        <CompanyFilters />
      </Suspense>
      <CompanyTable companies={companies} />
    </div>
  );
}
