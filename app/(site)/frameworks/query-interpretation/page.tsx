import type { Metadata } from "next";
import Link from "next/link";
import { Layers, Tag, RefreshCw, Cpu, HelpCircle } from "lucide-react";

export const metadata: Metadata = {
  title: { absolute: "Query interpretation in search systems | Find Sherpas" },
  description:
    "A framework for understanding how search engines interpret user queries and why query understanding failures are among the most common causes of poor search quality.",
  alternates: { canonical: "https://findsherpas.com/frameworks/query-interpretation" },
};

const failurePatterns = [
  "Compound queries treated as unstructured text instead of decomposed into attribute filters",
  "Attribute values like color, size, and material matched against descriptions rather than faceted fields",
  "Synonym lists creating false equivalences that mask deeper interpretation problems",
  "Misspellings and regional variants returning zero results instead of fuzzy-matched alternatives",
  "Multi-word brand names split across tokens and matched incorrectly",
  'Queries with implicit intent ("gift for dad") returning literal keyword matches',
  'Negation and exclusion queries ("dress not black") ignored entirely by the search engine',
];

const overviewItems = [
  { id: "compound-queries",      label: "Compound queries",    icon: Layers    },
  { id: "attribute-queries",     label: "Attribute queries",   icon: Tag       },
  { id: "synonyms-vs-meaning",   label: "Synonyms vs meaning", icon: RefreshCw },
  { id: "tokenization",          label: "Tokenization",        icon: Cpu       },
  { id: "ambiguous-queries",     label: "Ambiguous queries",   icon: HelpCircle},
];

