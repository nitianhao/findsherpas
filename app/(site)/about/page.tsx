import type { Metadata } from "next";
import Link from "next/link";
import { Search, Slash, Database, Layers, GitBranch, CheckCircle, Users, AlertCircle, Globe } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AboutSidebar } from "@/components/site/about-sidebar";
import { LANGUAGES_EXCLUDED, SUPPORTED_LANGUAGES } from "@/lib/site";

export const metadata: Metadata = {
  title: { absolute: "About Find Sherpas — ecommerce internal search specialists" },
  description:
    "Find Sherpas is a specialist studio focused on diagnosing and improving internal search for ecommerce and marketplaces.",
  alternates: { canonical: "https://findsherpas.com/about" },
};

const environmentCards = [
  { value: "10k–10M+", label: "Catalog scale" },
  { value: "High-traffic", label: "Search queries" },
  { value: "Complex ranking", label: "Boosting and weighting" },
  { value: "Vendor agnostic", label: "Algolia, Elasticsearch, Typesense" },
  { value: "Multilingual", label: "European markets" },
];

const auditSteps = [
  {
    number: "01",
    title: "Query reality",
    description: "Analyze real queries and patterns.",
  },
  {
    number: "02",
    title: "Relevance evaluation",
    description: "Structured test sets reveal ranking failures.",
  },
  {
    number: "03",
    title: "Ranking logic",
    description: "Synonyms, boosts, filters.",
  },
  {
    number: "04",
    title: "Improvement roadmap",
    description: "Prioritized changes and measurement plan.",
  },
];

const deliverables = [
  "Query classes and broken queries",
  "Failure-mode summary",
  "Ranking recommendations with examples",
  "UX findings (facets, sorting, zero results)",
  "Prioritized improvement roadmap",
];

