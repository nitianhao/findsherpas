import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { JsonLd } from "@/components/seo/json-ld";
import { ContactBand } from "@/components/site/contact-band";
import { TeardownForm } from "@/components/site/teardown-form";
import { breadcrumbSchema, createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Request a search teardown | Find Sherpas",
  description:
    "Get a private analysis of your store's search capability. We'll test your site against the same probes used in our benchmark and show you exactly where it falls short.",
  path: "/teardown",
  absoluteTitle: true,
});

export default function TeardownPage() {
  return (
    <>
      <JsonLd
        data={breadcrumbSchema([
          { name: "Home", path: "/" },
          { name: "Benchmark", path: "/benchmark" },
          { name: "Request a teardown", path: "/teardown" },
        ])}
      />

      <section className="fs-teardown-hero">
        <div className="fs-teardown-hero-copy">
          <h1>
            See exactly where
            <br />
            your search fails.
          </h1>
          <p>
            We'll run the same tests we use for our benchmark against your
            store—typos, synonyms, constraints, rankings—and show you exactly
            where shoppers hit dead ends.
          </p>
          <p className="fs-small">
            Private report. No store names published. Delivered within a few
            days.
          </p>
        </div>
        <div className="fs-teardown-hero-form">
          <TeardownForm />
        </div>
      </section>

      <section className="fs-section fs-teardown-what" aria-labelledby="what-title">
        <h2 id="what-title">What you'll get.</h2>
        <div className="fs-teardown-what-grid">
          <div>
            <h3>Search capability scores</h3>
            <p>
              How your store handles typos, synonyms, plurals, constraints,
              brand searches, and more—each scored and compared to benchmark
              averages.
            </p>
          </div>
          <div>
            <h3>Real failure examples</h3>
            <p>
              Specific queries that return zero results (or wrong results) while
              a slight variant finds products—with screenshots.
            </p>
          </div>
          <div>
            <h3>Benchmark comparison</h3>
            <p>
              How your store compares to others in your vertical. See which
              capabilities you're behind on and which you're handling well.
            </p>
          </div>
          <div>
            <h3>Actionable insights</h3>
            <p>
              What to fix first based on what actually fails—not generic advice
              but specific gaps in your search configuration.
            </p>
          </div>
        </div>
      </section>

      <section className="fs-section fs-teardown-process" aria-labelledby="process-title">
        <h2 id="process-title">How it works.</h2>
        <ol className="fs-teardown-steps">
          <li>
            <span className="fs-teardown-step-num">1</span>
            <div>
              <h3>Submit your store</h3>
              <p>
                Tell us your store URL, email, and any searches that feel wrong
                to you.
              </p>
            </div>
          </li>
          <li>
            <span className="fs-teardown-step-num">2</span>
            <div>
              <h3>We run the tests</h3>
              <p>
                Our scanner runs the full probe battery against your search:
                exact matches, typos, synonyms, constraints, and more.
              </p>
            </div>
          </li>
          <li>
            <span className="fs-teardown-step-num">3</span>
            <div>
              <h3>Review and delivery</h3>
              <p>
                We review the results, add context, and send you a private
                report with your scores and failure examples.
              </p>
            </div>
          </li>
        </ol>
      </section>

      <section className="fs-section fs-teardown-benchmark-link">
        <div className="fs-prose">
          <p>
            Want to see the kind of failures we find? Browse the{" "}
            <Link href="/benchmark">anonymised benchmark data</Link> from stores
            across verticals.
          </p>
          <Link href="/benchmark" className="fs-text-link">
            View the benchmark <ArrowUpRight size={19} aria-hidden="true" />
          </Link>
        </div>
      </section>

      <ContactBand />
    </>
  );
}
