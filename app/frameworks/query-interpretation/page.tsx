import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Query interpretation in search systems — Find Sherpas",
  description:
    "A framework for understanding how search engines interpret user queries and why query understanding failures are among the most common causes of poor search quality.",
};

const challenges = [
  {
    id: "compound-queries",
    number: "01",
    title: "Compound queries",
    explanation:
      "Users frequently combine multiple concepts in a single search: product type, color, size, material, gender. Most search engines treat the entire input as a single text string and attempt to match it against indexed fields. When the system cannot decompose the query into structured components, results degrade sharply.",
    example:
      "\"red dress silk size 38\" — the engine matches on partial keyword overlap instead of filtering by color, material, and size as distinct attributes.",
  },
  {
    id: "attribute-queries",
    number: "02",
    title: "Attribute queries",
    explanation:
      "Some queries express a specific product attribute: a color, a material, a brand, a size. If these values are not mapped to structured product fields, the search engine falls back to full-text matching — which produces noisy, unreliable results.",
    example:
      "\"waterproof hiking jacket men\" — \"waterproof\" is a product property, \"men\" is a gender filter, but both are matched against description text instead of faceted attributes.",
  },
  {
    id: "synonyms-vs-meaning",
    number: "03",
    title: "Synonyms vs. meaning",
    explanation:
      "Synonym lists are the most common attempt at improving query understanding. They help in narrow cases, but they don't solve the underlying problem: the search engine doesn't understand what the user means. Synonyms map strings to strings. They cannot distinguish intent, context, or the relationship between terms.",
    example:
      "\"sneakers\" mapped to \"trainers\" works. But \"running shoes\" mapped to \"sneakers\" may surface casual shoes instead of performance footwear. The synonym is correct; the interpretation is wrong.",
  },
  {
    id: "tokenization",
    number: "04",
    title: "Tokenization and normalization",
    explanation:
      "Before matching, queries are split into tokens and normalized: lowercased, stripped of punctuation, sometimes stemmed. These transformations are invisible to users and to most teams — but they determine what the search engine actually looks for. Misconfigured tokenization silently distorts query meaning.",
    example:
      "\"t-shirt\" tokenized as [\"t\", \"shirt\"] matches any product containing the word \"shirt.\" Hyphenated terms, model numbers, and SKU-like queries are especially fragile.",
  },
  {
    id: "ambiguous-queries",
    number: "05",
    title: "Ambiguous queries",
    explanation:
      "Many queries are genuinely ambiguous. \"apple\" could be a fruit or a brand. \"coach\" could be a brand or a product type. Search systems rarely have mechanisms to handle ambiguity explicitly — they pick one interpretation based on whatever the ranking model favors, often producing results that are correct for one intent and invisible for the other.",
    example:
      "\"jaguar\" in an outdoor equipment store — the system returns zero results because it tries to match a brand name that doesn't exist in the catalog, instead of interpreting it as an animal print or pattern.",
  },
];

const failurePatterns = [
  "Compound queries treated as unstructured text instead of decomposed into attribute filters",
  "Attribute values like color, size, and material matched against product descriptions rather than faceted fields",
  "Synonym lists creating false equivalences that mask deeper interpretation problems",
  "Misspellings and regional variants returning zero results instead of fuzzy-matched alternatives",
  "Multi-word brand names split across tokens and matched incorrectly",
  "Queries with implicit intent (\"gift for dad\") returning literal keyword matches",
  "Negation and exclusion queries (\"dress not black\") ignored entirely by the search engine",
];