export default function AboutPage() {
  return (
    <div className="py-4 sm:py-10">
      <div className="grid grid-cols-1 gap-0 md:grid-cols-[60px_1fr]">
        <AboutSidebar />

        <div>
      {/* ── 1. Headline ─────────────────────────────────────── */}
      <section id="focus" className="scroll-mt-24">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        Focused on internal search.
      </h1>
      <p className="mt-4 max-w-xl text-muted-foreground">
        Find Sherpas diagnoses why search returns the wrong results — and maps a
        clear path to fixing it. Ecommerce and marketplace sites only.
      </p>
      <p className="mt-2 text-sm text-muted-foreground/60">
        Not SEO. Not CRO. Not a vendor implementation partner.
      </p>
      </section>

      {/* ── 2. What we do / What we don't ───────────────────── */}
      <section id="what-we-do" className="mt-10 scroll-mt-24">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
            <div className="flex items-center gap-2">
              <Search size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
              <h2 className="text-sm font-bold uppercase tracking-wide text-gray-500">We do</h2>
            </div>
            <ul className="mt-3 space-y-1.5 text-sm text-gray-800">
              <li className="flex items-baseline gap-2">
                <span className="text-gray-300">&bull;</span>
                Diagnose ranking, query interpretation, and dead ends
              </li>
              <li className="flex items-baseline gap-2">
                <span className="text-gray-300">&bull;</span>
                Deliver a prioritized roadmap your team can act on
              </li>
            </ul>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center gap-2">
              <Slash size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
              <h2 className="text-sm font-bold uppercase tracking-wide text-gray-500">We don&apos;t do</h2>
            </div>
            <ul className="mt-3 space-y-1.5 text-sm text-gray-500">
              <li className="flex items-baseline gap-2">
                <span className="text-gray-300">&bull;</span>
                SEO or marketing work
              </li>
              <li className="flex items-baseline gap-2">
                <span className="text-gray-300">&bull;</span>
                Ongoing embedded consulting
              </li>
              <li className="flex items-baseline gap-2">
                <span className="text-gray-300">&bull;</span>
                Reselling or implementing a platform
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── 3. Background + Search environments ─────────────── */}
      <section id="background" className="mt-10 scroll-mt-24 sm:mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          Background in search systems
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          The work behind Find Sherpas comes from years inside large-scale
          search environments — catalogs with millions of products, multilingual
          query handling, complex ranking configurations, and search analytics
          built to measure what actually matters.
        </p>

        <div className="mt-6 flex items-center gap-2">
          <Database size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            Search environments we&apos;ve worked in
          </p>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
          {environmentCards.map((card) => (
            <div
              key={card.value}
              className="rounded-xl border border-gray-200 bg-white p-5"
            >
              <p className="text-lg font-semibold text-gray-900">{card.value}</p>
              <p className="mt-0.5 text-sm text-gray-600">{card.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── 4. Vendor-agnostic expertise ────────────────────── */}
      <section id="vendor-agnostic" className="mt-10 scroll-mt-24 sm:mt-14">
        <div className="flex items-center gap-2">
          <Layers size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h2 className="text-xl font-semibold tracking-tight">Vendor-agnostic</h2>
        </div>
        <p className="mt-3 max-w-xl text-muted-foreground">
          We work across platforms, not for them. The method stays the same
          regardless of which engine you run: evaluate with real queries and a
          structured test set.
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

      {/* ── 5. How we audit search — vertical timeline ──────── */}
      <section id="how-we-audit" className="mt-10 scroll-mt-24 sm:mt-14">
        <div className="flex items-center gap-2">
          <GitBranch size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h2 className="text-xl font-semibold tracking-tight">How we audit search</h2>
        </div>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Grounded in real queries and structured relevance evaluation — not
          sample checks or assumptions.
        </p>

        <div className="mt-8 space-y-6">
          {auditSteps.map((step) => (
            <div key={step.number} className="flex items-start gap-6">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-900 text-sm font-semibold text-white">
                {step.number}
              </div>
              <div className="pt-0.5">
                <h3 className="text-sm font-bold tracking-tight text-gray-900">
                  {step.title}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 6. What you get — card grid ─────────────────────── */}
      <section id="what-you-get" className="mt-10 scroll-mt-24 sm:mt-14">
        <div className="flex items-center gap-2">
          <CheckCircle size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h2 className="text-xl font-semibold tracking-tight">What you get</h2>
        </div>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Concrete deliverables your team can act on immediately.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          {deliverables.map((item) => (
            <div
              key={item}
              className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-4"
            >
              <span className="mt-px text-sm font-bold text-gray-900">✓</span>
              <span className="text-sm text-gray-700">{item}</span>
            </div>
          ))}
          <div className="flex items-start gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <span className="mt-px text-sm text-gray-400">+</span>
            <span className="text-sm text-gray-500">
              Optional: evaluation framework and monitoring plan
            </span>
          </div>
        </div>
      </section>

      {/* ── 7. Who we work with ───────────────────────────── */}
      <section id="who-we-work-with" className="mt-10 scroll-mt-24 sm:mt-14">
        <div className="flex items-center gap-2">
          <Users size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h2 className="text-xl font-semibold tracking-tight">Who we work with</h2>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          Most often: ecommerce teams, marketplaces, and large-catalog sites.
          Typically product or engineering leads who own search quality.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {[
            "Head of Product",
            "Search / Discovery teams",
            "Growth teams",
            "Engineering leads",
          ].map((role) => (
            <span
              key={role}
              className="rounded-md border border-gray-200 px-3 py-1 text-sm text-gray-600"
            >
              {role}
            </span>
          ))}
        </div>

        <div id="typical-situations" className="mt-8 flex scroll-mt-24 items-center gap-2">
          <AlertCircle size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h3 className="text-base font-semibold tracking-tight">Typical situations</h3>
        </div>
        <ul className="mt-3 space-y-1.5 text-sm text-muted-foreground">
          {[
            'Search "works", but conversion from search feels low',
            "Merch rules and boosts have accumulated — relevance is inconsistent",
            "Zero-results are rare, but results still feel wrong",
            "You need a test set or evaluation method before making changes",
          ].map((item) => (
            <li key={item} className="flex items-baseline gap-2">
              <span className="text-gray-300">&bull;</span>
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* ── 8. Insight callout ──────────────────────────────── */}
      <div className="mt-10 sm:mt-14 rounded-xl border border-gray-200 bg-gray-50 p-6">
        <p className="max-w-2xl text-base leading-relaxed text-gray-700">
          Search engines almost always return something. That makes ranking
          failures difficult to detect until they quietly start hurting
          conversion.
        </p>
      </div>

      {/* ── 9. Why this studio exists ───────────────────────── */}
      <section id="why-this-studio" className="mt-10 scroll-mt-24">
        <h2 className="text-xl font-semibold tracking-tight">
          Why this studio exists
        </h2>
        <p className="mt-3 max-w-xl text-muted-foreground">
          Find Sherpas exists because diagnosing search quality is a specific
          skill that sits between product, engineering, and data, and rarely
          gets the focused attention it needs.
        </p>
      </section>

      {/* ── 10. Languages ───────────────────────────────────── */}
      <section id="languages" className="mt-10 scroll-mt-24 sm:mt-14">
        <div className="flex items-center gap-2">
          <Globe size={18} strokeWidth={1.5} className="shrink-0 text-gray-600" />
          <h2 className="text-xl font-semibold tracking-tight">Languages</h2>
        </div>
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
              <p key={lang} className="py-0.5 text-sm text-muted-foreground">
                {lang}
              </p>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground/60">
            Excludes {LANGUAGES_EXCLUDED.join(", ")}.
          </p>
        </details>
      </section>

      {/* ── 11. CTA ─────────────────────────────────────────── */}
      <section
        id="contact"
        className="mt-10 scroll-mt-24 border-t border-border/40 pt-8 sm:mt-14 sm:pt-10"
      >
        <h2 className="text-xl font-semibold tracking-tight">
          See something off in your search results?
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Send us 3-5 queries that feel wrong and what you expected to see.
          We&apos;ll reply with what we&apos;d investigate.
        </p>
        <p className="mt-3 text-sm text-muted-foreground/70">
          Not ready to reach out yet?{" "}
          <Link href="/search-check" className="font-medium text-foreground hover:underline">
            Run the quick search self-assessment
          </Link>{" "}
          first — it takes five minutes and gives you a clearer picture of where issues might be.
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
        </div>{/* end main content */}
      </div>{/* end grid */}
    </div>
  );
}
