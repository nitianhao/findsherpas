"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/crm/ui/button";
import { toast } from "sonner";

interface EndExperimentButtonProps {
  experimentId: string;
}

export function EndExperimentButton({ experimentId }: EndExperimentButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleEnd() {
    if (!confirm("End this experiment? This cannot be undone.")) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/crm/experiments/${experimentId}`, { method: "PUT" });
      if (res.ok) {
        toast.success("Experiment ended");
        router.refresh();
      } else {
        toast.error("Failed to end experiment");
      }
    } catch {
      toast.error("Failed to end experiment");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button variant="outline" onClick={handleEnd} disabled={loading}>
      {loading ? "Ending..." : "End Experiment"}
    </Button>
  );
}
