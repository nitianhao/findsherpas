import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { listBlogPosts } from "@/lib/content";
import { ContactBand } from "@/components/site/contact-band";
import { createPageMetadata } from "@/lib/seo";

export const metadata = createPageMetadata({
  title: "Ecommerce search articles",
  description:
    "Practical articles on ecommerce search, relevance, product discovery and search UX.",
  path: "/blog",
});

export default async function BlogIndexPage() {
  const posts = await listBlogPosts();
  return (
    <>
      <section className="fs-page-hero">
        <h1>
          Articles about
          <br />
          ecommerce search.
        </h1>
        <p>
          Detailed, practical guidance on relevance, product discovery and the
          decisions that shape the on-site search experience.
        </p>
      </section>
      <section className="fs-section fs-writing-list" aria-label="Articles">
        {posts.length ? (
          posts.map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="fs-writing-item"
            >
              <time dateTime={post.frontmatter.date}>
                {new Date(post.frontmatter.date).toLocaleDateString("en-GB", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  timeZone: "UTC",
                })}
              </time>
              <div>
                <h2>{post.frontmatter.title}</h2>
                <p>{post.frontmatter.excerpt}</p>
              </div>
              <ArrowUpRight aria-hidden="true" />
            </Link>
          ))
        ) : (
          <p>New articles are on their way.</p>
        )}
      </section>
      <ContactBand />
    </>
  );
}
