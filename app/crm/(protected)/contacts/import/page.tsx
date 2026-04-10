import Link from 'next/link';
import { buttonVariants } from '@/components/crm/ui/button';
import { ContactCSVImportForm } from '@/components/crm/contacts/csv-import-form';
import { ArrowLeft } from 'lucide-react';

export default function ImportContactsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/crm/contacts"
          className={buttonVariants({ variant: 'ghost', size: 'icon' })}
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Import Contacts</h1>
          <p className="text-sm text-muted-foreground">
            Import contacts from a CSV file. Companies are matched by name.
          </p>
        </div>
      </div>
      <ContactCSVImportForm />
    </div>
  );
}
