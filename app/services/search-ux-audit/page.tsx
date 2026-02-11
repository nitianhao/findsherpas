import type { Metadata } from "next";
import Link from "next/link";
import { AuditSelector } from "@/components/site/AuditSelector";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Search UX Audit",
  description:
    "Identify friction in the query-to-product journey. Improve autocomplete, SERP layout, filters, and zero-results paths.",
};

export default function SearchUxAuditPage() {
  return (
    <div className="py-10">
      <p className="text-sm font-medium text-muted-foreground">Services</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
        Search UX Audit
      </h1>
      <p className="mt-3 max-w-2xl text-muted-foreground sm:text-lg">
        A focused review of how users search, filter, and discover products on
        your site. You get a prioritized list of usability issues and experiment
        ideas that lift conversion.
      </p>

      <div className="mt-8 flex items-center gap-4">
        <span className="text-2xl font-semibold">€990</span>
        <span className="text-sm text-muted-foreground">
          5–7 business days
        </span>
      </div>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Button asChild>
          <Link href="/book-a-call">Book a call</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/pricing">See all pricing</Link>
        </Button>
      </div>

      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          What the audit covers
        </h2>
        <ul className="mt-5 space-y-3 text-sm text-muted-foreground">
          {[
            "Autocomplete: query suggestions, zero-state behavior, interaction patterns",
            "SERP layout: result presentation, information hierarchy, visual clarity",
            "Filters and sorting: taxonomy, mobile usability, intent alignment",
            "Zero-results paths: fallback UX, recovery suggestions, dead-end prevention",
            "Mobile search UX: tap targets, scroll behavior, input ergonomics",
          ].map((item) => (
            <li key={item} className="flex items-start gap-2">
              <svg
                className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
                <path
                  d="M5 13l4 4L19 7"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-semibold tracking-tight">
          What you get
        </h2>
        <ul className="mt-5 space-y-3 text-sm text-muted-foreground">
          {[
            "Prioritized issue list with severity and effort estimates",
            "Quick wins your team can ship immediately",
            "Experiment ideas with success metrics",
            "60-minute walkthrough call",
            "Written report (PDF + Notion)",
          ].map((item) => (
            <li key={item} className="flex items-start gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10 border-t border-border/50 pt-8">
        <h2 className="text-xl font-semibold tracking-tight">
          Not included
        </h2>
        <p className="mt-3 text-sm text-muted-foreground">
          This audit is a diagnosis, not implementation. Your team or search
          vendor handles the build. The deliverable is designed to be directly
          actionable without ongoing involvement.
        </p>
      </section>

      <AuditSelector currentAudit="ux" className="mt-20 border-t border-border/50 pt-16" />
    </div>
  );
}
