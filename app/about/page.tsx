import type { Metadata } from "next";

import { Badge } from "@/components/ui/badge";
import { LANGUAGES_EXCLUDED, SUPPORTED_LANGUAGES } from "@/lib/site";

export const metadata: Metadata = {
  title: "About",
  description:
    "Find Sherpas is a specialist studio focused on diagnosing and improving internal search for ecommerce and marketplaces.",
};

export default function AboutPage() {
  return (
    <div className="py-10">
      {/* 1. Headline */}
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        Focused on internal search.
      </h1>
      <p className="mt-4 max-w-2xl text-muted-foreground">
        Find Sherpas exists to improve how search works inside ecommerce sites
        and marketplaces. Not SEO. Not external search. The search bar your
        customers use to find products.
      </p>

      {/* 2. Background */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          Background in search systems
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          The work behind Find Sherpas comes from years spent inside
          large-scale search environments — catalogs with millions of products,
          multilingual query handling, complex ranking configurations, and
          search analytics pipelines built to measure what actually matters.
        </p>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          That experience shapes how we evaluate search quality: not from the
          outside, but by understanding what happens between a query and the
          results it returns.
        </p>
      </section>

      {/* 3. Search platforms */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          Vendor-agnostic expertise
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          We work across search platforms, not for them. The methodology applies
          regardless of your stack.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
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
        <p className="mt-4 text-sm text-muted-foreground">
          And others. If your search engine returns results, we can evaluate it.
        </p>
      </section>

      {/* 4. Why Find Sherpas exists */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          Why this studio exists
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Most ecommerce teams don&apos;t have a reliable way to evaluate
          whether their search is working well. Ranking issues, weak query
          understanding, and dead ends go unnoticed because search engines
          always return <em>something</em>.
        </p>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Find Sherpas exists because diagnosing search quality is a specific
          skill — one that sits between product, engineering, and data, and
          rarely gets the focused attention it needs.
        </p>
      </section>

      {/* 5. How we work */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">
          How we work with teams
        </h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          We collaborate with product and engineering teams to audit search
          quality, identify where results fail, and build a roadmap of concrete
          improvements. The deliverables are designed to be actionable by your
          team or search vendor — no ongoing dependency required.
        </p>
      </section>

      {/* 6. Languages */}
      <section className="mt-14">
        <h2 className="text-xl font-semibold tracking-tight">Languages</h2>
        <p className="mt-3 text-sm text-muted-foreground">
          Audits and query analysis conducted in all major European languages
          except {LANGUAGES_EXCLUDED.join(", ")}.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <Badge key={lang} variant="secondary">
              {lang}
            </Badge>
          ))}
        </div>
      </section>
    </div>
  );
}
