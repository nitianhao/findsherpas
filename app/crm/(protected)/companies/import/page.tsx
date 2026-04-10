import Link from 'next/link';
import { buttonVariants } from '@/components/crm/ui/button';
import { CSVImportForm } from '@/components/crm/companies/csv-import-form';
import { ArrowLeft } from 'lucide-react';

export default function ImportCompaniesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/crm/companies"
          className={buttonVariants({ variant: 'ghost', size: 'icon' })}
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Import Companies</h1>
          <p className="text-sm text-muted-foreground">
            Import companies from a CSV file
          </p>
        </div>
      </div>
      <CSVImportForm />
    </div>
  );
}
