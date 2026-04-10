import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import type { ExperimentVariant } from "@/lib/crm/types";

interface ExperimentStatsProps {
  variants: ExperimentVariant[];
}

function VariantCard({ variant }: { variant: ExperimentVariant }) {
  const replyRate = variant.sent > 0 ? Math.round((variant.replied / variant.sent) * 100) : 0;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          Variant {variant.label} — {variant.sequence_name}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Enrolled</span>
          <span className="font-medium">{variant.enrolled}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Sent</span>
          <span className="font-medium">{variant.sent}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Replied</span>
          <span className="font-medium">{variant.replied}</span>
        </div>
        <div className="flex justify-between border-t pt-2">
          <span className="text-muted-foreground">Reply rate</span>
          <span className="font-semibold">{replyRate}%</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function ExperimentStats({ variants }: ExperimentStatsProps) {
  const sorted = [...variants].sort((a, b) => a.label.localeCompare(b.label));
  return (
    <div className="grid grid-cols-2 gap-4">
      {sorted.map((v) => (
        <VariantCard key={v.id} variant={v} />
      ))}
    </div>
  );
}
