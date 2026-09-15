"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { FocusMark } from "./focus-mark";

const links = [
  { href: "/expertise", label: "What we do" },
  { href: "/approach", label: "How we work" },
  {
    href: "/resources",
    label: "Resources",
    matches: ["/resources", "/blog", "/search-check", "/frameworks"],
  },
  { href: "/about", label: "About" },
];

export function SiteNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    menu.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.current?.focus();
      }
      if (event.key !== "Tab") return;
      const items =
        menu.current?.querySelectorAll<HTMLElement>("a[href],button");
      if (!items?.length) return;
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = oldOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };

  return (
    <header className={`fs-header ${pathname === "/" ? "fs-header-home" : ""}`}>
      <Link href="/" className="fs-wordmark" aria-label="Find Sherpas home">
        find sherpas
        <FocusMark />
      </Link>
      <nav className="fs-desktop-nav" aria-label="Main navigation">
        {links.map(({ href, label, matches }) => (
          <Link
            key={href}
            href={href}
            aria-current={
              (matches ?? [href]).some((path) => pathname.startsWith(path))
                ? "page"
                : undefined
            }
          >
            {label}
          </Link>
        ))}
      </nav>
      <Link href="/contact" className="fs-button fs-header-cta">
        Discuss your search <ArrowUpRight size={18} aria-hidden="true" />
      </Link>
      <button
        className="fs-menu-toggle"
        ref={trigger}
        aria-expanded={open}
        aria-controls="fs-mobile-menu"
        aria-label="Open menu"
        onClick={() => setOpen(true)}
      >
        <Menu aria-hidden="true" />
      </button>
      {open && (
        <div
          className="fs-mobile-menu"
          id="fs-mobile-menu"
          role="dialog"
          aria-modal="true"
          aria-label="Main navigation"
          ref={menu}
        >
          <div className="fs-mobile-top">
            <span className="fs-wordmark">find sherpas</span>
            <button onClick={close} aria-label="Close menu">
              <X aria-hidden="true" />
            </button>
          </div>
          <nav aria-label="Mobile navigation">
            {links.map(({ href, label, matches }) => (
              <Link
                key={href}
                href={href}
                onClick={close}
                aria-current={
                  (matches ?? [href]).some((path) => pathname.startsWith(path))
                    ? "page"
                    : undefined
                }
              >
                {label}
                <ArrowUpRight aria-hidden="true" />
              </Link>
            ))}
          </nav>
          <Link className="fs-button" href="/contact" onClick={close}>
            Discuss your search <ArrowUpRight size={20} aria-hidden="true" />
          </Link>
          <a href="mailto:michal@findsherpas.com" className="fs-mobile-email">
            michal@findsherpas.com
          </a>
        </div>
      )}
    </header>
  );
}
