"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";

const serviceItems = [
  { href: "/services/search-ux-audit", label: "Search UX Audit" },
  { href: "/services/search-relevance-audit", label: "Search Relevance Audit" },
  { href: "/services/search-analytics-audit", label: "Search Analytics Audit" },
] as const;

export function SiteNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileServicesOpen, setMobileServicesOpen] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* ------------------------------------------------------------------ */
  /*  Active-route helpers                                               */
  /* ------------------------------------------------------------------ */
  const isServicesActive = pathname.startsWith("/services");
  const isApproachActive = pathname === "/approach";
  const isPricingActive = pathname === "/pricing";
  const isInsightsActive =
    pathname.startsWith("/blog") || pathname.startsWith("/insights");
  const isAboutActive = pathname === "/about";

  /* ------------------------------------------------------------------ */
  /*  Desktop dropdown – hover / focus / keyboard                        */
  /* ------------------------------------------------------------------ */
  const openDropdown = useCallback(() => {
    clearTimeout(timeoutRef.current);
    setDropdownOpen(true);
  }, []);

  const closeDropdown = useCallback(() => {
    timeoutRef.current = setTimeout(() => setDropdownOpen(false), 120);
  }, []);

  /* Close on Escape */
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setDropdownOpen(false);
        setMobileOpen(false);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  /* Lock scroll when mobile menu is open */
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  /* Close mobile menu on route change */
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  /* ------------------------------------------------------------------ */
  /*  Helpers                                                            */
  /* ------------------------------------------------------------------ */
  const navLink = (active: boolean) =>
    `text-sm transition-colors ${active
      ? "font-medium text-foreground"
      : "text-muted-foreground hover:text-foreground"
    }`;

  return (
    <>
      {/* ============================================================= */}
      {/*  HEADER                                                        */}
      {/* ============================================================= */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-20 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-90">
            <div className="relative size-9 shrink-0 overflow-hidden rounded-xl border bg-card shadow-sm">
              <Image
                src="/favicon.ico"
                alt=""
                width={36}
                height={36}
                className="object-contain"
              />
            </div>
            <span className="text-base font-bold tracking-tight">
              Find Sherpas
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-10 md:flex" aria-label="Main">
            {/* Services dropdown */}
            <div
              ref={dropdownRef}
              className="relative"
              onMouseEnter={openDropdown}
              onMouseLeave={closeDropdown}
              onBlur={(e) => {
                if (
                  !dropdownRef.current?.contains(e.relatedTarget as Node)
                ) {
                  setDropdownOpen(false);
                }
              }}
            >
              <button
                type="button"
                className={`inline-flex items-center gap-1.5 py-2 ${navLink(isServicesActive)}`}
                aria-expanded={dropdownOpen}
                aria-haspopup="true"
                onClick={() => setDropdownOpen((v) => !v)}
                onFocus={openDropdown}
              >
                Services
                <svg
                  className={`h-3.5 w-3.5 text-muted-foreground/70 transition-transform duration-200 ${dropdownOpen ? "rotate-180" : ""}`}
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M4 6l4 4 4-4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>

              {dropdownOpen && (
                <div
                  role="menu"
                  className="absolute left-1/2 top-full z-50 mt-4 w-64 -translate-x-1/2 rounded-xl border bg-background p-2 shadow-xl shadow-black/5"
                >
                  {serviceItems.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      role="menuitem"
                      className={`block rounded-lg px-4 py-3 text-sm transition-colors ${pathname === item.href
                          ? "bg-primary/[0.08] font-medium text-foreground"
                          : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                        }`}
                      onClick={() => setDropdownOpen(false)}
                    >
                      {item.label}
                    </Link>
                  ))}
                  <div className="mt-2 border-t border-border/50 pt-2">
                    <Link
                      href="/services"
                      role="menuitem"
                      className="block rounded-lg px-4 py-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                      onClick={() => setDropdownOpen(false)}
                    >
                      All services &rarr;
                    </Link>
                  </div>
                </div>
              )}
            </div>

            <Link href="/approach" className={navLink(isApproachActive)}>
              Approach
            </Link>
            <Link href="/pricing" className={navLink(isPricingActive)}>
              Pricing &amp; Scope
            </Link>
            <Link href="/blog" className={navLink(isInsightsActive)}>
              Insights
            </Link>
            <Link href="/about" className={navLink(isAboutActive)}>
              About
            </Link>
          </nav>

          {/* Right side: desktop CTA + mobile hamburger */}
          <div className="flex items-center gap-4">
            <Button asChild className="hidden md:inline-flex rounded-full">
              <Link href="/book-a-call">Book a call</Link>
            </Button>

            {/* Hamburger toggle */}
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground md:hidden"
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              onClick={() => setMobileOpen((v) => !v)}
            >
              {mobileOpen ? (
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M18 6L6 18M6 6l12 12"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              ) : (
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M4 7h16M4 12h16M4 17h16"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* ============================================================= */}
      {/*  MOBILE MENU OVERLAY                                           */}
      {/* ============================================================= */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-background md:hidden">
          {/* Mirror header */}
          <div className="flex h-14 shrink-0 items-center justify-between border-b px-4">
            <Link
              href="/"
              className="flex items-center gap-2"
              onClick={() => setMobileOpen(false)}
            >
              <div className="relative size-8 shrink-0 overflow-hidden rounded-lg border bg-card">
                <Image
                  src="/favicon.ico"
                  alt=""
                  width={32}
                  height={32}
                  className="object-contain"
                />
              </div>
              <span className="text-sm font-semibold tracking-tight">
                Find Sherpas
              </span>
            </Link>
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden
              >
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>

          {/* Nav links */}
          <nav
            className="flex-1 overflow-y-auto px-4 py-6"
            aria-label="Mobile"
          >
            <div className="space-y-1">
              {/* Services (expandable) */}
              <div>
                <button
                  type="button"
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left text-base transition-colors ${isServicesActive
                      ? "font-medium text-foreground"
                      : "text-muted-foreground"
                    }`}
                  onClick={() => setMobileServicesOpen((v) => !v)}
                  aria-expanded={mobileServicesOpen}
                >
                  Services
                  <svg
                    className={`h-4 w-4 transition-transform ${mobileServicesOpen ? "rotate-180" : ""}`}
                    viewBox="0 0 16 16"
                    fill="none"
                    aria-hidden
                  >
                    <path
                      d="M4 6l4 4 4-4"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>

                {mobileServicesOpen && (
                  <div className="ml-3 space-y-0.5 border-l border-border/50 pl-3">
                    {serviceItems.map((item) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`block rounded-md px-3 py-2.5 text-sm transition-colors ${pathname === item.href
                            ? "font-medium text-foreground"
                            : "text-muted-foreground hover:text-foreground"
                          }`}
                        onClick={() => setMobileOpen(false)}
                      >
                        {item.label}
                      </Link>
                    ))}
                    <Link
                      href="/services"
                      className="block rounded-md px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => setMobileOpen(false)}
                    >
                      All services &rarr;
                    </Link>
                  </div>
                )}
              </div>

              <Link
                href="/approach"
                className={`block rounded-lg px-3 py-3 text-base transition-colors ${isApproachActive
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                  }`}
                onClick={() => setMobileOpen(false)}
              >
                Approach
              </Link>
              <Link
                href="/pricing"
                className={`block rounded-lg px-3 py-3 text-base transition-colors ${isPricingActive
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                  }`}
                onClick={() => setMobileOpen(false)}
              >
                Pricing &amp; Scope
              </Link>
              <Link
                href="/blog"
                className={`block rounded-lg px-3 py-3 text-base transition-colors ${isInsightsActive
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                  }`}
                onClick={() => setMobileOpen(false)}
              >
                Insights
              </Link>
              <Link
                href="/about"
                className={`block rounded-lg px-3 py-3 text-base transition-colors ${isAboutActive
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                  }`}
                onClick={() => setMobileOpen(false)}
              >
                About
              </Link>
            </div>
          </nav>

          {/* Pinned CTA */}
          <div className="shrink-0 border-t px-4 py-4">
            <Button asChild size="lg" className="w-full">
              <Link href="/book-a-call" onClick={() => setMobileOpen(false)}>
                Book a call
              </Link>
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
