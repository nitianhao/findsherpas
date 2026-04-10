import type { StepPerformance } from "@/lib/crm/queries/sequences";
import { Badge } from "@/components/crm/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";

function RateBadge({ rate, label }: { rate: number; label: string }) {
  const variant = rate >= 30 ? "default" : rate >= 10 ? "secondary" : "outline";
  return (
    <div className="text-center">
      <Badge variant={variant} className="text-xs">{rate}%</Badge>
      <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
    </div>
  );
}

interface SequencePerformanceProps {
  steps: StepPerformance[];
}

export function SequencePerformance({ steps }: SequencePerformanceProps) {
  if (steps.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-sm text-muted-foreground">No emails sent yet — stats will appear once contacts receive emails.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">Per-Step Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y">
          <div className="grid grid-cols-6 gap-4 pb-2 text-xs font-medium text-muted-foreground">
            <span className="col-span-2">Step</span>
            <span className="text-center">Sent</span>
            <span className="text-center">Open rate</span>
            <span className="text-center">Click rate</span>
            <span className="text-center">Reply rate</span>
          </div>
          {steps.map((step) => (
            <div key={step.step_order} className="grid grid-cols-6 gap-4 py-3 items-center">
              <div className="col-span-2 min-w-0">
                <p className="text-sm font-medium">Step {step.step_order}</p>
                {step.subject_template && (
                  <p className="text-xs text-muted-foreground truncate">{step.subject_template}</p>
                )}
              </div>
              <p className="text-sm text-center font-medium">{step.sent}</p>
              <RateBadge rate={step.open_rate} label={`${step.opened} opens`} />
              <RateBadge rate={step.click_rate} label={`${step.clicked} clicks`} />
              <RateBadge rate={step.reply_rate} label={`${step.replied} replies`} />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
