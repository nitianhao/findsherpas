"use client";

import { Button } from "@/components/crm/ui/button";
import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export function DeleteCompanyButton({ companyId }: { companyId: string }) {
  const router = useRouter();

  async function handleDelete() {
    if (!confirm("Delete this company? All associated contacts and sequence data will be removed.")) return;

    const res = await fetch(`/api/crm/companies/${companyId}`, { method: "DELETE" });
    if (res.ok) {
      toast.success("Company deleted");
      router.push("/crm/companies");
      router.refresh();
    } else {
      toast.error("Failed to delete company");
    }
  }

  return (
    <Button variant="destructive" onClick={handleDelete}>
      <Trash2 className="mr-2 h-4 w-4" />
      Delete
    </Button>
  );
}
