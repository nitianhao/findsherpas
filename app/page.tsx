import Link from "next/link";
import { Target, CornerDownLeft, SlidersHorizontal, BarChart3 } from "lucide-react";

import { Button } from "@/components/ui/button";

export default async function Home() {
  return (
    <div>
      {/* ============================================================
          1. HERO
          ============================================================ */}
      <section className="pb-16 pt-16 sm:pb-20 sm:pt-24 lg:pb-24 lg:pt-32">
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
      <section className="-mx-4 bg-primary/[0.04] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-[1120px]">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Most teams assume their search works well enough
          </h2>
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
      </section>

      {/* ============================================================
          3. WHAT FIND SHERPAS DOES
          ============================================================ */}
      <section id="what-we-do" className="py-12 sm:py-16 lg:py-20">
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
      </section>

      {/* ============================================================
          SEARCH CHECK PROMO
          ============================================================ */}
      <section className="-mx-4 border-y border-primary/10 bg-gradient-to-br from-primary/[0.06] via-primary/[0.03] to-transparent px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-20">
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

          <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_auto]">
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
      </section>

      {/* ============================================================
          4. HOW WE AUDIT SEARCH
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-[1120px]">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            How we audit search
          </h2>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            We examine real queries, real results, and the ranking logic behind them —
            then turn the findings into a prioritized improvement roadmap.
          </p>

          {(() => {
            const auditSteps = [
              {
                number: "01",
                title: "Query patterns",
                description:
                  "How people actually search — high-volume queries, high-intent queries, edge cases, and failure patterns.",
              },
              {
                number: "02",
                title: "Result relevance",
                description:
                  "Whether search results match intent, surface the right products, and avoid silent dead ends.",
              },
              {
                number: "03",
                title: "Ranking behavior",
                description:
                  "Boosting, ranking rules, attribute weighting, and other logic that shapes result ordering.",
              },
              {
                number: "04",
                title: "Evaluation framework",
                description:
                  "How search quality is measured, where validation is missing, and what should be tested systematically.",
              },
              {
                number: "05",
                title: "Improvement roadmap",
                description:
                  "Findings translated into a clear, prioritized plan teams can implement internally.",
              },
            ];
            return (
              <>
                {/* Desktop: horizontal 5-step flow */}
                <div className="relative mt-10 hidden lg:grid lg:grid-cols-5 lg:gap-0">
                  {/* Timeline connector */}
                  <div className="absolute left-[20px] right-[20px] top-[19px] h-px bg-border" aria-hidden />
                  {auditSteps.map((step) => (
                    <div key={step.number} className="relative flex flex-col">
                      <div className="relative z-10 pr-6">
                        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-background text-sm font-bold tabular-nums text-foreground/70 ring-1 ring-border">
                          {step.number}
                        </span>
                        <h3 className="mt-4 text-sm font-bold tracking-tight">{step.title}</h3>
                        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                          {step.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Desktop: loop indicator */}
                <div className="mt-6 hidden items-center gap-2.5 lg:flex" aria-hidden>
                  <svg width="20" height="16" viewBox="0 0 20 16" fill="none" className="text-muted-foreground/40">
                    <path d="M16 12H4a3 3 0 0 1-3-3V5a3 3 0 0 1 3-3h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    <path d="M14 5l3-3-3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="text-xs text-muted-foreground/50">Continuous evaluation</span>
                </div>

                {/* Mobile / Tablet: vertical stacked */}
                <div className="mt-8 space-y-0 lg:hidden">
                  {auditSteps.map((step, i) => (
                    <div
                      key={step.number}
                      className={`flex gap-4 py-5 ${i > 0 ? "border-t border-border/50" : ""}`}
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-background text-xs font-bold tabular-nums text-foreground/70 ring-1 ring-border">
                        {step.number}
                      </span>
                      <div>
                        <h3 className="text-sm font-bold tracking-tight">{step.title}</h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {step.description}
                        </p>
                      </div>
                    </div>
                  ))}
                  {/* Mobile: loop indicator */}
                  <div className="flex items-center gap-2.5 border-t border-border/50 pt-5">
                    <svg width="18" height="14" viewBox="0 0 20 16" fill="none" className="text-muted-foreground/40">
                      <path d="M16 12H4a3 3 0 0 1-3-3V5a3 3 0 0 1 3-3h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      <path d="M14 5l3-3-3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="text-xs text-muted-foreground/50">Continuous evaluation</span>
                  </div>
                </div>

                {/* Supporting line */}
                <p className="mt-6 text-xs text-muted-foreground/60">
                  Search systems improve through continuous evaluation and iteration.
                </p>
              </>
            );
          })()}
          {/* Credibility strip */}
          <div className="mt-16 grid gap-8 border-t border-border/30 pt-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-12">
            <div>
              <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">
                Large catalogs
              </p>
              <p className="mt-1.5 text-sm font-semibold text-foreground">
                10k&ndash;10M+ searchable products
              </p>
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">
                Complex ranking systems
              </p>
              <p className="mt-1.5 text-sm font-semibold text-foreground">
                Boosting rules, attribute weighting, query rewriting
              </p>
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">
                Multiple search platforms
              </p>
              <p className="mt-1.5 text-sm font-semibold text-foreground">
                Algolia, Elasticsearch, OpenSearch, Typesense
              </p>
            </div>
            <div>
              <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground/50">
                Multilingual search
              </p>
              <p className="mt-1.5 text-sm font-semibold text-foreground">
                European ecommerce environments
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================
          5. SEARCH THINKING
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.02] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-[1120px]">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Search thinking
          </h2>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Ideas and frameworks for understanding how internal search systems behave.
          </p>

          <div className="mt-10 grid gap-10 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-border/30">
            <div className="border-t border-border/40 pt-6 sm:pr-8 lg:pr-10">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                Framework 01
              </p>
              <h3 className="mt-3 text-base font-bold tracking-tight sm:text-lg">
                Evaluating search relevance
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Search quality cannot be judged by analytics alone.
              </p>
              <p className="mt-3 text-xs font-medium text-muted-foreground/70">Key signals:</p>
              <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Structured query test sets</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Human relevance judging</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Result comparison across ranking changes</li>
              </ul>
              <p className="mt-4 text-xs text-muted-foreground/60">
                Focus: test sets, query judging, result comparison
              </p>
            </div>

            <div className="border-t border-border/40 pt-6 sm:border-t-0 sm:px-8 lg:px-10">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                Framework 02
              </p>
              <h3 className="mt-3 text-base font-bold tracking-tight sm:text-lg">
                Query taxonomy
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Different query types behave differently in search systems.
              </p>
              <p className="mt-3 text-xs font-medium text-muted-foreground/70">Key types:</p>
              <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Navigational queries</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Attribute queries</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Exploratory searches</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Long-tail discovery</li>
              </ul>
              <p className="mt-4 text-xs text-muted-foreground/60">
                Focus: navigational, attribute, exploratory, long-tail
              </p>
            </div>

            <div className="border-t border-border/40 pt-6 sm:border-t-0 sm:pl-8 lg:pl-10">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                Framework 03
              </p>
              <h3 className="mt-3 text-base font-bold tracking-tight sm:text-lg">
                Ranking failure modes
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Certain patterns consistently cause relevance breakdowns.
              </p>
              <p className="mt-3 text-xs font-medium text-muted-foreground/70">Common failure modes:</p>
              <ul className="mt-1 space-y-0.5 text-sm text-muted-foreground">
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Boosting distortions</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Synonym gaps</li>
                <li className="flex items-baseline gap-2"><span className="text-muted-foreground/40">&bull;</span>Category bias in results</li>
              </ul>
              <p className="mt-4 text-xs text-muted-foreground/60">
                Focus: boosting distortions, synonym gaps, category bias
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================
          6. OUR EXPERTISE
          ============================================================ */}
      <section className="py-12 sm:py-16 lg:py-20">
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
      </section>

      {/* ============================================================
          5. HOW WE WORK
          ============================================================ */}
      <section className="py-12 sm:py-16 lg:py-20">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          How we work with teams
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          A focused process — we do the diagnostic work, your team ships the changes.
        </p>

        <div className="mt-8 grid gap-0 sm:mt-10">
          {[
            {
              number: "01",
              title: "Search audit",
              description:
                "We evaluate search quality across real queries — relevance, ranking, query handling, and UX.",
            },
            {
              number: "02",
              title: "Diagnosis",
              description:
                "We identify where ranking, query understanding, and configuration fail — and why.",
            },
            {
              number: "03",
              title: "Improvement roadmap",
              description:
                "We design concrete, prioritized changes tailored to your search stack and team capacity.",
            },
            {
              number: "04",
              title: "Implementation support",
              description:
                "We help your team or vendor ship and validate improvements. No ongoing dependency required.",
            },
          ].map((step, i) => (
            <div
              key={step.number}
              className={`flex gap-4 py-6 sm:gap-6 ${
                i > 0 ? "border-t border-border/50" : ""
              }`}
            >
              <span className="text-sm font-semibold text-muted-foreground/50 tabular-nums">
                {step.number}
              </span>
              <div>
                <h3 className="text-base font-semibold">{step.title}</h3>
                <p className="mt-1 max-w-lg text-sm text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ============================================================
          DIAGNOSTIC EXAMPLE
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.02] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-[1120px]">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            What a search problem can look like
          </h2>
          <p className="mt-3 max-w-2xl text-foreground/70">
            A simple example of the kinds of relevance issues that remain
            invisible until search is examined closely.
          </p>

          <div className="mx-auto mt-10 flex max-w-xl flex-col items-stretch">
            {/* Step 1: Query */}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Step 1 &mdash; Query
              </p>
              <p className="mt-3 font-mono text-lg font-bold tracking-tight text-foreground">
                black running shoes
              </p>
            </div>

            {/* Connector */}
            <div className="flex justify-start py-4 pl-1 text-muted-foreground/30" aria-hidden>
              <svg width="16" height="28" viewBox="0 0 16 28" fill="none"><path d="M8 0v20m0 0-4-4m4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>

            {/* Step 2: Observed ranking behavior */}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Step 2 &mdash; Observed ranking behavior
              </p>
              <p className="mt-3 text-sm leading-relaxed text-foreground/80">
                Bestselling products appear below weak matches, while less
                relevant products surface too high.
              </p>
            </div>

            {/* Connector */}
            <div className="flex justify-start py-4 pl-1 text-muted-foreground/30" aria-hidden>
              <svg width="16" height="28" viewBox="0 0 16 28" fill="none"><path d="M8 0v20m0 0-4-4m4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>

            {/* Step 3: Likely causes */}
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Step 3 &mdash; Likely causes
              </p>
              <ul className="mt-3 space-y-1.5 text-sm text-foreground/80">
                <li className="flex items-baseline gap-2"><span className="text-foreground/30">&bull;</span>Boosting rules overpowering relevance</li>
                <li className="flex items-baseline gap-2"><span className="text-foreground/30">&bull;</span>Attribute weighting misaligned with query intent</li>
                <li className="flex items-baseline gap-2"><span className="text-foreground/30">&bull;</span>Ranking behavior not evaluated systematically</li>
              </ul>
            </div>
          </div>

          <p className="mt-10 border-t border-border/40 pt-6 text-sm text-muted-foreground">
            The exact query changes. The pattern does not.
          </p>
        </div>
      </section>

      {/* ============================================================
          CLOSING CTA
          ============================================================ */}
      <section className="py-16 sm:py-20 lg:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Let&apos;s talk about your search system
          </h2>
          <p className="mt-4 text-muted-foreground">
            If your team is unsure whether your internal search is performing as
            well as it should, we can take a look.
          </p>
          <p className="mt-3 text-sm text-muted-foreground/70">
            Search systems often appear to work — but deeper inspection
            frequently reveals ranking issues, query interpretation problems, or
            evaluation gaps.
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:justify-center sm:gap-4">
            <Button asChild size="lg" className="h-12 w-full text-base font-semibold sm:w-auto px-8">
              <Link href="/book-a-call">Start a conversation</Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="h-12 w-full text-base font-medium sm:w-auto px-8">
              <Link href="/#what-we-do">Learn about our approach</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
