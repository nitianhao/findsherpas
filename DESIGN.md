---
name: Find Sherpas
description: Internal search audit and optimization for ecommerce — diagnosed and improved
colors:
  neutral-canvas: "oklch(1 0 0)"
  neutral-ink: "oklch(0.145 0 0)"
  neutral-mist: "oklch(0.97 0 0)"
  neutral-graphite: "oklch(0.556 0 0)"
  hairline-gray: "oklch(0.922 0 0)"
  signal-teal: "oklch(0.50 0.14 200)"
  signal-teal-foreground: "oklch(0.985 0 0)"
  teal-wash: "oklch(0.96 0.03 200)"
  alert-red: "oklch(0.577 0.245 27.325)"
  warning-amber: "oklch(0.96 0.045 85)"
  warning-amber-foreground: "oklch(0.34 0.055 70)"
  warning-amber-strong: "oklch(0.43 0.11 65)"
typography:
  display:
    fontFamily: "Geist, ui-sans-serif, system-ui"
    fontSize: "clamp(2.25rem, 4vw, 3.5rem)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Geist, ui-sans-serif, system-ui"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.75
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui"
    fontSize: "0.6875rem"
    fontWeight: 600
    letterSpacing: "0.08em"
  data:
    fontFamily: "Geist Mono, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontWeight: 500
rounded:
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.signal-teal}"
    textColor: "{colors.signal-teal-foreground}"
    rounded: "{rounded.lg}"
    padding: "10px 24px"
  button-primary-hover:
    backgroundColor: "{colors.signal-teal}"
    textColor: "{colors.signal-teal-foreground}"
  button-outline:
    backgroundColor: "{colors.neutral-canvas}"
    textColor: "{colors.neutral-ink}"
    rounded: "{rounded.lg}"
    padding: "10px 24px"
  badge-default:
    backgroundColor: "{colors.signal-teal}"
    textColor: "{colors.signal-teal-foreground}"
    rounded: "{rounded.full}"
    padding: "2px 8px"
  card:
    backgroundColor: "{colors.neutral-canvas}"
    textColor: "{colors.neutral-ink}"
    rounded: "{rounded.xl}"
    padding: "24px"
  input:
    backgroundColor: "{colors.neutral-canvas}"
    textColor: "{colors.neutral-ink}"
    rounded: "{rounded.md}"
    padding: "4px 12px"
---

# Design System: Find Sherpas

## Overview

**Creative North Star: "The Instrument Panel"**

Find Sherpas reads a search system the way an instrument reads a signal: calmly, precisely, without editorializing. The surface is quiet by default — a near-white canvas, hairline borders, restrained type — so that when something needs attention (a CTA, a finding, a live data figure) it registers as a genuine signal rather than one more loud element competing for the eye. A single narrow "spine" rail tracks position down the page like a gauge, and raw data — queries, rankings, stats — switches into a monospace register that visually separates measurement from narrative prose.

The voice is diagnostic and evidence-led: short declarative sentences, uppercase micro-labels as section eyebrows, findings stated plainly before any pitch. Confidence comes from clarity and restraint, not decoration. Explicitly rejected: the generic SaaS look — gradient meshes, glassmorphism, glowing blob backgrounds, purple-to-blue washes. This system stays flat, hairline-bordered, and typographically led.

**Key Characteristics:**
- Near-white canvas with a single sparing teal accent
- A narrow scroll-spy "spine" rail as the signature navigation device
- Monospace type reserved for data/query figures, never for prose
- Uppercase, wide-tracked micro-labels as section eyebrows
- Flat surfaces at rest; shadow appears only as a response to interaction

## Colors

Overwhelmingly neutral — near-white canvas, near-black ink, hairline gray dividers — with one accent held in reserve for the moment it's needed.

### Primary
- **Signal Teal** (oklch(0.50 0.14 200)): the single accent color in the system. Used almost exclusively on the primary call-to-action button and focus rings — the color that tells the eye "act here."

### Neutral
- **Canvas** (oklch(1 0 0)): page and card background.
- **Ink** (oklch(0.145 0 0)): primary text color.
- **Mist** (oklch(0.97 0 0)): secondary surfaces (secondary buttons, muted backgrounds).
- **Graphite** (oklch(0.556 0 0)): muted/secondary text — body copy under headlines, captions.
- **Hairline Gray** (oklch(0.922 0 0)): borders, dividers, input strokes.
- **Teal Wash** (oklch(0.96 0.03 200)): the accent's tinted background form, used only where a soft highlight is needed (e.g. active nav state background), never as a substitute for the full accent.

### Named Rules (optional, powerful)
**The One Signal Rule.** Signal Teal appears on at most one element per screen at rest — the primary action. Everything else stays neutral so the accent keeps its meaning as "the thing to do here," not decoration. Scoped exception: the sticky header's "Book a call" button is exempt, since persistent navigation chrome is expected to keep its own affordance visible through scroll. If a page's in-flow content adds a second teal element while the header CTA is on screen, that in-flow element is the violation to fix, not the header.

## Typography

**Display/Body Font:** Geist (with ui-sans-serif, system-ui fallback)
**Data/Label Font:** Geist Mono (with ui-monospace, monospace fallback) — reserved for figures, not prose

**Character:** A single grotesque sans carries every weight of narrative content; Geist Mono is switched in only where raw data appears, so a reader can tell "measurement" from "explanation" at a glance without being told.

