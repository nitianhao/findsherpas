"use client";

import { useState } from "react";
import type { PipelineContact, DealStage } from "@/lib/crm/queries/pipeline";
import { DEAL_STAGES } from "@/lib/crm/queries/pipeline";
import { Card, CardContent } from "@/components/crm/ui/card";
import { Badge } from "@/components/crm/ui/badge";
import Link from "next/link";
import { Building2, Mail } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

const STAGE_LABELS: Record<DealStage, string> = {
  replied: "Replied",
  "meeting-booked": "Meeting Booked",
  "proposal-sent": "Proposal Sent",
  won: "Won",
  lost: "Lost",
  "not-interested": "Not Interested",
};

const STAGE_COLORS: Record<DealStage, string> = {
  replied: "bg-blue-50 border-blue-200",
  "meeting-booked": "bg-purple-50 border-purple-200",
  "proposal-sent": "bg-amber-50 border-amber-200",
  won: "bg-green-50 border-green-200",
  lost: "bg-red-50 border-red-200",
  "not-interested": "bg-gray-50 border-gray-200",
};

const STAGE_HEADER_COLORS: Record<DealStage, string> = {
  replied: "text-blue-700",
  "meeting-booked": "text-purple-700",
  "proposal-sent": "text-amber-700",
  won: "text-green-700",
  lost: "text-red-700",
  "not-interested": "text-gray-600",
};

interface PipelineBoardProps {
  initialContacts: PipelineContact[];
}

export function PipelineBoard({ initialContacts }: PipelineBoardProps) {
  const router = useRouter();
  const [contacts, setContacts] = useState(initialContacts);
  const [loading, setLoading] = useState<Set<string>>(new Set());

  async function moveStage(enrollmentId: string, stage: DealStage) {
    setLoading((prev) => new Set(prev).add(enrollmentId));
    try {
      const res = await fetch(`/api/crm/enrollments/${enrollmentId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deal_stage: stage }),
      });
      if (res.ok) {
        setContacts((prev) =>
          prev.map((c) =>
            c.enrollment_id === enrollmentId ? { ...c, deal_stage: stage } : c
          )
        );
        router.refresh();
      } else {
        toast.error("Failed to update stage");
      }
    } catch {
      toast.error("Failed to update stage");
    } finally {
      setLoading((prev) => {
        const next = new Set(prev);
        next.delete(enrollmentId);
        return next;
      });
    }
  }

  const byStage = DEAL_STAGES.reduce<Record<DealStage, PipelineContact[]>>(
    (acc, stage) => {
      acc[stage] = contacts.filter((c) => c.deal_stage === stage);
      return acc;
    },
    {} as Record<DealStage, PipelineContact[]>
  );

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {DEAL_STAGES.map((stage) => (
        <div
          key={stage}
          className={`flex-shrink-0 w-64 rounded-lg border p-3 ${STAGE_COLORS[stage]}`}
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className={`text-sm font-semibold ${STAGE_HEADER_COLORS[stage]}`}>
              {STAGE_LABELS[stage]}
            </h3>
            <Badge variant="secondary" className="text-xs">
              {byStage[stage].length}
            </Badge>
          </div>
          <div className="space-y-2">
            {byStage[stage].map((contact) => (
              <Card key={contact.enrollment_id} className="bg-background shadow-sm">
                <CardContent className="p-3 space-y-2">
                  <div>
                    <Link
                      href={`/crm/contacts/${contact.contact_id}`}
                      className="text-sm font-medium hover:underline leading-tight block"
                    >
                      {contact.contact_name}
                    </Link>
                    {contact.company_name && (
                      <div className="flex items-center gap-1 mt-0.5">
                        <Building2 className="h-3 w-3 text-muted-foreground" />
                        {contact.company_id ? (
                          <Link
                            href={`/crm/companies/${contact.company_id}`}
                            className="text-xs text-muted-foreground hover:underline"
                          >
                            {contact.company_name}
                          </Link>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {contact.company_name}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Mail className="h-3 w-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground truncate">
                      {contact.sequence_name}
                    </span>
                  </div>
                  <select
                    value={stage}
                    disabled={loading.has(contact.enrollment_id)}
                    onChange={(e) =>
                      moveStage(contact.enrollment_id, e.target.value as DealStage)
                    }
                    className="w-full text-xs border rounded px-2 py-1 bg-background text-foreground disabled:opacity-50"
                  >
                    {DEAL_STAGES.map((s) => (
                      <option key={s} value={s}>
                        {STAGE_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </CardContent>
              </Card>
            ))}
            {byStage[stage].length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                No contacts
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
