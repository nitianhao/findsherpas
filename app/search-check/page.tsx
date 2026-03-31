import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Quick Search Check",
  description:
    "A simple diagnostic guide to help ecommerce teams assess whether their internal search has hidden relevance issues.",
};

export default function SearchCheckPage() {
  return (
    <div>
      {/* ================================================================
          HERO
          ================================================================ */}
      <section className="-mx-4 -mt-10 bg-gradient-to-b from-primary/[0.08] via-primary/[0.03] to-transparent px-4 pb-12 pt-16 sm:-mx-6 sm:px-6 sm:pb-16 sm:pt-20 lg:-mx-8 lg:px-8 lg:pb-20 lg:pt-28">
        <div className="mx-auto max-w-3xl text-center">
          <Badge
            variant="outline"
            className="mb-6 border-primary/30 px-3 py-1 text-xs font-medium text-primary"
          >
            3 quick checks &middot; 5 minutes &middot; no setup
          </Badge>
          <h1 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Is your internal search working as well as it should?
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Many ecommerce teams assume their search works well enough. Simple
            checks often reveal ranking issues, query gaps, or relevance
            problems that quietly affect revenue.
          </p>
          <div className="mt-8 flex items-center justify-center gap-6 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500/70" />
              Good sign
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-amber-500/70" />
              Warning sign
            </span>
          </div>
        </div>
      </section>

      {/* ================================================================
          ASSESSMENT CARDS
          ================================================================ */}
      <section className="py-10 sm:py-14 lg:py-16">
        <div className="mx-auto max-w-3xl space-y-6 sm:space-y-8">

          {/* ── Check 01 ──────────────────────────────────────────── */}
          <div className="group relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-background to-primary/[0.04] shadow-sm">
            {/* Step indicator bar */}
            <div className="flex items-center gap-3 border-b border-border/50 bg-primary/[0.03] px-6 py-3 sm:px-8">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                1
              </span>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Relevance check
              </span>
              <span className="ml-auto text-xs text-muted-foreground/50">
                Step 1 of 3
              </span>
            </div>

            <div className="p-6 sm:p-8">
              <h3 className="text-xl font-bold tracking-tight sm:text-2xl">
                Search your most important query
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Take one of your highest-intent product queries (for example:
                &ldquo;black running shoes&rdquo; or &ldquo;wireless
                headphones&rdquo;).
              </p>

              {/* Example query */}
              <div className="mt-5 inline-flex items-center gap-2 rounded-lg border border-border/60 bg-background px-4 py-2.5 shadow-sm">
                <span className="text-xs font-medium text-muted-foreground/60">Try:</span>
                <span className="font-mono text-sm font-semibold text-foreground">
                  black running shoes
                </span>
              </div>

              {/* What to look for */}
              <div className="mt-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  What to look for
                </p>
                <div className="mt-3 space-y-2.5">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-500/70" />
                    <span className="text-sm text-foreground/80">
                      Most relevant products appear in the first few results
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-500/70" />
                    <span className="text-sm text-foreground/80">
                      Bestselling products are easy to find
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Weaker matches appear above stronger ones
                    </span>
                  </div>
                </div>
              </div>

              {/* Interpretation */}
              <div className="mt-6 rounded-lg border border-amber-500/20 bg-amber-500/[0.04] px-4 py-3">
                <p className="text-sm text-foreground/70">
                  <span className="font-semibold text-amber-600 dark:text-amber-400">If unclear:</span>{" "}
                  your ranking logic may not be aligned with real query intent.
                </p>
              </div>
            </div>
          </div>

          {/* ── Check 02 ──────────────────────────────────────────── */}
          <div className="group relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-background to-primary/[0.04] shadow-sm">
            <div className="flex items-center gap-3 border-b border-border/50 bg-primary/[0.03] px-6 py-3 sm:px-8">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                2
              </span>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Query parsing check
              </span>
              <span className="ml-auto text-xs text-muted-foreground/50">
                Step 2 of 3
              </span>
            </div>

            <div className="p-6 sm:p-8">
              <h3 className="text-xl font-bold tracking-tight sm:text-2xl">
                Try a compound query
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Search for a query combining multiple attributes.
              </p>

              <div className="mt-5 inline-flex items-center gap-2 rounded-lg border border-border/60 bg-background px-4 py-2.5 shadow-sm">
                <span className="text-xs font-medium text-muted-foreground/60">Try:</span>
                <span className="font-mono text-sm font-semibold text-foreground">
                  waterproof hiking boots men
                </span>
              </div>

              <div className="mt-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  What to look for
                </p>
                <div className="mt-3 space-y-2.5">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Attribute interpretation errors
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Incorrect product filtering
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Unexpected ranking behavior
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-lg border border-amber-500/20 bg-amber-500/[0.04] px-4 py-3">
                <p className="text-sm text-foreground/70">
                  <span className="font-semibold text-amber-600 dark:text-amber-400">Common issue:</span>{" "}
                  compound queries often expose weaknesses in query parsing and ranking logic.
                </p>
              </div>
            </div>
          </div>

          {/* ── Check 03 ──────────────────────────────────────────── */}
          <div className="group relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-background to-primary/[0.04] shadow-sm">
            <div className="flex items-center gap-3 border-b border-border/50 bg-primary/[0.03] px-6 py-3 sm:px-8">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                3
              </span>
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Coverage check
              </span>
              <span className="ml-auto text-xs text-muted-foreground/50">
                Step 3 of 3
              </span>
            </div>

            <div className="p-6 sm:p-8">
              <h3 className="text-xl font-bold tracking-tight sm:text-2xl">
                Look at your zero-result queries
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Review queries that return no results.
              </p>

              <div className="mt-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  What to look for
                </p>
                <div className="mt-3 space-y-2.5">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Legitimate product searches returning nothing
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Synonyms that exist but are not recognized
                    </span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-amber-500/70" />
                    <span className="text-sm text-foreground/80">
                      Simple wording changes that suddenly produce results
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-lg border border-amber-500/20 bg-amber-500/[0.04] px-4 py-3">
                <p className="text-sm text-foreground/70">
                  <span className="font-semibold text-amber-600 dark:text-amber-400">Often reveals:</span>{" "}
                  missing synonym coverage or indexing gaps.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          WHY THIS MATTERS
          ================================================================ */}
      <section className="-mx-4 border-y border-border/40 bg-primary/[0.03] px-4 py-10 sm:-mx-6 sm:px-6 sm:py-14 lg:-mx-8 lg:px-8 lg:py-16">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Why this matters
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Internal search is used by customers with the strongest purchase
            intent. Even small ranking issues can affect revenue, conversion
            rate, and product discovery.
          </p>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground/70">
            Most search systems appear to work — until their behavior is
            examined closely.
          </p>
        </div>
      </section>

      {/* ================================================================
          CTA
          ================================================================ */}
      <section className="py-14 sm:py-16 lg:py-20">
        <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/[0.06] via-primary/[0.03] to-background shadow-md">
          <div className="p-8 text-center sm:p-10 lg:p-12">
            <p className="text-xs font-semibold uppercase tracking-wide text-primary">
              Assessment complete
            </p>
            <h2 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">
              Want help interpreting what you found?
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
              We specialize in diagnosing internal search systems in ecommerce
              and marketplaces. If something looked off, we can take a closer look.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center sm:gap-4">
              <Button
                asChild
                size="lg"
                className="h-12 w-full text-base font-semibold sm:w-auto px-8"
              >
                <Link href="/book-a-call">Start a conversation</Link>
              </Button>
              <Button
                asChild
                variant="outline"
                size="lg"
                className="h-12 w-full text-base font-medium sm:w-auto px-8"
              >
                <Link href="/">Back to homepage</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
