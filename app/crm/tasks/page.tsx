import { getTodaysEmailTasks } from "@/lib/crm/queries/tasks";
import { getTodaysReminders } from "@/lib/crm/queries/reminders";
import { TaskList } from "@/components/crm/tasks/task-list";
import { ReminderForm } from "@/components/crm/tasks/reminder-form";
import { CalendarCheck, Mail, Clock } from "lucide-react";

export default async function TasksPage() {
  const emailTasks = await getTodaysEmailTasks();
  const reminders = await getTodaysReminders();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <CalendarCheck className="h-6 w-6" />
          Today&apos;s Tasks
        </h1>
        <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Mail className="h-4 w-4" />
            {emailTasks.length} {emailTasks.length === 1 ? "email" : "emails"} to send
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-4 w-4" />
            {reminders.length} {reminders.length === 1 ? "reminder" : "reminders"} due
          </span>
        </div>
      </div>

      <ReminderForm />

      <TaskList initialEmailTasks={emailTasks} initialReminders={reminders} />
    </div>
  );
}
