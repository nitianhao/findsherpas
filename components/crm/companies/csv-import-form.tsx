'use client';

import { useState, useCallback } from 'react';
import { parseCSV, suggestMapping } from '@/lib/crm/csv';
import { Button } from '@/components/crm/ui/button';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/crm/ui/card';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/crm/ui/select';
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from '@/components/crm/ui/table';
import { Upload, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle, FileSpreadsheet } from 'lucide-react';

const SKIP_VALUE = '__skip__';

const COMPANY_FIELDS: { value: string; label: string }[] = [
  { value: SKIP_VALUE, label: '-- Skip --' },
  { value: 'name', label: 'Company Name' },
  { value: 'website', label: 'Website' },
  { value: 'industry', label: 'Industry' },
  { value: 'platform', label: 'Platform' },
  { value: 'search_solution', label: 'Search Solution' },
  { value: 'size_estimate', label: 'Size Estimate' },
  { value: 'revenue_estimate', label: 'Revenue Estimate' },
  { value: 'social_linkedin', label: 'LinkedIn' },
  { value: 'social_twitter', label: 'Twitter / X' },
  { value: 'social_facebook', label: 'Facebook' },
  { value: 'notes', label: 'Notes' },
  { value: 'status', label: 'Status' },
];

type Step = 1 | 2 | 3 | 4;

interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

export function CSVImportForm() {
  const [step, setStep] = useState<Step>(1);
  const [headers, setHeaders] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (!content) {
        setError('File is empty.');
        return;
      }
      const parsed = parseCSV(content);
      if (parsed.headers.length === 0) {
        setError('No headers found in CSV file.');
        return;
      }
      if (parsed.rows.length === 0) {
        setError('No data rows found in CSV file.');
        return;
      }
      setHeaders(parsed.headers);
      setRows(parsed.rows);
      setMapping(suggestMapping(parsed.headers));
      setStep(2);
    };
    reader.onerror = () => {
      setError('Failed to read file.');
    };
    reader.readAsText(file);
  }, []);

  const handleMappingChange = useCallback((csvHeader: string, value: string | null) => {
    setMapping((prev) => {
      const next = { ...prev };
      if (!value || value === SKIP_VALUE) {
        delete next[csvHeader];
      } else {
        next[csvHeader] = value;
      }
      return next;
    });
  }, []);

  const hasNameMapping = Object.values(mapping).includes('name');

  const previewRows = rows.slice(0, 5);
  const mappedFields = Object.entries(mapping).filter(([, v]) => v !== '' && v !== SKIP_VALUE);

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/companies/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows, mapping }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Import failed');
      }
      const data: ImportResult = await res.json();
      setResult(data);
      setStep(4);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setLoading(false);
    }
  }, [rows, mapping]);

  const reset = useCallback(() => {
    setStep(1);
    setHeaders([]);
    setRows([]);
    setMapping({});
    setResult(null);
    setError(null);
    setFileName('');
  }, []);

  return (
    <div className="max-w-4xl space-y-4">
      {/* Step indicator */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                step >= s
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {s}
            </span>
            <span className={step >= s ? 'text-foreground' : ''}>
              {s === 1 && 'Upload'}
              {s === 2 && 'Map Columns'}
              {s === 3 && 'Preview'}
              {s === 4 && 'Results'}
            </span>
            {s < 4 && <ArrowRight className="h-3 w-3" />}
          </div>
        ))}
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Step 1: File Upload */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload CSV File</CardTitle>
            <CardDescription>
              Select a CSV file with company data to import.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-muted-foreground/25 p-12 transition-colors hover:border-muted-foreground/50">
              <Upload className="h-10 w-10 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">Click to upload CSV</p>
                <p className="text-sm text-muted-foreground">or drag and drop</p>
              </div>
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileUpload}
              />
            </label>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Column Mapping */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Map Columns</CardTitle>
            <CardDescription>
              Match each CSV column to a company field. {fileName && `File: ${fileName}`} ({rows.length} rows)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {headers.map((header) => (
                <div key={header} className="flex items-center gap-4">
                  <div className="flex w-48 shrink-0 items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                    <span className="truncate text-sm font-medium" title={header}>
                      {header}
                    </span>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <Select
                    value={mapping[header] || SKIP_VALUE}
                    onValueChange={(val) => handleMappingChange(header, val)}
                  >
                    <SelectTrigger className="w-56">
                      <SelectValue placeholder="-- Skip --" />
                    </SelectTrigger>
                    <SelectContent>
                      {COMPANY_FIELDS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>
                          {f.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" onClick={reset}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <Button
              onClick={() => setStep(3)}
              disabled={!hasNameMapping}
            >
              Preview Import
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardFooter>
          {!hasNameMapping && (
            <div className="px-4 pb-4 text-sm text-muted-foreground">
              You must map at least one column to "Company Name" to proceed.
            </div>
          )}
        </Card>
      )}

      {/* Step 3: Preview */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Preview Import</CardTitle>
            <CardDescription>
              Showing first {previewRows.length} of {rows.length} rows with mapped fields.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {mappedFields.map(([csvH, field]) => (
                    <TableHead key={csvH}>
                      {COMPANY_FIELDS.find((f) => f.value === field)?.label ?? field}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {previewRows.map((row, i) => (
                  <TableRow key={i}>
                    {mappedFields.map(([csvH]) => (
                      <TableCell key={csvH} className="max-w-48 truncate">
                        {row[csvH] || '-'}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {rows.length > 5 && (
              <p className="mt-2 text-sm text-muted-foreground">
                ...and {rows.length - 5} more rows
              </p>
            )}
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(2)}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Importing...' : `Import ${rows.length} Companies`}
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Step 4: Results */}
      {step === 4 && result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              Import Complete
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-green-50 p-4 dark:bg-green-950/30">
                <p className="text-2xl font-bold text-green-700 dark:text-green-400">
                  {result.imported}
                </p>
                <p className="text-sm text-green-600 dark:text-green-500">
                  Companies imported
                </p>
              </div>
              <div className="rounded-lg bg-orange-50 p-4 dark:bg-orange-950/30">
                <p className="text-2xl font-bold text-orange-700 dark:text-orange-400">
                  {result.skipped}
                </p>
                <p className="text-sm text-orange-600 dark:text-orange-500">
                  Rows skipped
                </p>
              </div>
            </div>
            {result.errors.length > 0 && (
              <div className="space-y-1">
                <p className="text-sm font-medium">Errors:</p>
                <div className="max-h-48 overflow-y-auto rounded-lg bg-muted p-3">
                  {result.errors.map((err, i) => (
                    <p key={i} className="text-sm text-muted-foreground">
                      {err}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex gap-3">
            <Button variant="outline" onClick={reset}>
              Import Another
            </Button>
            <Button
              onClick={() => {
                window.location.href = '/companies';
              }}
            >
              View Companies
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
