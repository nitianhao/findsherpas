import Link from "next/link";
import { getAuditRequests, getAuditRequestStats, type AuditRequestStatus } from "@/lib/crm/queries/audit-requests";
import { Badge } from "@/components/crm/ui/badge";
import { Button } from "@/components/crm/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { AuditRequestTable } from "@/components/crm/audit-requests/audit-request-table";

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

export default async function AuditRequestsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; search?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = params.status as AuditRequestStatus | undefined;
  const search = params.search;
  const page = parseInt(params.page || "1", 10);
  const limit = 20;
  const offset = (page - 1) * limit;

  const [{ requests, total }, stats] = await Promise.all([
    getAuditRequests({ status, search, limit, offset }),
    getAuditRequestStats(),
  ]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Teardown Requests</h1>
          <p className="text-muted-foreground">
            Manage incoming teardown requests from the public form.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-6">
        {(Object.keys(STATUS_LABELS) as AuditRequestStatus[]).map((s) => (
          <Card key={s}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {STATUS_LABELS[s]}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.byStatus[s]}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Request Queue</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Link href="/crm/audit-requests">
                <Badge variant={!status ? "default" : "outline"}>All ({stats.total})</Badge>
              </Link>
              {(Object.keys(STATUS_LABELS) as AuditRequestStatus[]).map((s) => (
                <Link key={s} href={`/crm/audit-requests?status=${s}`}>
                  <Badge variant={status === s ? STATUS_VARIANTS[s] : "outline"}>
                    {STATUS_LABELS[s]} ({stats.byStatus[s]})
                  </Badge>
                </Link>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {requests.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {status
                ? `No ${STATUS_LABELS[status].toLowerCase()} requests.`
                : "No teardown requests yet."}
            </div>
          ) : (
            <AuditRequestTable requests={requests} />
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {offset + 1}-{Math.min(offset + limit, total)} of {total}
              </p>
              <div className="flex gap-2">
                {page > 1 && (
                  <Link
                    href={`/crm/audit-requests?${new URLSearchParams({
                      ...(status && { status }),
                      ...(search && { search }),
                      page: String(page - 1),
                    })}`}
                  >
                    <Button variant="outline" size="sm">
                      Previous
                    </Button>
                  </Link>
                )}
                {page < totalPages && (
                  <Link
                    href={`/crm/audit-requests?${new URLSearchParams({
                      ...(status && { status }),
                      ...(search && { search }),
                      page: String(page + 1),
                    })}`}
                  >
                    <Button variant="outline" size="sm">
                      Next
                    </Button>
                  </Link>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
