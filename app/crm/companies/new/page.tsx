import { CompanyForm } from "@/components/crm/companies/company-form";

export default function NewCompanyPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Add Company</h1>
      <CompanyForm />
    </div>
  );
}
