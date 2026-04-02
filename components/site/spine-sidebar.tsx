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
    <div className="sticky top-32 hidden self-start md:flex md:flex-col md:items-center">
      <div className="relative flex flex-col items-center gap-8">
        {/* Vertical connecting line */}
        <div
          className="absolute left-1/2 top-1.5 -translate-x-1/2 bg-gray-200"
          style={{ width: "1px", bottom: "6px" }}
        />
        {sections.map(({ id, label }) => {
          const isActive = activeId === id;
          return (
            <a
              key={id}
              href={`#${id}`}
              aria-label={label}
              title={label}
              className="relative z-10 transition-transform duration-150 hover:scale-125"
            >
              {isActive ? (
                <span className="block h-3 w-3 rounded-full bg-gray-900 transition-all duration-200" />
              ) : (
                <span className="block h-3 w-3 rounded-full border border-gray-400 bg-white transition-all duration-200" />
              )}
            </a>
          );
        })}
      </div>
    </div>
  );
}
