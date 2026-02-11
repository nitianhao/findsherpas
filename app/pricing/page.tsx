import type { Metadata } from "next";
import Link from "next/link";
import { AuditSelector } from "@/components/site/AuditSelector";

import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Pricing & Scope",
  description:
    "Transparent pricing for on-site search audits. UX, relevance, and analytics — fixed scope, clear deliverables, money-back guarantee.",
};

const AUDIT_IDS: Record<string, string> = {
  "Search UX Audit": "ux",
  "Search Relevance Audit": "relevance",
  "End-to-End Search Audit": "analytics",
};

const audits = [
  {
    name: "Search UX Audit",
    price: "€990",
    timeline: "5–7 business days",
    href: "/services/search-ux-audit",
    description:
      "A focused review of the query-to-product journey. You get a prioritized list of usability issues and experiment ideas that lift conversion.",
    includes: [
      "Audit of autocomplete, SERP layout, filters, sorting, zero-results",
      "Prioritized issue list with severity and effort estimates",
      "Quick wins and recommended A/B experiments",
      "60-minute walkthrough call",
      "Written report (PDF + Notion)",
    ],
    excludes: [
      "Implementation or code changes",
      "Relevance tuning or ranking configuration",
      "Analytics instrumentation",
    ],
    goodFit:
      "Teams with a live search experience that feels clunky or leaky. You have traffic but suspect the search UI is costing you conversions.",
    notAFit:
      "Teams that need someone to implement changes in code. This audit tells you what to fix and why — your team or vendor handles the build.",
  },
  {
    name: "Search Relevance Audit",
    price: "€2,490",
    timeline: "10–14 business days",
    href: "/services/search-relevance-audit",
    recommended: true,
    description:
      "Deep analysis of ranking quality, query handling, and relevance configuration. Covers everything in the UX audit plus relevance and analytics.",
    includes: [
      "Everything in the Search UX Audit",
      "Relevance audit: synonyms, weighting rules, facets, boosting logic",
      "Query set analysis (top queries, long-tail, zero-result queries)",
      "Search analytics review: events, funnels, key drop-off points",
      "Measurement plan with KPI definitions",
      "2× 60-minute working sessions",
      "Written report (PDF + Notion)",
    ],
    excludes: [
      "Implementation or code changes",
      "Ongoing tuning or maintenance",
      "Search platform migration",
    ],
    goodFit:
      "Teams where products exist in the catalog but search results don't match intent. You want to understand why ranking is off and have a plan to fix it.",
    notAFit:
      "Teams looking for a vendor to take over search operations. This is a diagnostic with a clear handoff — not a managed service.",
  },
  {
    name: "End-to-End Search Audit",
    price: "Custom (typically €4,000–8,000)",
    timeline: "2–4 weeks",
    href: "/services/search-analytics-audit",
    description:
      "A full search diagnostic for complex catalogs or marketplaces. Combines UX, relevance, and analytics into one comprehensive baseline.",
    includes: [
      "Everything in the Relevance Audit",
      "Custom query set design and offline evaluation approach",
      "Advanced failure mode analysis (coverage gaps, long-tail, merchandising rules)",
      "Executive summary for leadership alignment",
      "Stakeholder workshop (up to 2 hours)",
      "Implementation handover document with acceptance criteria",
    ],
    excludes: [
      "Implementation or code changes",
      "Ongoing consulting or retainer",
      "Search platform selection or procurement",
    ],
    goodFit:
      "Teams managing a complex catalog (10k+ SKUs, multilingual, marketplace) who want a full reset on how search works and how it's measured.",
    notAFit:
      "Teams with a simple catalog and a clear single issue. A focused audit is more efficient — don't overspend on scope.",
  },
];

