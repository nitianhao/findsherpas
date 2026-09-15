import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { MDXRemote } from "next-mdx-remote/rsc";
import { ArrowUpRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { mdxComponents } from "@/components/mdx/mdx-components";
import { getCaseStudyBySlug, getCaseStudySlugs } from "@/lib/content";

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
  const study = await getCaseStudyBySlug(slug);
  if (!study) return {};

  const title = study.frontmatter.seoTitle ?? study.frontmatter.title;
  const description = study.frontmatter.seoDescription ?? study.frontmatter.excerpt;

  return {
    title,
    description,
    alternates: { canonical: `https://findsherpas.com/case-studies/${slug}` },
  };
}

export default async function CaseStudyPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const study = await getCaseStudyBySlug(slug);
  if (!study) notFound();

  const { client, industry, problem, approach, outcome, stack, reportUrl, date } =
    study.frontmatter;

  const summaryItems = [
    { label: "Problem", value: problem },
    { label: "Approach", value: approach },
    { label: "Outcome", value: outcome },
  ].filter((item): item is { label: string; value: string } => Boolean(item.value));

  return (
    <article className="py-10">
      <div className="max-w-3xl">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
          {industry ? <span>{industry}</span> : null}
          {industry ? <span aria-hidden>&middot;</span> : null}
          <span>
            {new Date(date).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </span>
          {client ? <span aria-hidden>&middot;</span> : null}
          {client ? <span>{client}</span> : null}
        </div>
        <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">
          {study.frontmatter.title}
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          {study.frontmatter.excerpt}
        </p>

        {stack && stack.length > 0 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {stack.map((tech) => (
              <Badge key={tech} variant="secondary">
                {tech}
              </Badge>
            ))}
          </div>
        ) : null}

        {reportUrl ? (
          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-foreground underline underline-offset-4 decoration-muted-foreground/40 hover:decoration-muted-foreground"
          >
            View full report
            <ArrowUpRight size={14} strokeWidth={2} aria-hidden />
          </a>
        ) : null}
      </div>

      {summaryItems.length > 0 ? (
        <div className="mt-10 grid max-w-3xl gap-6 rounded-xl border bg-card p-6 sm:grid-cols-3">
          {summaryItems.map((item) => (
            <div key={item.label}>
              <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                {item.label}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{item.value}</p>
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-10 max-w-3xl">
        <MDXRemote source={study.content} components={mdxComponents} />
      </div>

      <div className="mt-12 max-w-3xl border-t pt-6">
        <Link
          href="/case-studies"
          className="text-sm text-muted-foreground underline underline-offset-4 decoration-muted-foreground/40 hover:decoration-muted-foreground"
        >
          ← All case studies
        </Link>
      </div>
    </article>
  );
}
