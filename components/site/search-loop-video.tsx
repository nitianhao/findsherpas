"use client";

import { Pause, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

const DESCRIPTION =
  "Search on a fictional store: the query “black dress for winter wedding” returns sundresses, " +
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
    return () => mq.removeEventListener("change", update);
  }, [query]);

  return matches;
}

/**
 * The still, art-directed per breakpoint. Server-rendered, so the hero is never
 * an empty box: it covers first paint before hydration, visitors without JS, and
 * anyone who prefers reduced motion. A <picture> rather than next/image because
 * the two cuts have different aspect ratios, which is art direction, not resizing.
 */
function PosterPicture() {
  return (
    <picture>
      <source media={MOBILE_QUERY} srcSet={CUTS.mobile.poster} />
      <source srcSet={CUTS.wide.poster} />
      <img src={CUTS.wide.poster} alt="" className="h-full w-full object-cover" />
    </picture>
  );
}

/**
 * Two cuts of the same sequence. The wide cut's six-across grid renders product
 * names at about 5px on a phone, which defeats the point — the failure only lands
 * if you can read “Otto Ceramic Bud Vase” under a wedding-dress query. The mobile
 * cut is laid out at phone width with four products, two across.
 *
 * The cut is chosen on the client rather than with two CSS-hidden elements:
 * `autoplay` overrides `preload`, so a hidden <video> downloads in full — a phone
 * was pulling both cuts, 1.6MB, to show one. The box reserves its space in CSS, so
 * swapping the poster for the video after mount costs no layout shift.
 *
 * h264 mp4 only: the VP9 webm came out the same size, so it bought nothing, and
 * Chrome rejected it with MEDIA_ERR_DECODE.
 */
export function SearchLoopVideo({ className }: { className?: string }) {
  const isMobile = useMediaQuery(MOBILE_QUERY);
  const prefersReducedMotion = useMediaQuery(REDUCED_MOTION_QUERY);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [videoFailed, setVideoFailed] = useState(false);

  const cut = isMobile === null ? null : isMobile ? CUTS.mobile : CUTS.wide;
  const showVideo = cut !== null && prefersReducedMotion === false && !videoFailed;

  // React assigns `muted` as a property, not an attribute, and WebKit gates
  // inline autoplay on the attribute. Without this, Safari and iOS show a
  // motionless poster.
  const attachVideo = useCallback((element: HTMLVideoElement | null) => {
    videoRef.current = element;
    if (element) element.setAttribute("muted", "");
  }, []);

  const toggle = useCallback(() => {
    const element = videoRef.current;
    if (!element) return;
    if (element.paused) void element.play().catch(() => setIsPlaying(false));
    else element.pause();
  }, []);

  return (
    <figure className={cn("w-full", className)}>
      <div className="relative aspect-[1080/1508] w-full overflow-hidden rounded-xl border border-border/60 bg-muted sm:aspect-video">
        {showVideo ? (
          <video
            key={cut.video}
            ref={attachVideo}
            className="h-full w-full object-cover"
            autoPlay
            muted
            loop
            playsInline
            preload="metadata"
            poster={cut.poster}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            // Fall back to the still on a missing file or a codec the browser
            // refuses — the failure mode that got the webm dropped, since a
            // <source> list does not recover from a decode error.
            onError={() => setVideoFailed(true)}
            // A remount after a breakpoint change does not reliably re-trigger the
            // autoplay attribute, leaving the new cut paused on its poster.
            onCanPlay={(event) => {
              const element = event.currentTarget;
              if (element.paused) void element.play().catch(() => setIsPlaying(false));
            }}
          >
            <source src={cut.video} type="video/mp4" />
          </video>
        ) : (
          <PosterPicture />
        )}

        {showVideo && (
          // WCAG 2.2.2: anything auto-playing for more than five seconds needs a
          // way to stop it. prefers-reduced-motion only covers people who set it.
          <button
            type="button"
            onClick={toggle}
            aria-pressed={!isPlaying}
            className="absolute bottom-3 right-3 rounded-full bg-background/80 p-2 text-foreground shadow-sm ring-1 ring-border/60 backdrop-blur transition-opacity hover:bg-background focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            {isPlaying ? (
              <Pause className="size-4" aria-hidden="true" />
            ) : (
              <Play className="size-4" aria-hidden="true" />
            )}
            <span className="sr-only">
              {isPlaying ? "Pause the animation" : "Play the animation"}
            </span>
          </button>
        )}
      </div>

      {/* The caption below is marketing framing; this is the actual description,
          and it stays available to screen readers in every branch above. */}
      <span className="sr-only">{DESCRIPTION}</span>

      <figcaption className="mt-3 text-sm text-muted-foreground">
        A failure pattern we find in real audits, shown on a fictional retailer.
      </figcaption>
    </figure>
  );
}
