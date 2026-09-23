import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { MDXRemote } from "next-mdx-remote/rsc";

import { mdxComponents } from "@/components/mdx/mdx-components";
import { JsonLd } from "@/components/seo/json-ld";
import {
  getBlogPostBySlug,
  listBlogPosts,
} from "@/lib/content";
import {
  breadcrumbSchema,
  DEFAULT_SOCIAL_IMAGE,
  SITE_AUTHOR,
  SITE_AUTHOR_URL,
  SITE_NAME,
  SITE_URL,
} from "@/lib/seo";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getBlogPostBySlug(slug);
  if (!post) return {};

  const title = post.frontmatter.seoTitle ?? post.frontmatter.title;
  const description =
    post.frontmatter.seoDescription ?? post.frontmatter.excerpt;
  const canonical = `${SITE_URL}/blog/${slug}`;
  const socialTitle = `${title} | ${SITE_NAME}`;

  return {
    title,
    description,
    authors: [{ name: SITE_AUTHOR, url: SITE_AUTHOR_URL }],
    alternates: { canonical },
    openGraph: {
      type: "article",
      title: socialTitle,
      description,
      url: canonical,
      siteName: SITE_NAME,
      publishedTime: post.frontmatter.date,
      modifiedTime: post.frontmatter.updated ?? post.frontmatter.date,
      authors: [SITE_AUTHOR_URL],
      tags: post.frontmatter.tags,
      images: [
        {
          url: DEFAULT_SOCIAL_IMAGE,
          width: 1200,
          height: 630,
          alt: `${SITE_NAME} — ecommerce search optimization`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: socialTitle,
      description,
      images: [DEFAULT_SOCIAL_IMAGE],
    },
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getBlogPostBySlug(slug);
  if (!post) notFound();
  const canonical = `${SITE_URL}/blog/${slug}`;
  const relatedPosts = (await listBlogPosts())
    .filter((candidate) => candidate.slug !== slug)
    .slice(0, 2);

  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.frontmatter.title,
    description:
      post.frontmatter.seoDescription ?? post.frontmatter.excerpt,
    datePublished: post.frontmatter.date,
    dateModified: post.frontmatter.updated ?? post.frontmatter.date,
    mainEntityOfPage: canonical,
    image: DEFAULT_SOCIAL_IMAGE,
    keywords: post.frontmatter.tags,
    author: {
      "@type": "Person",
      name: SITE_AUTHOR,
      url: SITE_AUTHOR_URL,
    },
    publisher: {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: SITE_NAME,
    },
  };

  return (
    <article className="fs-article">
      <JsonLd data={articleSchema} />
      <JsonLd
        data={breadcrumbSchema([
          { name: "Home", path: "/" },
          { name: "Articles", path: "/blog" },
          { name: post.frontmatter.title, path: `/blog/${slug}` },
        ])}
      />
      <Link href="/blog" className="fs-back-link">
        <ArrowLeft size={18} aria-hidden="true" />
        All articles
      </Link>
      <div className="max-w-3xl">
        <div className="flex flex-wrap gap-x-2 text-xs text-muted-foreground">
          <time dateTime={post.frontmatter.date}>
            {new Date(post.frontmatter.date).toLocaleDateString("en-GB", {
              timeZone: "UTC",
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </time>
          <span aria-hidden="true">·</span>
          <span>
            By{" "}
            <Link href="/about" rel="author" className="underline underline-offset-2">
              {SITE_AUTHOR}
            </Link>
          </span>
        </div>
        <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">
          {post.frontmatter.title}
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          {post.frontmatter.excerpt}
        </p>
      </div>

      <div className="mt-10 max-w-3xl">
        {post.format === "html" ? (
          <div className="fs-article-body" dangerouslySetInnerHTML={{ __html: post.content }} />
        ) : (
          <MDXRemote source={post.content} components={mdxComponents} />
        )}
      </div>

      {relatedPosts.length > 0 ? (
        <section className="mt-14 max-w-3xl border-t border-border pt-8" aria-labelledby="related-reading">
          <h2 id="related-reading" className="text-xl font-semibold">
            Related reading
          </h2>
          <ul className="mt-4 space-y-3">
            {relatedPosts.map((related) => (
              <li key={related.slug}>
                <Link
                  href={`/blog/${related.slug}`}
                  className="font-medium underline decoration-muted-foreground/40 underline-offset-4 hover:decoration-muted-foreground"
                >
                  {related.frontmatter.title}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
