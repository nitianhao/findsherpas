import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listCaseStudies } from "@/lib/content";

export const metadata: Metadata = {
  title: "Case Studies",
  description: "Real examples of on-site search improvements and outcomes.",
};

export default async function CaseStudiesIndexPage() {
  const caseStudies = await listCaseStudies();

  return (
    <div className="py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Case Studies</h1>
      <p className="mt-3 max-w-2xl text-muted-foreground">
        Examples of work, audit approaches, and outcomes.
      </p>

      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {caseStudies.map((cs) => (
          <Card key={cs.slug} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between gap-4">
                <CardTitle className="text-lg">
                  <Link
                    href={`/case-studies/${cs.slug}`}
                    className="hover:underline"
                  >
                    {cs.frontmatter.title}
                  </Link>
                </CardTitle>
                {cs.frontmatter.featured ? <Badge>Featured</Badge> : null}
              </div>
              <div className="text-xs text-muted-foreground">
                {new Date(cs.frontmatter.date).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {cs.frontmatter.excerpt}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(cs.frontmatter.stack ?? []).slice(0, 4).map((tech) => (
                  <Badge key={tech} variant="secondary">
                    {tech}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

