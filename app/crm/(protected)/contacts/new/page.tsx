import { ContactForm } from "@/components/crm/contacts/contact-form";

export default async function NewContactPage({
  searchParams,
}: {
  searchParams: Promise<{ company_id?: string }>;
}) {
  const params = await searchParams;
  const defaultCompanyId = params.company_id ? params.company_id : undefined;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Add Contact</h1>
      <ContactForm defaultCompanyId={defaultCompanyId} />
    </div>
  );
}
