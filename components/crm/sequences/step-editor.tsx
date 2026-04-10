"use client";

import { useState, useCallback } from "react";
import type { SequenceStep } from "@/lib/crm/types";
import { Button } from "@/components/crm/ui/button";
import { Input } from "@/components/crm/ui/input";
import { Label } from "@/components/crm/ui/label";
import { Textarea } from "@/components/crm/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/crm/ui/card";
import { Plus, Trash2, ArrowUp, ArrowDown } from "lucide-react";
import { toast } from "sonner";

interface StepDraft {
  id?: string;
  step_order: number;
  subject_template: string;
  body_template: string;
  delay_days: number;
}

function toStepDraft(step: SequenceStep, index: number): StepDraft {
  return {
    id: step.id,
    step_order: index + 1,
    subject_template: step.subject_template || "",
    body_template: step.body_template || "",
    delay_days: step.delay_days,
  };
}

interface StepEditorProps {
  sequenceId: string;
  initialSteps: SequenceStep[];
}

export function StepEditor({ sequenceId, initialSteps }: StepEditorProps) {
  const [steps, setSteps] = useState<StepDraft[]>(
    initialSteps.map(toStepDraft)
  );
  const [saving, setSaving] = useState(false);

  const saveSteps = useCallback(
    async (updatedSteps: StepDraft[]) => {
      setSaving(true);
      try {
        const payload = updatedSteps.map((s, i) => ({
          step_order: i + 1,
          subject_template: s.subject_template || null,
          body_template: s.body_template || null,
          delay_days: s.delay_days,
        }));

        const res = await fetch(`/api/crm/sequences/${sequenceId}/steps`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ steps: payload }),
        });

        if (res.ok) {
          const saved: SequenceStep[] = await res.json();
          setSteps(saved.map(toStepDraft));
          toast.success("Steps saved");
        } else {
          const err = await res.json();
          toast.error(err.error || "Failed to save steps");
        }
      } catch {
        toast.error("Failed to save steps");
      } finally {
        setSaving(false);
      }
    },
    [sequenceId]
  );

  function addStep() {
    setSteps((prev) => [
      ...prev,
      {
        step_order: prev.length + 1,
        subject_template: "",
        body_template: "",
        delay_days: prev.length === 0 ? 0 : 3,
      },
    ]);
  }

  function removeStep(index: number) {
    setSteps((prev) => {
      const updated = prev.filter((_, i) => i !== index);
      return updated.map((s, i) => ({ ...s, step_order: i + 1 }));
    });
  }

  function moveStep(index: number, direction: "up" | "down") {
    setSteps((prev) => {
      const newIndex = direction === "up" ? index - 1 : index + 1;
      if (newIndex < 0 || newIndex >= prev.length) return prev;
      const updated = [...prev];
      [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
      return updated.map((s, i) => ({ ...s, step_order: i + 1 }));
    });
  }

  function updateField(index: number, field: keyof StepDraft, value: string | number) {
    setSteps((prev) =>
      prev.map((s, i) => (i === index ? { ...s, [field]: value } : s))
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Sequence Steps</h3>
        <div className="flex gap-2">
          <Button variant="outline" onClick={addStep}>
            <Plus className="mr-2 h-4 w-4" />
            Add Step
          </Button>
          <Button onClick={() => saveSteps(steps)} disabled={saving}>
            {saving ? "Saving..." : "Save Steps"}
          </Button>
        </div>
      </div>

      {steps.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No steps yet. Click "Add Step" to create the first email in this sequence.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {steps.map((step, index) => (
            <Card key={index}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">
                    Step {index + 1}
                  </CardTitle>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => moveStep(index, "up")}
                      disabled={index === 0}
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => moveStep(index, "down")}
                      disabled={index === steps.length - 1}
                    >
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeStep(index)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-4 gap-4">
                  <div className="col-span-3 space-y-2">
                    <Label>Subject</Label>
                    <Input
                      value={step.subject_template}
                      onChange={(e) =>
                        updateField(index, "subject_template", e.target.value)
                      }
                      placeholder="Email subject line..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Delay (days)</Label>
                    <Input
                      type="number"
                      min={0}
                      value={step.delay_days}
                      onChange={(e) =>
                        updateField(
                          index,
                          "delay_days",
                          parseInt(e.target.value) || 0
                        )
                      }
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Body</Label>
                  <Textarea
                    value={step.body_template}
                    onChange={(e) =>
                      updateField(index, "body_template", e.target.value)
                    }
                    placeholder="Email body template..."
                    rows={4}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
