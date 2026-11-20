import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";

import { JsonLd } from "@/components/seo/json-ld";
import { ContactBand } from "@/components/site/contact-band";
import { BenchmarkContent } from "@/components/site/benchmark-content";
import { breadcrumbSchema, createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Search capability benchmark | Find Sherpas",
  description:
    "How ecommerce search performs across verticals and countries. Anonymous benchmark data showing where site search commonly fails—and what shoppers actually see.",
  path: "/benchmark",
  absoluteTitle: true,
});

export default function BenchmarkPage() {
  return (
    <>
      <JsonLd
        data={breadcrumbSchema([
          { name: "Home", path: "/" },
          { name: "Resources", path: "/resources" },
          { name: "Benchmark", path: "/benchmark" },
        ])}
      />

      <section className="fs-page-hero fs-benchmark-hero">
        <h1>
          How does your search
          <br />
          compare?
        </h1>
        <div>
          <p>
            Anonymous benchmark data from ecommerce stores across verticals and
            markets. See which search capabilities most sites handle well—and
            where they commonly fail.
          </p>
          <p className="fs-small">
            No store names. Only patterns that matter for your customers.
          </p>
        </div>
      </section>

      <BenchmarkContent />

      <section className="fs-section fs-benchmark-cta">
        <div className="fs-section-heading">
          <h2>
            See how your
            <br />
            store performs.
          </h2>
          <div className="fs-prose">
            <p>
              Request a private teardown of your site's search. We'll run the
              same tests and show you exactly where your search falls short—and
              how it compares to stores in your vertical.
            </p>
            <Link className="fs-button" href="/teardown">
              Request a teardown <ArrowRight size={21} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      <section className="fs-section fs-benchmark-method" aria-labelledby="method-title">
        <h2 id="method-title">How we test.</h2>
        <div className="fs-prose">
          <p>
            Each store is tested against a fixed battery of deterministic
            probes: exact product names, typos, synonyms, plurals, constraints,
            and more. We compare variant queries against control queries that
            should return results.
          </p>
          <p>
            A failure means a query that works one way returns nothing (or the
            wrong things) when asked slightly differently—the same gap a shopper
            hits when they don't phrase their search exactly right.
          </p>
          <div className="fs-benchmark-reading">
            <Link href="/frameworks/query-interpretation" className="fs-text-link">
              How query interpretation fails
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>
            <Link href="/frameworks/search-failure-modes" className="fs-text-link">
              The diagnostic framework
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      <ContactBand />
    </>
  );
}
