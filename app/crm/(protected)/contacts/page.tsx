import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { ContactTable } from "@/components/crm/contacts/contact-table";
import { ContactFilters } from "@/components/crm/contacts/contact-filters";
import { ExportButton } from "@/components/crm/shared/export-button";
import { PaginationControls } from "@/components/crm/shared/pagination-controls";
import { getContacts } from "@/lib/crm/queries/contacts";
import { Plus, Upload } from "lucide-react";
import { ContactStatus } from "@/lib/crm/types";
import { Suspense } from "react";

const PAGE_SIZE = 50;

export default async function ContactsPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string; status?: string; company_id?: string; page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const { contacts, total } = await getContacts({
    search: params.search,
    status: params.status as ContactStatus | undefined,
    company_id: params.company_id ? params.company_id : undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Contacts</h1>
          <p className="text-sm text-muted-foreground">{total} contacts total</p>
        </div>
        <div className="flex items-center gap-2">
          <ExportButton type="contacts" />
          <Link href="/crm/contacts/import" className={buttonVariants({ variant: "outline" })}>
            <Upload className="mr-2 h-4 w-4" />
            Import CSV
          </Link>
          <Link href="/crm/contacts/new" className={buttonVariants()}>
            <Plus className="mr-2 h-4 w-4" />
            Add Contact
          </Link>
        </div>
      </div>
      <Suspense fallback={<div>Loading filters...</div>}>
        <ContactFilters />
      </Suspense>
      <ContactTable contacts={contacts} />
      <PaginationControls
        basePath="/crm/contacts"
        currentPage={page}
        pageSize={PAGE_SIZE}
        total={total}
        searchParams={params}
      />
    </div>
  );
}
