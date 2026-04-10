import { getCompanyById } from "@/lib/crm/queries/companies";
import { CompanyForm } from "@/components/crm/companies/company-form";
import { notFound } from "next/navigation";

export default async function EditCompanyPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const company = await getCompanyById(id);
  if (!company) notFound();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Edit {company.name}</h1>
      <CompanyForm company={company} />
    </div>
  );
}
