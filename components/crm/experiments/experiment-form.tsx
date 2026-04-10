"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { toast } from "sonner";
import type { Sequence } from "@/lib/crm/types";

export function ExperimentForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [sequenceAId, setSequenceAId] = useState("");
  const [sequenceBId, setSequenceBId] = useState("");
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch("/api/crm/sequences")
      .then((r) => r.json())
      .then((d) => setSequences(Array.isArray(d) ? d : (d.sequences ?? [])))
      .catch(() => toast.error("Failed to load sequences"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !sequenceAId || !sequenceBId) {
      toast.error("All fields are required");
      return;
    }
    if (sequenceAId === sequenceBId) {
      toast.error("Variant A and B must be different sequences");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/crm/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, sequence_a_id: sequenceAId, sequence_b_id: sequenceBId }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success("Experiment created");
        router.push(`/crm/experiments/${data.id}`);
      } else {
        const err = await res.json();
        toast.error(err.error || "Failed to create experiment");
      }
    } catch {
      toast.error("Failed to create experiment");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Experiment Details</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Experiment Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Subject line test — May 2025"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="seq-a">Variant A — Sequence</Label>
              <select
                id="seq-a"
                value={sequenceAId}
                onChange={(e) => setSequenceAId(e.target.value)}
                disabled={loading}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">Select sequence...</option>
                {sequences.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="seq-b">Variant B — Sequence</Label>
              <select
                id="seq-b"
                value={sequenceBId}
                onChange={(e) => setSequenceBId(e.target.value)}
                disabled={loading}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">Select sequence...</option>
                {sequences.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !name.trim() || !sequenceAId || !sequenceBId}>
              {submitting ? "Creating..." : "Create Experiment"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
