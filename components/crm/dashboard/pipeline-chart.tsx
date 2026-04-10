'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/crm/ui/card';

interface PipelineChartProps {
  companyByStatus: Array<{ status: string; count: number }>;
}

function formatStatus(status: string): string {
  return status
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function PipelineChart({ companyByStatus }: PipelineChartProps) {
  const data = companyByStatus.map((item) => ({
    ...item,
    label: formatStatus(item.status),
  }));

  return (
    <div className="rounded-xl border border-border/50 bg-card p-5">
      <h3 className="text-sm font-semibold mb-4">Pipeline by Status</h3>
      <div>
        {data.length === 0 ? (
          <p className="text-sm text-muted-foreground">No companies yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 13 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#14b8a6" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
