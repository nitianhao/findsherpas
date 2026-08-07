---
target: the homepage
total_score: 24
max_score: 32
na_heuristics: 7,10
p0_count: 1
p1_count: 4
timestamp: 2026-08-07T10-54-41Z
slug: app-site-page-tsx
---
Method: dual-agent (A: general-purpose · B: general-purpose)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Spine dot gives a live-position cue on desktop; no mobile equivalent |
| 2 | Match Between System and Real World | 4 | Vocabulary and examples are drawn from real ecommerce search practice |
| 3 | User Control and Freedom | 3 | Mobile menu handles focus/Escape correctly; but "back" only returns to page top, not to a section |
| 4 | Consistency and Standards | 2 | Page violates its own DESIGN.md: global gradient wash, multiple simultaneous Signal Teal elements at rest, a raw un-tokened `teal-700` hover class on links |
| 5 | Error Prevention | 3 | No destructive controls on this page to assess |
| 6 | Recognition Rather Than Recall | 3 | Consistent card/eyebrow-label pattern across sections |
| 7 | Flexibility and Efficiency of Use | n/a | Single-visit marketing page — no repeat-use accelerators expected |
| 8 | Aesthetic and Minimalist Design | 3 | Clean type/whitespace, but gradient + dual-teal moments fight the "quiet by default" system |
| 9 | Error Recovery | 3 | No error states present; no negative evidence found |
| 10 | Help and Documentation | n/a | No task complex enough on a landing page to need in-context help |
| **Total** | | **24/32** | **Good (75%)** — n/a on #7, #10 (single-session marketing surface, no power-user workflow) |

## Design Specificity Verdict

**LLM assessment:** The copy is genuinely specific — "red dress size 38" treated as free text, a boosting rule silently overriding textual relevance — written by someone who has actually read ecommerce search logs, not generic B2B filler. But the visual execution undercuts that specificity: a persistent gradient wash sits behind every page (`app/(site)/layout.tsx:15`), directly contradicting DESIGN.md's own anti-reference ("gradient meshes… rejected"); section iconography is stock Lucide glyphs any SaaS product would use; and the system's one named signature differentiator — Geist Mono for data — doesn't appear until ~80% down the page. Swap "search" for "supplier compliance" and most of the first two viewports would pass as a different B2B tool unnoticed. The specificity lives in the prose, not yet in the design system's execution of itself.

**Deterministic scan:** CLI static scan (`detect.mjs` over `app/(site)/page.tsx` + `components/site`) came back clean — exit 0, zero findings. The **in-browser runtime detector** (computed-style/layout level, which the static scan can't see) found 11 anti-patterns on desktop: `all-caps-body` ×1 (uppercase applied to a 76-character span — text that long belongs in Body, not the Label role), `overused-font` ×1 (**the live page's computed primary font is "Inter," 100% of text — not Geist Sans as DESIGN.md documents**), and `text-overflow` ×9 on `a.hover:text-teal-700` links, overflowing their containers by 23–82px. At mobile width (390×844) only the `all-caps-body` and `overused-font` findings recurred; the 9 overflow instances did not reproduce, suggesting they're tied to a wider-viewport layout state. The `teal-700` class name is itself notable: it's a raw Tailwind color, not one of DESIGN.md's OKLCH tokens, so this is a second, independent piece of evidence for the same consistency violation the design review flagged in heuristic #4.

**Visual overlays:** Browser-side overlay injection succeeded; the assessment agent read the live console output directly (findings above) rather than presenting a persistent on-page overlay to the user in this run.

## Overall Impression

The prose and diagnostic methodology are the real asset here — specific, credible, written by someone who's actually looked at broken search. The visual system doesn't yet back that up: it breaks its own documented rules (gradient, multiple simultaneous accents, an untokened raw color), the primary conversion button fails contrast, and the page isn't even rendering the typeface the design system claims. The single biggest opportunity is tightening the gap between "what the copy proves" and "what the pixels show" — right now the design reads more generic-SaaS than the words do.

## What's Working

- **Diagnostic-example section**: the query → observed behavior → root-causes flow, placed right before the closing CTA, is a genuine "here's proof of method" moment exactly where a skeptical reader needs it.
- **Spine scroll-spy nav**: on desktop it's cleanly implemented (correct IntersectionObserver-driven active state) and actually reads as the "instrument gauge" DESIGN.md describes — real differentiation when it's working.
- **Card discipline**: `border-border/50` on the pattern cards correctly matches DESIGN.md's "quieter grid" guidance — a fidelity check that passed.

## Priority Issues

**[P0] Primary CTA fails contrast.** The "Book a call" button (white text on Signal Teal) measures **3.12:1**, below WCAG AA's 4.5:1 for normal text. Why it matters: this is the single conversion action the whole page exists to drive, appearing 3 times — a legibility failure here undermines the entire funnel and is a real accessibility risk. Fix: darken the teal or switch to near-black button text; re-verify ≥4.5:1. Suggested command: `$impeccable harden`.

**[P1] Design system violates its own stated rules.** A global gradient wash sits behind every page (`layout.tsx:15`), and the search-check promo section shows Signal Teal simultaneously on the CTA, six numbered badges, the card border tint, and a floating scroll-to-top FAB — all at rest. This directly contradicts DESIGN.md's anti-reference and its "One Signal Rule." Fix: remove the global gradient, recolor the numbered badges to ink-outlined circles, mute the FAB to an outline treatment. Suggested command: `$impeccable quieter`.

