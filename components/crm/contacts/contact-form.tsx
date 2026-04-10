"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { contactCreateSchema } from "@/lib/crm/validations";
import { CONTACT_STATUSES, DEFAULT_ROLES } from "@/lib/crm/constants";
import { Contact, Company } from "@/lib/crm/types";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { Textarea } from "@/components/crm/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/crm/ui/select";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

type FormData = z.input<typeof contactCreateSchema>;

interface ContactFormProps {
  contact?: Contact;
  defaultCompanyId?: string;
}

export function ContactForm({ contact, defaultCompanyId }: ContactFormProps) {
  const router = useRouter();
  const isEditing = !!contact;
  const [companies, setCompanies] = useState<Company[]>([]);
  const [customRole, setCustomRole] = useState(false);
  const [customFields, setCustomFields] = useState<{ key: string; value: string }[]>(
    Object.entries(contact?.custom_fields ?? {}).map(([key, value]) => ({ key, value }))
  );

  const form = useForm<FormData>({
    resolver: zodResolver(contactCreateSchema),
    defaultValues: {
      company_id: contact?.company_id ?? defaultCompanyId ?? (undefined as unknown as string),
      name: contact?.name || "",
      email: contact?.email || "",
      role: contact?.role || "",
      phone: contact?.phone || "",
      linkedin_url: contact?.linkedin_url || "",
      status: contact?.status || "active",
      notes: contact?.notes || "",
    },
  });

  useEffect(() => {
    fetch("/api/crm/companies?limit=1000")
      .then((res) => res.json())
      .then((data) => setCompanies(data.companies || []))
      .catch(() => toast.error("Failed to load companies"));
  }, []);

  // Check if the current role is a custom one (not in DEFAULT_ROLES)
  useEffect(() => {
    const currentRole = contact?.role;
    if (currentRole && !DEFAULT_ROLES.includes(currentRole)) {
      setCustomRole(true);
    }
  }, [contact?.role]);

  async function onSubmit(data: FormData) {
    const url = isEditing ? `/api/crm/contacts/${contact.id}` : "/api/crm/contacts";
    const method = isEditing ? "PUT" : "POST";

    // Build custom_fields object from key-value pairs
    const custom_fields = customFields.length > 0
      ? Object.fromEntries(customFields.filter(f => f.key.trim()).map(f => [f.key.trim(), f.value]))
      : null;

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...data, custom_fields }),
    });

    if (res.ok) {
      const result = await res.json();
      toast.success(isEditing ? "Contact updated" : "Contact created");
      router.push(`/crm/contacts/${result.id}`);
      router.refresh();
    } else {
      const err = await res.json();
      toast.error(err.error || "Something went wrong");
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 max-w-2xl">
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Contact Information</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input id="name" {...form.register("name")} />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email *</Label>
            <Input id="email" type="email" {...form.register("email")} />
            {form.formState.errors.email && (
              <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Company *</Label>
            <Select
              value={form.watch("company_id") || ""}
              onValueChange={(value) => {
                if (value) form.setValue("company_id", value);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select company" />
              </SelectTrigger>
              <SelectContent>
                {companies.map((c) => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.company_id && (
              <p className="text-sm text-destructive">{form.formState.errors.company_id.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Status</Label>
            <Select
              value={form.watch("status") || "active"}
              onValueChange={(value) => { if (value) form.setValue("status", value as FormData["status"]); }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CONTACT_STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Role</Label>
            {customRole ? (
              <div className="flex gap-2">
                <Input
                  {...form.register("role")}
                  placeholder="Enter custom role"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setCustomRole(false);
                    form.setValue("role", "");
                  }}
                >
                  List
                </Button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Select
                  value={form.watch("role") || ""}
                  onValueChange={(value) => form.setValue("role", value ?? "")}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    {DEFAULT_ROLES.map((r) => (
                      <SelectItem key={r} value={r}>{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCustomRole(true)}
                >
                  Custom
                </Button>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" {...form.register("phone")} placeholder="+1 234 567 890" />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="linkedin_url">LinkedIn URL</Label>
          <Input id="linkedin_url" {...form.register("linkedin_url")} placeholder="https://linkedin.com/in/..." />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-medium">Notes</h3>
        <div className="space-y-2">
          <Textarea {...form.register("notes")} placeholder="Any notes about this contact..." rows={4} />
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium">Personalization Fields</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Use <code className="bg-muted px-1 rounded">{"{{key}}"}</code> in email templates to insert these values.</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => setCustomFields(prev => [...prev, { key: "", value: "" }])}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            Add Field
          </Button>
        </div>
        {customFields.map((field, i) => (
          <div key={i} className="flex gap-2 items-center">
            <Input
              placeholder="field_name"
              value={field.key}
              onChange={e => setCustomFields(prev => prev.map((f, j) => j === i ? { ...f, key: e.target.value } : f))}
              className="w-40 font-mono text-sm"
            />
            <Input
              placeholder="value"
              value={field.value}
              onChange={e => setCustomFields(prev => prev.map((f, j) => j === i ? { ...f, value: e.target.value } : f))}
              className="flex-1"
            />
            <Button type="button" variant="ghost" size="icon-sm" onClick={() => setCustomFields(prev => prev.filter((_, j) => j !== i))}>
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </div>
        ))}
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving..." : isEditing ? "Update Contact" : "Create Contact"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.back()}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
