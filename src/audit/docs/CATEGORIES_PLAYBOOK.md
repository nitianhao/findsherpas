# Categories Playbook — Phase 2 knowledge base

> **Read this BEFORE running Phase 2 (`select_categories`).** It records which query
> categories tend to fire wrongly per site type and per site, so we don't re-tune the
> same set each audit. When the user adds/removes categories, capture the reasoning here.
>
> Companion docs: `ARCHITECTURE.md` and the `synthetic-search-audit` skill. This file is
> operational memory for the **category selection** phase specifically.

---

## How to use this file

1. Before Phase 2, check the **Per-site profile** and the **By site-type** notes below.
   Apply known add/remove decisions before presenting the selection to the user.
2. Target **12–16** categories. Categories are `QueryCategory` enum values — when editing,
   rebuild as `list[QueryCategory]` from the enum directly.
3. After the user edits the set, record why a category was added or dropped.

---

## General learnings (apply to every site)

- Keep the set to **12–16**. Fewer than ~12 under-tests the search engine; more than ~16
  dilutes the report with low-signal queries.
- Categories must be **answerable by the site's catalog**. Selecting a category the site
  has no inventory for guarantees zero-result queries that look like search failures but
  are really category-selection errors.
- The category set should follow `site_type` (set in Phase 1). A wrong `site_type` shows
  up here as obviously off categories — if that happens, go back and fix discovery.
- **BROAD_CATEGORY is retired (do not offer it).** It tested the user typing the site's
  *own* category term ("knitwear", "coats") — low-signal and overlapping with
  CATEGORY_MAPPING. We only test the harder, more realistic case where the user types a
  *colloquial/different* word than the site taxonomy → **CATEGORY_MAPPING** only. Removed
  from all `SITE_TYPE_DEFAULTS`, the selector's description library, and query generation
  (enum kept only for backward-compat with old reports).
- **`USE_CASE` is renamed to `OCCASION`** (enum value `OCCASION`, label "Occasion"). Same
  meaning: queries describing the occasion/purpose, not the product ("gift for dad",
  "housewarming present"). Distinct from `SEASONAL_OCCASION` (date/event-driven).

## By site-type

| site_type | Categories that usually fit | Categories to usually drop |
|---|---|---|
| PHYSICAL_GOODS | product attributes, occasion, brand, price-tier, compatibility | service/booking-style categories; BROAD_CATEGORY (retired) |
| MARKETPLACE_MIXED | category-mapping, brand, gift/occasion, narrow intent | BROAD_CATEGORY (retired) |
| SERVICES_EXPERIENCES | location, date/availability, experience-type, party-size | hard SKU/spec categories; BROAD_CATEGORY (retired) |

_(refine these rows as the user teaches the real distinctions)_

---

## Per-site profiles

### baechli-bergsport.ch (Bächli Bergsport, PHYSICAL_GOODS)
- Base selection (14): DIRECT_MATCH, TYPO, SYNONYM, MERGED_WORDS, SPLIT_WORD, BRAND_SEARCH, PLURAL_SINGULAR, MULTI_ATTRIBUTE, ABBREVIATION, SPECIAL_CHARACTER, PARTIAL_QUERY, LOCALE_VARIATION, SEASONAL_OCCASION, CATEGORY_MAPPING.
- User requested "misspelled brand" + "price tier" added. Neither exists as a dedicated `QueryCategory` enum value — closest matches are **PRICE_ANCHORED** (price-tier intent) and **TYPO** (already in set; misspelled-brand queries are generated as a TYPO variant targeting a brand name rather than a new category). Added `PRICE_ANCHORED`, kept TYPO to cover misspelled-brand. Final count: 15.

---

### bergzeit.de (Bergzeit, PHYSICAL_GOODS)
- Base selection (15): DIRECT_MATCH, TYPO, SYNONYM, MERGED_WORDS, SPLIT_WORD, BRAND_SEARCH, PLURAL_SINGULAR, MULTI_ATTRIBUTE, ABBREVIATION, SPECIAL_CHARACTER, PARTIAL_QUERY, NATURAL_LANGUAGE, SEASONAL_OCCASION, CATEGORY_MAPPING, SUBJECTIVE_ATTRIBUTE.
- User kept NATURAL_LANGUAGE and added PRICE_ANCHORED (price-tier intent queries). Final count: 16.

### cotswoldoutdoor.com (Cotswold Outdoor, MARKETPLACE_MIXED)
- Base selection (14): DIRECT_MATCH, TYPO, SYNONYM, MERGED_WORDS, SPLIT_WORD, BRAND_SEARCH, SKU_MODEL_NUMBER, PLURAL_SINGULAR, MULTI_ATTRIBUTE, ABBREVIATION, SPECIAL_CHARACTER, PARTIAL_QUERY, SEASONAL_OCCASION, SEMANTIC_MEANING.
- User asked to add more broadly ("add more", then "add all of them" from the suggested list). Added CATEGORY_MAPPING, PRICE_ANCHORED, SUBJECTIVE_ATTRIBUTE, NATURAL_LANGUAGE, OCCASION, FACET_EXTRACTION. Final count: 20 — above the usual 12-16 target, but user explicitly wanted full breadth for this audit.

## When you learn something new

After every Phase 2 edit, append a per-site profile (which categories to force-include or
force-drop for this host and why) or a By-site-type refinement if it generalizes.
