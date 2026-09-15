import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { ContactBand } from "@/components/site/contact-band";
import { listBlogPosts } from "@/lib/content";
import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Ecommerce search resources",
  description:
    "Practical articles, a five-minute self-assessment and diagnostic frameworks for improving ecommerce on-site search.",
  path: "/resources",
});

const frameworks = [
  {
    href: "/frameworks/search-failure-modes",
    title: "Search failure modes",
    description:
      "A systematic way to diagnose failures across interpretation, ranking, coverage, evaluation, merchandising and operations.",
  },
  {
    href: "/frameworks/query-interpretation",
    title: "Query interpretation",
    description:
      "Understand compound, attribute and ambiguous queries before trying to tune ranking around the wrong problem.",
  },
];

export default async function ResourcesPage() {
  const posts = await listBlogPosts();

  return (
    <>
      <section className="fs-page-hero">
        <h1>
          Resources for better
          <br />
          ecommerce search.
        </h1>
        <p>
          Practical articles, a quick self-assessment and diagnostic frameworks
          for teams that want to understand what their search is doing—and what
          to improve next.
        </p>
      </section>

      <section className="fs-section fs-resource-start" aria-labelledby="resource-start-title">
        <h2 id="resource-start-title">Start with a five-minute search check.</h2>
        <div className="fs-prose">
          <p>
            Run six paired probes on your own store to test exact products,
            typos, customer vocabulary, constraints, local language handling
            and mobile filtering.
          </p>
          <Link href="/search-check" className="fs-text-link">
            Use the search self-assessment <ArrowUpRight size={20} aria-hidden="true" />
          </Link>
        </div>
      </section>

      <section className="fs-section fs-resource-frameworks" aria-labelledby="frameworks-title">
        <div className="fs-section-heading">
          <h2 id="frameworks-title">Frameworks for diagnosing search.</h2>
          <p>Use these when you need to go beyond a quick check and identify where a search system is breaking down.</p>
        </div>
        <div className="fs-resource-list">
          {frameworks.map((framework) => (
            <Link key={framework.href} href={framework.href} className="fs-resource-row">
              <h3>{framework.title}</h3>
              <p>{framework.description}</p>
              <ArrowUpRight aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>

      <section className="fs-section" aria-labelledby="articles-title">
        <div className="fs-section-heading fs-resource-articles-heading">
          <h2 id="articles-title">Articles</h2>
          <Link href="/blog" className="fs-text-link">
            View all articles <ArrowUpRight size={20} aria-hidden="true" />
          </Link>
        </div>
        <div className="fs-writing-list">
          {posts.slice(0, 3).map((post) => (
            <Link key={post.slug} href={`/blog/${post.slug}`} className="fs-writing-item">
              <time dateTime={post.frontmatter.date}>
                {new Date(post.frontmatter.date).toLocaleDateString("en-GB", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  timeZone: "UTC",
                })}
              </time>
              <div>
                <h3>{post.frontmatter.title}</h3>
                <p>{post.frontmatter.excerpt}</p>
              </div>
              <ArrowUpRight aria-hidden="true" />
            </Link>
          ))}
        </div>
      </section>
      <ContactBand />
    </>
  );
}
