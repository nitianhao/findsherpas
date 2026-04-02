import type { Metadata } from "next";
import Link from "next/link";
import { Target, Sliders, SearchX, ArrowUpDown, Sparkles, Filter, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: { absolute: "Internal search self-assessment — Is your ecommerce search working? | Find Sherpas" },
  description:
    "A simple diagnostic guide to help ecommerce teams assess whether their internal search has hidden relevance issues.",
  alternates: { canonical: "https://findsherpas.com/search-check" },
};

const checks: {
  number: string;
  category: string;
  title: string;
  icon: LucideIcon;
  instruction: string;
  example: string;
  bullets: string[];
  signalLabel: string;
  signal: string;
}[] = [
  {
    number: "01",
    category: "Relevance check",
    title: "Core relevance",
    icon: Target,
    instruction: "Search your most important commercial query.",
    example: "black running shoes",
    bullets: [
      "Top results match intent",
      "Bestsellers appear early",
      "Irrelevant products do not dominate",
    ],
    signalLabel: "If unclear:",
    signal: "ranking logic may not reflect user intent.",
  },
  {
    number: "02",
    category: "Query parsing",
    title: "Attribute queries",
    icon: Sliders,
    instruction: "Try a query with multiple attributes.",
    example: "waterproof hiking boots men",
    bullets: [
      "Attributes are interpreted correctly",
      "Filters behave logically",
      "Ranking does not become erratic",
    ],
    signalLabel: "Common issue:",
    signal: "compound queries expose parsing and ranking weaknesses.",
  },
  {
    number: "03",
    category: "Coverage check",
    title: "Coverage gaps",
    icon: SearchX,
    instruction: "Review searches that return zero results.",
    example: "trail running vest",
    bullets: [
      "Legitimate searches do not return nothing",
      "Synonym gaps are visible",
      "Small wording changes do not radically change results",
    ],
    signalLabel: "Often reveals:",
    signal: "missing synonyms, indexing gaps, or normalization issues.",
  },
  {
    number: "04",
    category: "Ranking controls",
    title: "Sorting behavior",
    icon: ArrowUpDown,
    instruction: "Switch between key sorting modes.",
    example: "price / newest / popularity",
    bullets: [
      "Sorting actually changes results",
      "Relevance is not destroyed",
      "Overrides do not create chaos",
    ],
    signalLabel: "Watch for:",
    signal: "hidden merchandising rules or brittle ranking logic.",
  },
  {
    number: "05",
    category: "Query assistance",
    title: "Autocomplete quality",
    icon: Sparkles,
    instruction: "Type slowly and watch the suggestions.",
    example: "running sho",
    bullets: [
      "Suggestions are useful",
      "Spelling recovery works",
      "Popular intents are surfaced",
    ],
    signalLabel: "Watch for:",
    signal: "weak autocomplete often signals poor query understanding.",
  },
  {
    number: "06",
    category: "Facet check",
    title: "Filter behavior",
    icon: Filter,
    instruction: "Apply and combine a few important filters.",
    example: "brand + size + price",
    bullets: [
      "Result counts stay sensible",
      "Strong products do not disappear unexpectedly",
      "Filter combinations feel stable",
    ],
    signalLabel: "Often reveals:",
    signal: "broken faceting logic, bad attribute data, or hidden inventory issues.",
  },
];

