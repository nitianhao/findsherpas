"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { companyCreateSchema } from "@/lib/crm/validations";
import { COMPANY_STATUSES, PLATFORMS, SEARCH_SOLUTIONS, SIZE_ESTIMATES, REVENUE_ESTIMATES } from "@/lib/crm/constants";
import { Company } from "@/lib/crm/types";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { Textarea } from "@/components/crm/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/crm/ui/select";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

type FormData = z.input<typeof companyCreateSchema>;

interface CompanyFormProps {
  company?: Company;
}

export function CompanyForm({ company }: CompanyFormProps) {
  const router = useRouter();
  const isEditing = !!company;

  const form = useForm<FormData>({
    resolver: zodResolver(companyCreateSchema),
    defaultValues: {
      name: company?.name || "",
      website: company?.website || "",
      industry: company?.industry || "",
      platform: company?.platform || "",
      search_solution: company?.search_solution || "",
      size_estimate: company?.size_estimate || "",
      revenue_estimate: company?.revenue_estimate || "",
      social_linkedin: company?.social_linkedin || "",
      social_twitter: company?.social_twitter || "",
      social_facebook: company?.social_facebook || "",
      tech_stack_notes: company?.tech_stack_notes || "",
      notes: company?.notes || "",
      status: company?.status || "prospect",
    },
  });

  async function onSubmit(data: FormData) {
    const url = isEditing ? `/api/crm/companies/${company.id}` : "/api/crm/companies";
    const method = isEditing ? "PUT" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      const result = await res.json();
      toast.success(isEditing ? "Company updated" : "Company created");
      router.push(`/crm/companies/${result.id}`);
      router.refresh();
    } else {
      const err = await res.json();
      toast.error(err.error || "Something went wrong");
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-2xl">
      {/* Basic Info */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Basic Information</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Company Name *</Label>
            <Input id="name" {...form.register("name")} />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="website">Website</Label>
            <Input id="website" {...form.register("website")} placeholder="https://..." />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="industry">Industry</Label>
            <Input id="industry" {...form.register("industry")} placeholder="e.g. Fashion, Electronics" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select
              value={form.watch("status")}
              onValueChange={(value) => { if (value) form.setValue("status", value as FormData["status"]); }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COMPANY_STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Ecommerce Details */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Ecommerce Details</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Platform</Label>
            <Select
              value={form.watch("platform") || ""}
              onValueChange={(value) => form.setValue("platform", value ?? "")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select platform" />
              </SelectTrigger>
              <SelectContent>
                {PLATFORMS.map((p) => (
                  <SelectItem key={p} value={p}>{p}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Search Solution</Label>
            <Select
              value={form.watch("search_solution") || ""}
              onValueChange={(value) => form.setValue("search_solution", value ?? "")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select search solution" />
              </SelectTrigger>
              <SelectContent>
                {SEARCH_SOLUTIONS.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Company Size</Label>
            <Select
              value={form.watch("size_estimate") || ""}
              onValueChange={(value) => form.setValue("size_estimate", value ?? "")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select size" />
              </SelectTrigger>
              <SelectContent>
                {SIZE_ESTIMATES.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Revenue Estimate</Label>
            <Select
              value={form.watch("revenue_estimate") || ""}
              onValueChange={(value) => form.setValue("revenue_estimate", value ?? "")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select revenue" />
              </SelectTrigger>
              <SelectContent>
                {REVENUE_ESTIMATES.map((r) => (
                  <SelectItem key={r} value={r}>{r}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Social Links */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Social Links</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>LinkedIn</Label>
            <Input {...form.register("social_linkedin")} placeholder="LinkedIn URL" />
          </div>
          <div className="space-y-2">
            <Label>Twitter/X</Label>
            <Input {...form.register("social_twitter")} placeholder="Twitter URL" />
          </div>
          <div className="space-y-2">
            <Label>Facebook</Label>
            <Input {...form.register("social_facebook")} placeholder="Facebook URL" />
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Notes</h3>
        <div className="space-y-2">
          <Label>Tech Stack Notes</Label>
          <Textarea {...form.register("tech_stack_notes")} placeholder="Search technology, integrations, etc." rows={3} />
        </div>
        <div className="space-y-2">
          <Label>General Notes</Label>
          <Textarea {...form.register("notes")} placeholder="Any additional notes..." rows={3} />
        </div>
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving..." : isEditing ? "Update Company" : "Create Company"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.back()}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
