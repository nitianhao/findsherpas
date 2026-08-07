"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { DropdownMenu } from "radix-ui";
import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/#what-we-do", label: "Approach" },
  { href: "/search-check", label: "Search check" },
  { href: "/blog", label: "Blog" },
] as const;

const frameworkItems = [
  { href: "/frameworks/search-failure-modes", label: "Failure modes" },
  { href: "/frameworks/query-interpretation", label: "Query interpretation" },
] as const;

export function SiteNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const menuDialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const isActive = useCallback(
    (href: string) => {
      if (href === "/#what-we-do") return pathname === "/";
      if (href === "/frameworks/search-failure-modes") return pathname === "/frameworks/search-failure-modes";
      if (href === "/frameworks/query-interpretation") return pathname === "/frameworks/query-interpretation";
      if (href === "/blog") return pathname.startsWith("/blog");
      if (href === "/search-check") return pathname === "/search-check";
      if (href === "/about") return pathname === "/about";
      if (href === "/book-a-call") return pathname === "/book-a-call";
      return pathname === href;
    },
    [pathname],
  );

  const frameworksActive = frameworkItems.some((item) => isActive(item.href));

  /* Manage focus while the mobile navigation is open. */
  useEffect(() => {
    if (!mobileOpen) return;

    closeButtonRef.current?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setMobileOpen(false);
        menuButtonRef.current?.focus();
        return;
      }

      if (e.key !== "Tab" || !menuDialogRef.current) return;

      const focusable = Array.from(
        menuDialogRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      const first = focusable[0];
      const last = focusable.at(-1);

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    }

    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  /* Lock scroll when mobile menu is open */
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  const navLinkClass = (active: boolean) =>
    `inline-flex min-h-11 items-center text-sm transition-colors ${
      active
        ? "font-medium text-foreground"
        : "text-muted-foreground hover:text-foreground"
    }`;

  return (
    <>
      {/* HEADER */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-20 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo */}
          <Link
            href="/"
            className="flex min-h-11 items-center gap-3 transition-opacity hover:opacity-90"
          >
            <div className="relative size-9 shrink-0 overflow-hidden rounded-xl border bg-card shadow-sm">
              <Image
                src="/icon.svg"
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
          <nav className="hidden items-center gap-7 md:flex" aria-label="Main">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={navLinkClass(isActive(item.href))}
              >
                {item.label}
              </Link>
            ))}

            <DropdownMenu.Root>
              <DropdownMenu.Trigger
                id="frameworks-menu-trigger"
                className={`${navLinkClass(frameworksActive)} gap-1 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`}
              >
                Frameworks
                <ChevronDown size={14} strokeWidth={2} aria-hidden />
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  align="start"
                  sideOffset={10}
                  className="z-50 min-w-56 rounded-xl border border-border bg-card p-1.5 shadow-md"
                >
                  {frameworkItems.map((item) => (
                    <DropdownMenu.Item key={item.href} asChild>
                      <Link
                        href={item.href}
                        className={`block rounded-lg px-3 py-2 text-sm outline-none transition-colors data-[highlighted]:bg-muted data-[highlighted]:text-foreground ${
                          isActive(item.href)
                            ? "font-medium text-foreground"
                            : "text-muted-foreground"
                        }`}
                      >
                        {item.label}
                      </Link>
                    </DropdownMenu.Item>
                  ))}
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>

            <Button asChild size="sm" className="ml-3">
              <Link href="/book-a-call">Book a call</Link>
            </Button>
          </nav>

          {/* Mobile: compact CTA + hamburger */}
          <div className="flex items-center gap-2 md:hidden">
            <Button asChild size="sm">
              <Link href="/book-a-call">Book a call</Link>
            </Button>
            <button
              ref={menuButtonRef}
              type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground md:hidden"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            aria-controls="mobile-navigation"
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

      {/* MOBILE MENU OVERLAY */}
      {mobileOpen && (
        <div
          ref={menuDialogRef}
          id="mobile-navigation"
          role="dialog"
          aria-modal="true"
          aria-label="Main navigation"
          className="fixed inset-0 z-50 flex flex-col bg-background md:hidden"
        >
          {/* Mirror header */}
          <div className="flex h-14 shrink-0 items-center justify-between border-b px-4">
            <Link
              href="/"
              className="flex items-center gap-2"
              onClick={() => setMobileOpen(false)}
            >
              <div className="relative size-8 shrink-0 overflow-hidden rounded-lg border bg-card">
                <Image
                  src="/icon.svg"
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
              ref={closeButtonRef}
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground"
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
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-lg px-3 py-3 text-base transition-colors ${
                    isActive(item.href)
                      ? "font-medium text-foreground"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setMobileOpen(false)}
                >
                  {item.label}
                </Link>
              ))}

              <p className="px-3 pt-4 pb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60">
                Frameworks
              </p>
              {frameworkItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-lg px-3 py-3 text-base transition-colors ${
                    isActive(item.href)
                      ? "font-medium text-foreground"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setMobileOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>

          {/* Subtle email footer */}
          <div className="shrink-0 border-t px-4 py-4">
            <a
              href="mailto:michal@findsherpas.com"
              className="inline-flex min-h-11 items-center text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              michal@findsherpas.com
            </a>
          </div>
        </div>
      )}
    </>
  );
}