export default function QueryInterpretationPage() {
  return (
    <div>
      {/* ── Hero ── */}
      <section className="pb-12 pt-16 sm:pb-16 sm:pt-24 lg:pt-32">
        <div className="mx-auto max-w-3xl">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
            Framework
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl lg:text-[2.75rem] lg:leading-[1.15]">
            Query interpretation in search systems
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Search quality depends on how queries are interpreted before ranking
            begins. If the system misunderstands what the user is looking for,
            no amount of ranking tuning will fix the results.
          </p>
          <p className="mt-4 text-sm text-muted-foreground/70">
            These patterns are vendor-agnostic. They apply to Algolia,
            Elasticsearch, OpenSearch, Typesense, and other search platforms.
          </p>
        </div>
      </section>

      {/* ── Challenge overview ── */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-10 sm:-mx-6 sm:px-6 sm:py-14 lg:-mx-8 lg:px-8">
        <div className="mx-auto max-w-[1120px]">
          <h2 className="text-base font-semibold tracking-tight">
            Five key interpretation challenges
          </h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {challenges.map((c) => (
              <a
                key={c.id}
                href={`#${c.id}`}
                className="group rounded-lg border border-border/50 bg-background px-5 py-4 transition-colors hover:border-primary/30"
              >
                <span className="text-xs font-bold tabular-nums text-muted-foreground/50">
                  {c.number}
                </span>
                <p className="mt-1 text-sm font-semibold tracking-tight group-hover:text-primary">
                  {c.title}
                </p>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ── Challenge sections ── */}
      {challenges.map((c, i) => (
        <section
          key={c.id}
          id={c.id}
          className={`scroll-mt-24 py-12 sm:py-16 lg:py-20 ${
            i % 2 === 1
              ? "-mx-4 bg-primary/[0.02] px-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8"
              : ""
          }`}
        >
          <div className="mx-auto max-w-3xl">
            <p className="text-xs font-bold tabular-nums text-muted-foreground/50">
              {c.number}
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
              {c.title}
            </h2>
            <p className="mt-4 text-base leading-relaxed text-muted-foreground">
              {c.explanation}
            </p>

            <div className="mt-8">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/60">
                Example
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-foreground/80">
                {c.example}
              </p>
            </div>
          </div>
        </section>
      ))}

      {/* ── Common failure patterns ── */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Common failure patterns
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            Specific interpretation failures we encounter during search audits.
          </p>
          <ul className="mt-6 space-y-2 text-sm text-foreground/80">
            {failurePatterns.map((pattern, i) => (
              <li key={i} className="flex items-baseline gap-2">
                <span className="text-muted-foreground/40">&bull;</span>
                {pattern}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Why teams underestimate query interpretation ── */}
      <section className="py-12 sm:py-16 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Why teams underestimate query interpretation
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Ranking tuning is visible and measurable. Teams can change a boost
            value and see the result order shift immediately. Query
            interpretation problems are harder to see: the system returns
            results, they look plausible, and no alert fires. The failure is
            silent.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Most search optimization effort goes into ranking configuration,
            synonyms, and merchandising rules. Query understanding — how the
            system decomposes, normalizes, and maps the raw input before
            matching — receives far less attention. Yet it determines what the
            ranking model actually works with.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            A well-ranked set of wrong candidates is still a failed search.
          </p>
        </div>
      </section>

      {/* ── Closing ── */}
      <section className="-mx-4 border-t border-border/30 bg-primary/[0.04] px-4 py-12 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Diagnosis starts with the query
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Every search audit we conduct begins with query interpretation.
            Before examining{" "}
            <Link href="/frameworks/search-failure-modes#ranking" className="font-medium text-foreground hover:underline">
              ranking behavior
            </Link>
            , coverage gaps, or evaluation frameworks, we look at how the
            system reads the input. If queries are misunderstood at this stage,
            everything downstream inherits the error.
          </p>
          <p className="mt-8 text-sm text-muted-foreground/70">
            Related:{" "}
            <Link
              href="/frameworks/search-failure-modes"
              className="font-medium text-foreground hover:underline"
            >
              Search failure modes
            </Link>
            {" "}&middot;{" "}
            <Link
              href="/book-a-call"
              className="font-medium text-foreground hover:underline"
            >
              Talk to us about your search system
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
