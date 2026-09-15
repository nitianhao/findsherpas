import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { QueryInterpretation } from "@/components/site/query-interpretation";
import { SearchDemonstration } from "@/components/site/search-demonstration";
import { ContactBand } from "@/components/site/contact-band";
import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "On-site search optimization for ecommerce | Find Sherpas",
  description:
    "A boutique agency improving ecommerce search through query analysis, relevance tuning, search UX and experimentation. First fixes through ongoing optimization.",
  path: "/",
  absoluteTitle: true,
});

export default function Home() {
  return (
    <>
      <section className="fs-hero" aria-labelledby="home-title">
        <div className="fs-hero-copy">
          <h1 id="home-title">
            They know
            <br />
            what they want.
            <br />
            Does your
            <br />
            search?
          </h1>
          <p className="fs-hero-service">
            On-site search optimization
            <br />
            for ecommerce.
          </p>
          <p className="fs-hero-description">
            We improve the search inside your store—not your Google rankings.
            We turn search data into better results, from the first fixes to the
            finer details of relevance, analytics and search UX.
          </p>
          <Link href="/contact" className="fs-button">
            Discuss your search <ArrowRight size={21} aria-hidden="true" />
          </Link>
        </div>
        <QueryInterpretation />
      </section>

      <section className="fs-intro fs-section" id="what-we-do">
        <h2>A search engine is only as good as the decisions behind it.</h2>
        <div className="fs-prose">
          <p>
            Your platform can do a lot. Which data it searches, how it
            interprets a query and what it puts first depend on how it is set
            up.
          </p>
          <p>
            Find Sherpas brings those decisions together. We study what your
            customers search for, assess what happens next and give your team a
            clear order of improvements.
          </p>
          <Link href="/approach" className="fs-text-link">
            How we work <ArrowUpRight size={20} aria-hidden="true" />
          </Link>
        </div>
      </section>

      <section className="fs-engagement fs-section">
        <div className="fs-section-heading">
          <h2>
            Start with what
            <br />
            will make a difference.
          </h2>
          <p>
            Then keep going.
            <br />
            The depth of the work follows your ambition.
          </p>
        </div>
        <div className="fs-engagement-grid">
          <article className="fs-initial">
            <h3>The first few weeks</h3>
            <p>
              Share your search data and, where possible, access to your
              platform. We analyze the queries, group the patterns and assess
              your search in depth.
            </p>
            <p>
              You get a prioritized set of improvements: what to change, why it
              matters, and how to measure the result.
            </p>
            <ul>
              <li>Query analysis and a search capability audit</li>
              <li>Early fixes ranked by impact and effort</li>
              <li>Clear recommendations and engineering tickets</li>
            </ul>
          </article>
          <article className="fs-ongoing">
            <h3>The work that follows</h3>
            <p>
              Stay with us on a monthly basis to improve the details that a
              one-off review cannot settle. Each cycle builds on what the last
              one taught us.
            </p>
            <p>
              We help refine relevance, strengthen analytics, improve search UX
              and test capabilities your industry and customers actually need.
            </p>
            <ul>
              <li>Ranking refinements and A/B test plans</li>
              <li>Deeper work across languages and query types</li>
              <li>Semantic search and AI opportunities where useful</li>
            </ul>
          </article>
        </div>
        <p className="fs-engagement-note">
          Advice, detailed tickets or closer work with your team. We agree the
          scope together; your engineers own production implementation.
        </p>
      </section>

      <section className="fs-demo-section fs-section">
        <div className="fs-section-heading">
          <h2>
            Same query.
            <br />A different experience.
          </h2>
          <div className="fs-prose">
            <p>
              A matching word does not always mean a relevant product. See how a
              small misunderstanding changes the whole result set.
            </p>
            <p className="fs-small">
              These are fictional shop scenarios, illustrating the kinds of
              issues we investigate.
            </p>
          </div>
        </div>
        <SearchDemonstration />
      </section>

      <section className="fs-expertise-section fs-section">
        <div className="fs-section-heading">
          <h2>
            The whole search
            <br />
            experience, connected.
          </h2>
          <p>
            The query, the catalogue, the ranking and the interface all affect
            what a customer finds. We work across them.
          </p>
        </div>
        <div className="fs-expertise-list">
          {[
            [
              "analytics",
              "Know what the data is telling you.",
              "Query classes, reformulations, zero results and abandonment. Understand which searches deserve attention and whether the changes help.",
            ],
            [
              "relevance",
              "Put the right products first.",
              "Searchable attributes, query interpretation, synonyms, ranking rules and merchandising. Tune for different kinds of intent.",
            ],
            [
              "experience",
              "Make the next step easier.",
              "Suggestions, filters, sorting and recovery when a search goes wrong. Connect the interface to what the search engine can actually do.",
            ],
            [
              "development",
              "Find the next worthwhile improvement.",
              "Unused platform features, semantic retrieval and focused AI scripts. Test the opportunity against your catalogue and customer behavior.",
            ],
          ].map(([id, title, description]) => (
            <Link
              href={`/expertise#${id}`}
              key={id}
              className="fs-expertise-row"
            >
              <h3>{title}</h3>
              <p>{description}</p>
              <ArrowUpRight aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>

      <section className="fs-experience fs-section">
        <div>
          <h2>
            Experience at the scale
            <br />
            you are growing into.
          </h2>
          <p>
            Prior in-house search experience across businesses with
            approximately €50M, €200M and €1.2B in annual revenue, serving
            millions of customers across 25+ European countries.
          </p>
          <p className="fs-small">
            That experience comes from roles at Footshop, Dr. Max and Groupon.
          </p>
          <Link href="/about" className="fs-text-link">
            The experience behind Find Sherpas{" "}
            <ArrowUpRight size={20} aria-hidden="true" />
          </Link>
        </div>
        <div className="fs-platforms">
          <h3>Independent of your platform.</h3>
          <p>Experience with</p>
          <ul>
            <li>Elasticsearch</li>
            <li>Algolia</li>
            <li>Luigi’s Box</li>
            <li>Constructor</li>
            <li>Bloomreach Discovery</li>
            <li>Nosto</li>
            <li>Athos Commerce</li>
            <li>Coveo</li>
            <li>In-house search engines</li>
          </ul>
          <p className="fs-small">We start with the search you already have.</p>
        </div>
      </section>
      <ContactBand />
    </>
  );
}
