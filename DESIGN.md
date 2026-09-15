---
name: Find Sherpas
description: Boutique ecommerce search optimization
colors:
  deep-ink: "#293b44"
  deep-ink-hover: "#1d2b32"
  reading-ink: "#1c272d"
  soft-white: "#f5f6f4"
  white: "#ffffff"
  context-grey: "#dce5e8"
  muted-ink: "#56636b"
  divider: "#d8dedf"
  annotation: "#aabdc5"
  inverse-secondary-text: "#d3dfe3"
  ongoing-surface: "#e5ebed"
  note-surface: "#edf1f2"
  field-border: "#7d8b92"
  error-ink: "#8b2025"
  error-surface: "#fff0ed"
typography:
  display:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "clamp(3.3rem, 6.5vw, 6rem)"
    fontWeight: 850
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  page-display:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "clamp(3rem, 5.8vw, 5.6rem)"
    fontWeight: 750
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "clamp(2.35rem, 3.8vw, 3.6rem)"
    fontWeight: 650
    lineHeight: 1.08
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "1.7rem"
    fontWeight: 650
    lineHeight: 1.17
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.55
  compact-body:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "16px"
    fontWeight: 600
  small:
    fontFamily: "Hanken Grotesk, sans-serif"
    fontSize: "15px"
    lineHeight: 1.6
rounded:
  control: "4px"
spacing:
  small: "8px"
  medium: "16px"
  group: "24px"
  panel: "32px"
  section-mobile: "56px"
  section-tablet: "72px"
  section-desktop: "96px"
components:
  button-primary:
    backgroundColor: "{colors.deep-ink}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    padding: "15px 24px"
  button-primary-hover:
    backgroundColor: "{colors.deep-ink-hover}"
    textColor: "{colors.white}"
  button-light:
    backgroundColor: "{colors.context-grey}"
    textColor: "{colors.reading-ink}"
    rounded: "{rounded.control}"
    padding: "15px 24px"
  field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.reading-ink}"
    rounded: "{rounded.control}"
    padding: "13px 14px"
  contact-panel:
    backgroundColor: "{colors.soft-white}"
    textColor: "{colors.reading-ink}"
    padding: "36px"
---

# Design System: Find Sherpas

## Overview

**Creative North Star: "Customer language, understood"**

The public site uses confident humanist typography, broad fields of deep ink and soft white, and restrained blue-grey highlights to make the interpretation of a search query visible. The work feels specific through real explanations and interactive examples. Flat surfaces and generous space keep the content readable.

This system replaces the former teal/Geist marketing identity under the September 2026 redesign. Its authority covers `app/(site)` and the public components. The CRM, private reports and audit tooling keep their existing styles. Existing articles and technical resources retain their content and diagrams; their older decorative treatments are not a template for new marketing pages.

**Key Characteristics:**

- Broad, heavy Hanken Grotesk headlines with clear supporting copy.
- Deep-ink fields, soft-white sections and contextual blue-grey highlights.
- Flat panels, fine dividers, bracket geometry and consistent SVG arrows.
- Specific search examples with explicit illustration labels.
- Responsive layouts and visible keyboard focus.

## Colors

### Primary

Deep Ink carries the query demonstration, closing invitation and primary controls. Its darker hover value provides state feedback without introducing another accent.

### Secondary

Context Grey marks interpreted context and provides a contrasting action on ink. Inverse Secondary Text and Annotation are the lighter blue-grey values used within the dark field.

### Neutral

Reading Ink is the primary reading colour; Muted Ink is supporting text. Soft White and White separate sections. Divider and Field Border distinguish structural lines from interactive fields. Ongoing Surface and Note Surface are the low-chroma blue-grey panel fills used for explanatory passages.

Error Ink on Error Surface is reserved for form feedback.

**The Surface Contrast Rule.** Focus outlines and supporting copy follow the surface underneath them: ink on paper; blue-grey or white on ink.

## Typography

Hanken Grotesk is the public display and body face, self-hosted through Next font with Latin and Latin Extended subsets. Geist remains available to the separate application and older technical figures.

The headline hierarchy is deliberately pronounced. Display is the largest and heaviest role; section headlines are lighter; body copy remains regular and comfortably spaced. Headings use balanced wrapping. Small labels are sentence case.

The homepage display contracts on mobile to `clamp(2.3rem, 11.8vw, 5.2rem)`. Ordinary page displays use their own fluid scale. Prose is generally constrained to about 65 characters per line; article content has a dedicated reading-width wrapper.

**The Meaning Before Decoration Rule.** Query words and their semantic annotations carry the visual idea. Typography does not require a decorative eyebrow to introduce a heading.

## Layout

The public site uses full-width sections with shared horizontal gutters. Desktop section padding is 4.2% horizontally, with the documented section spacing vertically. Two-column introductions pair a heading with supporting copy; detail rows pair the topic with the explanation. The engagement comparison uses adjacent contrasting panels.

