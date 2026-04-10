import { getSequenceById, getStepsBySequenceId } from "@/lib/crm/queries/sequences";
import { getEnrollmentsBySequenceId } from "@/lib/crm/queries/enrollments";
import { notFound } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { Badge } from "@/components/crm/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { StepEditor } from "@/components/crm/sequences/step-editor";
import { EnrollmentTable } from "@/components/crm/sequences/enrollment-table";
import { EnrollDialog } from "@/components/crm/sequences/enroll-dialog";
import { Pencil, ArrowLeft, Users } from "lucide-react";

export default async function SequenceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sequence = await getSequenceById(id);
  if (!sequence) notFound();

  const steps = await getStepsBySequenceId(sequence.id);
  const enrollments = await getEnrollmentsBySequenceId(sequence.id);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/crm/sequences" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{sequence.name}</h1>
            <Badge variant={sequence.is_active === 1 ? "default" : "secondary"}>
              {sequence.is_active === 1 ? "Active" : "Inactive"}
            </Badge>
          </div>
          {sequence.description && (
            <p className="text-sm text-muted-foreground mt-1">{sequence.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <EnrollDialog sequenceId={sequence.id} />
          <Link href={`/crm/sequences/${sequence.id}/edit`} className={buttonVariants({ variant: "outline" })}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Steps</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{sequence.steps_count ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Enrolled Contacts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <p className="text-2xl font-bold">{enrollments.length}</p>
              <Users className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {enrollments.filter((e) => e.status === "active").length}
            </p>
          </CardContent>
        </Card>
      </div>

      <StepEditor sequenceId={sequence.id} initialSteps={steps} />

      <div>
        <h2 className="text-lg font-semibold mb-3">Enrolled Contacts</h2>
        {enrollments.length > 0 ? (
          <EnrollmentTable enrollments={enrollments} />
        ) : (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-sm text-muted-foreground">
                No contacts enrolled yet. Click &quot;Enroll Contacts&quot; to get started.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
