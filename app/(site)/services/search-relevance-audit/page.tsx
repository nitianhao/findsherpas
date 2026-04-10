import type { Metadata } from "next";
import Link from "next/link";
import { AuditSelector } from "@/components/site/AuditSelector";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Search Relevance Audit",
  description:
    "Deep analysis of ranking quality, query handling, and relevance configuration. Improve how search results match user intent.",
};

export default function SearchRelevanceAuditPage() {
  return (
    <div className="py-10">
      <p className="text-sm font-medium text-muted-foreground">Services</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
        Search Relevance Audit
      </h1>
      <p className="mt-3 max-w-2xl text-muted-foreground sm:text-lg">
        Identify why ranking misses intent and where relevance improvements
        create measurable ROI. Covers everything in the UX audit plus deep
        analysis of ranking configuration, query handling, and analytics.
      </p>

      <div className="mt-8 flex items-center gap-4">
        <span className="text-2xl font-semibold">€2,490</span>
        <span className="text-sm text-muted-foreground">
          10–14 business days
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
            "Everything in the Search UX Audit",
            "Relevance audit: synonyms, weighting rules, facets, boosting logic",
            "Query set analysis: top queries, long-tail, zero-result queries",
            "Search analytics review: events, funnels, key drop-off points",
            "Measurement plan with KPI definitions",
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
            "Prioritized issue list across UX and relevance",
            "Ranking fix recommendations tied to specific queries",
            "Synonym and query normalization gaps",
            "Testing and iteration plan with success metrics",
            "2× 60-minute working sessions",
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
          This audit is a diagnosis, not implementation. It does not include
          ongoing tuning, maintenance, or search platform migration. Your team
          or search vendor handles the build using the deliverable as a
          blueprint.
        </p>
      </section>

      <AuditSelector currentAudit="relevance" className="mt-20 border-t border-border/50 pt-16" />
    </div>
  );
}
