import type { Metadata } from "next";
import Link from "next/link";
import {
  MessageSquare,
  ArrowUpDown,
  PackageSearch,
  BarChart2,
  Tag,
  Timer,
} from "lucide-react";

export const metadata: Metadata = {
  title: { absolute: "Search failure modes | Find Sherpas" },
  description:
    "A structured framework for understanding how internal search systems fail. Covers query interpretation, ranking, coverage, evaluation, merchandising distortions, and operational drift.",
  alternates: { canonical: "https://findsherpas.com/frameworks/search-failure-modes" },
};

// ─────────────────────────────────────────────
// Shared diagram primitives
// ─────────────────────────────────────────────

function Pill({
  children,
  variant = "default",
}: {
  children: React.ReactNode;
  variant?: "default" | "highlight" | "danger" | "muted" | "success";
}) {
  const styles = {
    default:   "border-gray-200   bg-gray-50    text-gray-800",
    highlight: "border-blue-200   bg-blue-50    text-blue-800",
    danger:    "border-red-200    bg-red-50     text-red-700",
    muted:     "border-gray-100   bg-white      text-gray-400",
    success:   "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1.5 font-mono text-sm font-medium ${styles[variant]}`}>
      {children}
    </span>
  );
}

function Arrow({ dir = "down" }: { dir?: "down" | "right" }) {
  return (
    <span className={`select-none text-gray-300 ${dir === "right" ? "text-base" : "text-lg"}`}>
      {dir === "down" ? "↓" : "→"}
    </span>
  );
}

