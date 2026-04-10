import { Building2, Users, Send, Percent, Calendar, CalendarCheck } from 'lucide-react';
import type { DashboardData } from '@/lib/crm/queries/dashboard';

interface StatsCardsProps {
  data: DashboardData;
}

const stats: Array<{
  key: keyof DashboardData;
  label: string;
  icon: typeof Building2;
  suffix?: string;
}> = [
  { key: 'total_companies', label: 'Total Companies', icon: Building2 },
  { key: 'total_contacts', label: 'Total Contacts', icon: Users },
  { key: 'emails_sent_this_month', label: 'Emails This Month', icon: Send },
  { key: 'response_rate', label: 'Response Rate', icon: Percent, suffix: '%' },
  { key: 'meetings_booked', label: 'Meetings Booked', icon: Calendar },
  { key: 'tasks_due_today', label: 'Tasks Due Today', icon: CalendarCheck },
];

export function StatsCards({ data }: StatsCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map(({ key, label, icon: Icon, suffix }) => (
        <div
          key={key}
          className="rounded-xl border border-border/50 bg-card p-5 transition-all duration-200 hover:shadow-sm"
        >
          <div className="flex items-center justify-between">
            <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
              <Icon className="h-4 w-4 text-primary" />
            </div>
          </div>
          <p className="mt-3 text-2xl font-semibold tracking-tight">
            {data[key as keyof DashboardData] as number}
            {suffix ?? ''}
          </p>
        </div>
      ))}
    </div>
  );
}
