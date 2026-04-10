import { getExperimentById, getEnrollmentsByExperimentId } from "@/lib/crm/queries/experiments";
import { notFound } from "next/navigation";
import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { Badge } from "@/components/crm/ui/badge";
import { ArrowLeft } from "lucide-react";
import { ExperimentStats } from "@/components/crm/experiments/experiment-stats";
import { EndExperimentButton } from "@/components/crm/experiments/end-experiment-button";
import { ExperimentEnrollDialog } from "@/components/crm/experiments/experiment-enroll-dialog";

export default async function ExperimentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [experiment, enrollments] = await Promise.all([
    getExperimentById(id),
    getEnrollmentsByExperimentId(id),
  ]);
  if (!experiment) notFound();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/crm/experiments" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
      </div>

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{experiment.name}</h1>
          <Badge variant={experiment.status === "active" ? "default" : "secondary"}>
            {experiment.status}
          </Badge>
        </div>
        <div className="flex gap-2">
          {experiment.status === "active" && (
            <>
              <ExperimentEnrollDialog experimentId={experiment.id} />
              <EndExperimentButton experimentId={experiment.id} />
            </>
          )}
        </div>
      </div>

      <ExperimentStats variants={experiment.variants} />

      <div>
        <h2 className="text-sm font-medium mb-3">Enrollments ({enrollments.length})</h2>
        {enrollments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No contacts enrolled yet.</p>
        ) : (
          <div className="rounded-md border divide-y">
            <div className="grid grid-cols-4 gap-4 px-4 py-2 text-xs font-medium text-muted-foreground">
              <span>Contact</span>
              <span>Variant</span>
              <span>Sequence</span>
              <span>Status</span>
            </div>
            {enrollments.map((enr) => (
              <div key={enr.id} className="grid grid-cols-4 gap-4 px-4 py-3 text-sm items-center">
                <div>
                  <p className="font-medium">{enr.contact_name}</p>
                  <p className="text-xs text-muted-foreground">{enr.contact_email}</p>
                </div>
                <Badge variant="outline" className="w-fit">
                  Variant {enr.ab_variant}
                </Badge>
                <span className="text-muted-foreground truncate">{enr.sequence_name}</span>
                <Badge
                  variant={enr.status === "active" ? "default" : "secondary"}
                  className="w-fit"
                >
                  {enr.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
