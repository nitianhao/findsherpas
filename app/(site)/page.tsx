import type { Metadata } from "next";
import Link from "next/link";
import { Target, CornerDownLeft, SlidersHorizontal, BarChart3, AlertTriangle, Workflow, Database, CheckCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { HomeSidebar } from "@/components/site/home-sidebar";

export const metadata: Metadata = {
  title: { absolute: "Internal search audit and optimization for ecommerce | Find Sherpas" },
  description:
    "Find Sherpas diagnoses why ecommerce search returns the wrong results — and maps a clear path to fixing ranking, query interpretation, and relevance.",
  alternates: { canonical: "https://findsherpas.com/" },
};

export default async function Home() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[80px_1fr]">

      {/* ── Spine column ────────────────────────────────────── */}
      <HomeSidebar />

      {/* ── Content column ──────────────────────────────────── */}
      <div>

        {/* ============================================================
            1. HERO
            ============================================================ */}
        <section id="hero" className="pb-16 pt-16 sm:pb-20 sm:pt-24 lg:pb-24 lg:pt-32">
          <div className="mx-auto max-w-3xl">
            <p className="text-sm font-medium tracking-wide text-muted-foreground">
              Internal search for ecommerce &amp; marketplaces
            </p>
            <h1 className="mt-4 text-balance text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.5rem]">
              Internal search,{" "}
              <br className="hidden sm:block" />
              diagnosed and improved.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
              Ranking, relevance, query understanding, and search
              analytics — evaluated and refined, independent of your search vendor.
            </p>
            <p className="mt-4 text-sm text-muted-foreground/70">
              Experience with large-scale ecommerce search systems — Algolia, Elasticsearch, OpenSearch, Typesense, Luigi&apos;s Box.
            </p>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:gap-4">
              <Button asChild size="lg" className="h-12 w-full text-base font-semibold sm:w-auto px-8">
                <Link href="/#what-we-do">Our expertise</Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="h-12 w-full text-base font-medium sm:w-auto px-8">
                <Link href="/book-a-call">Get in touch</Link>
              </Button>
            </div>
          </div>
        </section>

        {/* ============================================================
            2. THE PROBLEM WITH INTERNAL SEARCH
            ============================================================ */}
        <section id="search-problem" className="-mx-4 bg-primary/[0.04] px-4 py-8 md:-ml-20 md:pl-20 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <div className="flex items-center gap-2">
                <AlertTriangle size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
                <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                  Most teams assume their search works well enough
                </h2>
              </div>
              <p className="mt-3 max-w-2xl text-muted-foreground">
                Until you examine real queries closely, ranking issues, weak query
                handling, and dead ends stay invisible. The search engine returns
                results — just not the right ones, often enough to matter.
              </p>

              <div className="mt-8 grid gap-6 sm:mt-10 sm:grid-cols-2 lg:grid-cols-4">
                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background shadow-sm ring-1 ring-border/50">
                    <Target className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Ranking misses intent</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Results look plausible at a glance but don&apos;t match what
                      the customer meant — especially on your most important queries.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background shadow-sm ring-1 ring-border/50">
                    <SlidersHorizontal className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Query handling breaks quietly</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Synonyms, typos, and compound queries return poor or empty
                      results — and no one is alerted.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background shadow-sm ring-1 ring-border/50">
                    <CornerDownLeft className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">Dead ends cause silent exits</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Zero-result pages and no-click searches push people away,
                      but typical analytics don&apos;t flag them.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background shadow-sm ring-1 ring-border/50">
                    <BarChart3 className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold">No way to measure quality</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Without structured evaluation, teams can&apos;t tell whether
                      search is improving, degrading, or standing still.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            3. WHAT FIND SHERPAS DOES
            ============================================================ */}
        <section id="what-we-do" className="py-8 sm:py-12 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                Diagnostic patterns
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">
                What we find when we look closely
              </h2>
              <p className="mt-3 max-w-xl text-muted-foreground">
                These patterns appear in most ecommerce search systems. They&apos;re rarely visible in dashboards.
              </p>

              <div className="mt-8 grid gap-5 sm:mt-10 sm:grid-cols-2">
                <div className="rounded-xl border border-border/50 p-6">
                  <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Relevance</p>
                  <h3 className="mt-2 text-base font-bold tracking-tight">Results look right. They&apos;re not.</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Top queries return plausible products, but bestsellers are buried and weak matches surface first. The search appears functional — the ranking is wrong.
                  </p>
                </div>

                <div className="rounded-xl border border-border/50 p-6">
                  <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Query interpretation</p>
                  <h3 className="mt-2 text-base font-bold tracking-tight">Queries break without anyone noticing</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Synonyms missing. Compound queries split wrong. Attribute searches like &ldquo;red dress size 38&rdquo; treated as free text. No alerts, no fallback.
                  </p>
                </div>

                <div className="rounded-xl border border-border/50 p-6">
                  <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Ranking</p>
                  <h3 className="mt-2 text-base font-bold tracking-tight">Ranking rules nobody owns</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Boosting rules layered over months. Conflicting weights across categories. Result order changes and no one evaluates the impact.
                  </p>
                </div>

                <div className="rounded-xl border border-border/50 p-6">
                  <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Zero results</p>
                  <h3 className="mt-2 text-base font-bold tracking-tight">Silent dead ends</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Queries return nothing — no redirect, no suggestion, no signal. Users leave. It happens most on long-tail and misspelled queries.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            SEARCH CHECK PROMO
            ============================================================ */}
        <section id="search-check-promo" className="-mx-4 border-y border-primary/10 bg-gradient-to-br from-primary/[0.06] via-primary/[0.03] to-transparent px-4 py-8 md:-ml-20 md:pl-20 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-primary">
                Quick diagnostic
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">
                Test your search in 5 minutes
              </h2>
              <p className="mt-3 max-w-2xl text-muted-foreground">
                Run three simple checks that often reveal hidden ranking or query
                interpretation problems.
              </p>

              {/* Mobile: compact CTA */}
              <div className="mt-6 lg:hidden">
                <Button asChild size="lg" className="w-full font-semibold">
                  <Link href="/search-check">Run the quick search check &rarr;</Link>
                </Button>
                <p className="mt-2 text-center text-xs text-muted-foreground/60">3 checks &middot; 5 min &middot; no setup</p>
              </div>

              {/* lg+: full card layout */}
              <div className="mt-10 hidden gap-10 lg:grid lg:grid-cols-[1fr_auto]">
                {/* Left: explanation */}
                <div className="max-w-lg">
                  <p className="text-sm leading-relaxed text-foreground/80">
                    Most ecommerce teams assume their search works well. A few
                    simple tests often reveal issues with ranking logic, query
                    interpretation, or missing coverage.
                  </p>
                  <ul className="mt-5 space-y-2 text-sm text-foreground/70">
                    <li className="flex items-baseline gap-2">
                      <span className="text-primary/50">&bull;</span>
                      Check your most important query
                    </li>
                    <li className="flex items-baseline gap-2">
                      <span className="text-primary/50">&bull;</span>
                      Test a compound attribute search
                    </li>
                    <li className="flex items-baseline gap-2">
                      <span className="text-primary/50">&bull;</span>
                      Look at zero-result queries
                    </li>
                  </ul>
                </div>

                {/* Right: diagnostic card */}
                <div className="w-full overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-background to-primary/[0.04] shadow-md lg:w-[340px]">
                  <div className="border-b border-primary/10 bg-primary/[0.04] px-6 py-3">
                    <p className="text-sm font-bold text-foreground">
                      Internal search quick check
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      3 checks &middot; 5 minutes &middot; no setup
                    </p>
                  </div>
                  <div className="px-6 py-5">
                    <div className="space-y-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
                          1
                        </span>
                        <span className="text-sm font-medium text-foreground/80">
                          Relevance check
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
                          2
                        </span>
                        <span className="text-sm font-medium text-foreground/80">
                          Query parsing check
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
                          3
                        </span>
                        <span className="text-sm font-medium text-foreground/80">
                          Coverage check
                        </span>
                      </div>
                    </div>
                    <div className="mt-6">
                      <Button asChild size="default" className="w-full font-semibold">
                        <Link href="/search-check">
                          Run the quick search check &rarr;
                        </Link>
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            4. HOW WE AUDIT SEARCH
            ============================================================ */}
        <section id="how-we-diagnose" className="-mx-4 bg-primary/[0.04] px-4 py-8 md:-ml-20 md:pl-20 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                Diagnostic methodology
              </p>
              <div className="mt-3 flex items-center gap-2">
                <Workflow size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
                <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                  How we diagnose search
                </h2>
              </div>
              <p className="mt-3 max-w-xl text-muted-foreground">
                A structured process applied to every search system we evaluate.
              </p>

              {/* Desktop: 5 cards in a row */}
              <div className="mt-10 hidden lg:grid lg:grid-cols-5 lg:gap-3">
                {[
                  {
                    number: "01",
                    title: "Real queries",
                    desc: "Analyze actual user queries — high-volume, high-intent, long-tail, and failure patterns.",
                  },
                  {
                    number: "02",
                    title: "Query interpretation",
                    desc: "How the system reads the input. Tokenization, synonyms, compound handling, attribute mapping.",
                  },
                  {
                    number: "03",
                    title: "Result quality",
                    desc: "Whether results match intent. Position accuracy, dead ends, coverage gaps.",
                  },
                  {
                    number: "04",
                    title: "Ranking logic",
                    desc: "Boosting rules, attribute weights, merchandising overrides, and their cumulative effect.",
                  },
                  {
                    number: "05",
                    title: "Improvement roadmap",
                    desc: "Prioritized, actionable changes your team can implement. No dependency on us.",
                  },
                ].map((step, i) => (
                  <div key={step.number} className="relative flex flex-col">
                    {i > 0 && (
                      <div className="absolute -left-[10px] top-[22px] text-border" aria-hidden>
                        <svg width="8" height="12" viewBox="0 0 8 12" fill="none">
                          <path d="M1 1l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                    )}
                    <div className="rounded-lg border border-border/50 bg-background p-4">
                      <span className="text-[11px] font-bold tabular-nums text-primary/60">
                        {step.number}
                      </span>
                      <h3 className="mt-1.5 text-sm font-bold tracking-tight">
                        {step.title}
                      </h3>
                      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                        {step.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Mobile / Tablet: vertical cards */}
              <div className="mt-8 space-y-3 lg:hidden">
                {[
                  {
                    number: "01",
                    title: "Real queries",
                    desc: "Analyze actual user queries — high-volume, high-intent, long-tail, and failure patterns.",
                  },
                  {
                    number: "02",
                    title: "Query interpretation",
                    desc: "How the system reads the input. Tokenization, synonyms, compound handling, attribute mapping.",
                  },
                  {
                    number: "03",
                    title: "Result quality",
                    desc: "Whether results match intent. Position accuracy, dead ends, coverage gaps.",
                  },
                  {
                    number: "04",
                    title: "Ranking logic",
                    desc: "Boosting rules, attribute weights, merchandising overrides, and their cumulative effect.",
                  },
                  {
                    number: "05",
                    title: "Improvement roadmap",
                    desc: "Prioritized, actionable changes your team can implement. No dependency on us.",
                  },
                ].map((step) => (
                  <div key={step.number} className="flex gap-4 rounded-lg border border-border/50 bg-background p-4">
                    <span className="text-[11px] font-bold tabular-nums text-primary/60">
                      {step.number}
                    </span>
                    <div>
                      <h3 className="text-sm font-bold tracking-tight">{step.title}</h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {step.desc}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <p className="mt-6 text-xs text-muted-foreground/50">
                Each step informs the next. The process repeats as the system evolves.
              </p>
            </div>
          </div>
        </section>

        {/* ============================================================
            5. SEARCH FRAMEWORKS
            ============================================================ */}
        <section id="frameworks" className="-mx-4 bg-primary/[0.02] px-4 py-8 md:-ml-20 md:pl-20 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Search frameworks
              </h2>
              <p className="mt-3 max-w-2xl text-muted-foreground">
                Conceptual tools we use to analyze how search systems behave, where they fail, and how relevance should be evaluated.
              </p>

              <div className="mt-10 grid gap-10 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-border/30">
                <div className="border-t border-border/40 pt-6 sm:pr-8 lg:pr-10">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                    Framework 01
                  </p>
                  <h3 className="mt-3 text-base font-bold tracking-tight sm:text-lg">
                    Relevance evaluation
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A structured method for measuring whether search results match user intent — beyond click-through rates and conversion proxies.
                  </p>
                  <p className="mt-3 text-xs font-medium text-muted-foreground/70">Inputs:</p>
                  <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Representative query test sets</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Human relevance judgments</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Before/after result comparison</li>
                  </ul>
                </div>

                <div className="border-t border-border/40 pt-6 sm:border-t-0 sm:px-8 lg:px-10">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                    Framework 02
                  </p>
                  <h3 className="mt-3 text-base font-bold tracking-tight sm:text-lg">
                    <Link href="/frameworks/query-interpretation" className="hover:text-primary hover:underline">
                      Query taxonomy
                    </Link>
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A classification system for query types. Each type has different failure modes and requires different ranking logic.
                  </p>
                  <p className="mt-3 text-xs font-medium text-muted-foreground/70">Types:</p>
                  <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Navigational (exact product)</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Attribute (color, size, material)</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Exploratory (broad category)</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Long-tail (rare or compound)</li>
                  </ul>
                </div>

                <div className="border-t border-border/40 pt-6 sm:border-t-0 sm:pl-8 lg:pl-10">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                    Framework 03
                  </p>
                  <h3 className="mt-3 text-base font-bold tracking-tight sm:text-lg">
                    <Link href="/frameworks/search-failure-modes" className="hover:text-primary hover:underline">
                      Ranking failure modes
                    </Link>
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A diagnostic checklist for identifying why result ordering breaks down. Used to trace ranking problems to their configuration root cause.
                  </p>
                  <p className="mt-3 text-xs font-medium text-muted-foreground/70">Common modes:</p>
                  <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Boosting rule distortions</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Synonym and tokenization gaps</li>
                    <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Category or attribute bias</li>
                  </ul>
                </div>
              </div>

              <div className="mt-8">
                <Link
                  href="/frameworks/search-failure-modes"
                  className="text-sm font-medium text-primary hover:underline"
                >
                  Read the full failure modes framework &rarr;
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            6. OUR EXPERTISE
            ============================================================ */}
        <section id="expertise" className="py-8 sm:py-12 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                Deep, narrow expertise
              </h2>
              <p className="mt-3 max-w-2xl text-muted-foreground">
                We only do one thing: internal search for ecommerce. That focus
                means faster diagnosis, sharper recommendations, and less wasted scope.
              </p>

              <div className="mt-8 grid gap-6 sm:mt-10 sm:grid-cols-2">
                <div className="rounded-xl border border-border/50 p-6">
                  <h3 className="text-sm font-semibold">Vendor-agnostic</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Algolia, Elasticsearch, Luigi&apos;s Box, Doofinder, Coveo,
                    Bloomreach, and others. The methodology applies regardless
                    of your stack.
                  </p>
                </div>

                <div className="rounded-xl border border-border/50 p-6">
                  <h3 className="text-sm font-semibold">Experiment-driven</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Every recommendation includes testable hypotheses and success
                    metrics. Your team can prioritize and validate with controlled
                    experiments.
                  </p>
                </div>

                <div className="rounded-xl border border-border/50 p-6">
                  <h3 className="text-sm font-semibold">Multilingual</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Audits conducted in English, German, French, Spanish, Italian,
                    Dutch, and Swedish. Query analysis in the language your customers
                    actually use.
                  </p>
                </div>

                <div className="rounded-xl border border-border/50 p-6">
                  <h3 className="text-sm font-semibold">No lock-in</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    We deliver a diagnosis and a roadmap. Your team or vendor handles
                    the build. No retainer, no ongoing dependency.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            SEARCH ENVIRONMENTS
            ============================================================ */}
        <section className="-mx-4 border-t border-border/30 bg-primary/[0.04] px-4 py-6 md:-ml-20 md:pl-20 sm:-mx-6 sm:px-6 sm:py-10 lg:-mx-8 lg:px-8 lg:py-14">
          <div className="mx-auto max-w-[1120px]">
            <div className="flex items-center gap-2">
              <Database size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
              <h2 className="text-base font-semibold tracking-tight">
                Search environments we&apos;ve worked in
              </h2>
            </div>
            <div className="mt-6 grid gap-x-12 gap-y-4 sm:grid-cols-2 lg:grid-cols-5">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Catalog scale</p>
                <p className="mt-1 text-sm text-foreground">10k&ndash;10M+ products</p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Query volume</p>
                <p className="mt-1 text-sm text-foreground">High-traffic ecommerce</p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Ranking complexity</p>
                <p className="mt-1 text-sm text-foreground">Boosting, weighting, rewriting</p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Platforms</p>
                <p className="mt-1 text-sm text-foreground">Algolia, Elasticsearch, OpenSearch, Typesense</p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">Languages</p>
                <p className="mt-1 text-sm text-foreground">Multilingual European markets</p>
              </div>
            </div>
            <p className="mt-6 text-xs text-muted-foreground/50">
              Also Doofinder, Luigi&apos;s Box, Coveo, Bloomreach, and other platforms. The diagnostic methodology applies regardless of vendor.
            </p>
          </div>
        </section>

        {/* ============================================================
            WHAT TEAMS RECEIVE
            ============================================================ */}
        <section id="diagnostic-output" className="py-8 sm:py-12 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <div className="flex items-center gap-2">
                <CheckCircle size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
                <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                  What the diagnostic produces
                </h2>
              </div>
              <p className="mt-3 max-w-xl text-sm text-muted-foreground">
                A clear picture of where search is failing and a prioritized plan for what to fix.
              </p>
              <div className="mt-8 space-y-4 sm:max-w-xl">
                {[
                  {
                    label: "Diagnosis",
                    detail: "A clear account of where and how search is failing — broken down by query understanding, ranking behavior, coverage, and evaluation gaps.",
                  },
                  {
                    label: "Query analysis",
                    detail: "Examples of problematic query patterns drawn from real traffic: misinterpreted compound queries, attribute failures, silent zero-result cases.",
                  },
                  {
                    label: "Ranking observations",
                    detail: "An assessment of how ranking logic behaves across query types — where configuration is working and where it is distorting results.",
                  },
                  {
                    label: "Evaluation perspective",
                    detail: "An honest view of what is and is not being measured, and what a minimal structured evaluation process would look like for the system.",
                  },
                  {
                    label: "Improvement roadmap",
                    detail: "A prioritized list of changes — ordered by impact and feasibility — that your team or vendor can act on directly.",
                  },
                ].map((item, i, arr) => (
                  <div key={item.label} className={`flex flex-col gap-1 sm:flex-row sm:gap-4 pb-4 ${i < arr.length - 1 ? "border-b border-border/40" : ""}`}>
                    <p className="w-auto shrink-0 text-sm font-semibold text-foreground sm:w-40">{item.label}</p>
                    <p className="text-sm text-muted-foreground">{item.detail}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================
            DIAGNOSTIC EXAMPLE
            ============================================================ */}
        <section className="-mx-4 bg-primary/[0.02] px-4 py-8 md:-ml-20 md:pl-20 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                Example diagnosis
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">
                Ranking failure investigation
              </h2>
              <p className="mt-3 max-w-2xl text-foreground/70">
                A simplified version of the diagnostic process used during a search audit. The query, the observed result behavior, and the likely root causes.
              </p>

              <div className="mx-auto mt-10 flex max-w-xl flex-col items-stretch">
                {/* Step 1: Query */}
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Query
                  </p>
                  <p className="mt-3 font-mono text-lg font-bold tracking-tight text-foreground">
                    black running shoes
                  </p>
                </div>

                {/* Connector */}
                <div className="flex justify-start py-4 pl-1 text-muted-foreground/30" aria-hidden>
                  <svg width="16" height="28" viewBox="0 0 16 28" fill="none"><path d="M8 0v20m0 0-4-4m4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </div>

                {/* Step 2: Observed behavior */}
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Observed result behavior
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-foreground/80">
                    Top-selling SKUs ranked below weak text matches. Position 1&ndash;3 occupied by low-conversion products with partial keyword overlap.
                  </p>
                </div>

                {/* Connector */}
                <div className="flex justify-start py-4 pl-1 text-muted-foreground/30" aria-hidden>
                  <svg width="16" height="28" viewBox="0 0 16 28" fill="none"><path d="M8 0v20m0 0-4-4m4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                </div>

                {/* Step 3: Root causes */}
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Identified root causes
                  </p>
                  <ul className="mt-3 space-y-1.5 text-sm text-foreground/80">
                    <li className="flex items-baseline gap-2"><span className="text-foreground/30">&bull;</span>Boosting rule on &ldquo;new arrivals&rdquo; overriding textual relevance score</li>
                    <li className="flex items-baseline gap-2"><span className="text-foreground/30">&bull;</span>Color attribute not indexed as a filterable field</li>
                    <li className="flex items-baseline gap-2"><span className="text-foreground/30">&bull;</span>No ranking validation against a representative query set</li>
                  </ul>
                </div>
              </div>

              <p className="mt-10 border-t border-border/40 pt-6 text-sm text-muted-foreground">
                Different query. Same diagnostic structure.
              </p>
            </div>
          </div>
        </section>

        {/* ============================================================
            RECURRING AUDIT FINDINGS
            ============================================================ */}
        <section className="py-8 sm:py-12 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-[1120px]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                From real audits
              </p>
              <h2 className="mt-3 text-xl font-semibold tracking-tight sm:text-2xl">
                Failures we find repeatedly
              </h2>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground">
                Specific patterns that appear across search systems, regardless of vendor or catalog size.
              </p>
              <ul className="mt-6 grid gap-x-12 gap-y-2 text-sm text-foreground/80 sm:grid-cols-2 lg:max-w-3xl">
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Merchandising rules overriding textual relevance</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Synonym lists masking deeper indexing gaps</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Attribute queries parsed as free-text search</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Compound queries returning partial or empty results</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Zero-result queries with no fallback or redirect</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Ranking configuration drifting without evaluation</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Boosting rules conflicting across product categories</li>
              </ul>
            </div>
          </div>
        </section>

        {/* ============================================================
            CLOSING CTA
            ============================================================ */}
        <section id="homepage-cta" className="py-10 sm:py-16 lg:py-24">
          <div className="border-t border-gray-200 pt-8">
            <div className="mx-auto max-w-xl text-center">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                If search feels hard to evaluate, that&apos;s usually a signal
              </h2>
              <p className="mt-5 text-muted-foreground">
                Results look acceptable. Confidence is low. Something feels off but
                there&apos;s no clear evidence yet.
              </p>
              <p className="mt-3 text-sm text-muted-foreground/70">
                That&apos;s exactly the kind of system we diagnose. We examine real
                queries, ranking behavior, and evaluation gaps — then give your team
                a clear picture of what&apos;s happening and what to fix first.
              </p>
              <div className="mt-10">
                <Button asChild size="lg" className="h-12 px-8 text-base font-semibold">
                  <Link href="/book-a-call">Get in touch</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>

      </div>{/* end content column */}
    </div>
  );
}