At 760px and below, layouts become a single reading column with 24px gutters. The header becomes a keyboard-accessible menu. At 1100px the desktop density tightens; below 1281px the homepage header uses a single paper field to keep navigation on a consistent background. Above 1600px the content uses calculated gutters around a 1480px reference width.

The homepage's split opening and route strategy belong to its surface brief. They are not compulsory templates for other pages.

Framework field guides are the deliberate long-form exception. They open with a broad split editorial hero, then use a full-width Deep Ink principle and sequence to orient the reader before the detailed material. A numbered index leads into open, divider-led diagnostic stages: the stage title remains alongside evidence, actions and a decision rule on wide screens, then returns to normal document flow below 760px. The guide closes with a working method, a horizontally scrollable worksheet and two plain continuation links. Preserve that locate → inspect → act → record → continue reading order when extending the pattern.

## Elevation & Depth

The new marketing system is flat. Surface colour, whitespace and fine borders establish hierarchy; shadows are not part of its component vocabulary. Legacy resource diagrams may retain older container treatments without making them normative.

## Shapes

Controls have a small corner radius. Section panels have square corners. The wordmark uses four precise open brackets, rendered as an SVG. Arrows use Lucide's consistent stroke grammar.

**The Flat Form Rule.** Use an open layout, a tonal panel or a fine divider to group content. Do not add nested card shells to ordinary prose.

## Components

### Buttons

Primary controls use Deep Ink and white text. On a deep-ink closing section the action uses Context Grey; the homepage header uses a white variant. Buttons have a minimum height of 56px on desktop and 54px on mobile, with inline SVG arrows. Hover changes colour and moves the arrow slightly. Disabled submission controls remain visible with reduced opacity.

### Inputs / Fields

White fields have a distinct fine border, small corner radius, persistent visible labels and regular body typography. The contact form displays loading, error and success states; errors retain the entered message and receive focus. Successful submission is announced through a status region.

### Contact location

The contact route pairs a Deep Ink address field with an edge-to-edge live OpenStreetMap embed in a 36/64 desktop split. Below 760px, the address precedes a 390px-tall map. Keep the external OpenStreetMap link visibly underlined, the iframe titled and lazy-loaded, and the map attribution visible.

### Navigation

The desktop navigation is text-based with underline feedback for hover and the current route. A compact menu replaces it on mobile. The menu moves focus inside, contains Tab navigation, closes on Escape and restores focus to the trigger. The public layout includes a skip-to-content link.

### Query interpretation

Large query words sit in a deep-ink field. Fine horizontal connectors name product and colour; a blue-grey phrase and vertical connectors expose seasonal and occasion context. Language buttons use pressed states and update the explanatory text. The highlighted phrase reveals through a short clip animation; reduced-motion preferences disable animation and transitions.

### Search schematics

Small search concepts use a shared framed pictogram grammar: inline 136×80 SVGs with 1.5px non-scaling current-colour strokes, restrained muted structure and Context Grey signal fills. They diagram search mechanics rather than act as decorative icons. At mobile widths they reduce to 72px while preserving their aspect ratio and legibility.

### Search demonstration

Scenario controls select an illustrative shop recording. A responsive poster and explicit Play example button provide the idle preview. On activation, the video starts with native controls. Poster and video variants follow the mobile breakpoint together. The fiction label and textual explanation remain visible outside the media.

### Text links and reading lists

Text links pair an underlined action with an SVG arrow. Writing and expertise lists use spacious rows and dividers instead of decorative cards. Articles keep their source content in a reading-width wrapper.

### Framework field guides

Framework pages turn an abstract method into an operational reading sequence. Use the large split hero, Deep Ink principle band, numbered sequence and stage index once at the top; do not repeat them as decorative section furniture. Each diagnostic stage combines explanatory prose with one clearly labelled example, compact question/evidence/action lists and a tonal decision rule. Keep stages, working method, worksheet and related routes as open editorial regions separated by surface changes and fine rules, not nested cards.

On these unusually long guides, the floating “To the top” control appears only after the reader has passed the greater of 0.75 viewport or 520px. While analytics consent is visible, the control moves 12px above it to avoid a collision. Before then it stays outside pointer, keyboard and accessibility navigation; activation scrolls smoothly unless reduced motion is preferred, and its dual white-and-Deep-Ink focus ring must remain legible while crossing light and dark sections.

## Do's and Don'ts

### Do:

- Do use deep ink as a substantial field where it supports the subject.
- Do label fictional demonstrations and distinguish prior experience from agency results.
- Do match focus colour to the underlying surface.
- Do use the public font and token scope without changing the CRM.
- Do retain clear reading order and useful controls at mobile widths.
- Do make every framework stage resolve from symptom to evidence, decision and next action.

### Don't:

- Don't invent clients, performance numbers or team biographies to fill a layout.
- Don't revive the former teal marketing identity inside the redesigned routes.
- Don't add gradients, decorative shadows, eyebrow labels or glyph substitutes for icons to new marketing content.
- Don't promote legacy resource styling into the new component system.
