import { getSequenceById } from "@/lib/crm/queries/sequences";
import { SequenceForm } from "@/components/crm/sequences/sequence-form";
import { notFound } from "next/navigation";

export default async function EditSequencePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const sequence = await getSequenceById(id);
  if (!sequence) notFound();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Edit {sequence.name}</h1>
      <SequenceForm sequence={sequence} />
    </div>
  );
}
