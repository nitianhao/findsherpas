'use client';

import { useState } from 'react';
import { Button } from '@/components/crm/ui/button';
import { Download } from 'lucide-react';

interface ExportButtonProps {
  type: 'companies' | 'contacts';
}

export function ExportButton({ type }: ExportButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/crm/export?type=${type}`);
      if (!res.ok) {
        throw new Error('Export failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}-export.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Silent fail for export — user can retry
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button variant="outline" onClick={handleExport} disabled={loading}>
      <Download className="mr-2 h-4 w-4" />
      {loading ? 'Exporting...' : `Export ${type === 'companies' ? 'Companies' : 'Contacts'}`}
    </Button>
  );
}
