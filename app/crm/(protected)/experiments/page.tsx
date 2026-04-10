import { getExperiments } from "@/lib/crm/queries/experiments";
import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { Badge } from "@/components/crm/ui/badge";
import { Plus, FlaskConical } from "lucide-react";

export default async function ExperimentsPage() {
  const experiments = await getExperiments();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">A/B Experiments</h1>
          <p className="text-sm text-muted-foreground mt-1">Compare two sequences to find which performs better.</p>
        </div>
        <Link href="/crm/experiments/new" className={buttonVariants()}>
          <Plus className="mr-2 h-4 w-4" />
          New Experiment
        </Link>
      </div>

      {experiments.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
          <FlaskConical className="h-8 w-8 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">No experiments yet. Create one to start A/B testing your sequences.</p>
          <Link href="/crm/experiments/new" className={buttonVariants({ variant: "outline", size: "sm" }) + " mt-4"}>
            Create Experiment
          </Link>
        </div>
      ) : (
        <div className="divide-y rounded-md border">
          {experiments.map((exp) => {
            const variantA = exp.variants.find((v) => v.label === "A");
            const variantB = exp.variants.find((v) => v.label === "B");
            const totalEnrolled = exp.variants.reduce((n, v) => n + v.enrolled, 0);
            return (
              <div key={exp.id} className="flex items-center justify-between p-4">
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Link href={`/crm/experiments/${exp.id}`} className="font-medium hover:underline">
                      {exp.name}
                    </Link>
                    <Badge variant={exp.status === "active" ? "default" : "secondary"}>
                      {exp.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    A: {variantA?.sequence_name ?? "—"} · B: {variantB?.sequence_name ?? "—"} · {totalEnrolled} enrolled
                  </p>
                </div>
                <Link href={`/crm/experiments/${exp.id}`} className={buttonVariants({ variant: "ghost", size: "sm" })}>
                  View
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
