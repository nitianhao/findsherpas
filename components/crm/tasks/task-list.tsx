"use client";

import { useState } from "react";
import type { EmailTask } from "@/lib/crm/queries/tasks";
import type { Reminder } from "@/lib/crm/types";
import { Button } from "@/components/crm/ui/button";
import { Badge } from "@/components/crm/ui/badge";
import { Card } from "@/components/crm/ui/card";
import { Checkbox } from "@/components/crm/ui/checkbox";
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
} from "lucide-react";

interface TaskListProps {
  initialEmailTasks: EmailTask[];
  initialReminders: Reminder[];
}

export function TaskList({ initialEmailTasks, initialReminders }: TaskListProps) {
  const router = useRouter();
  const [emailTasks, setEmailTasks] = useState(initialEmailTasks);
  const [reminders, setReminders] = useState(initialReminders);
  const [loadingEvents, setLoadingEvents] = useState<Set<string>>(new Set());
  const [loadingReminders, setLoadingReminders] = useState<Set<string>>(new Set());

  // Group email tasks by company
  const tasksByCompany = emailTasks.reduce<Record<string, EmailTask[]>>((acc, task) => {
    const key = task.company_name || "No Company";
    if (!acc[key]) acc[key] = [];
    acc[key].push(task);
    return acc;
  }, {});

  async function handleMarkEvent(eventId: string, action: "sent" | "replied") {
    setLoadingEvents((prev) => new Set(prev).add(eventId));
    try {
      const res = await fetch(`/api/crm/events/${eventId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        setEmailTasks((prev) => prev.filter((t) => t.event_id !== eventId));
        toast.success(action === "sent" ? "Marked as sent" : "Marked as replied");
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
      const res = await fetch(`/api/crm/reminders/${reminderId}`, {
        method: "DELETE",
      });
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
                          </div>
                          <div className="text-sm text-muted-foreground">
                            <span className="font-medium">{task.sequence_name}</span>
                            {" -- "}
                            Step {task.step_order}
                          </div>
                          {task.subject_template && (
                            <p className="text-sm truncate">
                              Subject: {task.subject_template}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Button
                            size="sm"
                            onClick={() => handleMarkEvent(task.event_id, "sent")}
                            disabled={loadingEvents.has(task.event_id)}
                          >
                            <Send className="h-3.5 w-3.5 mr-1.5" />
                            Mark Sent
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMarkEvent(task.event_id, "replied")}
                            disabled={loadingEvents.has(task.event_id)}
                          >
                            <Reply className="h-3.5 w-3.5 mr-1.5" />
                            Mark Replied
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
  );
}
