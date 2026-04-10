import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MDXRemote } from "next-mdx-remote/rsc";

import { mdxComponents } from "@/components/mdx/mdx-components";
import { getBlogPostBySlug, getBlogPostSlugs } from "@/lib/content";

export async function generateStaticParams() {
  const slugs = await getBlogPostSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getBlogPostBySlug(slug);
  if (!post) return {};

  const title = post.frontmatter.seoTitle ?? post.frontmatter.title;
  const description = post.frontmatter.seoDescription ?? post.frontmatter.excerpt;

  return { title, description };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getBlogPostBySlug(slug);
  if (!post) notFound();

  return (
    <article className="py-10">
      <div className="max-w-3xl">
        <div className="text-xs text-muted-foreground">
          {new Date(post.frontmatter.date).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </div>
        <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">
          {post.frontmatter.title}
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          {post.frontmatter.excerpt}
        </p>
      </div>

      <div className="mt-10 max-w-3xl">
        <MDXRemote source={post.content} components={mdxComponents} />
      </div>
    </article>
  );
}

