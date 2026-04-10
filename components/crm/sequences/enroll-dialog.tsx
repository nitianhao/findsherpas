"use client";

import { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/crm/ui/dialog";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Checkbox } from "@/components/crm/ui/checkbox";
import { ScrollArea } from "@/components/crm/ui/scroll-area";
import { Label } from "@/components/crm/ui/label";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { UserPlus, Search, Loader2 } from "lucide-react";
import type { Contact } from "@/lib/crm/types";

interface EnrollDialogProps {
  sequenceId: string;
}

export function EnrollDialog({ sequenceId }: EnrollDialogProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch("/api/crm/contacts?limit=500")
      .then((res) => res.json())
      .then((data) => {
        setContacts(data.contacts || []);
      })
      .catch(() => {
        toast.error("Failed to load contacts");
      })
      .finally(() => setLoading(false));
  }, [open]);

  const filtered = useMemo(() => {
    if (!search) return contacts;
    const q = search.toLowerCase();
    return contacts.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        (c.company_name && c.company_name.toLowerCase().includes(q))
    );
  }, [contacts, search]);

  function toggleContact(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  async function handleSubmit() {
    if (selectedIds.size === 0) {
      toast.error("Select at least one contact");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch("/api/crm/sequences/enroll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact_ids: Array.from(selectedIds),
          sequence_id: sequenceId,
        }),
      });

      if (res.ok) {
        toast.success(`Enrolled ${selectedIds.size} contact(s)`);
        setOpen(false);
        setSelectedIds(new Set());
        setSearch("");
        router.refresh();
      } else {
        const data = await res.json();
        toast.error(data.error || "Failed to enroll contacts");
      }
    } catch {
      toast.error("Failed to enroll contacts");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        className="inline-flex shrink-0 items-center justify-center rounded-lg bg-primary px-2.5 h-8 text-sm font-medium text-primary-foreground gap-1.5"
      >
        <UserPlus className="h-4 w-4" />
        Enroll Contacts
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Enroll Contacts in Sequence</DialogTitle>
          <DialogDescription>
            Select contacts to enroll. They will start receiving emails based on the sequence steps.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search contacts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          <ScrollArea className="h-[280px] rounded-md border p-2">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No contacts found
              </p>
            ) : (
              <div className="space-y-1">
                {filtered.map((contact) => (
                  <label
                    key={contact.id}
                    className="flex items-center gap-3 rounded-md px-2 py-1.5 hover:bg-muted cursor-pointer"
                  >
                    <Checkbox
                      checked={selectedIds.has(contact.id)}
                      onCheckedChange={() => toggleContact(contact.id)}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {contact.name}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {contact.email}
                        {contact.company_name && ` - ${contact.company_name}`}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </ScrollArea>

          {selectedIds.size > 0 && (
            <p className="text-xs text-muted-foreground">
              {selectedIds.size} contact(s) selected
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            onClick={handleSubmit}
            disabled={submitting || selectedIds.size === 0}
          >
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Enrolling...
              </>
            ) : (
              `Enroll ${selectedIds.size > 0 ? selectedIds.size : ""} Contact${selectedIds.size !== 1 ? "s" : ""}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
