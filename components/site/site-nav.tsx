"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/#what-we-do", label: "What we do" },
  { href: "/blog", label: "Insights" },
  { href: "/search-check", label: "Search check" },
  { href: "/about", label: "About" },
  { href: "/book-a-call", label: "Contact" },
] as const;

export function SiteNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = useCallback(
    (href: string) => {
      if (href === "/#what-we-do") return pathname === "/" || pathname.startsWith("/services");
      if (href === "/blog")
        return pathname.startsWith("/blog") || pathname.startsWith("/insights");
      if (href === "/search-check") return pathname === "/search-check";
      if (href === "/about") return pathname === "/about";
      if (href === "/book-a-call") return pathname === "/book-a-call";
      return pathname === href;
    },
    [pathname],
  );

  /* Close on Escape */
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false);
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

  const navLinkClass = (active: boolean) =>
    `text-sm transition-colors ${
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
            className="flex items-center gap-3 transition-opacity hover:opacity-90"
          >
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
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={navLinkClass(isActive(item.href))}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Mobile hamburger */}
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
      </header>

      {/* MOBILE MENU OVERLAY */}
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
            </div>
          </nav>

          {/* Subtle email footer */}
          <div className="shrink-0 border-t px-4 py-4">
            <a
              href="mailto:michal.pekarcik@gmail.com"
              className="text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              michal.pekarcik@gmail.com
            </a>
          </div>
        </div>
      )}
    </>
  );
}
