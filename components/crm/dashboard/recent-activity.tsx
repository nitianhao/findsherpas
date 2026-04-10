import { Send, Reply } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/crm/ui/card';

interface RecentActivityProps {
  activities: Array<{ type: string; description: string; date: string }>;
}

export function RecentActivity({ activities }: RecentActivityProps) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-5">
      <h3 className="text-sm font-semibold mb-4">Recent Activity</h3>
      <div>
        {activities.length === 0 ? (
          <p className="text-sm text-muted-foreground">No activity yet.</p>
        ) : (
          <ul className="space-y-3">
            {activities.map((activity, i) => {
              const Icon = activity.type === 'reply' ? Reply : Send;
              const timeAgo = activity.date
                ? formatDistanceToNow(new Date(activity.date), { addSuffix: true })
                : '';

              return (
                <li key={i} className="flex items-start gap-3">
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-snug">{activity.description}</p>
                    {timeAgo && (
                      <p className="text-xs text-muted-foreground">{timeAgo}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