export default function QueryInterpretationPage() {
  return (
    <div>
      {/* ── Hero ── */}
      <section className="pb-8 pt-12 sm:pb-12 sm:pt-20 lg:pt-28">
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

      {/* ── Interpretation map ── */}
      <section className="pb-8 sm:pb-12">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Five interpretation challenges
            </p>

            {/* Mobile: vertical stack */}
            <div className="mt-4 flex flex-col gap-2 md:hidden">
              {overviewItems.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={item.id} className="flex flex-col items-center gap-1">
                    <a
                      href={`#${item.id}`}
                      className="inline-flex w-full items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-colors hover:border-gray-400 hover:text-gray-900"
                    >
                      <Icon size={13} strokeWidth={1.5} className="shrink-0 text-gray-500" />
                      <span className="mr-auto">{item.label}</span>
                      <span className="text-xs text-gray-400">{i + 1}</span>
                    </a>
                    {i < overviewItems.length - 1 && (
                      <span className="select-none text-sm text-gray-300">↓</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* md+: horizontal connected pills */}
            <div className="mt-5 hidden flex-wrap items-center gap-2 md:flex">
              {overviewItems.map((item, i) => {
                const Icon = item.icon;
                return (
                  <div key={item.id} className="flex items-center gap-2">
                    <a
                      href={`#${item.id}`}
                      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-colors hover:border-gray-400 hover:text-gray-900"
                    >
                      <Icon size={13} strokeWidth={1.5} className="text-gray-500" />
                      {item.label}
                    </a>
                    {i < overviewItems.length - 1 && (
                      <span className="select-none text-gray-300">→</span>
                    )}
                  </div>
                );
              })}
            </div>

            <p className="mt-4 text-xs text-gray-500">
              Each challenge compounds the others. Scroll to explore each one.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          01 — COMPOUND QUERIES
          ═══════════════════════════════════════════ */}
      <section id="compound-queries" className="scroll-mt-24 py-8 sm:py-12 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">01</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Compound queries
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Users frequently combine multiple concepts in a single search:
            product type, color, size, material, gender. Most search engines
            treat the entire input as a single text string and attempt to match
            it against indexed fields. When the system cannot decompose the
            query into structured components, results degrade sharply.
          </p>

          {/* Diagram */}
          <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Query decomposition
            </p>

            {/* Query pill */}
            <div className="mt-5 flex justify-center">
              <span className="rounded-full border border-gray-300 bg-gray-50 px-5 py-2 font-mono text-sm font-semibold text-gray-800">
                "red dress size 38"
              </span>
            </div>

            {/* Arrow */}
            <div className="my-3 flex justify-center text-gray-300 text-lg">↓</div>

            {/* Good decomposition */}
            <div className="flex flex-wrap justify-center gap-3">
              {[
                { token: "red",     label: "color" },
                { token: "dress",   label: "product type" },
                { token: "size 38", label: "size" },
              ].map(({ token, label }) => (
                <div key={token} className="flex flex-col items-center gap-1.5">
                  <span className="rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-800">
                    {token}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <span className="text-gray-300">→</span>
                    {label}
                  </span>
                </div>
              ))}
            </div>

            <div className="my-6 border-t border-dashed border-gray-200" />

            {/* Bad interpretation */}
            <p className="text-center text-xs font-semibold uppercase tracking-wide text-red-500">
              Without decomposition
            </p>
            <div className="mt-3 overflow-x-auto">
              <div className="flex justify-center">
                <span className="rounded-md border border-red-200 bg-red-50 px-5 py-2 font-mono text-sm text-red-700 whitespace-nowrap">
                  "red dress size 38" → matched as one string
                </span>
              </div>
            </div>
            <p className="mt-3 text-center text-xs text-gray-400">
              Partial keyword overlap only — attributes are ignored
            </p>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Example</p>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">
              "red dress silk size 38" — the engine matches on partial keyword
              overlap instead of filtering by color, material, and size as distinct attributes.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          02 — ATTRIBUTE QUERIES
          ═══════════════════════════════════════════ */}
      <section
        id="attribute-queries"
        className="-mx-4 scroll-mt-24 bg-primary/[0.02] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-20"
      >
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">02</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Attribute queries
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Some queries express a specific product attribute: a color, a
            material, a brand, a size. If these values are not mapped to
            structured product fields, the search engine falls back to full-text
            matching — which produces noisy, unreliable results.
          </p>

          {/* Diagram */}
          <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Attribute mapping
            </p>

            <div className="mt-5 flex justify-center">
              <span className="rounded-full border border-gray-300 bg-gray-50 px-5 py-2 font-mono text-sm font-semibold text-gray-800">
                "waterproof hiking jacket men"
              </span>
            </div>

            <div className="my-5 flex justify-center text-gray-300 text-lg">↓</div>

            <div className="mx-auto max-w-xs space-y-2">
              {[
                { word: "waterproof", attr: "feature",      ok: true  },
                { word: "hiking",     attr: "activity",     ok: true  },
                { word: "jacket",     attr: "product type", ok: true  },
                { word: "men",        attr: "gender",       ok: true  },
              ].map(({ word, attr }) => (
                <div key={word} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-center font-mono text-sm font-medium text-gray-800">
                    {word}
                  </span>
                  <span className="text-gray-300">→</span>
                  <span className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-700">
                    {attr}
                  </span>
                </div>
              ))}
            </div>

            <div className="my-6 border-t border-dashed border-gray-200" />

            <p className="text-center text-xs font-semibold uppercase tracking-wide text-red-500">
              Without attribute mapping
            </p>
            <p className="mt-2 text-center text-xs text-gray-400">
              All four words matched against product description text → noisy results
            </p>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Example</p>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">
              "waterproof hiking jacket men" — "waterproof" is a product
              property, "men" is a gender filter, but both are matched against
              description text instead of faceted attributes.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          03 — SYNONYMS VS MEANING
          ═══════════════════════════════════════════ */}
      <section id="synonyms-vs-meaning" className="scroll-mt-24 py-8 sm:py-12 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">03</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Synonyms vs. meaning
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Synonym lists are the most common attempt at improving query
            understanding. They help in narrow cases, but they don't solve the
            underlying problem: the search engine doesn't understand what the
            user means. Synonyms map strings to strings. They cannot distinguish
            intent, context, or the relationship between terms.
          </p>

          {/* Diagram */}
          <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Synonym expansion
            </p>

            <div className="mt-5 flex justify-center">
              <span className="rounded-full border border-gray-300 bg-gray-50 px-5 py-2 font-mono text-sm font-semibold text-gray-800">
                sneakers
              </span>
            </div>

            <div className="my-5 flex justify-center text-gray-300 text-lg">↓</div>

            <div className="flex flex-wrap justify-center gap-3">
              {[
                { term: "trainers",      ok: true,  note: "correct" },
                { term: "running shoes", ok: true,  note: "correct" },
                { term: "sport shoes",   ok: false, note: "may surface casual shoes" },
              ].map(({ term, ok, note }) => (
                <div key={term} className="flex flex-col items-center gap-1">
                  <span className={`rounded-full border px-3 py-1.5 text-sm font-medium ${
                    ok
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-amber-200 bg-amber-50 text-amber-800"
                  }`}>
                    {term}
                  </span>
                  <span className="text-xs text-gray-400">{note}</span>
                </div>
              ))}
            </div>

            <div className="my-6 border-t border-dashed border-gray-200" />

            <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
              <span className="font-semibold">The limit of synonyms: </span>
              "running shoes" → "sneakers" may surface casual footwear.
              The synonym string is correct; the user intent is not served.
            </div>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Example</p>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">
              "sneakers" mapped to "trainers" works. But "running shoes" mapped
              to "sneakers" may surface casual shoes instead of performance
              footwear. The synonym is correct; the interpretation is wrong.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          04 — TOKENIZATION
          ═══════════════════════════════════════════ */}
      <section
        id="tokenization"
        className="-mx-4 scroll-mt-24 bg-primary/[0.02] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-20"
      >
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">04</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Tokenization and normalization
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Before matching, queries are split into tokens and normalized:
            lowercased, stripped of punctuation, sometimes stemmed. These
            transformations are invisible to users and to most teams — but they
            determine what the search engine actually looks for. Misconfigured
            tokenization silently distorts query meaning.
          </p>

          {/* Diagram */}
          <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Processing pipeline
            </p>

            <div className="mt-6 flex flex-col items-center gap-0">
              {[
                { label: "Raw query",      value: '"t-shirt"',          highlight: false },
                { label: "Lowercase",      value: '"t-shirt"',          highlight: false },
                { label: "Tokenize",       value: '["t", "shirt"]',     highlight: true  },
                { label: "Normalize",      value: '["t", "shirt"]',     highlight: false },
                { label: "Search tokens",  value: 'matches any "shirt"',highlight: true  },
              ].map((step, i) => (
                <div key={step.label} className="flex w-full flex-col items-center">
                  <div className={`flex w-full max-w-sm items-center justify-between gap-3 rounded-lg border px-4 py-3 ${
                    step.highlight
                      ? "border-red-200 bg-red-50"
                      : "border-gray-200 bg-gray-50"
                  }`}>
                    <span className="shrink-0 text-xs font-semibold text-gray-500">{step.label}</span>
                    <span className={`overflow-x-auto font-mono text-sm ${step.highlight ? "text-red-700" : "text-gray-800"}`}>
                      {step.value}
                    </span>
                  </div>
                  {i < 4 && (
                    <span className="my-1 text-gray-300">↓</span>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              <span className="font-semibold">Problem: </span>
              "t-shirt" splits into ["t", "shirt"] — now matches all products containing "shirt",
              including dress shirts, workshirts, and unrelated items.
            </div>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Example</p>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">
              "t-shirt" tokenized as ["t", "shirt"] matches any product
              containing the word "shirt." Hyphenated terms, model numbers,
              and SKU-like queries are especially fragile.
            </p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          05 — AMBIGUOUS QUERIES
          ═══════════════════════════════════════════ */}
      <section id="ambiguous-queries" className="scroll-mt-24 py-8 sm:py-12 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">05</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
            Ambiguous queries
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Many queries are genuinely ambiguous. "apple" could be a fruit or a
            brand. "coach" could be a brand or a product type. Search systems
            rarely have mechanisms to handle ambiguity explicitly — they pick
            one interpretation based on whatever the ranking model favors, often
            producing results that are correct for one intent and invisible for
            the other.
          </p>

          {/* Diagram */}
          <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Intent branching
            </p>

            <div className="mt-5 flex justify-center">
              <span className="rounded-full border border-gray-300 bg-gray-50 px-5 py-2 font-mono text-sm font-semibold text-gray-800">
                apple
              </span>
            </div>

            <div className="my-5 grid grid-cols-2 gap-4">
              <div className="flex flex-col items-center gap-2">
                <span className="text-gray-300 text-sm">↙</span>
                <div className="w-full rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
                  <p className="text-sm font-semibold text-emerald-800">🍎 apple fruit</p>
                  <p className="mt-1 text-xs text-emerald-600">grocery / produce intent</p>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2">
                <span className="text-gray-300 text-sm">↘</span>
                <div className="w-full rounded-lg border border-blue-200 bg-blue-50 p-3 text-center">
                  <p className="text-sm font-semibold text-blue-800"> Apple brand</p>
                  <p className="mt-1 text-xs text-blue-600">electronics / brand intent</p>
                </div>
              </div>
            </div>

            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              <span className="font-semibold">Ranking must resolve the ambiguity. </span>
              Without explicit signals, the system picks one branch and silently ignores the other.
            </div>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Example</p>
            <p className="mt-2 text-sm leading-relaxed text-gray-600">
              "jaguar" in an outdoor equipment store — the system returns zero
              results because it tries to match a brand name that doesn't exist
              in the catalog, instead of interpreting it as an animal print or
              pattern.
            </p>
          </div>
        </div>
      </section>

      {/* ── Failure patterns ── */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
            Common failure patterns
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            Specific interpretation failures we encounter during search audits.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {failurePatterns.map((pattern) => (
              <div
                key={pattern}
                className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-700"
              >
                <span className="mr-2 font-semibold text-gray-400">—</span>
                {pattern}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Why teams underestimate ── */}
      <section className="py-8 sm:py-12 lg:py-20">
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
          <p className="mt-4 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4 text-sm font-medium text-gray-700">
            A well-ranked set of wrong candidates is still a failed search.
          </p>
        </div>
      </section>

      {/* ── Closing ── */}
      <section className="-mx-4 border-t border-border/30 bg-primary/[0.04] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8">
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
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Running a few structured tests on your own system often reveals whether query interpretation is working as expected. The{" "}
            <Link href="/search-check" className="font-medium text-foreground hover:underline">
              internal search self-assessment
            </Link>{" "}
            includes checks designed to surface exactly these gaps.
          </p>
          {/* Next steps */}
          <div className="mt-10 border-t border-border/40 pt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/50">
              Next steps
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Link
                href="/search-check"
                className="group flex flex-col rounded-lg border border-primary/20 bg-primary/[0.03] p-4 transition-colors hover:border-primary/40 hover:bg-primary/[0.06]"
              >
                <span className="text-[11px] font-semibold uppercase tracking-wide text-primary/70">
                  Self-check
                </span>
                <span className="mt-1.5 text-sm font-medium text-foreground group-hover:underline">
                  Run these checks on your own search system →
                </span>
                <span className="mt-1 text-xs text-muted-foreground">6 checks · 5 min · no setup</span>
              </Link>

              <Link
                href="/frameworks/search-failure-modes"
                className="group flex flex-col rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-gray-400"
              >
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/50">
                  Related framework
                </span>
                <span className="mt-1.5 text-sm font-medium text-foreground group-hover:underline">
                  Six categories of search failure modes
                </span>
                <span className="mt-1 text-xs text-muted-foreground">Search failure modes framework</span>
              </Link>

              <Link
                href="/book-a-call"
                className="group flex flex-col rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-gray-400"
              >
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/50">
                  Get help
                </span>
                <span className="mt-1.5 text-sm font-medium text-foreground group-hover:underline">
                  Talk to us about your search system
                </span>
                <span className="mt-1 text-xs text-muted-foreground">Short intro call · no commitment</span>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
