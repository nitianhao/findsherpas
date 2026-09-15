import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { JsonLd } from "@/components/seo/json-ld";
import { ContactBand } from "@/components/site/contact-band";
import { SearchCheckAssessment } from "@/components/site/search-check-assessment";
import { breadcrumbSchema, createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Five-minute ecommerce search check | Find Sherpas",
  description:
    "Run six practical probes to uncover obvious retrieval, query-understanding and search UX failures in your ecommerce site search.",
  path: "/search-check",
  absoluteTitle: true,
});

export default function SearchCheckPage() {
  return (
    <>
      <JsonLd
        data={breadcrumbSchema([
          { name: "Home", path: "/" },
          { name: "Resources", path: "/resources" },
          { name: "Five-minute search check", path: "/search-check" },
        ])}
      />

      <section className="fs-page-hero fs-check-hero">
        <h1>
          Find the search failures
          <br />a dashboard can hide.
        </h1>
        <div>
          <p>
            Six practical probes for your own store. Start with products you
            know exist, change one thing at a time, and judge what a shopper
            actually sees.
          </p>
          <p className="fs-check-duration">
            About five minutes. No setup or analytics access needed.
          </p>
        </div>
      </section>

      <section className="fs-section fs-check-setup" aria-labelledby="check-setup-title">
        <h2 id="check-setup-title">Choose a known-good starting point.</h2>
        <div className="fs-prose">
          <p>
            Pick one important product category and one in-stock product you
            can verify in the catalogue. Use examples that fit your store and
            market; the examples below only show the shape of each test.
          </p>
          <p>
            Compare every variation with the query you already know works. A
            genuine catalogue gap is not a search failure, and a different
            result count is not automatically a problem.
          </p>
        </div>
      </section>

      <SearchCheckAssessment />

      <section className="fs-section fs-check-method" aria-labelledby="check-method-title">
        <h2 id="check-method-title">
          A useful signal.
          <br />Not a complete audit.
        </h2>
        <div className="fs-prose">
          <p>
            This check is designed to expose visible dead ends quickly. It
            cannot tell you how often they happen, which catalogue segments are
            affected, or whether a fix improves the rest of your query set.
          </p>
          <p>
            A full audit repeats these probes systematically across real query
            patterns, products, languages and customer intents. It separates
            retrieval, interpretation, ranking and interface failures before
            prioritising the fixes by customer impact.
          </p>
          <div className="fs-check-reading">
            <Link href="/frameworks/query-interpretation" className="fs-text-link">
              How query interpretation fails
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>
            <Link href="/frameworks/search-failure-modes" className="fs-text-link">
              The wider diagnostic framework
              <ArrowUpRight size={19} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      <ContactBand />
    </>
  );
}
