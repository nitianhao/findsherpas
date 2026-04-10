import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { ContactTable } from "@/components/crm/contacts/contact-table";
import { ContactFilters } from "@/components/crm/contacts/contact-filters";
import { ExportButton } from "@/components/crm/shared/export-button";
import { getContacts } from "@/lib/crm/queries/contacts";
import { Plus } from "lucide-react";
import { ContactStatus } from "@/lib/crm/types";
import { Suspense } from "react";

export default async function ContactsPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string; status?: string; company_id?: string }>;
}) {
  const params = await searchParams;
  const { contacts, total } = await getContacts({
    search: params.search,
    status: params.status as ContactStatus | undefined,
    company_id: params.company_id ? params.company_id : undefined,
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
          <Link href="/contacts/new" className={buttonVariants()}>
            <Plus className="mr-2 h-4 w-4" />
            Add Contact
          </Link>
        </div>
      </div>
      <Suspense fallback={<div>Loading filters...</div>}>
        <ContactFilters />
      </Suspense>
      <ContactTable contacts={contacts} />
    </div>
  );
}
