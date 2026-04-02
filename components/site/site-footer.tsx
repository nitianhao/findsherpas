import Link from "next/link";

import { Button } from "@/components/ui/button";

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="text-sm font-semibold tracking-tight">
              Find Sherpas
            </div>
            <p className="mt-2 max-w-xs text-sm text-muted-foreground">
              On-site search optimization for e-commerce teams. Not SEO.
            </p>
          </div>

          {/* Explore */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Explore
            </div>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link
                  href="/frameworks/search-failure-modes"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Failure modes
                </Link>
              </li>
              <li>
                <Link
                  href="/frameworks/query-interpretation"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Query interpretation
                </Link>
              </li>
              <li>
                <Link
                  href="/search-check"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Search check
                </Link>
              </li>
              <li>
                <Link
                  href="/about"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  About
                </Link>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Company
            </div>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link
                  href="/#what-we-do"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Approach
                </Link>
              </li>
              <li>
                <Link
                  href="/notes"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Insights
                </Link>
              </li>
              <li>
                <Link
                  href="/book-a-call"
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  Contact
                </Link>
              </li>
            </ul>
          </div>

          {/* Get started */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Get started
            </div>
            <div className="mt-4">
              <Button asChild size="sm">
                <Link href="/book-a-call">Book a call</Link>
              </Button>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 border-t border-border/50 pt-6">
          <div className="flex flex-col gap-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <div>
              &copy; {new Date().getFullYear()} Find Sherpas. All rights
              reserved.
            </div>
            <div className="flex items-center gap-3">
              <span>
                Languages: EN&nbsp;&middot; DE&nbsp;&middot;
                FR&nbsp;&middot; ES&nbsp;&middot; IT&nbsp;&middot;
                NL&nbsp;&middot; SV
              </span>
            </div>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            <a
              href="mailto:michal.pekarcik@gmail.com"
              className="transition-colors hover:text-foreground"
            >
              michal.pekarcik@gmail.com
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
