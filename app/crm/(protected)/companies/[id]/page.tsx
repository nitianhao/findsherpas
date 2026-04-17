import { getCompanyById } from "@/lib/crm/queries/companies";
import { getContactsByCompanyId } from "@/lib/crm/queries/contacts";
import { getEnrollmentCountByCompanyId } from "@/lib/crm/queries/enrollments";
import { notFound } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { StatusBadge } from "@/components/crm/shared/status-badge";
import { TagBadge } from "@/components/crm/tags/tag-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/crm/ui/tabs";
import { Pencil, ExternalLink, ArrowLeft, Plus, Mail } from "lucide-react";
import { DeleteCompanyButton } from "@/components/crm/companies/delete-company-button";
import { CompanyPDF } from "@/components/crm/companies/company-pdf";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const company = await getCompanyById(id);
  if (!company) notFound();

  const [contacts, enrollmentCount] = await Promise.all([
    getContactsByCompanyId(company.id),
    getEnrollmentCountByCompanyId(company.id),
  ]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/crm/companies" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{company.name}</h1>
            <StatusBadge status={company.status} />
          </div>
          {company.website && (
            <a
              href={company.website.startsWith("http") ? company.website : `https://${company.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-blue-600 hover:underline mt-1"
            >
              {company.website} <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {company.tags && company.tags.length > 0 && (
            <div className="flex gap-1 mt-2">
              {company.tags.map((tag) => (
                <TagBadge key={tag.id} name={tag.name} color={tag.color} />
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Link href={`/crm/companies/${company.id}/edit`} className={buttonVariants({ variant: "outline" })}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Link>
          <DeleteCompanyButton companyId={company.id} />
        </div>
      </div>

      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">Info</TabsTrigger>
          <TabsTrigger value="contacts">
            Contacts <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-xs font-medium">{contacts.length}</span>
          </TabsTrigger>
          <TabsTrigger value="sequences">
            Sequences <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-xs font-medium">{enrollmentCount}</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="space-y-4 mt-4">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Ecommerce Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Platform</span>
                  <span>{company.platform || "-"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Search Solution</span>
                  <span>{company.search_solution || "-"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Industry</span>
                  <span>{company.industry || "-"}</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Company Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Size</span>
                  <span>{company.size_estimate || "-"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Revenue</span>
                  <span>{company.revenue_estimate || "-"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Country</span>
                  <span>{company.country || "-"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Language</span>
                  <span>{company.language || "-"}</span>
                </div>
                {company.report_url && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Report</span>
                    <a
                      href={company.report_url.startsWith("http") ? company.report_url : `https://${company.report_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-blue-600 hover:underline"
                    >
                      View <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {(company.social_linkedin || company.social_twitter || company.social_facebook || company.social_other) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Social Links</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {company.social_linkedin && (
                  <div>
                    <a href={company.social_linkedin} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      LinkedIn
                    </a>
                  </div>
                )}
                {company.social_twitter && (
                  <div>
                    <a href={company.social_twitter} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      Twitter/X
                    </a>
                  </div>
                )}
                {company.social_facebook && (
                  <div>
                    <a href={company.social_facebook} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      Facebook
                    </a>
                  </div>
                )}
                {company.social_other && (
                  <div>
                    <a href={company.social_other} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      Other
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <CompanyPDF
            companyId={company.id}
            initialPdfUrl={company.pdf_url}
            initialPdfName={company.pdf_name}
          />

          {(company.tech_stack_notes || company.notes) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {company.tech_stack_notes && (
                  <div>
                    <p className="text-muted-foreground mb-1">Tech Stack</p>
                    <p className="whitespace-pre-wrap">{company.tech_stack_notes}</p>
                  </div>
                )}
                {company.notes && (
                  <div>
                    <p className="text-muted-foreground mb-1">General</p>
                    <p className="whitespace-pre-wrap">{company.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="contacts" className="mt-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">{contacts.length} contact{contacts.length !== 1 ? "s" : ""}</p>
              <Link
                href={`/crm/contacts/new?company_id=${company.id}`}
                className={buttonVariants({ size: "sm" })}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Contact
              </Link>
            </div>
            {contacts.length > 0 ? (
              <div className="divide-y rounded-md border">
                {contacts.map((contact) => (
                  <div key={contact.id} className="flex items-center justify-between p-4">
                    <div className="space-y-1">
                      <Link
                        href={`/crm/contacts/${contact.id}`}
                        className="font-medium hover:underline"
                      >
                        {contact.name}
                      </Link>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Mail className="h-3 w-3" />
                        <span>{contact.email}</span>
                        {contact.role && (
                          <>
                            <span>-</span>
                            <span>{contact.role}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <StatusBadge status={contact.status} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No contacts yet. Add your first contact for this company.</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="sequences" className="mt-4">
          <p className="text-muted-foreground">Sequence enrollments will be shown here after Phase 5.</p>
        </TabsContent>
      </Tabs>
    </div>
  );
}
