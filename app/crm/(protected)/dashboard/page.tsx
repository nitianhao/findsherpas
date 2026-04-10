import Link from 'next/link';
import { getDashboardData } from '@/lib/crm/queries/dashboard';
import { StatsCards } from '@/components/crm/dashboard/stats-cards';
import { PipelineChart } from '@/components/crm/dashboard/pipeline-chart';
import { RecentActivity } from '@/components/crm/dashboard/recent-activity';
import { buttonVariants } from '@/components/crm/ui/button';
import { CalendarCheck } from 'lucide-react';

export default async function DashboardPage() {
  const data = await getDashboardData();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-1 text-muted-foreground">Overview of your outreach pipeline.</p>
      </div>

      <StatsCards data={data} />

      {data.tasks_due_today > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-yellow-300 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-950">
          <CalendarCheck className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
          <p className="flex-1 text-sm">
            You have <strong>{data.tasks_due_today}</strong> task{data.tasks_due_today !== 1 ? 's' : ''} due today
            {data.reminders_due_today > 0 && (
              <> and <strong>{data.reminders_due_today}</strong> reminder{data.reminders_due_today !== 1 ? 's' : ''}</>
            )}
            .
          </p>
          <Link href="/crm/tasks" className={buttonVariants({ size: 'sm', variant: 'outline' })}>
            View Tasks
          </Link>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <PipelineChart companyByStatus={data.company_by_status} />
        <RecentActivity activities={data.recent_activity} />
      </div>
    </div>
  );
}
