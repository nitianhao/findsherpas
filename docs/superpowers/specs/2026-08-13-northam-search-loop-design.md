# NORTHAM search-loop video — design

**Date:** 2026-08-13
**Status:** approved, ready for implementation planning

## Purpose

The homepage must *show* a search failure rather than describe it. Search is abstract; every
attempt to explain it in copy or diagram has read as generic (see the rejected directions in
`docs/positioning-interview.md`). The accepted direction is a short, looping animation of a
realistic but fictional retailer — NORTHAM — where a customer's clear intent returns obviously
wrong products, and then the correct ones.

This is the second implementation. The first was deleted on 2026-08-13 for two reasons, both of
which this design addresses directly:

1. **It didn't look real.** The fake storefront read as a mockup, which is the same failure that
   sank the rejected wireframe direction.
2. **The setup was messy.** 573MB of Remotion and `node_modules` lived inside the site repo,
   which only ever needs the rendered output.

## Architecture

Two units, connected by three files.

### Unit 1 — `northam-video` (new sibling repo)

Location: `~/Documents/Directories/northam-video`. Standalone Remotion 4 project, TypeScript, own
`package.json`. It does not import from the site and the site does not import from it.

- Composition: 1920×1080, 30fps, 420 frames (14s).
- `npm run render` → `out/search-loop.mp4`, `out/search-loop.webm`, `out/poster.jpg`.
- `npm run sync` → copies those three into the site's `public/video/`. Destination read from
  `SITE_PUBLIC_DIR`, defaulting to `~/Cursor/FInd Sherpas/find-sherpas/public`.
- `npm run preview` → Remotion Studio, for iterating on timing without a full render.

Internal structure, one purpose per file:

| File | Responsibility |
| --- | --- |
| `src/Root.tsx` | Composition registry only |
| `src/SearchLoop.tsx` | Sequence orchestration and timing — owns the frame map, nothing else |
| `src/components/Storefront.tsx` | NORTHAM chrome: wordmark, nav, footer edge |
| `src/components/SearchBar.tsx` | Field, caret, typed-query animation |
| `src/components/ResultsHeader.tsx` | Result count, sort dropdown, filter chips |
| `src/components/ProductGrid.tsx` | Grid layout and stagger |
| `src/components/ProductCard.tsx` | Single card: image, name, price |
| `src/data/products.ts` | The two result sets as plain data |
| `src/assets/` | Product photography + `CREDITS.md` |

Consequence of this split: retiming the sequence touches only `SearchLoop.tsx`, and changing which
products appear touches only `products.ts`.

### Unit 2 — site integration (`find-sherpas`)

- `components/site/search-loop-video.tsx` — presentational, no props beyond optional `className`.
- `public/video/{search-loop.webm,search-loop.mp4,poster.jpg}` — committed build output, ~2MB.
- One edit to `app/(site)/page.tsx`.

## The sequence

30fps. Frame ranges are authoritative; seconds are for reading.

| Frames | Time | Beat |
| --- | --- | --- |
| 0–90 | 0–3s | Storefront idle. `black dress for winter wedding` types in character by character, with a blinking caret and slightly irregular keystroke timing. Enter. |
| 90–120 | 3–4s | Loading skeleton in the grid. Establishes that a query actually ran. |
| 120–270 | 4–9s | **Wrong results.** Six cards stagger in: floral sundress, printed sundress, leggings, leggings, ceramic bud vase, linen shorts. Held long enough to read the names. |
| 270–390 | 9–13s | Results reflow into six black occasion dresses. Cross-fade with position transitions, not a hard cut. |
| 390–420 | 13–14s | Hold on the corrected grid, then fade to the idle state so the loop seam is invisible. |

**No annotation during the failure beat.** No arrows, no highlighted match tokens, no captions
inside the frame. "Ceramic Bud Vase" under a winter-wedding-dress query is self-evident, and
in-frame annotation is precisely what caused the Result Set direction to be rejected as "a
document about search."

## Making it read as real

The first implementation failed here, so these are requirements, not polish:

- **NORTHAM has its own identity, deliberately not ours.** A different typeface from the site's
  Geist, its own neutral palette, and no `signal-teal` anywhere. If the storefront shares visual
  DNA with the surrounding page it reads as our own UI mockup.
- **Full PLP furniture.** Wordmark, primary nav (Women / Men / Home / Sale), a result count
  ("1,284 results"), a sort control, and filter chips. Retail pages are dense; sparse ones look
  like prototypes.
- **Real photography.** Roughly 14 stock images under Unsplash or Pexels license, 4:5 portrait,
  colour-corrected to a consistent near-white background so the grid looks like one catalogue
  rather than a scrape. Plausible product names and prices.
- **Motion has weight.** Staggered entrance, eased reflow. Instantaneous state changes read as
  slideshow.

## Site integration

Placement: full width of the 1120px content column, in the hero, directly below the CTA buttons.
It replaces the mono line `"black running shoes" → bestseller ranked #14, weak match ranked #1`,
which the video now says better.

Playback: `autoplay muted loop playsinline`, `preload="metadata"`, `<source>` webm before mp4,
`poster` set. Wrapped in a fixed aspect-ratio box with the `rounded-xl` border treatment from
`DESIGN.md` so it doesn't reflow the page during load.

Accessibility:

- Under `prefers-reduced-motion: reduce`, render the poster as a static `<img>` instead of the
  video. Implemented with a CSS media query rather than JS so there is no flash of video.
- The video is decorative-adjacent but carries meaning, so it gets an `aria-label` describing the
  failure it depicts.
- No audio track at all — not merely muted.

Honesty: a small muted caption below the frame identifies this as an illustration of a real
failure pattern from audits, on a fictional retailer. NORTHAM must not be presentable as a real
customer or a real site.

## Error handling and constraints

- **Missing video files.** The component renders the poster if the sources fail; the aspect-ratio
  box means a failed load degrades to a still image, never to a collapsed layout.
- **Size budget.** webm under 2MB, mp4 under 3MB. If exceeded, reduce to 24fps before reducing
  resolution — the content is mostly static, and sharpness matters more than frame rate here.
- **Asset licensing.** Every image recorded in `src/assets/CREDITS.md` with source URL, author,
  and license. An image without a recorded license does not ship.

## Verification

- Render completes and all three outputs land in `public/video/`.
- Dev server: hero screenshot at desktop and mobile widths, console clean, video request returns
  200 with the expected content type.
- Reduced-motion emulation shows the poster, not the video.
- Both result sets legible at the size the video actually occupies on a 1280px viewport — checked
  on the rendered page, not in Remotion Studio.

## Out of scope

Reusing the animation elsewhere on the site, a second scenario, interactivity, and any change to
hero copy beyond removing the one mono line the video replaces.
