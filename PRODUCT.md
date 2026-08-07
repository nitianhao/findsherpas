# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary buyers are the people accountable for on-site search performance at ecommerce and marketplace companies: product leads, heads of product, CRO/CPOs, and ecommerce managers. Their operating context: catalogs from 10k to 10M+ SKUs, high-traffic search, complex ranking/boosting logic, on vendors like Algolia, Elasticsearch, or Typesense, often serving multilingual European markets.

Scope note: this record covers the public marketing site only (`app/(site)/*`). The internal CRM app (`app/crm/*`) is out of scope for now — team ops tooling, not a design priority at this time.

## Product Purpose

Find Sherpas diagnoses why on-site search returns the wrong results and maps a prioritized, actionable path to fixing it. Deliverables: query classes and broken-query examples, a failure-mode summary, ranking recommendations with examples, UX findings (facets, sorting, zero-results), and a prioritized improvement roadmap. Success means reduced zero-results rate, improved product discovery, and a client team that knows exactly what to fix next.

## Positioning

A specialist, vendor-independent audit — not a generalist agency service. Explicitly not SEO, not CRO, not a vendor implementation partner. Works across search vendors (Algolia, Elasticsearch, Typesense, others) rather than being tied to one. Scope is narrow and deliberate: internal/on-site search for ecommerce and marketplace sites only, which a general UX or SEO shop could not credibly claim.

## Operating Context

Engagement model: tiered one-time audit purchases via Stripe Checkout (Starter / Growth / Enterprise), a free "search-check" tool as a lead magnet, and a book-a-call flow for larger engagements. Blog and case studies serve as content marketing and authority-building; "frameworks" pages (search failure modes, query interpretation) establish domain expertise publicly.

## Capabilities and Constraints

Confirmed: vendor-agnostic methodology (Algolia, Elasticsearch, Typesense); handles catalog scale from 10k to 10M+ SKUs; supports multilingual/European markets. Explicitly out of scope: SEO work, CRO work, vendor implementation/migration work.

Undecided: whether the underlying audit pipeline's methodology details (e.g. automated/structured query evaluation) become a customer-facing claim — do not surface implementation specifics as marketing copy without confirming with the user first.

## Brand Commitments

Name: "Find Sherpas." Confirmed: the "sherpa" (mountain guide) reference is just the company name — not a locked identity element. Future work has no obligation to lean into guide/journey/mountain motifs visually or verbally, and should not assume that direction without a separate decision. Contact: michal@findsherpas.com.

## Evidence on Hand

The one published case study ("Search UX quick wins") is currently a placeholder — client name, outcome metrics, and details are explicitly marked "coming soon" in its frontmatter. No real client names, quotes, or metrics exist yet. One live blog post exists ("Welcome to Find Sherpas"). No testimonials are on file. Pricing tiers (Starter/Growth/Enterprise) exist as real Stripe Price IDs in the current implementation — treat the tier structure as real, but do not invent specific price points, feature lists, or client-facing proof beyond what's already written in the codebase.

## Product Principles

- Search-only specialism: go deep on internal/on-site search; resist scope creep into SEO, CRO, or general UX work that would dilute the expert positioning.
- Vendor independence: audits and recommendations must read as agnostic to the underlying search engine; never imply lock-in to or partnership with one vendor.
- Ecommerce/marketplace-only: the target buyer runs a catalog-driven business, not a general SaaS or content site — copy and examples should stay in that world.
- Evidence-led, not hype: findings come from structured relevance evaluation and real query analysis; don't fabricate proof (testimonials, metrics, named clients) while the case-study/evidence base is still a placeholder.
- Diagnosis ends in action: every audit resolves to a prioritized, actionable roadmap, not just a list of problems.
