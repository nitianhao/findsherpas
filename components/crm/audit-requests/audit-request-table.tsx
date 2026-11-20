"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ExternalLink, MoreHorizontal, Eye, CheckCircle, XCircle, Mail, Loader2 } from "lucide-react";
import type { AuditRequest, AuditRequestStatus } from "@/lib/crm/queries/audit-requests";
import { Badge } from "@/components/crm/ui/badge";
import { Button } from "@/components/crm/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/crm/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/crm/ui/table";

const STATUS_LABELS: Record<AuditRequestStatus, string> = {
  new: "New",
  scanning: "Scanning",
  ready_for_review: "Ready for Review",
  approved: "Approved",
  sent: "Sent",
  rejected: "Rejected",
};

const STATUS_VARIANTS: Record<AuditRequestStatus, "default" | "secondary" | "destructive" | "outline"> = {
  new: "default",
  scanning: "secondary",
  ready_for_review: "default",
  approved: "secondary",
  sent: "outline",
  rejected: "destructive",
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

interface AuditRequestTableProps {
  requests: AuditRequest[];
}

export function AuditRequestTable({ requests }: AuditRequestTableProps) {
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function handleAction(requestId: string, action: string) {
    setLoading(requestId);
    try {
      const response = await fetch(`/api/crm/audit-requests/${requestId}/${action}`, {
        method: "POST",
      });
      if (response.ok) {
        router.refresh();
      }
    } finally {
      setLoading(null);
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Store</TableHead>
          <TableHead>Contact</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Score</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="w-[70px]"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {requests.map((request) => (
          <TableRow key={request.id}>
            <TableCell>
              <div className="flex flex-col gap-1">
                <span className="font-medium">{extractDomain(request.store_url)}</span>
                <a
                  href={request.store_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-muted-foreground hover:underline flex items-center gap-1"
                >
                  {request.store_url.length > 40
                    ? `${request.store_url.slice(0, 40)}...`
                    : request.store_url}
                  <ExternalLink size={12} />
                </a>
              </div>
            </TableCell>
            <TableCell>
              <div className="flex flex-col gap-0.5">
                <span>{request.name}</span>
                <span className="text-xs text-muted-foreground">{request.email}</span>
                {request.company_name && (
                  <Link
                    href={`/crm/companies/${request.company_id}`}
                    className="text-xs text-muted-foreground hover:underline"
                  >
                    {request.company_name}
                  </Link>
                )}
              </div>
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANTS[request.status]}>
                {STATUS_LABELS[request.status]}
              </Badge>
            </TableCell>
            <TableCell>
              {request.teardown_scan ? (
                <Badge
                  variant={
                    request.teardown_scan.overall_score === "pass"
                      ? "outline"
                      : request.teardown_scan.overall_score === "fail"
                      ? "destructive"
                      : "secondary"
                  }
                >
                  {request.teardown_scan.overall_score}
                </Badge>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {formatDate(request.created_at)}
            </TableCell>
            <TableCell>
              {loading === request.id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <DropdownMenu>
                  <DropdownMenuTrigger className="inline-flex items-center justify-center rounded-md h-8 w-8 p-0 hover:bg-accent hover:text-accent-foreground">
                    <MoreHorizontal className="h-4 w-4" />
                    <span className="sr-only">Open menu</span>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => router.push(`/crm/audit-requests/${request.id}`)}>
                      <Eye className="mr-2 h-4 w-4" />
                      View details
                    </DropdownMenuItem>
                    {request.report_slug && (
                      <DropdownMenuItem onClick={() => window.open(`/teardown-report/${request.report_slug}`, "_blank")}>
                        <ExternalLink className="mr-2 h-4 w-4" />
                        View report
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    {request.status === "ready_for_review" && (
                      <>
                        <DropdownMenuItem onClick={() => handleAction(request.id, "approve")}>
                          <CheckCircle className="mr-2 h-4 w-4" />
                          Approve
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleAction(request.id, "reject")}>
                          <XCircle className="mr-2 h-4 w-4" />
                          Reject
                        </DropdownMenuItem>
                      </>
                    )}
                    {request.status === "approved" && (
                      <DropdownMenuItem onClick={() => handleAction(request.id, "send")}>
                        <Mail className="mr-2 h-4 w-4" />
                        Send email
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
