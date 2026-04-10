import Link from "next/link";
import { buttonVariants } from "@/components/crm/ui/button";
import { SequenceTable } from "@/components/crm/sequences/sequence-table";
import { getSequences } from "@/lib/crm/queries/sequences";
import { Plus } from "lucide-react";

export default async function SequencesPage() {
  const sequences = await getSequences();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sequences</h1>
          <p className="text-sm text-muted-foreground">
            {sequences.length} sequence{sequences.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <Link href="/crm/sequences/new" className={buttonVariants()}>
          <Plus className="mr-2 h-4 w-4" />
          Create Sequence
        </Link>
      </div>
      <SequenceTable sequences={sequences} />
    </div>
  );
}
