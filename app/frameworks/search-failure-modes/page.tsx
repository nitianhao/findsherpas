import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Search failure modes — Find Sherpas",
  description:
    "A structured framework for understanding how internal search systems fail. Covers query interpretation, ranking, coverage, evaluation, merchandising distortions, and operational drift.",
};

const failureModes = [
  {
    id: "query-understanding",
    number: "01",
    title: "Query understanding failures",
    explanation:
      "The search system misinterprets what the user is looking for. It treats all queries as simple keyword matches, ignoring structure, intent, and context.",
    inPractice: [
      "Compound queries like \"red running shoes size 42\" are split into unrelated keyword fragments",
      "Attribute values (color, size, material) are matched against product descriptions instead of structured fields",
      "Synonyms are missing or incomplete — \"sneakers\" and \"trainers\" return different result sets",
      "Misspellings and regional spelling variants return zero results",
    ],
    whyMissed:
      "Teams test with queries they already know work. Real user queries are more varied, misspelled, and structurally complex than internal test cases.",
    impact:
      "Users searching with natural, specific queries get poor results or nothing. The highest-intent searches — the ones closest to purchase — are most affected.",
  },
  {
    id: "ranking",
    number: "02",
    title: "Ranking failures",
    explanation:
      "The search engine finds the right products but shows them in the wrong order. Result relevance degrades because ranking logic is misconfigured, outdated, or never validated.",
    inPractice: [
      "Bestselling products for a given query are buried below position 10",
      "Boosting rules for promotions or new arrivals override textual relevance scores",
      "Category-level ranking weights produce inconsistent ordering across product types",
      "Result order changes after configuration updates, but no one evaluates the difference",
    ],
    whyMissed:
      "Ranking problems are invisible in aggregate metrics. Click-through rates and conversion data reflect many variables at once. Without query-level result inspection, ranking degradation goes unnoticed.",
    impact:
      "The right products exist in the catalog but don't surface where they should. Users see plausible results, assume the selection is poor, and leave.",
  },
  {
    id: "coverage",
    number: "03",
    title: "Coverage failures",
    explanation:
      "Searchable queries that should return results return nothing — or return results that miss entire product segments. The catalog is there, but search doesn't reach it.",
    inPractice: [
      "Long-tail queries return zero results despite matching products existing in the catalog",
      "Products added recently are not indexed or are indexed with incomplete attributes",
      "Filters and facets exclude valid products due to missing or inconsistent attribute data",
      "Category-specific terminology doesn't map to how users actually search",
    ],
    whyMissed:
      "Zero-result rates are rarely monitored at the query level. Teams see a low overall zero-result percentage and assume coverage is fine. The long tail — hundreds of low-volume queries — is where gaps concentrate.",
    impact:
      "Users with specific intent hit dead ends. No redirect, no suggestion, no signal. They leave silently, and the exit never shows up in conversion funnels.",
  },
  {
    id: "evaluation",
    number: "04",
    title: "Evaluation failures",
    explanation:
      "There is no structured way to measure whether search is improving, degrading, or standing still. Changes are shipped without validation. Quality is assumed, not measured.",
    inPractice: [
      "No representative query test set exists for the catalog",
      "Relevance is judged informally — someone searches a few queries and eyeballs the results",
      "Ranking changes are deployed without before/after comparison",
      "Search quality metrics (nDCG, precision, recall) are not tracked or not understood",
    ],
    whyMissed:
      "Search evaluation requires deliberate setup: curated query sets, relevance judgments, comparison tooling. Without it, teams rely on anecdotal checks and aggregate analytics that mask individual query failures.",
    impact:
      "Search quality drifts in unpredictable directions. Improvements in one area silently break another. Teams lose the ability to make confident changes.",
  },
  {
    id: "merchandising",
    number: "05",
    title: "Merchandising distortions",
    explanation:
      "Manual merchandising rules — pinning, boosting, burying — accumulate over time and begin to override the relevance model. The search system serves business rules instead of user intent.",
    inPractice: [
      "Pinned products remain at the top long after promotions end",
      "Boosting rules for high-margin products push relevant results down",
      "Seasonal merchandising rules are not removed after the season",
      "Competing rules across teams create inconsistent result behavior",
    ],
    whyMissed:
      "Merchandising rules are managed by different people at different times. There is rarely a single view of all active rules, their interactions, or their cumulative effect on ranking.",
    impact:
      "Relevance degrades gradually. The search system becomes a manual curation tool rather than an intelligent retrieval system. Maintenance cost increases while result quality decreases.",
  },
  {
    id: "operational-drift",
    number: "06",
    title: "Operational drift",
    explanation:
      "Search configuration degrades over time because no one owns it continuously. Settings, rules, and data pipelines fall out of alignment with the current catalog and user behavior.",
    inPractice: [
      "Synonym lists reference discontinued product lines or outdated terminology",
      "Index mappings don't reflect new product attributes added to the catalog",
      "Query rules written for a previous catalog structure produce unexpected results",
      "Search platform upgrades introduce behavior changes that aren't reviewed",
    ],
    whyMissed:
      "Search is treated as infrastructure rather than a product. After initial setup, it receives attention only when something visibly breaks. Gradual degradation doesn't trigger alerts.",
    impact:
      "Search quality erodes slowly. Each individual change is minor, but the cumulative effect is a system that no longer matches the catalog it serves or the users it's meant to help.",
  },
];

