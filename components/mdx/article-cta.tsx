import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * In-article calls to action.
 *
 * Deliberately does NOT link to /book-a-call. A reader arriving from a search
 * result is several steps away from wanting a sales conversation, and a
 * calendar link at that moment reads as the article having been bait. Both
 * variants offer something the reader can act on alone.
 *
 * Built around one large, high-contrast button rather than a paragraph with a
 * text link — the point of an in-article CTA is that a scanning reader sees it
 * without reading the surrounding prose, which a same-weight-as-body text link
 * does not achieve.
 *
 * `midway`  — the free self-assessment. Zero commitment, immediately useful,
 *             and it demonstrates the diagnostic rather than describing it.
 * `closing` — a direct human contact for readers who do want to talk. Email,
 *             not a booking funnel, and framed around the problem rather than
 *             the engagement.
 */

export function ArticleCtaMidway() {
  return (
    <aside className="not-prose my-10 rounded-2xl border border-primary/20 bg-primary/[0.04] p-6 text-center sm:p-8">
      <p className="text-lg font-semibold tracking-tight text-foreground sm:text-xl">
        Check your own search in 5 minutes
      </p>
      <p className="mt-2 text-sm text-muted-foreground">
        Free self-assessment — search your top commercial query and see what comes back.
      </p>
      <Button asChild size="lg" className="mt-5">
        <Link href="/search-check">
          Run the search self-assessment
          <ArrowRight />
        </Link>
      </Button>
    </aside>
  );
}

export function ArticleCtaClosing() {
  return (
    <aside className="not-prose my-12 rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/[0.08] via-primary/[0.04] to-transparent p-6 text-center sm:p-10">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-primary">
        If this sounded familiar
      </p>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
        Most of the damage is invisible from the dashboard
      </h2>
      <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-muted-foreground">
        I work on ecommerce and marketplace search — relevance, ranking, and
        query understanding, independent of whichever vendor you run. If your
        search feels off and you can&apos;t name why, that&apos;s usually the
        interesting case.
      </p>
      <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <Button asChild size="lg">
          <a href="mailto:michal@findsherpas.com?subject=Search%20relevance">
            Email me about your search
            <ArrowRight />
          </a>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href="/search-check">Start with the self-assessment</Link>
        </Button>
      </div>
    </aside>
  );
}
