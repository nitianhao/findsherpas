import { SequenceForm } from "@/components/crm/sequences/sequence-form";

export default function NewSequencePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Create Sequence</h1>
      <SequenceForm />
    </div>
  );
}
