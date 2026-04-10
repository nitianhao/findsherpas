import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { ArrowLeft } from "lucide-react";
import { ExperimentForm } from "@/components/crm/experiments/experiment-form";

export default function NewExperimentPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/crm/experiments" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
      </div>
      <h1 className="text-2xl font-bold">New A/B Experiment</h1>
      <ExperimentForm />
    </div>
  );
}
