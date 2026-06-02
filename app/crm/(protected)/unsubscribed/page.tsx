import { ContactTable } from "@/components/crm/contacts/contact-table";
import { UnsubscribedSearch } from "@/components/crm/contacts/unsubscribed-search";
import { UnsubscribedExportButton } from "@/components/crm/shared/unsubscribed-export-button";
import { PaginationControls } from "@/components/crm/shared/pagination-controls";
import { getUnsubscribedContacts } from "@/lib/crm/queries/contacts";
import { Suspense } from "react";

const PAGE_SIZE = 50;

export default async function UnsubscribedPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string; page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const { contacts, total } = await getUnsubscribedContacts({
    search: params.search,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Unsubscribed</h1>
          <p className="text-sm text-muted-foreground">
            {total} unsubscribed contact{total === 1 ? "" : "s"}
          </p>
        </div>
        <UnsubscribedExportButton />
      </div>
      <Suspense fallback={<div>Loading...</div>}>
        <UnsubscribedSearch />
      </Suspense>
      <ContactTable contacts={contacts} />
      <PaginationControls
        basePath="/crm/unsubscribed"
        currentPage={page}
        pageSize={PAGE_SIZE}
        total={total}
        searchParams={params}
      />
    </div>
  );
}
