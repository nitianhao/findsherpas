import type { Metadata } from "next";
import Link from "next/link";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Examples",
  description:
    "Common on-site search problems we diagnose in audits. Real patterns, no fabricated case studies.",
};

const examples = [
  {
    title: "High-intent queries return irrelevant results",
    context:
      "A mid-sized e-commerce team with strong traffic and a well-known brand. Users frequently search for specific product names or categories, but results show loosely related items or out-of-stock products first.",
    problem:
      "The ranking configuration treats all fields equally — product title, description, and metadata all have the same weight. Synonyms are not maintained. The result: intent-rich queries like brand names or specific product types get diluted by partial matches.",
    whatWeDidLabel: "What the audit covers",
    whatWeDid: [
      "Audit top 50 revenue queries against actual result sets",
      "Map weighting rules and identify where ranking diverges from intent",
      "Review synonym coverage and query normalization",
      "Recommend reweighting strategy with testable hypotheses",
    ],
    outcome:
      "The team gets a prioritized list of ranking fixes tied to specific queries, with before/after examples and a measurement plan to track search CVR improvement.",
    metric: "Metric to track: search conversion rate on top queries",
  },
  {
    title: "Zero-result searches are high but nobody owns them",
    context:
      "A large catalog retailer where 8–12% of searches return zero results. The search team knows this is a problem but lacks a clear breakdown of why queries fail or who should fix what.",
    problem:
      "Zero-result queries fall into multiple categories: misspellings the search engine doesn't handle, long-tail queries that need synonym mapping, and queries for products that are genuinely out of stock. Without categorization, the number feels overwhelming and nobody takes ownership.",
    whatWeDidLabel: "What the audit covers",
    whatWeDid: [
      "Categorize zero-result queries: spelling, synonyms, gaps, out-of-stock",
      "Identify which categories are solvable with configuration vs. catalog changes",
      "Audit zero-results page UX: fallback paths, suggestions, recovery experience",
      "Build a prioritized fix list by query volume and revenue potential",
    ],
    outcome:
      "The team gets a clear taxonomy of failure modes with specific fix recommendations for each category, turning an abstract metric into actionable work items.",
    metric: "Metric to track: zero-result rate segmented by failure type",
  },
  {
    title: "Search looks fine but nobody can prove it drives revenue",
    context:
      "A product team that recently invested in a new search platform. Adoption is up, but leadership asks 'what's the ROI?' and the team can't answer confidently. Search analytics are limited to basic usage metrics.",
    problem:
      "The team tracks search volume and click-through rate but has no visibility into search-to-purchase conversion, assisted revenue, or which query improvements actually moved the needle. Without this, search improvements compete poorly for engineering time.",
    whatWeDidLabel: "What the audit covers",
    whatWeDid: [
      "Audit current analytics instrumentation: events, funnels, attribution",
      "Identify gaps between what's tracked and what's needed to prove search ROI",
      "Design a measurement framework: search CVR, assisted revenue, no-click rate",
      "Recommend dashboard structure and KPI definitions for recurring reporting",
    ],
    outcome:
      "The team gets an analytics specification they can hand to engineering, plus a KPI framework that makes search impact visible to leadership.",
    metric: "Metric to track: search-assisted revenue as % of total revenue",
  },
  {
    title: "Filters and sorting create friction instead of clarity",
    context:
      "A fashion or home goods retailer with a deep and varied catalog. Users rely heavily on filters and sorting to narrow results, but the experience feels clunky — too many options, unclear labels, inconsistent behavior across categories.",
    problem:
      "Filters were built from product data (attributes, categories) rather than shopping intent. Users see 15+ filter options but the most useful ones aren't prominent. Sort-by options don't match how people actually shop (e.g., no 'best match' or 'trending' option). Mobile filter UX requires too many taps.",
    whatWeDidLabel: "What the audit covers",
    whatWeDid: [
      "Audit filter taxonomy against actual query and browsing patterns",
      "Review sort-by options and their ranking logic",
      "Assess mobile filter UX: taps to filter, visibility, back-navigation",
      "Recommend filter simplification and intent-based reorganization",
    ],
    outcome:
      "The team gets a filter restructuring plan that reduces cognitive load, surfaces the most useful refinements first, and improves mobile usability — all testable via A/B experiments.",
    metric: "Metric to track: filter usage rate and post-filter conversion",
  },
];

export default function ExamplesPage() {
  return (
    <div className="py-10">
      {/* Header */}
      <div className="max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Engagement examples
        </h1>
        <p className="mt-3 text-muted-foreground sm:text-lg">
          These are common patterns we encounter in on-site search audits. They
          are not fabricated case studies — no client names, no made-up
          performance numbers. Each one represents a real, recurring problem
          category.
        </p>
      </div>

      {/* Examples */}
      <div className="mt-12 space-y-12">
        {examples.map((ex, i) => (
          <section
            key={ex.title}
            className="border-t border-border/50 pt-10 first:border-t-0 first:pt-0"
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-border/50 text-[11px] font-medium text-muted-foreground">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h2 className="text-lg font-semibold tracking-tight sm:text-xl">
                {ex.title}
              </h2>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              {/* Left: Context + Problem */}
              <div className="space-y-5">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    Context
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {ex.context}
                  </p>
                </div>
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    Problem
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {ex.problem}
                  </p>
                </div>
              </div>

              {/* Right: What we did + Outcome */}
              <div className="space-y-5">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    {ex.whatWeDidLabel}
                  </h3>
                  <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
                    {ex.whatWeDid.map((item) => (
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
                </div>
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    Outcome
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {ex.outcome}
                  </p>
                  <p className="mt-2 text-xs font-medium text-primary">
                    {ex.metric}
                  </p>
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>

      {/* CTA */}
      <section className="mt-14 border-t border-border/50 pt-10">
        <h2 className="text-xl font-semibold tracking-tight">
          See yourself in one of these patterns?
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Book a call and I&apos;ll tell you which audit scope makes sense for
          your situation. No pitch, no pressure.
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
