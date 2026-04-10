"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { reminderCreateSchema } from "@/lib/crm/validations";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { Textarea } from "@/components/crm/ui/textarea";
import { Card } from "@/components/crm/ui/card";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { format } from "date-fns";

type FormData = z.input<typeof reminderCreateSchema>;

export function ReminderForm() {
  const router = useRouter();

  const form = useForm<FormData>({
    resolver: zodResolver(reminderCreateSchema),
    defaultValues: {
      title: "",
      description: "",
      due_date: format(new Date(), "yyyy-MM-dd"),
      company_id: null,
      contact_id: null,
    },
  });

  async function onSubmit(data: FormData) {
    try {
      const res = await fetch("/api/crm/reminders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        toast.success("Reminder created");
        form.reset({
          title: "",
          description: "",
          due_date: format(new Date(), "yyyy-MM-dd"),
          company_id: null,
          contact_id: null,
        });
        router.refresh();
      } else {
        const err = await res.json();
        toast.error(err.error || "Failed to create reminder");
      }
    } catch {
      toast.error("Failed to create reminder");
    }
  }

  return (
    <Card className="p-4">
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <h3 className="text-sm font-semibold">New Reminder</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="reminder-title">Title *</Label>
            <Input
              id="reminder-title"
              placeholder="Follow up with..."
              {...form.register("title")}
            />
            {form.formState.errors.title && (
              <p className="text-sm text-destructive">
                {form.formState.errors.title.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="reminder-due-date">Due Date *</Label>
            <Input
              id="reminder-due-date"
              type="date"
              {...form.register("due_date")}
            />
            {form.formState.errors.due_date && (
              <p className="text-sm text-destructive">
                {form.formState.errors.due_date.message}
              </p>
            )}
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="reminder-description">Description (optional)</Label>
          <Textarea
            id="reminder-description"
            placeholder="Additional details..."
            rows={2}
            {...form.register("description")}
          />
        </div>
        <div className="flex justify-end">
          <Button type="submit" size="sm" disabled={form.formState.isSubmitting}>
            <Plus className="h-4 w-4 mr-1.5" />
            {form.formState.isSubmitting ? "Adding..." : "Add Reminder"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