### Hierarchy
- **Display** (600, clamp(2.25rem, 4vw, 3.5rem), 1.1 line-height, -0.01em tracking): hero headlines only, one per page.
- **Headline** (600, 1.875rem/30px, 1.2 line-height): section headers, always preceded by an eyebrow label.
- **Title** (700, 1rem/16px, 1.3 line-height): card and finding-block titles.
- **Body** (400, 1rem/16px, 1.75 line-height, ~65–75ch max width): paragraph copy, set in Graphite when secondary to a headline.
- **Label** (600, 0.6875rem/11px, 0.08em tracking, uppercase): section eyebrows and micro-labels ("Diagnostic patterns", "Relevance").
- **Data** (Geist Mono, 500, 0.875rem/14px): query strings, rankings, stat figures — anything that is a measurement rather than a sentence.

### Named Rules (optional)
**The Mono-for-Data Rule.** Any figure that represents a measured or literal value — a search query, a rank position, a stat — is set in Geist Mono. Sentences, headlines, and labels never are. The switch itself is the signal that "this is raw."

## Layout

Content sits in narrow, reading-width containers rather than full-bleed sections: a 768px column for hero copy, a 576px column for lead paragraphs, and a 1120px column for multi-card sections — all centered. A persistent 80px left rail carries the spine navigation on desktop; it collapses away on mobile rather than becoming a hamburger menu, since the marketing pages are meant to be scrolled and read, not navigated like an app. Section rhythm runs large (64–128px of vertical padding between major sections, tightening on mobile) with a hairline top border marking each new section start.

## Elevation & Depth

Flat at rest, ambient on interaction. Cards and default buttons carry only the faintest resting shadow (`shadow-sm` / `shadow-xs`); the primary button's shadow visibly deepens on hover (`shadow-md` → `shadow-lg`). Depth is not a static decoration — it's feedback that something is interactive or has just changed state.

### Shadow Vocabulary
- **Resting** (`box-shadow: 0 1px 2px rgba(0,0,0,0.05)` / Tailwind `shadow-xs`/`shadow-sm`): default state for cards, inputs, and the outline button.
- **Interactive** (`shadow-md` → `shadow-lg` on hover): reserved for the primary button, signaling "this is the action."

### Named Rules (optional)
**The Ambient-on-Interaction Rule.** Nothing is elevated by default. Shadow only appears, or deepens, in direct response to hover/focus/state change.

## Shapes

Corners are soft but not rounded-to-the-point-of-playful: buttons and inputs sit at 10–12px radius, cards at 16px, pills (badges, the search-check query chip) go fully rounded. Borders are single hairline strokes in Hairline Gray, never doubled or colored except for destructive/warning states. No clipping, masking, or decorative geometry — the form language stays functional.

## Components

### Buttons
- **Shape:** rounded-lg by default (12px), rounded-xl (16px) at the `lg` size, rounded-md (10px) at `sm`/`xs`.
- **Primary:** Signal Teal background, Canvas text, resting `shadow-sm`, hover deepens to `shadow-lg` and background dims to 90% opacity.
- **Outline:** transparent/canvas background, hairline border, `shadow-xs` at rest, fills with Mist on hover.
- **Secondary/Ghost/Link:** Secondary uses Mist background with no shadow; Ghost is borderless until hover (Mist fill); Link is text-only in Signal Teal with an underline on hover.

### Badges
- **Style:** fully rounded (pill), `px-2 py-0.5`, `text-xs font-medium`.
- **Default:** Signal Teal background — used sparingly, same rarity discipline as the primary button.
- **Outline/Secondary/Ghost:** neutral variants for non-emphasis tags.

### Cards / Containers
- **Corner Style:** 16px radius (`rounded-xl`).
- **Background:** Canvas.
- **Shadow Strategy:** resting `shadow-sm`; see Elevation.
- **Border:** hairline, often at reduced opacity (`border-border/50`) for a quieter grid of cards.
- **Internal Padding:** 24px (`py-6`, `px-6` in header/content/footer slots).

### Inputs / Fields
- **Style:** hairline border, transparent-to-canvas background, `rounded-md` (10px), `shadow-xs` at rest.
- **Focus:** border shifts to the ring color plus a 3px soft ring (`focus-visible:ring-ring/50`) — no glow or color fill.
- **Error/Disabled:** invalid state rings in destructive/20%; disabled drops to 50% opacity and blocks pointer events.

### Navigation — The Spine
- **Style:** an 80px sticky left rail, visible from `md` breakpoint up. A single 1px vertical hairline connects a column of dot markers, one per page section (11×11px hit target, 12px dot). The active section's dot fills solid Ink; inactive dots are outlined in Graphite over a Canvas fill. Driven by scroll-spy (IntersectionObserver), not click-only state.
- **Mobile treatment:** the rail is hidden entirely below `md`; no collapsed/hamburger equivalent — mobile relies on normal in-page scroll and content order.

### The Spine (signature component)
The defining visual device of the system: it reframes in-page navigation as an instrument readout rather than a menu, reinforcing the Instrument Panel north star. New long-scrolling marketing pages should default to reusing it rather than inventing a new wayfinding pattern.

## Do's and Don'ts

### Do:
- **Do** hold Signal Teal for one element per screen — the primary action or an active-state indicator.
- **Do** set any measured/literal figure (query, rank, stat) in Geist Mono; keep all prose in Geist Sans.
- **Do** keep surfaces flat at rest and let shadow communicate interactivity, not decoration.
- **Do** center content in reading-width containers (576–1120px) rather than stretching full-bleed.

### Don't:
- **Don't** introduce gradients, glassmorphism, or glow effects — the explicit anti-reference for this system is the generic SaaS template look.
- **Don't** add a second accent color; route additional emphasis through Ink weight/size or the Teal Wash tint instead.
- **Don't** collapse the spine into a hamburger menu on mobile — hide it and let the page scroll normally.
