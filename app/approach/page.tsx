import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Approach",
  description:
    "How Find Sherpas runs on-site search audits: lightweight process, vendor-agnostic, experiment-driven, revenue-first.",
};

const steps = [
  {
    number: "01",
    title: "Intake call (30 min)",
    description:
      "We discuss your goals, constraints, current search stack, and known pain points. I'll tell you which audit scope makes sense and what access I'll need.",
  },
  {
    number: "02",
    title: "Audit & analysis",
    description:
      "I review your search experience, configuration, and data. The depth depends on the scope: UX-only, relevance + UX, or end-to-end. I work asynchronously and don't need your team's time during this phase.",
  },
  {
    number: "03",
    title: "Deliverable + walkthrough",
    description:
      "You receive a written report with a prioritized issue list, experiment ideas with success metrics, and a clear roadmap. We walk through it together on a call so nothing is ambiguous.",
  },
  {
    number: "04",
    title: "Your team ships",
    description:
      "The deliverable is designed to be directly actionable by your team or search vendor. No ongoing dependency on me. If you want a follow-up review after changes ship, we can scope that separately.",
  },
];

const principles = [
  {
    title: "Vendor-agnostic",
    description:
      "I work with Algolia, Elasticsearch, Luigi's Box, Doofinder, Coveo, Bloomreach, and others. The methodology applies regardless of your stack — I'm not incentivized to recommend a specific platform.",
  },
  {
    title: "Revenue-first",
    description:
      "Every recommendation connects to conversion, revenue, or measurable search quality. I don't audit for audit's sake — the goal is commercial impact your team can validate.",
  },
  {
    title: "Experiment-driven",
    description:
      "Deliverables include testable hypotheses and success metrics, not just a list of opinions. Your team can prioritize fixes based on expected impact and run controlled experiments.",
  },
  {
    title: "No implementation, no lock-in",
    description:
      "I deliver a diagnosis and a roadmap. Your team or vendor handles the build. There's no retainer, no ongoing dependency, and no reason to over-scope.",
  },
];

export default function ApproachPage() {
  return (
    <div className="py-10">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        How it works
      </h1>
      <p className="mt-3 max-w-2xl text-muted-foreground sm:text-lg">
        A lightweight, vendor-agnostic process designed to deliver clear
        findings fast and keep your team moving. No retainers, no long
        timelines, no fluff.
      </p>

      {/* Process steps */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">Process</h2>
        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          {steps.map((step) => (
            <div key={step.number} className="flex items-start gap-3">
              <span className="mt-0.5 inline-flex h-7 min-w-7 items-center justify-center rounded-full border border-border/50 text-xs font-medium text-muted-foreground">
                {step.number}
              </span>
              <div>
                <h3 className="text-sm font-semibold">{step.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Principles */}
      <section className="mt-14 border-t border-border/50 pt-10">
        <h2 className="text-xl font-semibold tracking-tight">Principles</h2>
        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          {principles.map((p) => (
            <div key={p.title}>
              <h3 className="text-sm font-semibold">{p.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">
                {p.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mt-14 border-t border-border/50 pt-10">
        <h2 className="text-xl font-semibold tracking-tight">
          Ready to start?
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Book a 20-minute call. I&apos;ll ask about your search setup, look at
          your site, and recommend the smallest audit that makes sense.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Button asChild>
            <Link href="/book-a-call">Book a call</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/pricing">See pricing &amp; scope</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
