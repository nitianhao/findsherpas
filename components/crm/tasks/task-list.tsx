"use client";

import { useState } from "react";
import type { EmailTask } from "@/lib/crm/queries/tasks";
import type { Reminder } from "@/lib/crm/types";
import { resolveTemplate, buildVars } from "@/lib/crm/template";
import { Button } from "@/components/crm/ui/button";
import { Badge } from "@/components/crm/ui/badge";
import { Card } from "@/components/crm/ui/card";
import { Checkbox } from "@/components/crm/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/crm/ui/dialog";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import {
  Send,
  Reply,
  Trash2,
  Clock,
  Building2,
  User,
  Mail,
  Eye,
} from "lucide-react";

interface TaskListProps {
  initialEmailTasks: EmailTask[];
  initialReminders: Reminder[];
}

interface PreviewState {
  subject: string;
  body: string;
  to: string;
  task: EmailTask;
}

export function TaskList({ initialEmailTasks, initialReminders }: TaskListProps) {
  const router = useRouter();
  const [emailTasks, setEmailTasks] = useState(initialEmailTasks);
  const [reminders, setReminders] = useState(initialReminders);
  const [loadingEvents, setLoadingEvents] = useState<Set<string>>(new Set());
  const [loadingReminders, setLoadingReminders] = useState<Set<string>>(new Set());
  const [preview, setPreview] = useState<PreviewState | null>(null);

  // Group email tasks by company
  const tasksByCompany = emailTasks.reduce<Record<string, EmailTask[]>>((acc, task) => {
    const key = task.company_name || "No Company";
    if (!acc[key]) acc[key] = [];
    acc[key].push(task);
    return acc;
  }, {});

  function openPreview(task: EmailTask) {
    const vars = buildVars(task);
    const subject = task.subject_template ? resolveTemplate(task.subject_template, vars) : "(no subject)";
    const body = task.body_template ? resolveTemplate(task.body_template, vars) : "";
    setPreview({ subject, body, to: task.contact_email, task });
  }

  async function handleSendEmail(eventId: string) {
    setLoadingEvents((prev) => new Set(prev).add(eventId));
    try {
      const res = await fetch(`/api/crm/events/${eventId}/send`, { method: "POST" });
      if (res.ok) {
        setEmailTasks((prev) => prev.filter((t) => t.event_id !== eventId));
        if (preview?.task.event_id === eventId) setPreview(null);
        toast.success("Email sent");
        router.refresh();
      } else {
        const err = await res.json();
        if (res.status === 422 && err.code === 'INVALID_EMAIL') {
          toast.error("Invalid email domain — check address before sending");
        } else {
          toast.error(err.error || "Failed to send email");
        }
      }
    } catch {
      toast.error("Failed to send email");
    } finally {
      setLoadingEvents((prev) => {
        const next = new Set(prev);
        next.delete(eventId);
        return next;
      });
    }
  }

  async function handleMarkEvent(eventId: string, action: "replied") {
    setLoadingEvents((prev) => new Set(prev).add(eventId));
    try {
      const res = await fetch(`/api/crm/events/${eventId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        setEmailTasks((prev) => prev.filter((t) => t.event_id !== eventId));
        toast.success("Marked as replied");
        router.refresh();
      } else {
        toast.error("Failed to update event");
      }
    } catch {
      toast.error("Failed to update event");
    } finally {
      setLoadingEvents((prev) => {
        const next = new Set(prev);
        next.delete(eventId);
        return next;
      });
    }
  }

  async function handleCompleteReminder(reminderId: string) {
    setLoadingReminders((prev) => new Set(prev).add(reminderId));
    try {
      const res = await fetch(`/api/crm/reminders/${reminderId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_completed: 1 }),
      });
      if (res.ok) {
        setReminders((prev) => prev.filter((r) => r.id !== reminderId));
        toast.success("Reminder completed");
        router.refresh();
      } else {
        toast.error("Failed to complete reminder");
      }
    } catch {
      toast.error("Failed to complete reminder");
    } finally {
      setLoadingReminders((prev) => {
        const next = new Set(prev);
        next.delete(reminderId);
        return next;
      });
    }
  }

  async function handleDeleteReminder(reminderId: string) {
    setLoadingReminders((prev) => new Set(prev).add(reminderId));
    try {
      const res = await fetch(`/api/crm/reminders/${reminderId}`, { method: "DELETE" });
      if (res.ok) {
        setReminders((prev) => prev.filter((r) => r.id !== reminderId));
        toast.success("Reminder deleted");
        router.refresh();
      } else {
        toast.error("Failed to delete reminder");
      }
    } catch {
      toast.error("Failed to delete reminder");
    } finally {
      setLoadingReminders((prev) => {
        const next = new Set(prev);
        next.delete(reminderId);
        return next;
      });
    }
  }

  return (
    <>
      <div className="space-y-8">
        {/* Email Tasks Section */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Emails to Send
            {emailTasks.length > 0 && (
              <Badge variant="secondary">{emailTasks.length}</Badge>
            )}
          </h2>

          {emailTasks.length === 0 ? (
            <Card className="p-6">
              <p className="text-muted-foreground text-center">
                No emails to send today. All caught up!
              </p>
            </Card>
          ) : (
            <div className="space-y-6">
              {Object.entries(tasksByCompany).map(([companyName, tasks]) => (
                <div key={companyName}>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                    <Building2 className="h-3.5 w-3.5" />
                    {tasks[0].company_id ? (
                      <Link
                        href={`/crm/companies/${tasks[0].company_id}`}
                        className="hover:underline"
                      >
                        {companyName}
                      </Link>
                    ) : (
                      companyName
                    )}
                  </h3>
                  <div className="space-y-2">
                    {tasks.map((task) => (
                      <Card key={task.event_id} className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0 space-y-1">
                            <div className="flex items-center gap-2">
                              <User className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                              <Link
                                href={`/crm/contacts/${task.contact_id}`}
                                className="font-medium hover:underline truncate"
                              >
                                {task.contact_name}
                              </Link>
                              <span className="text-sm text-muted-foreground truncate">
                                {task.contact_email}
                              </span>
                              {task.is_overdue && (
                                <Badge variant="destructive" className="shrink-0">
                                  <Clock className="h-3 w-3 mr-1" />
                                  Overdue
                                </Badge>
                              )}
                              {task.send_hour != null && (
                                <Badge variant="outline" className="shrink-0 text-xs">
                                  <Clock className="h-3 w-3 mr-1" />
                                  {task.send_hour < 12 ? `${task.send_hour}:00 AM` : task.send_hour === 12 ? '12:00 PM' : `${task.send_hour - 12}:00 PM`}
                                </Badge>
                              )}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              <span className="font-medium">{task.sequence_name}</span>
                              {" — "}
                              Step {task.step_order}
                            </div>
                            {task.subject_template && (
                              <p className="text-sm truncate text-muted-foreground">
                                Subject: {resolveTemplate(task.subject_template, buildVars(task))}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => openPreview(task)}
                              title="Preview email"
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleSendEmail(task.event_id)}
                              disabled={loadingEvents.has(task.event_id)}
                            >
                              <Send className="h-3.5 w-3.5 mr-1.5" />
                              {loadingEvents.has(task.event_id) ? "Sending..." : "Send"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleMarkEvent(task.event_id, "replied")}
                              disabled={loadingEvents.has(task.event_id)}
                            >
                              <Reply className="h-3.5 w-3.5 mr-1.5" />
                              Replied
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Reminders Section */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Reminders
            {reminders.length > 0 && (
              <Badge variant="secondary">{reminders.length}</Badge>
            )}
          </h2>

          {reminders.length === 0 ? (
            <Card className="p-6">
              <p className="text-muted-foreground text-center">
                No reminders due. Use the form above to create one.
              </p>
            </Card>
          ) : (
            <div className="space-y-2">
              {reminders.map((reminder) => (
                <Card key={reminder.id} className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <Checkbox
                        checked={false}
                        disabled={loadingReminders.has(reminder.id)}
                        onCheckedChange={() => handleCompleteReminder(reminder.id)}
                        className="mt-0.5"
                      />
                      <div className="space-y-1">
                        <p className="font-medium">{reminder.title}</p>
                        {reminder.description && (
                          <p className="text-sm text-muted-foreground">
                            {reminder.description}
                          </p>
                        )}
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          {reminder.company_name && (
                            <span className="flex items-center gap-1">
                              <Building2 className="h-3 w-3" />
                              {reminder.company_name}
                            </span>
                          )}
                          {reminder.contact_name && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {reminder.contact_name}
                            </span>
                          )}
                          <span>Due: {reminder.due_date}</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteReminder(reminder.id)}
                      disabled={loadingReminders.has(reminder.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Email Preview Modal */}
      <Dialog open={!!preview} onOpenChange={(open) => { if (!open) setPreview(null); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Email Preview</DialogTitle>
          </DialogHeader>
          {preview && (
            <div className="space-y-4">
              <div className="text-sm space-y-2 border rounded-md p-3 bg-muted/40">
                <div className="flex gap-2">
                  <span className="text-muted-foreground w-14 shrink-0">To:</span>
                  <span>{preview.to}</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-muted-foreground w-14 shrink-0">Subject:</span>
                  <span className="font-medium">{preview.subject}</span>
                </div>
              </div>
              <div className="border rounded-md p-4 whitespace-pre-wrap text-sm font-mono bg-background min-h-32">
                {preview.body || <span className="text-muted-foreground">(no body)</span>}
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setPreview(null)}>
                  Cancel
                </Button>
                <Button
                  onClick={() => handleSendEmail(preview.task.event_id)}
                  disabled={loadingEvents.has(preview.task.event_id)}
                >
                  <Send className="h-3.5 w-3.5 mr-1.5" />
                  {loadingEvents.has(preview.task.event_id) ? "Sending..." : "Send"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
