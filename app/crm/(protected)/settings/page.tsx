import { getTags } from "@/lib/crm/queries/tags";
import { getCompanyCount } from "@/lib/crm/queries/companies";
import { getContactCount } from "@/lib/crm/queries/contacts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { TagManager } from "@/components/crm/tags/tag-manager";
import { ExportButton } from "@/components/crm/shared/export-button";
import { buttonVariants } from "@/components/crm/ui/button";
import Link from "next/link";
import { Upload, Database } from "lucide-react";

export default async function SettingsPage() {
  const tags = await getTags();
  const [companyCount, contactCount] = await Promise.all([getCompanyCount(), getContactCount()]);

  return (
    <div className="space-y-8 max-w-3xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Tags */}
      <Card>
        <CardHeader>
          <CardTitle>Tags</CardTitle>
        </CardHeader>
        <CardContent>
          <TagManager initialTags={tags} />
        </CardContent>
      </Card>

      {/* Data Management */}
      <Card>
        <CardHeader>
          <CardTitle>Data Management</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <ExportButton type="companies" />
            <ExportButton type="contacts" />
            <Link
              href="/crm/companies/import"
              className={buttonVariants({ variant: "outline" })}
            >
              <Upload className="mr-2 h-4 w-4" />
              Import CSV
            </Link>
          </div>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>
              <Database className="inline h-4 w-4 mr-1" />
              Database: data/crm.db
            </p>
            <p>
              {companyCount} companies, {contactCount} contacts
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
