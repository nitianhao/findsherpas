"use client";

import { useEffect, useState } from "react";

interface Section {
  id: string;
  label: string;
}

interface SpineSidebarProps {
  sections: Section[];
}

export function SpineSidebar({ sections }: SpineSidebarProps) {
  const [activeId, setActiveId] = useState<string>(sections[0]?.id ?? "");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActiveId(visible[0].target.id);
        }
      },
      { rootMargin: "-15% 0px -70% 0px", threshold: 0 }
    );

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sections]);

  return (
    <>
      <details className="mx-4 mt-6 border-y border-border sm:mx-6 lg:hidden">
        <summary className="flex min-h-11 cursor-pointer items-center justify-between py-3 text-sm font-semibold">
          On this page
          <span className="text-xs font-normal text-muted-foreground">{sections.find(({ id }) => id === activeId)?.label}</span>
        </summary>
        <nav aria-label="On this page" className="pb-3">
          {sections.map(({ id, label }) => (
            <a key={id} href={`#${id}`} className="flex min-h-11 items-center border-t border-border/60 py-2 text-sm">
              {label}
            </a>
          ))}
        </nav>
      </details>
      <nav aria-label="On this page" className="sticky top-28 z-10 hidden self-start px-5 py-12 lg:block">
        <p className="mb-4 text-sm font-semibold">On this page</p>
        <ol className="border-l border-border">
          {sections.map(({ id, label }) => {
            const isActive = activeId === id;
            return (
              <li key={id}>
                <a
                  href={`#${id}`}
                  aria-current={isActive ? "location" : undefined}
                  className={`block min-h-11 border-l-2 px-4 py-2 text-sm leading-6 transition-colors ${
                    isActive
                      ? "-ml-px border-foreground font-semibold text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {label}
                </a>
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}