export default function SearchFailureModesPage() {
  return (
    <div>
      {/* ── Hero ── */}
      <section className="pb-12 pt-16 sm:pb-16 sm:pt-24 lg:pt-32">
        <div className="mx-auto max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
            Framework
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl lg:text-[2.75rem] lg:leading-[1.15]">
            Search failure modes
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Most search systems return results. That doesn&apos;t mean they work.
            Underneath, the same structural failures appear again and again.
            This framework maps the six categories we diagnose most often.
          </p>
          <p className="mt-4 text-sm text-muted-foreground/70">
            These patterns are vendor-agnostic. They appear in Algolia,
            Elasticsearch, OpenSearch, Typesense, and other search platforms.
          </p>
        </div>
      </section>

      {/* ── Category overview ── */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-10 sm:-mx-6 sm:px-6 sm:py-14 lg:-mx-8 lg:px-8">
        <div className="mx-auto max-w-[1120px]">
          <h2 className="text-base font-semibold tracking-tight">
            Six common search failure modes
          </h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {failureModes.map((mode) => (
              <a
                key={mode.id}
                href={`#${mode.id}`}
                className="group rounded-lg border border-border/50 bg-background px-5 py-4 transition-colors hover:border-primary/30"
              >
                <span className="text-xs font-bold tabular-nums text-muted-foreground/50">
                  {mode.number}
                </span>
                <p className="mt-1 text-sm font-semibold tracking-tight group-hover:text-primary">
                  {mode.title}
                </p>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ── Failure mode sections ── */}
      {failureModes.map((mode, i) => (
        <section
          key={mode.id}
          id={mode.id}
          className={`scroll-mt-24 py-12 sm:py-16 lg:py-20 ${
            i % 2 === 1
              ? "-mx-4 bg-primary/[0.02] px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8"
              : ""
          }`}
        >
          <div className="mx-auto max-w-3xl">
            <p className="text-xs font-bold tabular-nums text-muted-foreground/50">
              {mode.number}
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
              {mode.title}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted-foreground">
              {mode.explanation}
            </p>

            {/* What it looks like */}
            <div className="mt-8">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/60">
                What it looks like in practice
              </h3>
              <ul className="mt-3 space-y-2 text-sm text-foreground/80">
                {mode.inPractice.map((item, j) => (
                  <li key={j} className="flex items-baseline gap-2">
                    <span className="text-muted-foreground/40">&bull;</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Why teams miss it */}
            <div className="mt-8">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/60">
                Why teams miss it
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-foreground/80">
                {mode.whyMissed}
              </p>
            </div>

            {/* Impact */}
            <div className="mt-8">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/60">
                Impact
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-foreground/80">
                {mode.impact}
              </p>
            </div>
          </div>
        </section>
      ))}

      {/* ── Closing note ── */}
      <section className="-mx-4 border-t border-border/30 bg-primary/[0.04] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Diagnosing search requires looking at the system whole
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            These failure modes rarely appear in isolation. A ranking problem may
            be caused by a{" "}
            <Link href="/frameworks/query-interpretation" className="font-medium text-foreground hover:underline">
              query understanding gap
            </Link>
            . A coverage failure may be masked by merchandising rules.
            Evaluation failures allow all other categories to persist undetected.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Most search systems exhibit several of these failure modes simultaneously.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Diagnosing search quality means examining real queries, real result
            behavior, ranking logic, and evaluation methods together — then
            turning findings into a prioritized improvement plan.
          </p>
          <p className="mt-8 text-sm text-muted-foreground/70">
            Related:{" "}
            <Link
              href="/frameworks/query-interpretation"
              className="font-medium text-foreground hover:underline"
            >
              Query interpretation in search systems
            </Link>
          </p>
          <p className="mt-3 text-sm text-muted-foreground/70">
            If any of these patterns sound familiar,{" "}
            <Link
              href="/book-a-call"
              className="font-medium text-foreground hover:underline"
            >
              we can take a look
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  );
}
