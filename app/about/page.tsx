import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LANGUAGES_EXCLUDED, SUPPORTED_LANGUAGES } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description:
    "Find Sherpas is a specialist studio focused on diagnosing and improving internal search for ecommerce and marketplaces.",
};

export default function AboutPage() {
  return (
    <div className="py-10">
      {/* ── 1. Headline ─────────────────────────────────────── */}
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        Focused on internal search.
      </h1>
      <p className="mt-4 max-w-2xl text-muted-foreground">
        Find Sherpas improves the search experience inside ecommerce sites and
        marketplaces — the search bar customers use to find products.
      </p>
      <p className="mt-3 max-w-2xl text-sm text-muted-foreground/70">
        Not SEO. Not CRO. Not external search. Not a vendor implementation
        partner.
      </p>

      {/* Jump links */}
      <nav className="mt-6 flex flex-wrap gap-x-1 gap-y-0.5 text-xs text-muted-foreground/60" aria-label="On this page">
        {[
          { href: "#background", label: "Background" },
          { href: "#vendor-agnostic", label: "Vendor-agnostic" },
          { href: "#how-we-audit", label: "How we audit" },
          { href: "#what-you-get", label: "What you get" },
          { href: "#who-we-work-with", label: "Who we work with" },
          { href: "#languages", label: "Languages" },
          { href: "#contact", label: "Contact" },
        ].map((link, i) => (
          <span key={link.href}>
            {i > 0 && <span className="mr-1" aria-hidden>&middot;</span>}
            <a href={link.href} className="hover:text-foreground hover:underline">
              {link.label}
            </a>
          </span>
        ))}
      </nav>

      {/* ── 2. What we do / What we don't ───────────────────── */}
      <section className="mt-14">
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="rounded-xl border border-border/50 bg-primary/[0.02] p-6">
            <h2 className="text-base font-bold tracking-tight">What we do</h2>
            <ul className="mt-3 space-y-1.5 text-sm text-foreground/80">
              <li className="flex items-baseline gap-2">
                <span className="text-foreground/30">&bull;</span>
                Diagnose where internal search fails — ranking, query
                interpretation, dead ends
              </li>
              <li className="flex items-baseline gap-2">
                <span className="text-foreground/30">&bull;</span>
                Turn findings into a prioritized improvement roadmap your team
                can implement
              </li>
            </ul>
          </div>
          <div className="rounded-xl border border-border/50 p-6">
            <h2 className="text-base font-bold tracking-tight">
              What we don&apos;t do
            </h2>
            <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
              <li className="flex items-baseline gap-2">
                <span className="text-muted-foreground/40">&bull;</span>
                SEO or marketing work
              </li>
              <li className="flex items-baseline gap-2">
                <span className="text-muted-foreground/40">&bull;</span>
                Ongoing &ldquo;embedded consulting&rdquo;
              </li>
              <li className="flex items-baseline gap-2">
                <span className="text-muted-foreground/40">&bull;</span>
                Reselling a specific search platform
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── 3. Background ───────────────────────────────────── */}
      <section id="background" className="mt-14 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">
          Background in search systems
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          The work behind Find Sherpas comes from years inside large-scale
          search environments — catalogs with millions of products, multilingual
          query handling, complex ranking configurations, and search analytics
          built to measure what actually matters.
        </p>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          That experience shapes how we evaluate search: not from the outside,
          but by understanding what happens between a query and the results it
          returns.
        </p>
        <p className="mt-4 text-sm text-muted-foreground/60">
          Catalogs from 10k to 10M+ products. Multilingual environments.
          Complex boosting and ranking configurations across multiple search
          platforms.
        </p>
      </section>

      {/* ── 4. Vendor-agnostic expertise ────────────────────── */}
      <section id="vendor-agnostic" className="mt-14 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">
          Vendor-agnostic expertise
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          We work across platforms, not for them. The method stays the same:
          evaluate with real queries and a structured test set.
        </p>
        <details className="mt-5">
          <summary className="cursor-pointer text-sm font-medium text-primary hover:underline">
            Platforms we&apos;ve worked with
          </summary>
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              "Algolia",
              "Elasticsearch",
              "OpenSearch",
              "Doofinder",
              "Luigi's Box",
              "Coveo",
              "Bloomreach",
              "Typesense",
            ].map((platform) => (
              <Badge key={platform} variant="secondary">
                {platform}
              </Badge>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground/60">
            And others. If your search engine returns results, we can evaluate
            it.
          </p>
        </details>
      </section>

      {/* ── 5. How we audit search ──────────────────────────── */}
      <section id="how-we-audit" className="mt-14 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">
          How we audit search
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          A structured process applied to real queries, real results, and the
          ranking logic behind them.
        </p>
        <p className="mt-2 text-sm text-muted-foreground/60">
          Every audit is built on real query data and a structured relevance
          test set — not assumptions or sample checks.
        </p>

        <div className="mt-8 space-y-0">
          {[
            {
              number: "01",
              title: "Intake",
              description:
                "Goals, constraints, and how search is configured today.",
            },
            {
              number: "02",
              title: "Query reality",
              description:
                "Analyze real queries and journeys — head terms and long tail.",
              output:
                "Top query classes + representative broken queries",
            },
            {
              number: "03",
              title: "Relevance evaluation",
              description:
                "Build or extend a test set and review where results fail.",
              output:
                "Structured test set + documented failure examples",
            },
            {
              number: "04",
              title: "Ranking & rules",
              description:
                "Inspect boosts, synonyms, filters, and mismatch patterns.",
            },
            {
              number: "05",
              title: "UX & edge cases",
              description:
                "Zero results, facets, sorting, autocomplete behavior.",
            },
            {
              number: "06",
              title: "Roadmap",
              description:
                "Prioritized fixes and how to measure improvements.",
              output:
                "Prioritized roadmap (impact x effort) + measurement plan",
            },
          ].map((step: { number: string; title: string; description: string; output?: string }, i) => (
            <div
              key={step.number}
              className={`flex gap-4 py-5 sm:gap-6 ${
                i > 0 ? "border-t border-border/50" : ""
              }`}
            >
              <span className="text-sm font-semibold tabular-nums text-muted-foreground/50">
                {step.number}
              </span>
              <div>
                <h3 className="text-sm font-bold tracking-tight">
                  {step.title}
                </h3>
                <p className="mt-1 max-w-lg text-sm text-muted-foreground">
                  {step.description}
                </p>
                {step.output && (
                  <p className="mt-1 max-w-lg text-xs text-muted-foreground/60">
                    Output: {step.output}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 6. What you get ─────────────────────────────────── */}
      <section id="what-you-get" className="mt-14 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">What you get</h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Concrete deliverables your team can act on.
        </p>
        <ul className="mt-4 space-y-2 text-sm text-foreground/80">
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Query classes and the highest-impact broken queries
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Failure-mode summary — what breaks and why
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Ranking and configuration recommendations with examples
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            UX findings — dead ends, filters, zero-results handling
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            A prioritized roadmap (impact x effort) your team can execute
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-muted-foreground/40">&bull;</span>
            <span className="text-muted-foreground">
              Optional: evaluation framework and monitoring plan as follow-up
            </span>
          </li>
        </ul>
      </section>

      {/* ── 7. Who we work with ───────────────────────────── */}
      <section id="who-we-work-with" className="mt-14 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">
          Who we work with
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Most often: ecommerce teams, marketplaces, and large-catalog sites.
        </p>
        <ul className="mt-4 space-y-1.5 text-sm text-foreground/80">
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Head of Product
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Search / Discovery teams
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Growth teams
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-foreground/30">&bull;</span>
            Engineering leads responsible for search
          </li>
        </ul>

        <h3 className="mt-8 text-base font-semibold tracking-tight">
          A good time to talk
        </h3>
        <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
          <li className="flex items-baseline gap-2">
            <span className="text-muted-foreground/40">&bull;</span>
            Search &ldquo;works&rdquo;, but conversion from search feels low
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-muted-foreground/40">&bull;</span>
            Merch rules and boosts have accumulated and relevance is
            inconsistent
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-muted-foreground/40">&bull;</span>
            Zero-results are rare, but results still feel wrong
          </li>
          <li className="flex items-baseline gap-2">
            <span className="text-muted-foreground/40">&bull;</span>
            You need a test set or evaluation method before making changes
          </li>
        </ul>
      </section>

      {/* ── 8. Why this studio exists ───────────────────────── */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          Why this studio exists
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Search engines always return <em>something</em>. That makes ranking
          problems invisible — until you look at actual queries closely. Weak
          results quietly erode conversion, product discovery, and revenue.
        </p>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Find Sherpas exists because diagnosing search quality is a specific
          skill that sits between product, engineering, and data — and rarely
          gets the focused attention it needs.
        </p>
      </section>

      {/* ── 8. How we work with teams ───────────────────────── */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          How we work with teams
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          We collaborate with product and engineering teams to audit search
          quality, identify where results fail, and build a roadmap of concrete
          improvements. Typical engagements are short and diagnostic — no
          ongoing dependency required.
        </p>
      </section>

      {/* ── 9. Languages ────────────────────────────────────── */}
      <section id="languages" className="mt-14 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">Languages</h2>
        <p className="mt-3 text-sm text-muted-foreground">
          Audits and query analysis can be conducted in most major European
          languages.
        </p>
        <details className="group mt-4">
          <summary className="cursor-pointer text-sm font-medium text-primary hover:underline">
            View all {SUPPORTED_LANGUAGES.length} supported languages
          </summary>
          <div className="mt-3 columns-2 gap-x-8 sm:columns-3 lg:columns-4">
            {SUPPORTED_LANGUAGES.map((lang) => (
              <p
                key={lang}
                className="py-0.5 text-sm text-muted-foreground"
              >
                {lang}
              </p>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground/60">
            Excludes {LANGUAGES_EXCLUDED.join(", ")}.
          </p>
        </details>
      </section>

      {/* ── 10. CTA ─────────────────────────────────────────── */}
      <section id="contact" className="mt-14 scroll-mt-24 border-t border-border/40 pt-10">
        <h2 className="text-xl font-semibold tracking-tight">
          See something off in your search results?
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Send us 3-5 queries that feel wrong and what you expected to see.
          We&apos;ll reply with what we&apos;d investigate.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:gap-4">
          <Button
            asChild
            size="lg"
            className="h-12 w-full px-8 text-base font-semibold sm:w-auto"
          >
            <Link href="/book-a-call">Start a conversation</Link>
          </Button>
          <Button
            asChild
            variant="outline"
            size="lg"
            className="h-12 w-full px-8 text-base font-medium sm:w-auto"
          >
            <a
              href={`mailto:michal.pekarcik@gmail.com?subject=${encodeURIComponent("Search looks off — query examples")}&body=${encodeURIComponent("Site:\n\nSearch platform (if known):\n\n3–5 queries:\n\nWhat I expected:\n\nWhat I got:\n\nAnything else:\n")}`}
            >
              Email 3-5 queries
            </a>
          </Button>
        </div>
      </section>
    </div>
  );
}