function Box({
  children,
  variant = "default",
  label,
}: {
  children: React.ReactNode;
  variant?: "default" | "danger" | "highlight" | "success";
  label?: string;
}) {
  const styles = {
    default:   "border-gray-200 bg-gray-50   text-gray-800",
    danger:    "border-red-200  bg-red-50    text-red-700",
    highlight: "border-blue-200 bg-blue-50   text-blue-800",
    success:   "border-emerald-200 bg-emerald-50 text-emerald-700",
  };
  return (
    <div className="flex flex-col items-center gap-1">
      {label && <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{label}</span>}
      <div className={`rounded-lg border px-4 py-2.5 text-sm font-medium ${styles[variant]}`}>
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Overview items
// ─────────────────────────────────────────────

const overviewItems = [
  { id: "query-understanding", number: "01", title: "Query understanding",     icon: MessageSquare, pipeline: "Query understanding" },
  { id: "ranking",             number: "02", title: "Ranking failures",        icon: ArrowUpDown,   pipeline: "Ranking" },
  { id: "coverage",            number: "03", title: "Coverage failures",       icon: PackageSearch, pipeline: "Coverage / filtering" },
  { id: "evaluation",          number: "04", title: "Evaluation failures",     icon: BarChart2,     pipeline: "Evaluation" },
  { id: "merchandising",       number: "05", title: "Merchandising distortions", icon: Tag,          pipeline: "Ranking" },
  { id: "operational-drift",   number: "06", title: "Operational drift",       icon: Timer,         pipeline: "All stages" },
];

// ─────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────

export default function SearchFailureModesPage() {
  return (
    <div>
      {/* ── Hero ── */}
      <section className="pb-8 pt-12 sm:pb-12 sm:pt-20 lg:pt-28">
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

      {/* ── System pipeline diagram ── */}
      <section className="pb-8 sm:pb-12">
        <div className="mx-auto max-w-3xl">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Search system pipeline
            </p>

            {/* Pipeline — mobile: vertical stack */}
            <div className="mt-5 flex flex-col items-center gap-1 md:hidden">
              {[
                "User query",
                "Query understanding",
                "Ranking",
                "Coverage / filtering",
                "Results",
              ].map((stage, i) => (
                <div key={stage} className="flex flex-col items-center gap-1">
                  <span className={`rounded-full border px-3 py-1.5 text-sm font-medium ${
                    i === 0 || i === 4
                      ? "border-gray-300 bg-white text-gray-700"
                      : "border-blue-200 bg-blue-50 text-blue-800"
                  }`}>
                    {stage}
                  </span>
                  {i < 4 && <span className="text-gray-300 text-base">↓</span>}
                </div>
              ))}
            </div>

            {/* Pipeline — md+: horizontal */}
            <div className="mt-5 hidden flex-wrap items-center justify-center gap-2 md:flex">
              {[
                "User query",
                "Query understanding",
                "Ranking",
                "Coverage / filtering",
                "Results",
              ].map((stage, i) => (
                <div key={stage} className="flex items-center gap-2">
                  <span className={`rounded-full border px-3 py-1.5 text-sm font-medium ${
                    i === 0 || i === 4
                      ? "border-gray-300 bg-white text-gray-700"
                      : "border-blue-200 bg-blue-50 text-blue-800"
                  }`}>
                    {stage}
                  </span>
                  {i < 4 && <Arrow dir="right" />}
                </div>
              ))}
            </div>

            {/* Failure modes mapped to pipeline */}
            <div className="mt-6 border-t border-gray-200 pt-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Where failures occur
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {overviewItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <a
                      key={item.id}
                      href={`#${item.id}`}
                      className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm transition-colors hover:border-gray-400"
                    >
                      <Icon size={14} strokeWidth={1.5} className="shrink-0 text-gray-400" />
                      <span className="font-medium text-gray-700">{item.title}</span>
                      <span className="ml-auto text-xs text-gray-400">{item.pipeline}</span>
                    </a>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* ═══════════════════════════════════════════
          01 — QUERY UNDERSTANDING
          ═══════════════════════════════════════════ */}
      <section id="query-understanding" className="scroll-mt-24 py-8 sm:py-12 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">01</p>
          <div className="mt-2 flex items-center gap-2">
            <MessageSquare size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Query understanding failures</h2>
          </div>

          {/* Diagram */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Parsing pipeline</p>
            <div className="mt-5 flex flex-col items-center gap-1.5">
              <Pill>red dress size 38</Pill>
              <Arrow />
              <Box>Parser</Box>
              <Arrow />
              <div className="grid grid-cols-2 gap-3">
                <Box variant="success" label="Correct">
                  [red] → color<br />[dress] → type<br />[38] → size
                </Box>
                <Box variant="danger" label="Without understanding">
                  "red dress size 38"<br />→ one text string
                </Box>
              </div>
              <Arrow />
              <div className="grid grid-cols-2 gap-3 w-full">
                <Box variant="success">Structured ranking</Box>
                <Box variant="danger">Keyword scatter</Box>
              </div>
            </div>
            <p className="mt-5 text-xs text-gray-500 text-center">
              When queries are not decomposed, attribute intent is lost at the ranking stage.
            </p>
          </div>

          <p className="mt-6 text-base leading-relaxed text-muted-foreground">
            The search system misinterprets what the user is looking for. It treats all queries as simple keyword matches, ignoring structure, intent, and context.
          </p>

          <div className="mt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Symptoms</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {[
                'Compound queries like "red running shoes size 42" split into unrelated fragments',
                "Attribute values (color, size, material) matched against descriptions instead of structured fields",
                'Synonyms incomplete — "sneakers" and "trainers" return different result sets',
                "Misspellings and regional variants return zero results",
              ].map((s) => (
                <div key={s} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                  <span className="mr-1.5 font-semibold text-red-400">—</span>{s}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why teams miss it</p>
            <p className="mt-2 text-sm text-gray-600">Teams test with queries they already know work. Real user queries are more varied, misspelled, and structurally complex than internal test cases.</p>
          </div>

          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">Impact</p>
            <p className="mt-2 text-sm text-red-700">Users searching with natural, specific queries get poor results or nothing. The highest-intent searches — closest to purchase — are most affected.</p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          02 — RANKING
          ═══════════════════════════════════════════ */}
      <section id="ranking" className="-mx-4 scroll-mt-24 bg-primary/[0.02] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">02</p>
          <div className="mt-2 flex items-center gap-2">
            <ArrowUpDown size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Ranking failures</h2>
          </div>

          {/* Diagram */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Ranking pipeline</p>
            <div className="mt-5 flex flex-col items-center gap-1.5">
              <Box>Candidate products</Box>
              <Arrow />
              <Box variant="highlight">Ranking algorithm</Box>
              <Arrow />
              <div className="w-full max-w-xs space-y-1.5">
                {[
                  { pos: "#1", label: "Promoted product (low relevance)", bad: true },
                  { pos: "#2", label: "New arrival (low conversion)",     bad: true },
                  { pos: "#3", label: "Boosted item",                     bad: true },
                  { pos: "...", label: "",                                 bad: false },
                  { pos: "#11", label: "Best-selling product ← here",     bad: false, good: true },
                ].map(({ pos, label, bad, good }) => (
                  <div key={pos} className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm ${
                    good  ? "border-emerald-200 bg-emerald-50 text-emerald-800" :
                    bad   ? "border-red-100 bg-red-50 text-red-600" :
                            "border-gray-100 text-gray-400"
                  }`}>
                    <span className="w-8 shrink-0 font-mono text-xs font-bold">{pos}</span>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>
            <p className="mt-5 text-xs text-center text-gray-500">
              The right product exists — it just never surfaces where users can find it.
            </p>
          </div>

          <p className="mt-6 text-base leading-relaxed text-muted-foreground">
            The search engine finds the right products but shows them in the wrong order. Result relevance degrades because ranking logic is misconfigured, outdated, or never validated.
          </p>

          <div className="mt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Symptoms</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {[
                "Bestselling products for a given query buried below position 10",
                "Boosting rules for promotions or new arrivals override textual relevance scores",
                "Category-level ranking weights produce inconsistent ordering across product types",
                "Result order changes after config updates, but no one evaluates the difference",
              ].map((s) => (
                <div key={s} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                  <span className="mr-1.5 font-semibold text-red-400">—</span>{s}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why teams miss it</p>
            <p className="mt-2 text-sm text-gray-600">Ranking problems are invisible in aggregate metrics. Without query-level result inspection, ranking degradation goes unnoticed.</p>
          </div>

          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">Impact</p>
            <p className="mt-2 text-sm text-red-700">The right products exist in the catalog but don't surface where they should. Users see plausible results, assume the selection is poor, and leave.</p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          03 — COVERAGE
          ═══════════════════════════════════════════ */}
      <section id="coverage" className="scroll-mt-24 py-8 sm:py-12 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">03</p>
          <div className="mt-2 flex items-center gap-2">
            <PackageSearch size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Coverage failures</h2>
          </div>

          {/* Diagram */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Catalog vs. visible results</p>
            <div className="mt-5 flex flex-col items-center gap-1.5">
              <div className="grid grid-cols-3 gap-2 w-full">
                {["Product A", "Product B", "Product C", "Product D", "Product E", "Product F"].map((p) => (
                  <div key={p} className="rounded border border-gray-200 bg-gray-50 p-2 text-center text-xs text-gray-600">{p}</div>
                ))}
              </div>
              <p className="text-xs text-gray-400">Full catalog (6 products)</p>
              <Arrow />
              <Box variant="highlight">Filtering / indexing</Box>
              <Arrow />
              <div className="grid grid-cols-3 gap-2 w-full">
                {[
                  { p: "Product A", ok: true  },
                  { p: "Product B", ok: false },
                  { p: "Product C", ok: true  },
                  { p: "Product D", ok: false },
                  { p: "Product E", ok: false },
                  { p: "Product F", ok: true  },
                ].map(({ p, ok }) => (
                  <div key={p} className={`rounded border p-2 text-center text-xs ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-red-200 bg-red-50 text-red-400 line-through"}`}>{p}</div>
                ))}
              </div>
              <p className="text-xs text-gray-400">Visible in search (3 of 6)</p>
            </div>
            <p className="mt-5 text-xs text-center text-gray-500">
              Products B, D, E exist in the catalog but never appear in results.
            </p>
          </div>

          <p className="mt-6 text-base leading-relaxed text-muted-foreground">
            Searchable queries that should return results return nothing — or return results that miss entire product segments. The catalog is there, but search doesn't reach it.
          </p>

          <div className="mt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Symptoms</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {[
                "Long-tail queries return zero results despite matching products existing in the catalog",
                "Products added recently are not indexed or indexed with incomplete attributes",
                "Filters and facets exclude valid products due to missing or inconsistent attribute data",
                "Category-specific terminology doesn't map to how users actually search",
              ].map((s) => (
                <div key={s} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                  <span className="mr-1.5 font-semibold text-red-400">—</span>{s}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why teams miss it</p>
            <p className="mt-2 text-sm text-gray-600">Zero-result rates are rarely monitored at the query level. Teams see a low overall zero-result percentage and assume coverage is fine.</p>
          </div>

          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">Impact</p>
            <p className="mt-2 text-sm text-red-700">Users with specific intent hit dead ends. No redirect, no suggestion, no signal. They leave silently, and the exit never shows up in conversion funnels.</p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          04 — EVALUATION
          ═══════════════════════════════════════════ */}
      <section id="evaluation" className="-mx-4 scroll-mt-24 bg-primary/[0.02] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">04</p>
          <div className="mt-2 flex items-center gap-2">
            <BarChart2 size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Evaluation failures</h2>
          </div>

          {/* Diagram */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Broken feedback loop</p>
            <div className="mt-5 flex flex-col items-center gap-1.5">
              <Box variant="highlight">Search change</Box>
              <Arrow />
              <Box variant="danger">Weak metrics (CTR, conversion)</Box>
              <Arrow />
              <Box variant="danger">Misleading conclusion</Box>
              <Arrow />
              <Box variant="danger">Next change based on bad signal</Box>
            </div>
            <div className="mt-5 border-t border-dashed border-gray-200 pt-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Healthy loop</p>
              <div className="mt-3 flex flex-col items-center gap-1.5">
                <Box variant="success">Search change</Box>
                <Arrow />
                <Box variant="success">Structured test set + relevance judgments</Box>
                <Arrow />
                <Box variant="success">Validated conclusion</Box>
              </div>
            </div>
          </div>

          <p className="mt-6 text-base leading-relaxed text-muted-foreground">
            There is no structured way to measure whether search is improving, degrading, or standing still. Changes are shipped without validation. Quality is assumed, not measured.
          </p>

          <div className="mt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Symptoms</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {[
                "No representative query test set exists for the catalog",
                "Relevance judged informally — someone searches a few queries and eyeballs the results",
                "Ranking changes deployed without before/after comparison",
                "Search quality metrics (nDCG, precision, recall) not tracked or not understood",
              ].map((s) => (
                <div key={s} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                  <span className="mr-1.5 font-semibold text-red-400">—</span>{s}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why teams miss it</p>
            <p className="mt-2 text-sm text-gray-600">Search evaluation requires deliberate setup: curated query sets, relevance judgments, comparison tooling. Without it, teams rely on anecdotal checks and aggregate analytics that mask individual query failures.</p>
          </div>

          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">Impact</p>
            <p className="mt-2 text-sm text-red-700">Search quality drifts in unpredictable directions. Improvements in one area silently break another. Teams lose the ability to make confident changes.</p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          05 — MERCHANDISING
          ═══════════════════════════════════════════ */}
      <section id="merchandising" className="scroll-mt-24 py-8 sm:py-12 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">05</p>
          <div className="mt-2 flex items-center gap-2">
            <Tag size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Merchandising distortions</h2>
          </div>

          {/* Diagram */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Ranking override model</p>
            <div className="mt-5 flex flex-col items-center gap-1.5">
              <div className="flex gap-4 items-end">
                <div className="flex flex-col items-center gap-1">
                  <Box variant="success">Relevance score</Box>
                  <span className="text-xs text-gray-400">from query match</span>
                </div>
                <span className="mb-3 text-gray-300 text-xl font-light">+</span>
                <div className="flex flex-col items-center gap-1">
                  <Box variant="danger">Business rules</Box>
                  <span className="text-xs text-gray-400">pins, boosts, buries</span>
                </div>
              </div>
              <Arrow />
              <Box variant="highlight">Final ranking</Box>
              <div className="w-full max-w-xs mt-2 space-y-1.5">
                {[
                  { rank: "#1", label: "Pinned promo — expired last month", bad: true },
                  { rank: "#2", label: "High-margin item (low relevance)",  bad: true },
                  { rank: "#3", label: "Most relevant product",              bad: false, good: true },
                ].map(({ rank, label, bad, good }) => (
                  <div key={rank} className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm ${
                    good ? "border-emerald-200 bg-emerald-50 text-emerald-800" :
                    bad  ? "border-red-100 bg-red-50 text-red-600" :
                           "border-gray-100 text-gray-400"
                  }`}>
                    <span className="w-8 shrink-0 font-mono text-xs font-bold">{rank}</span>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <p className="mt-6 text-base leading-relaxed text-muted-foreground">
            Manual merchandising rules — pinning, boosting, burying — accumulate over time and begin to override the relevance model. The search system serves business rules instead of user intent.
          </p>

          <div className="mt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Symptoms</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {[
                "Pinned products remain at the top long after promotions end",
                "Boosting rules for high-margin products push relevant results down",
                "Seasonal merchandising rules not removed after the season",
                "Competing rules across teams create inconsistent result behavior",
              ].map((s) => (
                <div key={s} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                  <span className="mr-1.5 font-semibold text-red-400">—</span>{s}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why teams miss it</p>
            <p className="mt-2 text-sm text-gray-600">Merchandising rules are managed by different people at different times. There is rarely a single view of all active rules, their interactions, or their cumulative effect on ranking.</p>
          </div>

          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">Impact</p>
            <p className="mt-2 text-sm text-red-700">Relevance degrades gradually. The search system becomes a manual curation tool rather than an intelligent retrieval system. Maintenance cost increases while result quality decreases.</p>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          06 — OPERATIONAL DRIFT
          ═══════════════════════════════════════════ */}
      <section id="operational-drift" className="-mx-4 scroll-mt-24 bg-primary/[0.02] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8 lg:py-20">
        <div className="mx-auto max-w-3xl">
          <p className="text-xs font-bold tabular-nums text-muted-foreground/50">06</p>
          <div className="mt-2 flex items-center gap-2">
            <Timer size={18} strokeWidth={1.5} className="shrink-0 text-gray-500" />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Operational drift</h2>
          </div>

          {/* Diagram */}
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Configuration timeline</p>
            <div className="mt-5 flex flex-col items-center gap-1.5">
              {[
                { label: "Initial configuration",  note: "Clean, intentional setup",                variant: "success"   as const },
                { label: "Rule additions",          note: "Synonyms, boosts, seasonal rules",        variant: "default"   as const },
                { label: "Manual tweaks",           note: "One-off fixes, undocumented changes",     variant: "highlight" as const },
                { label: "Platform upgrades",       note: "Behavior changes not reviewed",           variant: "danger"    as const },
                { label: "System drift",            note: "No longer matches catalog or users",      variant: "danger"    as const },
              ].map((step, i) => (
                <div key={step.label} className="flex w-full flex-col items-center">
                  <div className={`flex w-full max-w-sm flex-col items-start gap-0.5 rounded-lg border px-4 py-2.5 md:flex-row md:items-center md:justify-between ${
                    step.variant === "success"   ? "border-emerald-200 bg-emerald-50"  :
                    step.variant === "highlight" ? "border-blue-200   bg-blue-50"     :
                    step.variant === "danger"    ? "border-red-200    bg-red-50"      :
                                                   "border-gray-200   bg-gray-50"
                  }`}>
                    <span className={`text-sm font-medium ${
                      step.variant === "success"   ? "text-emerald-800" :
                      step.variant === "highlight" ? "text-blue-800"    :
                      step.variant === "danger"    ? "text-red-700"     :
                                                     "text-gray-700"
                    }`}>{step.label}</span>
                    <span className="text-xs text-gray-400">{step.note}</span>
                  </div>
                  {i < 4 && <span className="my-1 text-gray-300">↓</span>}
                </div>
              ))}
            </div>
          </div>

          <p className="mt-6 text-base leading-relaxed text-muted-foreground">
            Search configuration degrades over time because no one owns it continuously. Settings, rules, and data pipelines fall out of alignment with the current catalog and user behavior.
          </p>

          <div className="mt-8">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Symptoms</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {[
                "Synonym lists reference discontinued product lines or outdated terminology",
                "Index mappings don't reflect new product attributes added to the catalog",
                "Query rules written for a previous catalog structure produce unexpected results",
                "Search platform upgrades introduce behavior changes that aren't reviewed",
              ].map((s) => (
                <div key={s} className="rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                  <span className="mr-1.5 font-semibold text-red-400">—</span>{s}
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why teams miss it</p>
            <p className="mt-2 text-sm text-gray-600">Search is treated as infrastructure rather than a product. After initial setup, it receives attention only when something visibly breaks. Gradual degradation doesn't trigger alerts.</p>
          </div>

          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-red-500">Impact</p>
            <p className="mt-2 text-sm text-red-700">Search quality erodes slowly. Each individual change is minor, but the cumulative effect is a system that no longer matches the catalog it serves or the users it's meant to help.</p>
          </div>
        </div>
      </section>

      {/* ── Closing ── */}
      <section className="-mx-4 border-t border-border/30 bg-primary/[0.04] px-4 py-8 sm:-mx-6 sm:px-6 sm:py-12 lg:-mx-8 lg:px-8">
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
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            If you suspect any of these patterns in your own system, the{" "}
            <Link href="/search-check" className="font-medium text-foreground hover:underline">
              internal search self-assessment
            </Link>{" "}
            is a structured starting point — six checks that surface the most common failure signals in under five minutes.
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
                href="/frameworks/query-interpretation"
                className="group flex flex-col rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-gray-400"
              >
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/50">
                  Related framework
                </span>
                <span className="mt-1.5 text-sm font-medium text-foreground group-hover:underline">
                  How search engines interpret user queries
                </span>
                <span className="mt-1 text-xs text-muted-foreground">Query interpretation framework</span>
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
