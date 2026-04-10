import { adminDb } from '@/lib/crm/instant-db';
import { format } from 'date-fns';

export interface DashboardData {
  total_companies: number;
  total_contacts: number;
  emails_sent: number;
  emails_sent_this_month: number;
  response_rate: number;
  meetings_booked: number;
  tasks_due_today: number;
  reminders_due_today: number;
  company_by_status: Array<{ status: string; count: number }>;
  platform_distribution: Array<{ platform: string; count: number }>;
  recent_activity: Array<{ type: string; description: string; date: string }>;
}

export async function getDashboardData(): Promise<DashboardData> {
  const today = format(new Date(), 'yyyy-MM-dd');
  const monthStart = format(new Date(new Date().getFullYear(), new Date().getMonth(), 1), 'yyyy-MM-dd');

  const [companiesData, contactsData, eventsData, remindersData] = await Promise.all([
    adminDb.query({ companies: { $: { fields: ['id', 'status', 'platform'] } } }),
    adminDb.query({ contacts: { $: { fields: ['id'] } } }),
    adminDb.query({
      events: {
        enrollment: { contact: { company: {} }, sequence: {} },
        step: {},
      },
    }),
    adminDb.query({ reminders: { $: { fields: ['id', 'due_date', 'is_completed'] } } }),
  ]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const companies = companiesData.companies as any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const events = eventsData.events as any[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const reminders = remindersData.reminders as any[];

  const totalCompanies = companies.length;
  const totalContacts = (contactsData.contacts as unknown[]).length;

  const sentEvents = events.filter(e => e.status === 'sent' || e.status === 'replied');
  const emailsSent = sentEvents.length;
  const emailsSentThisMonth = sentEvents.filter(e => e.sent_at && e.sent_at >= monthStart).length;
  const repliedEvents = events.filter(e => e.status === 'replied');
  const responseRate = emailsSent > 0 ? Math.round((repliedEvents.length / emailsSent) * 100) : 0;
  const meetingsBooked = companies.filter(c => c.status === 'meeting-booked').length;

  const tasksDueToday = events.filter(e =>
    e.status === 'pending' &&
    e.enrollment?.status === 'active' &&
    e.scheduled_date <= today
  ).length;

  const remindersDueToday = reminders.filter(
    (r: { is_completed: number; due_date: string }) => r.is_completed === 0 && r.due_date <= today
  ).length;

  // Company by status
  const statusCounts = new Map<string, number>();
  for (const c of companies) {
    statusCounts.set(c.status, (statusCounts.get(c.status) ?? 0) + 1);
  }
  const companyByStatus = Array.from(statusCounts.entries())
    .map(([status, count]) => ({ status, count }))
    .sort((a, b) => b.count - a.count);

  // Platform distribution
  const platformCounts = new Map<string, number>();
  for (const c of companies) {
    const platform = c.platform || 'Unknown';
    platformCounts.set(platform, (platformCounts.get(platform) ?? 0) + 1);
  }
  const platformDistribution = Array.from(platformCounts.entries())
    .map(([platform, count]) => ({ platform, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  // Recent activity
  const recentActivity = sentEvents
    .filter(e => e.sent_at || e.replied_at)
    .map(e => ({
      type: e.status === 'replied' ? 'reply' : 'sent',
      description: `${e.enrollment?.contact?.name ?? 'Unknown'} (${e.enrollment?.contact?.company?.name ?? ''}) - Step ${e.step?.step_order ?? '?'}`,
      date: (e.replied_at || e.sent_at) as string,
    }))
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, 10);

  return {
    total_companies: totalCompanies,
    total_contacts: totalContacts,
    emails_sent: emailsSent,
    emails_sent_this_month: emailsSentThisMonth,
    response_rate: responseRate,
    meetings_booked: meetingsBooked,
    tasks_due_today: tasksDueToday,
    reminders_due_today: remindersDueToday,
    company_by_status: companyByStatus,
    platform_distribution: platformDistribution,
    recent_activity: recentActivity,
  };
}
