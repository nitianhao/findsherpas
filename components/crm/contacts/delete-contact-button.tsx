"use client";

import { Button } from "@/components/crm/ui/button";
import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export function DeleteContactButton({ contactId }: { contactId: string }) {
  const router = useRouter();

  async function handleDelete() {
    if (!confirm("Delete this contact? This cannot be undone.")) return;

    const res = await fetch(`/api/crm/contacts/${contactId}`, { method: "DELETE" });
    if (res.ok) {
      toast.success("Contact deleted");
      router.push("/contacts");
      router.refresh();
    } else {
      toast.error("Failed to delete contact");
    }
  }

  return (
    <Button variant="destructive" onClick={handleDelete}>
      <Trash2 className="mr-2 h-4 w-4" />
      Delete
    </Button>
  );
}
