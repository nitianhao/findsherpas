import type { ActivityItem } from "@/lib/crm/types";
import { Mail, MousePointer, MailOpen, Reply, AlertCircle, MessageSquare, Bell } from "lucide-react";

const ICON_MAP: Record<ActivityItem["type"], typeof Mail> = {
  email_sent: Mail,
  email_opened: MailOpen,
  email_clicked: MousePointer,
  email_replied: Reply,
  email_bounced: AlertCircle,
  email_skipped: Mail,
  comment: MessageSquare,
  reminder: Bell,
};

const COLOR_MAP: Record<ActivityItem["type"], string> = {
  email_sent: "text-blue-500",
  email_opened: "text-green-500",
  email_clicked: "text-purple-500",
  email_replied: "text-emerald-500",
  email_bounced: "text-destructive",
  email_skipped: "text-muted-foreground",
  comment: "text-muted-foreground",
  reminder: "text-amber-500",
};

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return isNaN(d.getTime())
    ? dateStr
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

interface ContactActivityProps {
  items: ActivityItem[];
}

export function ContactActivity({ items }: ContactActivityProps) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-4">No activity yet.</p>;
  }

  return (
    <div className="space-y-1">
      {items.map((item, i) => {
        const Icon = ICON_MAP[item.type] ?? Mail;
        const color = COLOR_MAP[item.type] ?? "text-muted-foreground";
        return (
          <div key={i} className="flex items-start gap-3 py-2 border-b last:border-0">
            <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${color}`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm">{item.description}</p>
            </div>
            <span className="text-xs text-muted-foreground shrink-0">{formatDate(item.date)}</span>
          </div>
        );
      })}
    </div>
  );
}