export default function SearchCheckPage() {
  return (
    <div>
      {/* ================================================================
          HERO
          ================================================================ */}
      <section className="-mx-4 bg-gradient-to-b from-primary/[0.08] via-primary/[0.03] to-transparent px-4 pb-8 pt-10 sm:-mx-6 sm:px-6 sm:pb-14 sm:pt-20 lg:-mx-8 lg:px-8 lg:pb-20 lg:pt-28">
        <div className="mx-auto max-w-3xl text-center">
          <Badge
            variant="outline"
            className="mb-6 border-primary/30 px-3 py-1 text-xs font-medium text-primary"
          >
            6 quick checks &middot; ~5 minutes &middot; no setup
          </Badge>
          <h1 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Is your internal search working as well as it should?
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Many ecommerce teams assume their search works well enough. Simple
            checks often reveal ranking issues, query gaps, or relevance
            problems that quietly affect revenue.
          </p>
        </div>
      </section>

      {/* ================================================================
          HOW TO USE THIS STRIP
          ================================================================ */}
      <div className="mx-auto mt-8 max-w-4xl px-0">
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-4">
          <span className="text-sm font-semibold text-gray-900">How to use this &nbsp;&middot;&nbsp; </span>
          <span className="text-sm text-gray-600">
            Run these checks on your own site. If you notice repeated warning
            signs, your search likely needs closer evaluation.
          </span>
        </div>
      </div>

      {/* ================================================================
          ASSESSMENT GRID
          ================================================================ */}
      <section className="py-6 sm:py-12">
        <div className="mx-auto max-w-4xl">
          <div className="grid gap-6 md:grid-cols-2">
            {checks.map((check) => (
              <div
                key={check.number}
                className="flex flex-col rounded-2xl border border-gray-200 bg-white p-4 sm:p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
              >
                {/* Top row: number + category */}
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cyan-600 text-sm font-semibold text-white">
                    {check.number}
                  </span>
                  <span className="text-[11px] uppercase tracking-[0.14em] text-gray-500">
                    {check.category}
                  </span>
                </div>

                {/* Title */}
                <div className="mt-3 flex items-center gap-2">
                  <check.icon size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
                  <h3 className="text-lg font-semibold text-gray-900 sm:text-xl">{check.title}</h3>
                </div>

                {/* Instruction */}
                <p className="mt-1 text-sm text-gray-600">
                  {check.instruction}
                </p>

                {/* Example */}
                <div className="mt-2">
                  <span className="inline-flex rounded-full border border-gray-200 bg-gray-50 px-3 py-1 font-mono text-sm text-gray-800">
                    {check.example}
                  </span>
                </div>

                {/* Bullets */}
                <ul className="mt-3 space-y-1.5">
                  {check.bullets.map((bullet) => (
                    <li key={bullet} className="flex items-start gap-2">
                      <span className="mt-[5px] inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400" />
                      <span className="text-sm text-gray-700">{bullet}</span>
                    </li>
                  ))}
                </ul>

                {/* Bottom signal strip */}
                <div className="mt-4 flex-1 content-end">
                  <div className="rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-gray-700 sm:px-4 sm:py-3">
                    <span className="font-semibold text-amber-700">{check.signalLabel}</span>{" "}
                    {check.signal}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================
          INTERPRETATION
          ================================================================ */}
      <section className="-mx-4 border-y border-gray-200 px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-16">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-xl font-semibold tracking-tight text-gray-900 sm:text-2xl">
            How to interpret what you found
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Count how many checks showed meaningful warning signs.
          </p>

          <div className="mt-6 rounded-2xl border border-gray-200 bg-[#f7fbfb] p-4 sm:p-6">
            <div className="space-y-3">
              {/* Tier 1 */}
              <div className="flex items-start gap-4 rounded-lg border border-emerald-200 bg-emerald-50 px-5 py-4">
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/20">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-emerald-800">0–1 warning signs</p>
                  <p className="mt-0.5 text-sm text-emerald-700">Search likely behaves well.</p>
                </div>
              </div>

              {/* Tier 2 */}
              <div className="flex items-start gap-4 rounded-lg border border-amber-200 bg-amber-50 px-5 py-4">
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20">
                  <span className="inline-block h-2 w-2 rounded-full bg-amber-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-amber-800">2–3 warning signs</p>
                  <p className="mt-0.5 text-sm text-amber-700">Some ranking or query-handling issues likely exist.</p>
                </div>
              </div>

              {/* Tier 3 */}
              <div className="flex items-start gap-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/20">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-red-800">4–6 warning signs</p>
                  <p className="mt-0.5 text-sm text-red-700">Search likely needs deeper diagnostic work.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          CTA
          ================================================================ */}
      <section className="py-8 sm:py-12 lg:py-16">
        <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/[0.06] via-primary/[0.03] to-background shadow-md">
          <div className="p-8 text-center sm:p-10">
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
