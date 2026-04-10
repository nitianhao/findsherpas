"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { sequenceCreateSchema } from "@/lib/crm/validations";
import { Sequence } from "@/lib/crm/types";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { Textarea } from "@/components/crm/ui/textarea";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

type FormData = z.input<typeof sequenceCreateSchema>;

interface SequenceFormProps {
  sequence?: Sequence;
}

export function SequenceForm({ sequence }: SequenceFormProps) {
  const router = useRouter();
  const isEditing = !!sequence;

  const form = useForm<FormData>({
    resolver: zodResolver(sequenceCreateSchema),
    defaultValues: {
      name: sequence?.name || "",
      description: sequence?.description || "",
      is_active: sequence?.is_active ?? 1,
    },
  });

  async function onSubmit(data: FormData) {
    const url = isEditing ? `/api/crm/sequences/${sequence.id}` : "/api/crm/sequences";
    const method = isEditing ? "PUT" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      const result = await res.json();
      toast.success(isEditing ? "Sequence updated" : "Sequence created");
      router.push(`/crm/sequences/${result.id}`);
      router.refresh();
    } else {
      const err = await res.json();
      toast.error(err.error || "Something went wrong");
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 max-w-2xl">
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Sequence Name *</Label>
          <Input id="name" {...form.register("name")} placeholder="e.g. Initial Outreach" />
          {form.formState.errors.name && (
            <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
          )}
        </div>
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            {...form.register("description")}
            placeholder="What is this sequence for?"
            rows={3}
          />
        </div>
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving..." : isEditing ? "Update Sequence" : "Create Sequence"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.back()}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
