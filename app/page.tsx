import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listBlogPosts, listCaseStudies } from "@/lib/content";
import { ContactForm } from "@/components/site/contact-form";

const companies = [
  "Company A",
  "Company B",
  "Company C",
  "Company D",
  "Company E",
] as const;

export default async function Home() {
  const [posts, caseStudies] = await Promise.all([
    listBlogPosts(),
    listCaseStudies(),
  ]);

  const featuredPosts = posts.filter((p) => p.frontmatter.featured).slice(0, 3);
  const featuredCaseStudies = caseStudies
    .filter((c) => c.frontmatter.featured)
    .slice(0, 3);

  return (
    <div>
      {/* ============================================================
          HERO — white background
          ============================================================ */}
      <section className="pb-10 sm:pb-16 lg:pb-24">
        <div className="relative grid gap-8 lg:grid-cols-12 lg:items-center">
          <div className="lg:col-span-8">
            <p className="text-sm font-medium text-muted-foreground">
              On-site search optimization
            </p>
            <h1 className="mt-2 text-balance text-3xl font-semibold leading-[1.15] tracking-tight sm:mt-3 sm:text-4xl sm:leading-[1.08] lg:text-5xl">
              Search users convert more.{" "}
              <span className="bg-gradient-to-r from-[oklch(0.62_0.14_200)] to-[oklch(0.62_0.14_220)] bg-clip-text text-transparent">
                Make product discovery
              </span>{" "}
              a revenue lever.
            </h1>
            <p className="mt-3 max-w-2xl text-pretty text-[15px] leading-relaxed text-muted-foreground sm:mt-5 sm:text-lg">
              This is not SEO. This is about how users find products once they
              are already on your site.
            </p>

            <ul className="mt-4 space-y-2 text-sm text-muted-foreground sm:mt-6 sm:space-y-2.5 sm:text-base">
              <li className="flex items-start gap-3">
                <span className="mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Higher conversion from better product discovery in internal search.
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Fewer sessions where relevant products exist but results miss intent.
              </li>
            </ul>

            <div className="mt-5 flex flex-col gap-2.5 sm:mt-8 sm:flex-row sm:gap-3 sm:items-center">
              <Button asChild size="lg" className="w-full sm:w-auto">
                <a href="#contact">Book a call</a>
              </Button>
              <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
                <Link href="/pricing">Get an audit</Link>
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground sm:text-sm">
              Vendor-agnostic. Designed for Heads of Product and Growth.
            </p>
          </div>

          <div className="relative hidden min-h-[180px] lg:col-span-4 lg:block" aria-hidden>
            <svg
              className="absolute -right-16 top-1/2 h-[250px] w-[360px] -translate-y-1/2 text-primary/[0.12]"
              viewBox="0 0 360 280"
              fill="none"
            >
              <defs>
                <pattern
                  id="hero-search-grid-right"
                  width="22"
                  height="22"
                  patternUnits="userSpaceOnUse"
                >
                  <path d="M22 0H0V22" stroke="currentColor" strokeWidth="1.5" />
                </pattern>
              </defs>
              <rect x="8" y="8" width="344" height="264" fill="url(#hero-search-grid-right)" />

              <path
                d="M42 192C88 166 132 171 176 150C218 131 262 132 304 114"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <circle cx="304" cy="114" r="16" stroke="currentColor" strokeWidth="1.5" />
              <path d="M315 125L329 139" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />

              <circle cx="70" cy="212" r="3" fill="currentColor" />
              <circle cx="118" cy="186" r="3" fill="currentColor" />
              <circle cx="166" cy="170" r="3" fill="currentColor" />
              <circle cx="215" cy="150" r="3" fill="currentColor" />
            </svg>
          </div>
        </div>
      </section>

      {/* ============================================================
          WHY SEARCH UNDERPERFORMS — tinted background
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-10 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-24">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Why internal search underperforms in most e-commerce
        </h2>
        <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-muted-foreground sm:mt-4 sm:text-base">
          Internal search is often under-owned and under-measured against
          business outcomes. The result is rarely one big failure, but small
          gaps that compound over time.
        </p>

        <div className="mt-6 grid gap-3 sm:mt-8 sm:gap-4 lg:mt-10 lg:grid-cols-2 lg:gap-8">
          <article className="rounded-lg bg-background p-3.5 sm:rounded-xl sm:p-5">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
                <path d="M12 4V7M12 17V20M4 12H7M17 12H20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-border/50 px-1.5 text-[11px] font-medium tracking-wide text-muted-foreground">
                01
              </span>
              <h3 className="text-sm font-semibold text-foreground sm:text-base">Results miss intent</h3>
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              Relevant products exist, but matching misses meaning.
              Ordering and query interpretation miss what shoppers actually mean.
            </p>
          </article>
          <article className="rounded-lg bg-background p-3.5 sm:rounded-xl sm:p-5">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                  d="M9.5 7.5L7 5a3 3 0 00-4 4l2.5 2.5M14.5 16.5L17 19a3 3 0 004-4l-2.5-2.5M8 16l8-8"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-border/50 px-1.5 text-[11px] font-medium tracking-wide text-muted-foreground">
                02
              </span>
              <h3 className="text-sm font-semibold text-foreground sm:text-base">Search is owned by no one</h3>
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              The journey is split across teams.
              Separate ownership makes cross-functional gaps hard to see.
            </p>
          </article>
          <article className="rounded-lg bg-background p-3.5 sm:rounded-xl sm:p-5">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M4 19h16M7 15v4M12 11v8M17 7v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-border/50 px-1.5 text-[11px] font-medium tracking-wide text-muted-foreground">
                03
              </span>
              <h3 className="text-sm font-semibold text-foreground sm:text-base">Measured by usage, not impact</h3>
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              Activity is tracked, outcomes are not.
              Usage is visible, but conversion and revenue contribution are not.
            </p>
          </article>
          <article className="rounded-lg bg-background p-3.5 sm:rounded-xl sm:p-5">
            <div className="flex items-center gap-2">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M20 12a8 8 0 10-2.3 5.7M20 12v-4M20 12h-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-border/50 px-1.5 text-[11px] font-medium tracking-wide text-muted-foreground">
                04
              </span>
              <h3 className="text-sm font-semibold text-foreground sm:text-base">Relevance is never revisited</h3>
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              Tuning happens once, then stalls.
              Catalog and intent evolve, but relevance is rarely re-evaluated.
            </p>
          </article>
        </div>

        <p className="mt-6 text-sm text-muted-foreground sm:mt-8">
          These are common patterns, and they are exactly the signals we
          evaluate in an audit.
        </p>
      </section>

      {/* ============================================================
          WHAT WE AUDIT — white background
          ============================================================ */}
      <section className="py-10 sm:py-16 lg:py-24">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          What we audit
        </h2>
        <p className="mt-2 text-sm text-muted-foreground sm:mt-3 sm:text-base">
          Three angles. One goal: higher conversion from search.
        </p>

        <div className="mt-6 grid gap-4 sm:mt-8 sm:gap-6 lg:mt-10 lg:grid-cols-3">
          <article className="flex h-full flex-col rounded-lg p-4 sm:rounded-xl sm:border sm:border-border/50 sm:p-6">
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M3 5h18M3 12h12M3 19h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <circle cx="18" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
              </svg>
              <h3 className="text-base font-semibold sm:text-lg">Search UX Audit</h3>
            </div>
            <p className="mt-2 text-sm text-muted-foreground sm:mt-3">
              Improves product discovery flow and on-site search usability.
            </p>
            <ul className="mt-4 space-y-2.5 sm:mt-5 sm:space-y-3">
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 6h16M4 12h10M4 18h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">Autocomplete</p>
                  <p className="text-xs text-muted-foreground">Query suggestions and zero-state behavior.</p>
                </div>
              </li>
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M4 10h16M10 10v9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">SERP structure</p>
                  <p className="text-xs text-muted-foreground">Layout, filters, and sorting clarity.</p>
                </div>
              </li>
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M12 3v11M12 18h.01M4.9 19h14.2c1 0 1.6-1.1 1-2l-7.1-12.2a1.2 1.2 0 00-2 0L3.9 17c-.6.9 0 2 1 2z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">No-results fallback</p>
                  <p className="text-xs text-muted-foreground">Recovery paths when queries fail.</p>
                </div>
              </li>
            </ul>
            <Link href="/services" className="mt-auto pt-5 text-sm font-medium text-primary hover:underline sm:pt-6">
              View audit scope &rarr;
            </Link>
          </article>

          {/* Mobile divider */}
          <div className="border-t border-border/30 sm:hidden" aria-hidden />

          <article className="flex h-full flex-col rounded-lg p-4 sm:rounded-xl sm:border sm:border-border/50 sm:p-6">
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.5" />
                <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <h3 className="text-base font-semibold sm:text-lg">Search Logic / Relevance Audit</h3>
            </div>
            <p className="mt-2 text-sm text-muted-foreground sm:mt-3">
              Improves ranking quality and alignment between query intent and results.
            </p>
            <ul className="mt-4 space-y-2.5 sm:mt-5 sm:space-y-3">
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 8h9M4 16h16M13 8h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <circle cx="11" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">Normalization</p>
                  <p className="text-xs text-muted-foreground">Synonyms and query handling quality.</p>
                </div>
              </li>
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M6 4v16M12 7v13M18 10v10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">Weighting rules</p>
                  <p className="text-xs text-muted-foreground">Business rules and ranking interactions.</p>
                </div>
              </li>
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M12 8v4l3 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">Evaluation loop</p>
                  <p className="text-xs text-muted-foreground">Offline checks plus live experiments.</p>
                </div>
              </li>
            </ul>
            <Link href="/services" className="mt-auto pt-5 text-sm font-medium text-primary hover:underline sm:pt-6">
              View audit scope &rarr;
            </Link>
          </article>

          {/* Mobile divider */}
          <div className="border-t border-border/30 sm:hidden" aria-hidden />

          <article className="flex h-full flex-col rounded-lg p-4 sm:rounded-xl sm:border sm:border-border/50 sm:p-6">
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M4 19h16M7 15v4M12 10v9M17 7v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <h3 className="text-base font-semibold sm:text-lg">Search Analytics Audit</h3>
            </div>
            <p className="mt-2 text-sm text-muted-foreground sm:mt-3">
              Improves visibility and faster, better decision-making from search data.
            </p>
            <ul className="mt-4 space-y-2.5 sm:mt-5 sm:space-y-3">
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 19h16M7 15v4M12 10v9M17 7v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">Coverage gaps</p>
                  <p className="text-xs text-muted-foreground">No-result and no-click reporting.</p>
                </div>
              </li>
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 5h16l-6 7v6l-4 2v-8L4 5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">Funnel visibility</p>
                  <p className="text-xs text-muted-foreground">Search-to-conversion step performance.</p>
                </div>
              </li>
              <li className="flex items-start gap-2.5">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 6h16M4 12h10M4 18h13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-sm font-semibold">KPI framework</p>
                  <p className="text-xs text-muted-foreground">Dashboards and recurring decision metrics.</p>
                </div>
              </li>
            </ul>
            <Link href="/services" className="mt-auto pt-5 text-sm font-medium text-primary hover:underline sm:pt-6">
              View audit scope &rarr;
            </Link>
          </article>
        </div>
      </section>

      {/* ============================================================
          SOCIAL PROOF — tinted background
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-10 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-24">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Trusted by teams at
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2 sm:mt-5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-5">
          {companies.map((c) => (
            <div
              key={c}
              className="grid h-11 place-items-center rounded-lg bg-background text-sm text-muted-foreground sm:h-12"
            >
              {c}
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-3 sm:mt-14 sm:gap-6 lg:grid-cols-3">
          <div className="rounded-lg bg-background p-4 sm:rounded-xl sm:p-6">
            <h3 className="text-base font-semibold sm:text-lg">UX audit &amp; optimization</h3>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              Find friction in query-to-product journeys, SERP layout, filters,
              sorting, and zero-results paths. Leave with a prioritized roadmap.
            </p>
          </div>
          <div className="rounded-lg bg-background p-4 sm:rounded-xl sm:p-6">
            <h3 className="text-base font-semibold sm:text-lg">
              Relevance audit &amp; optimization
            </h3>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              Tune ranking, synonyms, facets, and merchandising rules. Improve
              findability across head and long-tail queries.
            </p>
          </div>
          <div className="rounded-lg bg-background p-4 sm:rounded-xl sm:p-6">
            <h3 className="text-base font-semibold sm:text-lg">
              Search analytics audit &amp; design
            </h3>
            <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
              Make search measurable with clean events, funnels, dashboards, and a
              KPI framework your team can iterate on.
            </p>
          </div>
        </div>
      </section>

      {/* ============================================================
          PRICING — white background
          ============================================================ */}
      <section className="py-10 sm:py-16 lg:py-24">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Ways to work with us</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:mt-3 sm:text-base">
          Most teams start with a focused audit to identify the clearest revenue opportunities in search.
          Money-back guarantee included.
        </p>

        <div className="mt-6 grid gap-4 sm:mt-8 sm:gap-6 lg:mt-10 lg:grid-cols-3">
          <Card className="flex h-full flex-col border-border/50">
            <CardHeader className="space-y-2 p-4 pb-2 sm:space-y-3 sm:p-6 sm:pb-3">
              <CardTitle className="text-base sm:text-lg">Search UX Audit</CardTitle>
              <p className="text-sm text-muted-foreground">
                Best if search feels clunky, confusing, or leaky.
              </p>
              <p className="text-sm text-foreground">
                Clarifies where product discovery breaks and where usability fixes lift conversion.
              </p>
              <div className="pt-1 text-lg font-semibold">
                From &euro;990
              </div>
            </CardHeader>
            <CardContent className="flex h-full flex-col p-4 pt-2 sm:p-6 sm:pt-3">
              <ul className="space-y-2 text-sm text-muted-foreground sm:space-y-2.5">
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  UX diagnostic report
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Prioritized issues and quick wins
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Experiment ideas and success metrics
                </li>
              </ul>
              <p className="mt-3 text-sm text-muted-foreground sm:mt-4">
                Typical next step: prioritize 2-3 fixes and validate impact.
              </p>
              <div className="mt-auto pt-4 sm:pt-6">
                <p className="mb-2 text-xs text-muted-foreground sm:mb-3">
                  Typical investment: low four figures
                </p>
                <Button asChild variant="outline" className="w-full">
                  <a href="#contact">Get this audit</a>
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="flex h-full flex-col border-2 border-primary/50 lg:scale-[1.02]">
            <CardHeader className="space-y-2 p-4 pb-2 sm:space-y-3 sm:p-6 sm:pb-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                <CardTitle className="text-base sm:text-lg">Search Relevance Audit</CardTitle>
                <Badge className="w-fit bg-primary text-primary-foreground text-xs">
                  Most common starting point
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                Best if products exist, but search results do not make sense.
              </p>
              <p className="text-sm text-foreground">
                Identifies why ranking misses intent and where relevance improvements create measurable ROI.
              </p>
              <div className="pt-1 text-lg font-semibold">
                From &euro;2,490
              </div>
            </CardHeader>
            <CardContent className="flex h-full flex-col p-4 pt-2 sm:p-6 sm:pt-3">
              <ul className="space-y-2 text-sm text-muted-foreground sm:space-y-2.5">
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Query and relevance audit
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Weighting and rule evaluation
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Testing and iteration plan
                </li>
              </ul>
              <p className="mt-3 text-sm text-muted-foreground sm:mt-4">
                Typical next step: run a relevance sprint and measure conversion lift.
              </p>
              <div className="mt-auto pt-4 sm:pt-6">
                <p className="mb-2 text-xs text-muted-foreground sm:mb-3">
                  Typical investment: mid four figures
                </p>
                <Button asChild className="w-full">
                  <a href="#contact">Start here</a>
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="flex h-full flex-col border-border/50">
            <CardHeader className="space-y-2 p-4 pb-2 sm:space-y-3 sm:p-6 sm:pb-3">
              <CardTitle className="text-base sm:text-lg">End-to-end Search Audit</CardTitle>
              <p className="text-sm text-muted-foreground">
                Best for teams that want a full search reset.
              </p>
              <p className="text-sm text-foreground">
                Combines UX, relevance, and analytics into one complete diagnostic baseline.
              </p>
              <div className="pt-1 text-lg font-semibold">
                Custom
              </div>
            </CardHeader>
            <CardContent className="flex h-full flex-col p-4 pt-2 sm:p-6 sm:pt-3">
              <ul className="space-y-2 text-sm text-muted-foreground sm:space-y-2.5">
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Everything from UX and relevance audits
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Analytics and measurement framework
                </li>
                <li className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                  Executive summary and roadmap
                </li>
              </ul>
              <p className="mt-3 text-sm text-muted-foreground sm:mt-4">
                Typical next step: align teams around one roadmap and ownership model.
              </p>
              <div className="mt-auto pt-4 sm:pt-6">
                <p className="mb-2 text-xs text-muted-foreground sm:mb-3">Custom scope</p>
                <Button asChild variant="outline" className="w-full">
                  <a href="#contact">Talk to us</a>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trust claims */}
        <div className="mt-8 grid gap-4 sm:mt-10 sm:grid-cols-3 sm:gap-6">
          <div className="flex items-start gap-3">
            <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M4 12h16M12 4v16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <div>
              <p className="text-sm font-semibold">Vendor-agnostic</p>
              <p className="text-xs text-muted-foreground">Built for your existing search stack.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M12 3l7 3v6c0 4.5-2.7 7.4-7 9-4.3-1.6-7-4.5-7-9V6l7-3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
            <div>
              <p className="text-sm font-semibold">Money-back guarantee</p>
              <p className="text-xs text-muted-foreground">Low-risk start with clear accountability.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="M4 19h16M7 15v4M12 10v9M17 7v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <div>
              <p className="text-sm font-semibold">Actionable roadmap</p>
              <p className="text-xs text-muted-foreground">Prioritized next steps for your team.</p>
            </div>
          </div>
        </div>

        {/* Credibility strip */}
        <div className="mt-8 flex flex-col gap-6 border-t border-border/50 pt-8 sm:mt-12 sm:flex-row sm:items-start sm:gap-12 sm:pt-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Languages</p>
            <div className="mt-3 flex flex-wrap gap-1.5 sm:gap-2">
              {[
                { flag: "\ud83c\uddec\ud83c\udde7", label: "English" },
                { flag: "\ud83c\udde9\ud83c\uddea", label: "German" },
                { flag: "\ud83c\uddeb\ud83c\uddf7", label: "French" },
                { flag: "\ud83c\uddea\ud83c\uddf8", label: "Spanish" },
                { flag: "\ud83c\uddee\ud83c\uddf9", label: "Italian" },
                { flag: "\ud83c\uddf3\ud83c\uddf1", label: "Dutch" },
                { flag: "\ud83c\uddf8\ud83c\uddea", label: "Swedish" },
              ].map(({ flag, label }) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1 rounded-full border border-border/50 px-2 py-0.5 text-xs text-muted-foreground sm:gap-1.5 sm:px-2.5 sm:py-1"
                >
                  <span aria-hidden>{flag}</span>
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Works with</p>
            <div className="mt-3 flex flex-wrap items-center gap-3 sm:gap-5">
              <span className="inline-flex items-center gap-1.5">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="text-sm font-semibold tracking-tight text-muted-foreground">Algolia</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M10 4l-6 8 6 8M14 4l6 8-6 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="text-sm font-semibold tracking-tight text-muted-foreground">Elasticsearch</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <rect x="4" y="4" width="16" height="16" rx="3" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M9 12h6M12 9v6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="text-sm font-semibold tracking-tight text-muted-foreground">Luigi&apos;s Box</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <svg className="h-4 w-4 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M15 9l-6 6M9 9l6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="text-sm font-semibold tracking-tight text-muted-foreground">Doofinder</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================
          WHAT TEAMS GET — tinted background
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.04] px-4 py-10 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-24">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          What teams get from an audit
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:mt-3 sm:text-base">
          A clear diagnosis, prioritized opportunities, and an experiment plan your team can execute with confidence.
        </p>

        <div className="mt-6 grid gap-8 sm:mt-8 lg:mt-10 lg:grid-cols-12 lg:items-start">
          <div className="rounded-lg bg-background p-5 sm:rounded-xl sm:p-8 lg:col-span-7">
            <h3 className="text-base font-semibold sm:text-lg">Sample audit report</h3>
            <ul className="mt-4 space-y-3 text-sm sm:mt-6 sm:space-y-4">
              <li className="flex items-start gap-3">
                <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 6h16M4 12h12M4 18h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="font-semibold">Executive summary</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 19h16M7 15v4M12 11v8M17 7v12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="font-semibold">Revenue opportunities</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M4 10h16" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <span className="font-semibold">Evidence and examples</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="mt-0.5 h-5 w-5 shrink-0 text-primary" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path d="M4 6h16M4 12h10M4 18h7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="font-semibold">Prioritized roadmap</span>
              </li>
            </ul>

            <div className="mt-6 flex flex-col items-stretch gap-3 sm:mt-8 sm:flex-row sm:items-start">
              <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
                <Link href="/sample-report">View sample report</Link>
              </Button>
              <Link href="#contact" className="inline-flex items-center justify-center py-2 text-sm font-medium text-primary hover:underline sm:py-0">
                Book a call &rarr;
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5">
            <h3 className="text-base font-semibold sm:text-lg">Recent patterns we fix</h3>

            <div className="mt-4 space-y-5 sm:mt-6 sm:space-y-6">
              <div>
                <div className="text-sm font-semibold">Results miss intent on top queries</div>
                <div className="mt-2 grid grid-cols-3 gap-2 sm:mt-3 sm:gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Issue</div>
                    <div className="mt-0.5 text-sm sm:mt-1">Intent mismatch</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Change</div>
                    <div className="mt-0.5 text-sm sm:mt-1">Ranking aligned</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Metric</div>
                    <div className="mt-0.5 text-sm font-semibold text-primary sm:mt-1">Search CVR</div>
                  </div>
                </div>
              </div>

              <div className="border-t border-border/50 pt-5 sm:pt-6">
                <div className="text-sm font-semibold">No-click sessions hide decision friction</div>
                <div className="mt-2 grid grid-cols-3 gap-2 sm:mt-3 sm:gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Issue</div>
                    <div className="mt-0.5 text-sm sm:mt-1">Low result clicks</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Change</div>
                    <div className="mt-0.5 text-sm sm:mt-1">SERP clarity</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Metric</div>
                    <div className="mt-0.5 text-sm font-semibold text-primary sm:mt-1">No-click rate</div>
                  </div>
                </div>
              </div>

              <div className="border-t border-border/50 pt-5 sm:pt-6">
                <div className="text-sm font-semibold">Search assists were not being measured</div>
                <div className="mt-2 grid grid-cols-3 gap-2 sm:mt-3 sm:gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Issue</div>
                    <div className="mt-0.5 text-sm sm:mt-1">Impact hidden</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Change</div>
                    <div className="mt-0.5 text-sm sm:mt-1">Event mapping</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">Metric</div>
                    <div className="mt-0.5 text-sm font-semibold text-primary sm:mt-1">Assisted revenue</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <p className="mt-8 text-sm text-muted-foreground sm:mt-10">
          If you share 20-50 top queries and analytics access, we can usually identify the biggest opportunities quickly.
        </p>
      </section>

      {/* ============================================================
          CASE STUDIES + ARTICLES — white background
          ============================================================ */}
      <section className="py-10 sm:py-16 lg:py-24">
        <div className="grid gap-12 sm:gap-16 lg:grid-cols-12 lg:items-start">
          <div className="lg:col-span-7">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Case studies</h2>
            <p className="mt-2 text-sm text-muted-foreground sm:mt-3 sm:text-base">
              Real search problems. Measurable commercial impact.
            </p>

            <div className="mt-6 divide-y divide-border/50 sm:mt-8">
              <article className="pb-5 sm:pb-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:gap-4 sm:items-start">
                  <div className="h-16 w-16 shrink-0 rounded-lg border border-border/50 p-2 sm:h-24 sm:w-24 sm:p-2.5">
                    <svg viewBox="0 0 100 100" className="h-full w-full" fill="none" aria-hidden>
                      <rect x="8" y="10" width="54" height="14" rx="5" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M64 17H78" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" />
                      <path d="M80 17l-4-3v6l4-3z" fill="currentColor" className="text-primary" />
                      <rect x="12" y="36" width="72" height="9" rx="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <rect x="12" y="50" width="72" height="9" rx="3" stroke="currentColor" className="text-primary" strokeWidth="1.5" />
                      <rect x="12" y="64" width="72" height="9" rx="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                    </svg>
                  </div>
                  <div>
                    <Link
                      href={featuredCaseStudies[0] ? `/case-studies/${featuredCaseStudies[0].slug}` : "/case-studies"}
                      className="text-base font-semibold leading-snug tracking-tight hover:text-primary sm:text-lg"
                    >
                      Fixing high-intent queries that didn&apos;t convert
                    </Link>
                    <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
                      Mid-sized e-commerce with strong demand but weak search relevance.
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      +18% Search CVR on top revenue queries.
                    </p>
                    <p className="mt-1.5 text-xs text-muted-foreground sm:mt-2">Relevance &middot; Search analytics</p>
                  </div>
                </div>
              </article>

              <article className="py-5 sm:py-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:gap-4 sm:items-start">
                  <div className="h-16 w-16 shrink-0 rounded-lg border border-border/50 p-2 sm:h-24 sm:w-24 sm:p-2.5">
                    <svg viewBox="0 0 100 100" className="h-full w-full" fill="none" aria-hidden>
                      <rect x="8" y="10" width="54" height="14" rx="5" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M14 38h30" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <circle cx="50" cy="38" r="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M56 38h16" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" />
                      <path d="M74 38l-4-3v6l4-3z" fill="currentColor" className="text-primary" />
                      <rect x="10" y="52" width="17" height="17" rx="3" stroke="currentColor" className="text-primary" strokeWidth="1.5" />
                      <rect x="31" y="52" width="17" height="17" rx="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <rect x="52" y="52" width="17" height="17" rx="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                    </svg>
                  </div>
                  <div>
                    <Link
                      href={featuredCaseStudies[1] ? `/case-studies/${featuredCaseStudies[1].slug}` : "/case-studies"}
                      className="text-base font-semibold leading-snug tracking-tight hover:text-primary sm:text-lg"
                    >
                      Reducing zero-results without increasing noise
                    </Link>
                    <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
                      Large catalog with frequent long-tail and multilingual queries.
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      -42% zero-result searches in 6 weeks.
                    </p>
                    <p className="mt-1.5 text-xs text-muted-foreground sm:mt-2">UX &middot; Query handling</p>
                  </div>
                </div>
              </article>

              <article className="pt-5 sm:pt-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:gap-4 sm:items-start">
                  <div className="h-16 w-16 shrink-0 rounded-lg border border-border/50 p-2 sm:h-24 sm:w-24 sm:p-2.5">
                    <svg viewBox="0 0 100 100" className="h-full w-full" fill="none" aria-hidden>
                      <path d="M12 72h76" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M22 62V72M40 50V72M58 38V72M76 28V72" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" strokeLinecap="round" />
                      <circle cx="76" cy="28" r="4.5" stroke="currentColor" className="text-primary" strokeWidth="1.5" />
                      <path d="M22 62l18-12 18-12 18-10" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div>
                    <Link
                      href={featuredCaseStudies[2] ? `/case-studies/${featuredCaseStudies[2].slug}` : "/case-studies"}
                      className="text-base font-semibold leading-snug tracking-tight hover:text-primary sm:text-lg"
                    >
                      Turning search from a black box into a growth channel
                    </Link>
                    <p className="mt-1.5 text-sm text-muted-foreground sm:mt-2">
                      Product team lacked visibility into search impact.
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      Search-assisted revenue made visible and measurable.
                    </p>
                    <p className="mt-1.5 text-xs text-muted-foreground sm:mt-2">Analytics &middot; Measurement</p>
                  </div>
                </div>
              </article>
            </div>

            <Link
              href="/case-studies"
              className="mt-6 inline-flex text-sm font-medium text-primary hover:underline sm:mt-8"
            >
              View all case studies &rarr;
            </Link>
          </div>

          <div className="lg:col-span-5">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Articles</h2>
            <p className="mt-2 max-w-md text-sm text-muted-foreground sm:mt-3">
              Practical writing on on-site search - no SEO fluff, no tool bias.
            </p>

            <div className="mt-6 divide-y divide-border/50 sm:mt-8">
              <article className="pb-4 sm:pb-5">
                <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-3 sm:items-start">
                  <div className="h-12 w-12 shrink-0 rounded-lg border border-border/50 p-1.5 sm:h-14 sm:w-14 sm:p-2">
                    <svg viewBox="0 0 100 100" className="h-full w-full" fill="none" aria-hidden>
                      <rect x="10" y="18" width="24" height="18" rx="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <rect x="66" y="18" width="24" height="18" rx="3" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <rect x="38" y="62" width="24" height="18" rx="3" stroke="currentColor" className="text-primary" strokeWidth="1.5" />
                      <path d="M34 27h32M50 36v24M62 71h4" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div>
                    <Link
                      href={featuredPosts[0] ? `/blog/${featuredPosts[0].slug}` : "/blog"}
                      className="text-sm font-semibold leading-snug hover:text-primary sm:text-base"
                    >
                      Why most search relevance tuning never ships
                    </Link>
                    <p className="mt-1 text-sm text-muted-foreground sm:mt-2">
                      The organizational and measurement gaps that quietly kill impact.
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground sm:mt-2">Deep dive &middot; 9 min read</p>
                  </div>
                </div>
              </article>

              <article className="py-4 sm:py-5">
                <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-3 sm:items-start">
                  <div className="h-12 w-12 shrink-0 rounded-lg border border-border/50 p-1.5 sm:h-14 sm:w-14 sm:p-2">
                    <svg viewBox="0 0 100 100" className="h-full w-full" fill="none" aria-hidden>
                      <rect x="10" y="16" width="80" height="66" rx="6" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M10 38h80M34 38v44" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M20 49h8M20 58h8M20 67h8M42 50h38M42 66h26" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div>
                    <Link
                      href={featuredPosts[1] ? `/blog/${featuredPosts[1].slug}` : "/blog"}
                      className="text-sm font-semibold leading-snug hover:text-primary sm:text-base"
                    >
                      Search UX is not a UI problem
                    </Link>
                    <p className="mt-1 text-sm text-muted-foreground sm:mt-2">
                      Why filters, sorting, and SERPs fail without intent clarity.
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground sm:mt-2">Framework &middot; 7 min read</p>
                  </div>
                </div>
              </article>

              <article className="pt-4 sm:pt-5">
                <div className="flex flex-col gap-2.5 sm:flex-row sm:gap-3 sm:items-start">
                  <div className="h-12 w-12 shrink-0 rounded-lg border border-border/50 p-1.5 sm:h-14 sm:w-14 sm:p-2">
                    <svg viewBox="0 0 100 100" className="h-full w-full" fill="none" aria-hidden>
                      <path d="M12 84h76" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" />
                      <path d="M20 72V84M36 62V84M52 48V84M68 40V84" stroke="currentColor" className="text-muted-foreground" strokeWidth="1.5" strokeLinecap="round" />
                      <path d="M20 72l16-10 16-14 16-8" stroke="currentColor" className="text-primary" strokeWidth="1.5" strokeLinecap="round" />
                      <circle cx="68" cy="40" r="3.5" stroke="currentColor" className="text-primary" strokeWidth="1.5" />
                    </svg>
                  </div>
                  <div>
                    <Link
                      href={featuredPosts[2] ? `/blog/${featuredPosts[2].slug}` : "/blog"}
                      className="text-sm font-semibold leading-snug hover:text-primary sm:text-base"
                    >
                      No-result searches are not the real problem
                    </Link>
                    <p className="mt-1 text-sm text-muted-foreground sm:mt-2">
                      What no-click and assisted revenue metrics reveal instead.
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground sm:mt-2">Analytics &middot; 6 min read</p>
                  </div>
                </div>
              </article>
            </div>

            <Link
              href="/blog"
              className="mt-6 inline-flex text-sm font-medium text-primary hover:underline sm:mt-8"
            >
              Read the blog &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* ============================================================
          CONTACT — tinted background
          ============================================================ */}
      <section className="-mx-4 bg-primary/[0.04] px-4 pb-16 pt-10 sm:-mx-6 sm:px-6 sm:py-16 lg:-mx-8 lg:px-8 lg:py-24" id="contact">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Let&apos;s talk about your search
          </h2>
          <p className="mt-2 text-sm text-muted-foreground sm:mt-3 sm:text-base">
            Tell us what you&apos;re working on and we&apos;ll suggest the
            smallest audit that gets you to a clear next step.
          </p>
        </div>
        <div className="mt-6 max-w-2xl sm:mt-8">
          <ContactForm />
        </div>
        <p className="mt-4 max-w-2xl text-xs text-muted-foreground">
          No spam. Reply within 1&ndash;2 business days.
        </p>
      </section>
    </div>
  );
}
