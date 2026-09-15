"use client";

import { Pause, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/** Matches the `sm` breakpoint, below which the wide cut is unreadable. */
const MOBILE_QUERY = "(max-width: 639px)";
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

const SCENARIOS = [
  {
    mobile: { video: "/video/search-loop-mobile.mp4", poster: "/video/poster-mobile.jpg" },
    wide: { video: "/video/search-loop.mp4", poster: "/video/poster.jpg" },
    description:
      "The query “black dress for winter wedding” first returns sundresses, leggings, and a vase, then re-ranks to black occasion dresses.",
  },
  {
    mobile: { video: "/video/search-loop-typo-mobile.mp4", poster: "/video/poster-typo-mobile.jpg" },
    wide: { video: "/video/search-loop-typo.mp4", poster: "/video/poster-typo.jpg" },
    description:
      "The misspelled query “wirless headphones” first returns cables, accessories, and unrelated objects, then re-ranks to wireless headphones and earbuds.",
  },
  {
    mobile: { video: "/video/search-loop-synonym-mobile.mp4", poster: "/video/poster-synonym-mobile.jpg" },
    wide: { video: "/video/search-loop-synonym.mp4", poster: "/video/poster-synonym.jpg" },
    description:
      "The regional query “trainers for running” first returns gym equipment, then re-ranks to running shoes.",
  },
  {
    mobile: { video: "/video/search-loop-availability-mobile.mp4", poster: "/video/poster-availability-mobile.jpg" },
    wide: { video: "/video/search-loop-availability.mp4", poster: "/video/poster-availability.jpg" },
    description:
      "The query “linen shirt” first returns bedding and household linen, then re-ranks to linen shirts.",
  },
  {
    mobile: { video: "/video/search-loop-purity-mobile.mp4", poster: "/video/poster-purity-mobile.jpg" },
    wide: { video: "/video/search-loop-purity.mp4", poster: "/video/poster-purity.jpg" },
    description:
      "The query “black occasion dress” finds a good first result but mixes it with a vase, leggings, and shorts, then cleans the full result set.",
  },
  {
    mobile: { video: "/video/search-loop-negative-mobile.mp4", poster: "/video/poster-negative-mobile.jpg" },
    wide: { video: "/video/search-loop-negative.mp4", poster: "/video/poster-negative.jpg" },
    description:
      "The query “wireless headphones not earbuds” first promotes earbuds and an accessory, then removes the products the customer excluded.",
  },
  {
    mobile: { video: "/video/search-loop-variants-mobile.mp4", poster: "/video/poster-variants-mobile.jpg" },
    wide: { video: "/video/search-loop-variants.mp4", poster: "/video/poster-variants.jpg" },
    description:
      "The query “running shoes” first returns six colour variants of one model, then changes to a useful range of different running shoes.",
  },
] as const;

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
function PosterPicture({ scenario = SCENARIOS[0] }: { scenario?: (typeof SCENARIOS)[number] }) {
  return (
    // <picture> is inline by default, so the img's h-full would resolve
    // against an auto height and the still would not fill the band.
    <picture className="block h-full w-full">
      <source media={MOBILE_QUERY} srcSet={scenario.mobile.poster} />
      <source srcSet={scenario.wide.poster} />
      {/* Framed exactly as the video is, or the reduced-motion and fallback
          paths crop the search box out of the still. */}
      <img
        src={scenario.wide.poster}
        alt=""
        className="h-full w-full object-cover object-top lg:object-[20%_center]"
      />
    </picture>
  );
}

/**
 * The hero backdrop: the failing search itself, playing behind the diagnosis.
 *
 * Renders as a fill layer — the hero band owns the height, this owns nothing but
 * its own stacking. The parent lays the ink base and the scrims; this component
 * only picks the right cut, keeps it playing, and offers the pause control that
 * has to travel with the media (WCAG 2.2.2).
 *
 * Two cuts of the same sequence. The wide cut's six-across grid crops to a stripe
 * on a phone; the mobile cut is laid out at phone width, and its 1080x1508 frame
 * covers a tall mobile band with almost no crop.
 *
 * The cut is chosen on the client rather than with two CSS-hidden elements:
 * `autoplay` overrides `preload`, so a hidden <video> downloads in full — a phone
 * was pulling both cuts, 1.6MB, to show one. The band's height is set in CSS and
 * does not depend on the media, so swapping poster for video costs no layout shift.
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
  const [scenarioIndex, setScenarioIndex] = useState<number | null>(null);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const values = new Uint32Array(1);
      window.crypto.getRandomValues(values);
      setScenarioIndex(values[0]! % SCENARIOS.length);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  const scenario = SCENARIOS[scenarioIndex ?? 0];
  const cut = isMobile === null || scenarioIndex === null
    ? null
    : isMobile
      ? scenario.mobile
      : scenario.wide;
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
    // Full strength. The recording is a store page whose content runs edge to
    // edge, so there is no quiet region to print a headline over: washing out
    // enough of it to carry text costs the product names and prices, which are
    // the whole reason it is playing. It gets its own space instead — a column
    // at lg, the top of the stack below that — and keeps its own contrast.
    //
    // Below lg it sits in the band's normal flow so the band sizes itself
    // around the media. A fixed height plus a matching top padding on the band
    // cannot both track a cut's real aspect ratio, and that pair was cropping
    // the entire product grid off the bottom on a phone. The negative margins
    // undo the band's padding so it still bleeds edge to edge.
    <div
      className={cn(
        "pointer-events-none relative -mx-4 sm:-mx-6 md:-ml-20 lg:absolute lg:inset-y-0 lg:right-0 lg:mx-0 lg:flex lg:w-[56%] lg:items-center",
        className,
      )}
    >
      {/* Carrying each cut's own aspect ratio means nothing is cropped: the
          mobile cut is art-directed at phone width, the wide cut at 16:9. The
          column at lg carries a ratio too, rather than stretching to the band's
          height — stretching made the crop a function of the browser window's
          height, and the crop is where the argument lives. At a 720px-tall
          window it cut the ceramic vase's label in half; at 960px the vase was
          gone altogether and the hero was six clothes under a clothes query,
          which is not a failure at all. 1434x1080 is the wide cut framed on
          what has to survive: the store's logo at x96 through the vase at
          x1530. The 16:9 source is covered into it and offset 20% — one dead
          margin off the left — so that window is what shows, at every window
          height. The two products past the vase are the ones that go. */}
      {/* 1080x1267 is the mobile cut's own 1080x1508 with the last 16% dropped:
          that band holds only a second product row the source already crops
          mid-image, while the first row — the sundress and, next to it, the
          ceramic vase — carries the whole point and ends at 80%. Keeping the
          full frame pushed the headline under the fold on a small phone for a
          strip of half-products. */}
      <div className="relative aspect-[1080/1267] w-full sm:aspect-video lg:aspect-[1434/1080]">
        {showVideo ? (
          <video
            key={cut.video}
            ref={attachVideo}
            // Anchored so the query is never the part that gets cropped: top
            // when the panel is a strip, and at lg the 20% that lands the
            // window on logo-through-vase.
            className="h-full w-full object-cover object-top lg:object-[20%_center]"
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
          <PosterPicture scenario={scenario} />
        )}

        {/* Dissolves the panel's inner edge into the band instead of ending it
            on a line — the edge the copy sits against, so the foot of the strip
            on a phone and the left of the column above that.
            --hero-paper is set by the band. */}
        <div
          aria-hidden
          className="absolute inset-0 lg:hidden"
          style={{
            backgroundImage:
              // Short: the product names sit close to the foot of both cuts, so
              // a long fade would take the names with it.
              "linear-gradient(to top, rgb(var(--hero-paper)) 0%, rgb(var(--hero-paper) / 0.55) 3%, rgb(var(--hero-paper) / 0) 8%)",
          }}
        />
        <div
          aria-hidden
          className="absolute inset-0 hidden lg:block"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgb(var(--hero-paper)) 0%, rgb(var(--hero-paper) / 0.92) 8%, rgb(var(--hero-paper) / 0.45) 18%, rgb(var(--hero-paper) / 0) 30%)",
          }}
        />

        {showVideo && (
          // WCAG 2.2.2: anything auto-playing for more than five seconds needs
          // a way to stop it. prefers-reduced-motion only covers people who set
          // it. Kept inside the panel so it sits on the recording it controls.
          <button
            type="button"
            onClick={toggle}
            aria-pressed={!isPlaying}
            // Top-right on a phone: the foot of that cut is where the product
            // names sit, and the control was covering the ceramic vase's label
            // — the one result that makes the failure obvious.
            className="pointer-events-auto absolute right-4 top-3 z-20 rounded-full bg-background/85 p-2 text-foreground ring-1 ring-border backdrop-blur transition-colors hover:bg-background focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:bottom-5 sm:right-6 sm:top-auto lg:right-8"
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

      {/* The visible caption is marketing framing; this is the actual
          description, and it stays available in every branch above. */}
      <span className="sr-only">{scenario.description}</span>
    </div>
  );
}
