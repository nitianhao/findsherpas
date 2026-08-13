"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const ARIA_LABEL =
  "Search on a fictional store: the query 'black dress for winter wedding' returns sundresses, " +
  "leggings and a ceramic vase, before resolving to the correct black occasion dresses.";

/** Matches the `sm` breakpoint, below which the wide cut is unreadable. */
const MOBILE_QUERY = "(max-width: 639px)";
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

const CUTS = {
  mobile: { video: "/video/search-loop-mobile.mp4", poster: "/video/poster-mobile.jpg" },
  wide: { video: "/video/search-loop.mp4", poster: "/video/poster.jpg" },
} as const;

function useMediaQuery(query: string): boolean | null {
  const [matches, setMatches] = useState<boolean | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(query);
    const update = () => setMatches(mq.matches);
    update();
    mq.addEventListener("change", update);
    // Belt and braces: some environments resize the viewport without dispatching
    // a matchMedia change. setState with an unchanged value is a no-op.
    window.addEventListener("resize", update);
    return () => {
      mq.removeEventListener("change", update);
      window.removeEventListener("resize", update);
    };
  }, [query]);

  return matches;
}

/**
 * Two cuts of the same sequence. The wide cut's six-across grid renders product
 * names at about 5px on a phone, which defeats the point — the failure only lands
 * if you can read "Otto Ceramic Bud Vase" under a wedding-dress query. The mobile
 * cut is laid out at phone width with four products, two across.
 *
 * Chosen on the client rather than with two CSS-hidden elements: `autoplay`
 * overrides `preload`, so a hidden <video> downloads in full — a phone was
 * pulling both cuts, 1.6MB, to show one. The box reserves its space in CSS, so
 * picking the cut after mount costs no layout shift.
 *
 * h264 mp4 only: the VP9 webm came out the same size, so it bought nothing, and
 * Chrome rejected it with MEDIA_ERR_DECODE.
 */
export function SearchLoopVideo({ className }: { className?: string }) {
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const prefersReducedMotion = useMediaQuery(REDUCED_MOTION_QUERY);

  const cut = isMobile === null ? null : isMobile ? CUTS.mobile : CUTS.wide;

  return (
    <figure className={cn("w-full", className)}>
      <div className="relative aspect-[1080/1508] w-full overflow-hidden rounded-xl border border-border/60 bg-muted sm:aspect-video">
        {cut === null ? null : prefersReducedMotion ? (
          <Image
            src={cut.poster}
            alt={ARIA_LABEL}
            fill
            sizes="(max-width: 639px) 100vw, (max-width: 1120px) 100vw, 1120px"
            className="object-cover"
          />
        ) : (
          <video
            key={cut.video}
            className="h-full w-full object-cover"
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            poster={cut.poster}
            aria-label={ARIA_LABEL}
            // A remount after a breakpoint change does not reliably re-trigger
            // the autoplay attribute, leaving the new cut paused on its poster.
            onCanPlay={(event) => {
              const element = event.currentTarget;
              if (element.paused) void element.play().catch(() => {});
            }}
          >
            <source src={cut.video} type="video/mp4" />
          </video>
        )}
      </div>
      <figcaption className="mt-3 text-sm text-muted-foreground">
        A failure pattern we find in real audits, shown on a fictional retailer.
      </figcaption>
    </figure>
  );
}
