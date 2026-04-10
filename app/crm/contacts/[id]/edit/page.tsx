import { getContactById } from "@/lib/crm/queries/contacts";
import { ContactForm } from "@/components/crm/contacts/contact-form";
import { notFound } from "next/navigation";

export default async function EditContactPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const contact = await getContactById(id);
  if (!contact) notFound();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Edit {contact.name}</h1>
      <ContactForm contact={contact} />
    </div>
  );
}
