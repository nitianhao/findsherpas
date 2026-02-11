import type { Metadata } from "next";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export const metadata: Metadata = {
  title: "Services",
  description:
    "UX audits, relevance audits, and search analytics design—focused on on-site search optimization (not SEO).",
};

const technologies = ["Elasticsearch", "Algolia", "Luigi’s Box", "Doofinder"] as const;

export default function ServicesPage() {
  return (
    <div className="py-10">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            On-site search optimization services
          </p>
          <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight">
            Services
          </h1>
          <p className="mt-3 max-w-2xl text-pretty text-muted-foreground">
            This is not SEO. We focus on the moment a user is already on your
            site and uses search—then we improve UX, relevance, and analytics so
            search becomes reliable.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild>
            <Link href="/pricing">See pricing</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/#contact">Contact</Link>
          </Button>
        </div>
      </div>

      <Separator className="my-12" />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">UX audit & optimization</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p>
              Identify friction in the query-to-result journey and fix the
              interaction patterns that cause drop-off.
            </p>
            <ul className="ml-5 list-disc space-y-2">
              <li>SERP layout + result presentation</li>
              <li>Filters, sorting, and refinements</li>
              <li>Zero-results and no-click behavior</li>
              <li>Mobile search UX</li>
            </ul>
            <p className="text-xs">
              Output: prioritized issue list + quick wins + experiment ideas.
            </p>
          </CardContent>
        </Card>

        <Card className="border-foreground/30">
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle className="text-lg">Relevance audit & optimization</CardTitle>
              <Badge>Most requested</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p>
              Improve ranking quality so users get the right results for both
              head queries and the long tail.
            </p>
            <ul className="ml-5 list-disc space-y-2">
              <li>Synonyms, facets, and query handling</li>
              <li>Ranking signals and boosting strategy</li>
              <li>Merch rules (when and how to use them)</li>
              <li>Coverage gaps + long-tail discovery</li>
            </ul>
            <p className="text-xs">
              Output: tuning plan + evaluation approach + implementation guidance.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Search analytics audit & design</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p>
              Make search measurable and debuggable so improvements are visible
              and repeatable.
            </p>
            <ul className="ml-5 list-disc space-y-2">
              <li>Event design (query, click, add-to-cart, purchase)</li>
              <li>Funnels and failure modes</li>
              <li>Dashboards + KPI definitions</li>
              <li>Experiment measurement</li>
            </ul>
            <p className="text-xs">
              Output: analytics spec + KPI framework + dashboard recommendations.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-14 rounded-3xl border bg-card p-10">
        <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
          <div className="lg:col-span-7">
            <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              A lightweight process designed to deliver value fast and keep your
              team moving.
            </p>
            <ol className="mt-6 ml-5 list-decimal space-y-3 text-sm text-muted-foreground">
              <li>Short intake (goals, constraints, current stack)</li>
              <li>Audit & analysis (UX, relevance, analytics as scoped)</li>
              <li>Deliverables + walkthrough call</li>
              <li>Optional implementation support</li>
            </ol>
          </div>
          <div className="lg:col-span-5">
            <div className="rounded-2xl border bg-background p-6">
              <div className="text-sm font-semibold">Technologies</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {technologies.map((t) => (
                  <Badge key={t} variant="secondary">
                    {t}
                  </Badge>
                ))}
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                If you’re on a different stack, that’s fine—we’ll adapt the audit.
              </p>
              <div className="mt-6 flex gap-3">
                <Button asChild className="w-full">
                  <Link href="/pricing">Choose a tier</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

