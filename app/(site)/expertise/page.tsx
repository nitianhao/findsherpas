import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { ContactBand } from "@/components/site/contact-band";
import { ExpertiseIllustration } from "@/components/site/expertise-pictogram";
import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Search expertise",
  description:
    "Search analytics, query understanding, relevance tuning, search UX and experimentation for ecommerce teams across European markets.",
  path: "/expertise",
});

export default function ExpertisePage() {
  return (
    <>
      <section className="fs-page-hero">
        <h1>
          Every decision
          <br />
          between a query
          <br />
          and a good result.
        </h1>
        <p>
          Search quality connects data, language, ranking and the interface. We
          look at how they work together, then focus on the part that will make
          a difference.
        </p>
      </section>
      <section className="fs-section">
        <div className="fs-detail-list">
          <section className="fs-detail-row" id="analytics">
            <div className="fs-detail-heading">
              <ExpertiseIllustration kind="analytics" />
              <h2>Search analytics</h2>
            </div>
            <div>
              <h3>Know where customers lose their way.</h3>
              <p>
                A search can return products and still fail the customer. We
                look beyond zero results: query reformulations, abandonment,
                clicks and the journey after a search.
              </p>
              <p>
                Grouping queries by intent, product category and market helps
                reveal patterns that an average hides. We also review whether
                your tracking can answer the questions your team is asking.
              </p>
              <ul>
                <li>Query classification and recurring failure patterns</li>
                <li>
                  Analytics definitions, instrumentation gaps and useful
                  segments
                </li>
                <li>Baselines and measures for evaluating a change</li>
              </ul>
            </div>
          </section>
          <section className="fs-detail-row" id="relevance">
            <div className="fs-detail-heading">
              <ExpertiseIllustration kind="relevance" />
              <h2>
                Query understanding
                <br />
                &amp; relevance
              </h2>
            </div>
            <div>
              <h3>A match should make sense.</h3>
              <p>
                “Linen shirt” should favour shirts, not every product made from
                linen. “Winter wedding” adds context that a literal match can
                miss. Those distinctions depend on both your product data and
                the way the engine uses it.
              </p>
              <p>
                We examine searchable attributes, synonyms, typo handling,
                ranking and commercial rules. We test different query types and
                languages so a change that helps one group does not quietly harm
                another.
              </p>
              <ul>
                <li>
                  Catalogue attributes, index structure and query interpretation
                </li>
                <li>Ranking, boosts, availability and merchandising rules</li>
                <li>Language differences and industry-specific vocabulary</li>
              </ul>
              <Link
                href="/frameworks/query-interpretation"
                className="fs-text-link"
              >
                Explore query interpretation{" "}
                <ArrowUpRight size={19} aria-hidden="true" />
              </Link>
            </div>
          </section>
          <section className="fs-detail-row" id="experience">
            <div className="fs-detail-heading">
              <ExpertiseIllustration kind="experience" />
              <h2>Search UX</h2>
            </div>
            <div>
              <h3>Help customers finish what they started.</h3>
              <p>
                Suggestions set expectations before the results arrive. Filters,
                sorting and product information help a customer decide whether
                the results are useful. A dead end needs a credible next step.
              </p>
              <p>
                We connect those interface decisions to the capabilities of your
                engine and the behaviour in your data. Recommendations describe
                the interaction as well as the search logic behind it.
              </p>
              <ul>
                <li>Autocomplete, suggestions and discovery</li>
                <li>Facets, sorting and the results page</li>
                <li>Recovery from zero or poor results</li>
              </ul>
            </div>
          </section>
          <section className="fs-detail-row" id="experimentation">
            <div className="fs-detail-heading">
              <ExpertiseIllustration kind="experimentation" />
              <h2>Experimentation</h2>
            </div>
            <div>
              <h3>Better by evidence, not by intuition.</h3>
              <p>
                A ranking change can look convincing in a few examples and
                behave differently across the catalogue. We help define the
                hypothesis, evaluation queries, success measures and safeguards
                before it is released.
              </p>
              <p>
                Where traffic supports it, A/B testing measures the effect in
                real use. We interpret the outcome by query class and market
                when the data allows, then use it to decide what to keep, adjust
                or investigate.
              </p>
            </div>
          </section>
          <section className="fs-detail-row" id="development">
            <div className="fs-detail-heading">
              <ExpertiseIllustration kind="development" />
              <h2>
                Semantic search
                <br />
                &amp; new capabilities
              </h2>
            </div>
            <div>
              <h3>Start with the problem a feature would solve.</h3>
              <p>
                Your existing platform may already have useful features that are
                underused. Semantic retrieval or a focused AI script may help
                with particular kinds of intent, classification or evaluation.
                The value depends on your catalogue and customers.
              </p>
              <p>
                We assess the opportunity, define a useful test and work with
                your engineers on what implementation would require. Simulated
                customer searches can help explore emerging patterns; they
                complement real query data and customer experiments.
              </p>
              <ul>
                <li>Assessment of unused platform capabilities</li>
                <li>Semantic and hybrid search opportunities</li>
                <li>AI-assisted analysis and hypothetical search scenarios</li>
              </ul>
            </div>
          </section>
        </div>
      </section>
      <section className="fs-section fs-note-section fs-intro">
        <h2>
          Built around
          <br />
          your search platform.
        </h2>
        <div className="fs-prose">
          <p>
            Our experience includes Elasticsearch, Algolia, Luigi’s Box,
            Constructor, Bloomreach Discovery, Nosto, Athos Commerce, Coveo
            and in-house search engines. We begin with what your setup can do
            and where it falls short.
          </p>
          <p>
            The work can range from recommendations and configuration guidance
            to detailed engineering tickets and ongoing collaboration.
          </p>
          <Link href="/approach" className="fs-text-link">
            See how an engagement works{" "}
            <ArrowUpRight size={19} aria-hidden="true" />
          </Link>
        </div>
      </section>
      <ContactBand />
    </>
  );
}
