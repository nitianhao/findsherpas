import { getContactById } from "@/lib/crm/queries/contacts";
import { notFound } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { StatusBadge } from "@/components/crm/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { Pencil, ArrowLeft, ExternalLink, Mail, Phone } from "lucide-react";
import { DeleteContactButton } from "@/components/crm/contacts/delete-contact-button";
import { ContactSequenceStatus } from "@/components/crm/contacts/contact-sequence-status";

export default async function ContactDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const contact = await getContactById(id);
  if (!contact) notFound();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/crm/contacts" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{contact.name}</h1>
            <StatusBadge status={contact.status} />
          </div>
          {contact.role && (
            <p className="text-sm text-muted-foreground mt-1">{contact.role}</p>
          )}
          {contact.company_name && (
            <Link
              href={`/crm/companies/${contact.company_id}`}
              className="text-sm text-blue-600 hover:underline mt-1 block"
            >
              {contact.company_name}
            </Link>
          )}
        </div>
        <div className="flex gap-2">
          <Link href={`/crm/contacts/${contact.id}/edit`} className={buttonVariants({ variant: "outline" })}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Link>
          <DeleteContactButton contactId={contact.id} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Contact Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <a href={`mailto:${contact.email}`} className="text-blue-600 hover:underline">
                {contact.email}
              </a>
            </div>
            {contact.phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span>{contact.phone}</span>
              </div>
            )}
            {contact.linkedin_url && (
              <div className="flex items-center gap-2">
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
                <a
                  href={contact.linkedin_url.startsWith("http") ? contact.linkedin_url : `https://${contact.linkedin_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  LinkedIn Profile
                </a>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Company</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {contact.company_name ? (
              <Link href={`/crm/companies/${contact.company_id}`} className="text-blue-600 hover:underline font-medium">
                {contact.company_name}
              </Link>
            ) : (
              <span className="text-muted-foreground">No company assigned</span>
            )}
          </CardContent>
        </Card>
      </div>

      {contact.notes && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Notes</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <p className="whitespace-pre-wrap">{contact.notes}</p>
          </CardContent>
        </Card>
      )}

      <ContactSequenceStatus contactId={contact.id} />
    </div>
  );
}
