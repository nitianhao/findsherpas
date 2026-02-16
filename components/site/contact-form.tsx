"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type InterestedIn = "ux" | "relevance" | "analytics" | "other";

export function ContactForm() {
  const [status, setStatus] = useState<
    | { state: "idle" }
    | { state: "submitting" }
    | { state: "success" }
    | { state: "error"; message: string }
  >({ state: "idle" });

  const canSubmit = useMemo(() => status.state !== "submitting", [status.state]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus({ state: "submitting" });

    const form = e.currentTarget;
    const formData = new FormData(form);

    const payload = {
      name: String(formData.get("name") ?? "").trim(),
      email: String(formData.get("email") ?? "").trim(),
      company: String(formData.get("company") ?? "").trim(),
      interestedIn: (String(formData.get("interestedIn") ?? "other") ||
        "other") as InterestedIn,
      message: String(formData.get("message") ?? "").trim(),
      website: String(formData.get("website") ?? "").trim(), // honeypot
    };

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = (await res.json()) as { ok?: boolean; error?: string };
      if (!res.ok) {
        setStatus({
          state: "error",
          message: data.error ?? "Something went wrong. Please try again.",
        });
        return;
      }

      setStatus({ state: "success" });
      form.reset();
    } catch {
      setStatus({
        state: "error",
        message: "Network error. Please try again.",
      });
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5 sm:space-y-5">
      <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" name="name" autoComplete="name" required className="h-11 sm:h-9" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            className="h-11 sm:h-9"
          />
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 sm:gap-4">
        <div className="space-y-2">
          <Label htmlFor="company">Company (optional)</Label>
          <Input id="company" name="company" autoComplete="organization" className="h-11 sm:h-9" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="interestedIn">Interested in</Label>
          <select
            id="interestedIn"
            name="interestedIn"
            className="h-11 w-full rounded-md border bg-background px-3 text-sm shadow-xs sm:h-9"
            defaultValue="other"
          >
            <option value="ux">UX audit & optimization</option>
            <option value="relevance">Relevance audit & optimization</option>
            <option value="analytics">Search analytics audit & design</option>
            <option value="other">Other / not sure yet</option>
          </select>
        </div>
      </div>

      {/* Honeypot: hidden from humans */}
      <div className="hidden">
        <Label htmlFor="website">Website</Label>
        <Input id="website" name="website" tabIndex={-1} autoComplete="off" />
      </div>

      <div className="space-y-2">
        <Label htmlFor="message">Message</Label>
        <Textarea
          id="message"
          name="message"
          required
          rows={5}
          className="min-h-[120px] sm:min-h-0"
          placeholder="What are you trying to improve in on-site search? Any constraints (timeline, platform, analytics)?"
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Button type="submit" disabled={!canSubmit} size="lg" className="w-full sm:w-auto">
          {status.state === "submitting" ? "Sending…" : "Send message"}
        </Button>

        {status.state === "success" ? (
          <div className="text-sm text-muted-foreground">
            Message sent. I&apos;ll get back to you shortly.
          </div>
        ) : null}
        {status.state === "error" ? (
          <div className="text-sm text-destructive">{status.message}</div>
        ) : null}
      </div>

      <div className="text-xs text-muted-foreground">
        Prefer email? Write to{" "}
        <a className="underline" href="mailto:michal.pekarcik@gmail.com">
          michal.pekarcik@gmail.com
        </a>
        .
      </div>
    </form>
  );
}
