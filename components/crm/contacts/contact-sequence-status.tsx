"use client";

import { useState, useEffect, useCallback } from "react";
import type { ContactSequence, ContactSequenceEvent } from "@/lib/crm/types";
import { StatusBadge } from "@/components/crm/shared/status-badge";
import { Button } from "@/components/crm/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/crm/ui/table";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Send, MessageSquare, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import Link from "next/link";

interface EnrollmentWithEvents extends ContactSequence {
  events?: ContactSequenceEvent[];
  totalSteps?: number;
}

export function ContactSequenceStatus({ contactId }: { contactId: string }) {
  const router = useRouter();
  const [enrollments, setEnrollments] = useState<EnrollmentWithEvents[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchEnrollments = useCallback(async () => {
    try {
      const res = await fetch(`/api/crm/contacts/${contactId}/enrollments`);
      if (res.ok) {
        const data = await res.json();
        setEnrollments(data);
      }
    } catch {
      // Silently fail -- the section just won't show
    } finally {
      setLoading(false);
    }
  }, [contactId]);

  useEffect(() => {
    fetchEnrollments();
  }, [fetchEnrollments]);

  async function handleEventAction(eventId: string, action: string) {
    const res = await fetch(`/api/crm/events/${eventId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (res.ok) {
      toast.success(`Event marked as ${action}`);
      fetchEnrollments();
      router.refresh();
    } else {
      toast.error(`Failed to mark event as ${action}`);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Sequence Enrollments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (enrollments.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Sequence Enrollments</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Not enrolled in any sequences.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Sequence Enrollments</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {enrollments.map((enrollment) => (
          <div key={enrollment.id} className="rounded-md border">
            <button
              type="button"
              className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors text-left"
              onClick={() =>
                setExpandedId(expandedId === enrollment.id ? null : enrollment.id)
              }
            >
              <div className="flex items-center gap-3">
                <div>
                  <Link
                    href={`/crm/sequences/${enrollment.sequence_id}`}
                    className="text-sm font-medium hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {enrollment.sequence_name}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    Step {enrollment.current_step}
                    {enrollment.totalSteps
                      ? ` of ${enrollment.totalSteps}`
                      : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={enrollment.status} />
                {expandedId === enrollment.id ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </button>

            {expandedId === enrollment.id && enrollment.events && (
              <div className="border-t px-3 pb-3">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Step</TableHead>
                      <TableHead>Subject</TableHead>
                      <TableHead>Scheduled</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {enrollment.events.map((event) => (
                      <TableRow key={event.id}>
                        <TableCell className="text-sm">
                          {event.step_order}
                        </TableCell>
                        <TableCell className="text-sm max-w-[200px] truncate">
                          {event.subject_template || "--"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {event.scheduled_date || "--"}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={event.status} />
                        </TableCell>
                        <TableCell>
                          {event.status === "pending" && (
                            <div className="flex gap-1">
                              <Button
                                variant="ghost"
                                size="xs"
                                onClick={() =>
                                  handleEventAction(event.id, "sent")
                                }
                              >
                                <Send className="mr-1 h-3 w-3" />
                                Sent
                              </Button>
                              <Button
                                variant="ghost"
                                size="xs"
                                onClick={() =>
                                  handleEventAction(event.id, "skipped")
                                }
                              >
                                Skip
                              </Button>
                            </div>
                          )}
                          {event.status === "sent" && (
                            <Button
                              variant="ghost"
                              size="xs"
                              onClick={() =>
                                handleEventAction(event.id, "replied")
                              }
                            >
                              <MessageSquare className="mr-1 h-3 w-3" />
                              Replied
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
