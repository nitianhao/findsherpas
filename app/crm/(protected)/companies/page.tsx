import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { CompanyTable } from "@/components/crm/companies/company-table";
import { CompanyFilters } from "@/components/crm/companies/company-filters";
import { ExportButton } from "@/components/crm/shared/export-button";
import { PaginationControls } from "@/components/crm/shared/pagination-controls";
import { getCompanies } from "@/lib/crm/queries/companies";
import { Plus, Upload } from "lucide-react";
import { CompanyStatus } from "@/lib/crm/types";
import { Suspense } from "react";

const PAGE_SIZE = 50;

export default async function CompaniesPage({
  searchParams,
}: {
  searchParams: Promise<{
    search?: string;
    status?: string;
    platform?: string;
    search_solution?: string;
    report?: string;
    tag_id?: string;
    sort?: string;
    page?: string;
  }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const [requestedSortBy = "updated_at", requestedSortDir = "desc"] = (params.sort || "updated_at:desc").split(":");
  const sort_by = ["updated_at", "name", "contacts_count"].includes(requestedSortBy)
    ? requestedSortBy
    : "updated_at";
  const sort_dir = requestedSortDir === "asc" ? "asc" : "desc";
  const { companies, total } = await getCompanies({
    search: params.search,
    status: params.status as CompanyStatus | undefined,
    platform: params.platform,
    search_solution: params.search_solution,
    report: params.report === "yes" ? true : params.report === "no" ? false : undefined,
    tag_id: params.tag_id ? params.tag_id : undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
    sort_by: sort_by as "updated_at" | "name" | "contacts_count",
    sort_dir: sort_dir as "asc" | "desc",
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
      <PaginationControls
        basePath="/crm/companies"
        currentPage={page}
        pageSize={PAGE_SIZE}
        total={total}
        searchParams={params}
      />
    </div>
  );
}