**[P1] Live page doesn't render the documented type/color system.** The browser detector measured the page's computed primary font as Inter at 100% of text — not Geist Sans as `next/font` and DESIGN.md specify — and found a raw untokened `teal-700` Tailwind class driving link hover color instead of a DESIGN.md token. Why it matters: this is a gap between the documented system and what's actually shipping; either the font isn't loading/applying as intended, or a fallback is silently winning. Fix: verify `font-sans`/`--font-geist-sans` is actually applied to `body` (or wherever this is falling through), and replace `hover:text-teal-700` with the `signal-teal` token. Suggested command: `$impeccable audit`.

**[P1] Nine link instances overflow their containers.** The runtime detector found `a.hover:text-teal-700` overflowing its container by 23–82px in 9 places at desktop width; none reproduced at mobile width. Why it matters: visible layout breakage on a marketing page undermines the "precise and restrained" positioning the whole system is built on. Fix: audit the affected link containers for width/white-space handling at desktop breakpoints. Suggested command: `$impeccable audit`.

**[P1] Cognitive load is high — 4 of 8 checklist items fail.** Several sections show 5-6 items in one group ("How we diagnose" = 6 steps, "Search environments" = 5 stats, "What the diagnostic produces" = 5 items), the desktop header presents 7 simultaneous nav choices, and most sections inline full detail rather than teaser-plus-link. Why it matters: a scanning evaluator (not a linear reader) faces an uncapped stream of dense content before the value proposition fully lands, raising bounce risk. Fix: cap dense lists to 4 visible items with "see more," and collapse the header nav to 3-4 primary links. Suggested command: `$impeccable layout`.

**[P2] The signature "Mono-for-Data" device arrives too late.** The first real Geist Mono data figure shows up ~80% down the page; the hero and "What we find" section contain implicit data (query examples, pattern labels) but don't use it. Why it matters: this is the system's one named differentiator — burying it means the top of the funnel reads as generic SaaS despite specific copy. Fix: pull one real query/rank snippet into the hero, set in Geist Mono. Suggested command: `$impeccable distill`.

**[P3] Inconsistent framework-card link pattern.** "Framework 01: Relevance evaluation" links to `/search-check` while Frameworks 02 and 03 link to dedicated `/frameworks/*` pages — a broken implicit promise across an otherwise-identical card pattern. Fix: either build a matching framework page or relabel the card. Suggested command: `$impeccable clarify`.

## Persona Red Flags

**Jordan (first-timer):** Lands on a 6-link, 7-choice header with nothing signaling "start here" beyond the hero. Clicks "Relevance evaluation" expecting an article like its two neighbors, gets redirected to the search-check tool instead. Never sees a mockup of what a delivered audit report actually looks like.

**Riley (stress tester):** Measures the CTA at 3.12:1 — fails AA. Finds three simultaneous Signal Teal elements at rest in one section, directly against the documented One Signal Rule. Finds the page-wide gradient contradicting DESIGN.md's anti-reference almost word for word. Confirms the Framework 01 link mismatch by clicking it.

**Casey (distracted mobile user):** On mobile, "Book a call" isn't in the visible top bar — it's one level inside the hamburger menu, so once scrolled past the hero it takes 2 taps into a hidden menu to convert. The page is one long ~9000px scroll with only two CTA touchpoints between the hero and the close.

**Priya (Head of Product — project-specific persona, derived from PRODUCT.md's audience):** Looks for proof before committing 30 minutes to a call — finds no case study, named client, or metric anywhere (consistent with PRODUCT.md noting the evidence base is still placeholder, but nothing else compensates: no team bio, no "why us" beyond a methodology description). Looks for pricing to self-qualify — Starter/Growth/Enterprise tiers exist per PRODUCT.md but are absent from the homepage. Notices the only contact channel is a personal address (`michal@findsherpas.com`) rather than a team alias, which reads as under-resourced for an enterprise buying decision.

## Minor Observations

- Header logo mark is a mountain/triangle glyph — quietly reintroduces the "sherpa" guide motif that PRODUCT.md explicitly says is *not* a locked identity element; worth a deliberate call rather than an implicit one.
- Step numbers (01–06) use `tabular-nums` but not `font-mono` — an easy, obvious spot to reinforce the Mono-for-Data rule.
- `ScrollToTop` FAB is a second always-visible teal element present on every scroll, compounding the One Signal Rule violation beyond just the promo section.
- Header logo's empty `alt=""` is correct — adjacent visible "Find Sherpas" text already labels it.

## Questions to Consider

- What if the hero contained one real ranking-failure snippet in Geist Mono, instead of making visitors scroll ~2500px before the signature "data register" appears at all?
- What if the free search-check tool were the primary hero CTA and "Book a call" the secondary — since a skeptical evaluator is more likely to self-qualify with a 5-minute tool than give up 30 minutes for a first call?
- If the page fully committed to "one signal" — no gradient, ink-outlined badges, muted FAB — would that visible restraint itself become the strongest piece of evidence that "we notice small things everyone else misses" is true?

## Run Notes

- Target slug: `app-site-page-tsx` (resolved from `app/(site)/page.tsx`)
- Ignore list: none present (`.impeccable/critique/ignore.md` does not exist)
- Assessment independence: A and B ran as isolated parallel sub-agents, no cross-visibility
- CLI detector: ran clean, exit 0, 0 findings (static scan only — see runtime detector above for what it missed)
- Browser visibility / overlay injection: succeeded; live server started, `/detect.js` injected, console read, then stopped cleanly (confirmed via failed follow-up request to the port)
- One transient tab-routing hiccup during Assessment B (browser tab briefly pointed at an unrelated app on port 3450 mid-run) — self-corrected by re-navigating; not a design finding
- Live server cleanup: confirmed stopped
