import { getPipelineContacts } from "@/lib/crm/queries/pipeline";
import { PipelineBoard } from "@/components/crm/pipeline/pipeline-board";

export default async function PipelinePage() {
  const contacts = await getPipelineContacts();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Pipeline</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track deals after contacts reply to your sequences.
        </p>
      </div>

      {contacts.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <p className="text-sm text-muted-foreground">
            No contacts in the pipeline yet. Mark an enrollment as &quot;Replied&quot; from the contact page to get started.
          </p>
        </div>
      ) : (
        <PipelineBoard initialContacts={contacts} />
      )}
    </div>
  );
}
