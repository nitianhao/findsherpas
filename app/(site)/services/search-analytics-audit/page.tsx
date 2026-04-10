import type { Metadata } from "next";
import Link from "next/link";
import { AuditSelector } from "@/components/site/AuditSelector";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Search Analytics Audit",
  description:
    "Make search measurable. Event design, funnels, dashboards, and a KPI framework your team can iterate on.",
};

export default function SearchAnalyticsAuditPage() {
  return (
    <div className="py-10">
      <p className="text-sm font-medium text-muted-foreground">Services</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
        End-to-End Search Audit
      </h1>
      <p className="mt-3 max-w-2xl text-muted-foreground sm:text-lg">
        A full search diagnostic for complex catalogs or marketplaces. Combines
        UX, relevance, and analytics into one comprehensive baseline your team
        can align around.
      </p>

      <div className="mt-8 flex items-center gap-4">
        <span className="text-2xl font-semibold">Custom</span>
        <span className="text-sm text-muted-foreground">
          Typically €4,000–8,000 &middot; 2–4 weeks
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
            "Everything in the Relevance Audit (UX + relevance + analytics)",
            "Custom query set design and offline evaluation approach",
            "Advanced failure mode analysis: coverage gaps, long-tail, merch rules",
            "Analytics instrumentation audit and measurement framework",
            "Dashboard structure and KPI definitions for recurring reporting",
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
            "Executive summary for leadership alignment",
            "Complete diagnostic across UX, relevance, and analytics",
            "Stakeholder workshop (up to 2 hours)",
            "Implementation handover document with acceptance criteria",
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
          This audit does not include implementation, ongoing consulting, or
          search platform selection. It is a comprehensive diagnosis and roadmap
          — your team or vendor handles the build.
        </p>
      </section>

      <AuditSelector currentAudit="analytics" className="mt-20 border-t border-border/50 pt-16" />
    </div>
  );
}
