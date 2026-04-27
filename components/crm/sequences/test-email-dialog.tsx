"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/crm/ui/dialog";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { ScrollArea } from "@/components/crm/ui/scroll-area";
import { toast } from "sonner";
import { FlaskConical, Loader2 } from "lucide-react";
import type { SequenceStep } from "@/lib/crm/types";

interface TestEmailDialogProps {
  sequenceId: string;
  steps: SequenceStep[];
}

function extractVars(step: SequenceStep): string[] {
  const combined = `${step.subject_template ?? ""} ${step.body_template ?? ""}`;
  const matches = combined.matchAll(/\{\{(\w+)\}\}/g);
  const seen = new Set<string>();
  const result: string[] = [];
  for (const match of matches) {
    if (!seen.has(match[1])) {
      seen.add(match[1]);
      result.push(match[1]);
    }
  }
  return result;
}

export function TestEmailDialog({ sequenceId, steps }: TestEmailDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedStepId, setSelectedStepId] = useState(steps[0]?.id ?? "");
  const [toEmail, setToEmail] = useState("michal@findsherpas.com");
  const [vars, setVars] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const selectedStep = useMemo(
    () => steps.find((s) => s.id === selectedStepId) ?? steps[0],
    [steps, selectedStepId]
  );

  const varNames = useMemo(
    () => (selectedStep ? extractVars(selectedStep) : []),
    [selectedStep]
  );

  function handleStepChange(stepId: string) {
    setSelectedStepId(stepId);
    setVars({});
  }

  function setVar(key: string, value: string) {
    setVars((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSend() {
    if (!toEmail) {
      toast.error("Enter a recipient email address");
      return;
    }
    if (!selectedStep) {
      toast.error("Select a step");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`/api/crm/sequences/${sequenceId}/test-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          step_id: selectedStep.id,
          to_email: toEmail,
          vars,
        }),
      });

      if (res.ok) {
        toast.success(`Test email sent to ${toEmail}`);
        setOpen(false);
      } else {
        const data = await res.json();
        toast.error(data.error ?? "Failed to send test email");
      }
    } catch {
      toast.error("Failed to send test email");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="inline-flex shrink-0 items-center justify-center rounded-lg border border-input bg-background px-2.5 h-8 text-sm font-medium gap-1.5 hover:bg-muted">
        <FlaskConical className="h-4 w-4" />
        Send Test
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Send Test Email</DialogTitle>
          <DialogDescription>
            Fill in the variables for the selected step and send a test email to verify the output.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="test-step">Step</Label>
            <select
              id="test-step"
              value={selectedStepId}
              onChange={(e) => handleStepChange(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm"
            >
              {steps.map((step) => (
                <option key={step.id} value={step.id}>
                  Step {step.step_order + 1}
                  {step.subject_template ? ` — ${step.subject_template.slice(0, 50)}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="test-to">Send to</Label>
            <Input
              id="test-to"
              type="email"
              value={toEmail}
              onChange={(e) => setToEmail(e.target.value)}
              placeholder="your@email.com"
            />
          </div>

          {varNames.length > 0 && (
            <div className="space-y-1.5">
              <Label>Variables</Label>
              <ScrollArea className="max-h-64 rounded-md border p-3">
                <div className="space-y-3">
                  {varNames.map((name) => (
                    <div key={name} className="space-y-1">
                      <label className="text-xs font-mono text-muted-foreground">
                        {`{{${name}}}`}
                      </label>
                      <Input
                        value={vars[name] ?? ""}
                        onChange={(e) => setVar(name, e.target.value)}
                        placeholder={name}
                        className="h-8 text-sm"
                      />
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {varNames.length === 0 && selectedStep && (
            <p className="text-sm text-muted-foreground">
              This step has no template variables.
            </p>
          )}
        </div>

        <DialogFooter>
          <Button onClick={handleSend} disabled={submitting}>
            {submitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              "Send Test Email"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
