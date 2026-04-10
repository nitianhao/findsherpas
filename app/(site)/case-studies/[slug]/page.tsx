import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MDXRemote } from "next-mdx-remote/rsc";

import { mdxComponents } from "@/components/mdx/mdx-components";
import { getCaseStudyBySlug, getCaseStudySlugs } from "@/lib/content";
import { Badge } from "@/components/ui/badge";

export async function generateStaticParams() {
  const slugs = await getCaseStudySlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const item = await getCaseStudyBySlug(slug);
  if (!item) return {};

  const title = item.frontmatter.seoTitle ?? item.frontmatter.title;
  const description =
    item.frontmatter.seoDescription ?? item.frontmatter.excerpt;

  return { title, description };
}

export default async function CaseStudyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const item = await getCaseStudyBySlug(slug);
  if (!item) notFound();

  return (
    <article className="py-10">
      <div className="max-w-3xl">
        <div className="text-xs text-muted-foreground">
          {new Date(item.frontmatter.date).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </div>
        <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">
          {item.frontmatter.title}
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          {item.frontmatter.excerpt}
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          {(item.frontmatter.stack ?? []).map((tech) => (
            <Badge key={tech} variant="secondary">
              {tech}
            </Badge>
          ))}
        </div>
      </div>

      <div className="mt-10 max-w-3xl">
        <MDXRemote source={item.content} components={mdxComponents} />
      </div>
    </article>
  );
}

