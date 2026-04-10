"use client";

import { useState, useRef } from "react";
import { Button, buttonVariants } from "@/components/crm/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { FileText, Upload, Download, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface CompanyPDFProps {
  companyId: string;
  initialPdfUrl: string | null;
  initialPdfName: string | null;
}

export function CompanyPDF({ companyId, initialPdfUrl, initialPdfName }: CompanyPDFProps) {
  const [pdfUrl, setPdfUrl] = useState(initialPdfUrl);
  const [pdfName, setPdfName] = useState(initialPdfName);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      toast.error("Only PDF files are accepted");
      return;
    }

    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`/api/crm/companies/${companyId}/pdf`, {
        method: "POST",
        body: form,
      });
      if (res.ok) {
        const data = await res.json();
        setPdfUrl(data.pdf_url);
        setPdfName(data.pdf_name);
        toast.success("PDF uploaded");
      } else {
        const err = await res.json();
        toast.error(err.error || "Upload failed");
      }
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      const res = await fetch(`/api/crm/companies/${companyId}/pdf`, { method: "DELETE" });
      if (res.ok) {
        setPdfUrl(null);
        setPdfName(null);
        toast.success("PDF removed");
      } else {
        const err = await res.json();
        toast.error(err.error || "Delete failed");
      }
    } catch {
      toast.error("Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Report PDF</CardTitle>
      </CardHeader>
      <CardContent>
        {pdfUrl && pdfName ? (
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="text-sm truncate">{pdfName}</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                download={pdfName}
                className={buttonVariants({ size: "sm", variant: "outline" })}
              >
                <Download className="h-3.5 w-3.5 mr-1.5" />
                Download
              </a>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDelete}
                disabled={deleting}
              >
                <Trash2 className="h-3.5 w-3.5 text-destructive" />
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <p className="text-sm text-muted-foreground">No PDF uploaded yet.</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
            >
              <Upload className="h-3.5 w-3.5 mr-1.5" />
              {uploading ? "Uploading..." : "Upload PDF"}
            </Button>
          </div>
        )}
        {pdfUrl && (
          <div className="mt-3">
            <Button
              size="sm"
              variant="ghost"
              className="text-xs text-muted-foreground"
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
            >
              <Upload className="h-3 w-3 mr-1" />
              {uploading ? "Uploading..." : "Replace PDF"}
            </Button>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleUpload}
        />
      </CardContent>
    </Card>
  );
}