export default function PricingPage() {
  return (
    <div className="py-20 md:py-32 max-w-5xl mx-auto">
      {/* Header */}
      <div className="max-w-3xl mb-24">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl mb-6 text-foreground">
          Pricing &amp; Scope
        </h1>
        <p className="text-xl text-muted-foreground leading-relaxed max-w-2xl">
          Fixed-scope audits with transparent pricing. No retainers, no hourly
          billing, no surprises. You get a clear diagnosis, a prioritized
          roadmap, and experiment ideas your team can execute.
        </p>
      </div>

      {/* Audit Selector */}
      <div className="mb-32">
        <AuditSelector />
      </div>

      {/* Principles */}
      <div className="mb-32">
        <div className="grid gap-12 sm:grid-cols-3">
          <div className="flex flex-col gap-4">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
              <svg
                className="h-6 w-6 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
                <path
                  d="M4 12h16M12 4v16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold mb-2">Vendor-agnostic</h3>
              <p className="text-muted-foreground leading-relaxed">
                Works with Algolia, Elasticsearch, Luigi&apos;s Box, Doofinder,
                or any other search stack.
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
              <svg
                className="h-6 w-6 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
                <path
                  d="M4 19h16M7 15v4M12 10v9M17 7v12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold mb-2">Revenue-first</h3>
              <p className="text-muted-foreground leading-relaxed">
                Every recommendation connects to conversion, revenue, or
                measurable search quality.
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
              <svg
                className="h-6 w-6 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
                <path
                  d="M12 3l7 3v6c0 4.5-2.7 7.4-7 9-4.3-1.6-7-4.5-7-9V6l7-3z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-bold mb-2">Experiment-driven</h3>
              <p className="text-muted-foreground leading-relaxed">
                Deliverables include testable hypotheses and success metrics, not
                just a list of opinions.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Audit tiers */}
      <div className="space-y-24">
        {audits.map((audit) => (
          <section
            key={audit.name}
            id={AUDIT_IDS[audit.name]}
            className="scroll-mt-32"
          >
            <div className={`rounded-3xl p-8 md:p-12 transition-all ${audit.recommended
                ? "bg-primary/[0.03] ring-1 ring-primary/10"
                : "bg-background border border-border/60"
              }`}>
              <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between mb-12">
                <div className="max-w-2xl">
                  <div className="flex items-center gap-4 mb-4">
                    <h2 className="text-3xl font-bold tracking-tight">
                      {audit.name}
                    </h2>
                    {audit.recommended && (
                      <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary uppercase tracking-wide">
                        Most Popular
                      </span>
                    )}
                  </div>
                  <p className="text-xl text-muted-foreground leading-relaxed">
                    {audit.description}
                  </p>
                </div>
                <div className="shrink-0 text-left md:text-right">
                  <div className="text-3xl font-bold mb-1">{audit.price}</div>
                  <div className="text-sm font-medium text-muted-foreground">
                    {audit.timeline}
                  </div>
                </div>
              </div>

              <div className="grid gap-12 lg:grid-cols-2">
                {/* What's included */}
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-6">What&apos;s included</h3>
                  <ul className="space-y-4">
                    {audit.includes.map((item) => (
                      <li key={item} className="flex items-start gap-3">
                        <svg
                          className="mt-1 h-5 w-5 shrink-0 text-primary"
                          viewBox="0 0 24 24"
                          fill="none"
                          aria-hidden
                        >
                          <path
                            d="M5 13l4 4L19 7"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                        <span className="text-foreground/90">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* What's NOT included */}
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-6">
                    What&apos;s not included
                  </h3>
                  <ul className="space-y-4">
                    {audit.excludes.map((item) => (
                      <li key={item} className="flex items-start gap-3">
                        <svg
                          className="mt-1 h-5 w-5 shrink-0 text-muted-foreground/50"
                          viewBox="0 0 24 24"
                          fill="none"
                          aria-hidden
                        >
                          <path
                            d="M18 6L6 18M6 6l12 12"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                          />
                        </svg>
                        <span className="text-muted-foreground">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Good fit / Not a fit */}
              <div className="mt-12 pt-12 border-t border-border/50 grid gap-10 md:grid-cols-2">
                <div>
                  <h3 className="text-lg font-bold text-foreground mb-3">
                    Good fit
                  </h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {audit.goodFit}
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-foreground mb-3">Not a fit</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {audit.notAFit}
                  </p>
                </div>
              </div>

              <div className="mt-12 flex flex-col gap-4 sm:flex-row">
                <Button asChild size="lg" className="rounded-full px-8">
                  <Link href="/book-a-call">Book a call</Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="rounded-full px-8">
                  <Link href={audit.href}>View full details</Link>
                </Button>
              </div>
            </div>
          </section>
        ))}
      </div>

      {/* Money-back guarantee */}
      <section className="mt-32 rounded-3xl bg-muted/30 p-10 md:p-16 text-center md:text-left">
        <div className="flex flex-col md:flex-row items-center md:items-start gap-8">
          <div className="h-16 w-16 rounded-full bg-background shadow-sm flex items-center justify-center shrink-0">
            <svg
              className="h-8 w-8 text-primary"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden
            >
              <path
                d="M12 3l7 3v6c0 4.5-2.7 7.4-7 9-4.3-1.6-7-4.5-7-9V6l7-3z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-2xl font-bold mb-4">Money-back guarantee</h2>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-3xl">
              If the audit doesn&apos;t surface at least 3 actionable
              improvements your team agrees are worth testing, you get a full
              refund. No questions, no process. I&apos;d rather refund than
              deliver something that doesn&apos;t help.
            </p>
          </div>
        </div>
      </section>

      {/* FAQ-style notes */}
      <section className="mt-32 mb-20">
        <h2 className="text-3xl font-bold tracking-tight mb-12">
          Common questions
        </h2>
        <div className="grid gap-12 md:grid-cols-2">
          <div>
            <h3 className="text-lg font-bold mb-3">How fast can we start?</h3>
            <p className="text-muted-foreground leading-relaxed">
              Usually within 1&ndash;2 weeks. If you have a deadline, mention it
              in the call and I&apos;ll tell you what&apos;s realistic.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-3">What access do you need?</h3>
            <p className="text-muted-foreground leading-relaxed">
              Read-only access to search analytics, search configuration exports
              (or admin access), and a 30-minute intake call. I can start with
              limited access and expand as needed.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-3">How does payment work?</h3>
            <p className="text-muted-foreground leading-relaxed">
              One-time payment via Stripe or invoice. 50% upfront, 50% on
              delivery. Enterprise scoping is free.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-3">
              Do you implement the changes?
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              No. The audit is a diagnosis and a roadmap. Your team or search
              vendor handles implementation. The deliverable is designed to be
              directly actionable without my involvement.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-3">
              What if I&apos;m not sure which audit I need?
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              Book a call. I&apos;ll ask a few questions and recommend the
              smallest scope that gets you to a clear next step. I&apos;d rather
              you buy less than overpay.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-bold mb-3">
              What search platforms do you work with?
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              Algolia, Elasticsearch, Luigi&apos;s Box, Doofinder, Coveo,
              Bloomreach, and others. The audit is vendor-agnostic &mdash; the
              methodology works regardless of your stack.
            </p>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mt-24 border-t border-border/50 pt-24 text-center">
        <h2 className="text-3xl font-bold tracking-tight mb-6">
          Not sure where to start?
        </h2>
        <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
          Book a 20-minute call. I&apos;ll ask about your search setup, look at
          your site, and recommend the smallest audit that makes sense. No
          pressure, no pitch deck.
        </p>
        <div>
          <Button asChild size="lg" className="rounded-full h-14 px-10 text-lg">
            <Link href="/book-a-call">Book a call</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
