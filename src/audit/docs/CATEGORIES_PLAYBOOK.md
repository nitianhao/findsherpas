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

### zalando.co.uk (Zalando UK, MARKETPLACE_MIXED)
- Base `select_categories` output (16): DIRECT_MATCH, TYPO, SYNONYM, BRAND_SEARCH,
  NATURAL_LANGUAGE, CATEGORY_MAPPING, FACET_EXTRACTION, NEGATIVE_INTENT, MULTI_ATTRIBUTE,
  PLURAL_SINGULAR, PARTIAL_QUERY, SUBJECTIVE_ATTRIBUTE, PRICE_ANCHORED, SPECIAL_CHARACTER,
  MERGED_WORDS, SEASONAL_OCCASION.
- User asked for an **exhaustive** audit. Added all 9 remaining enum values:
  SKU_MODEL_NUMBER, LOCALE_VARIATION, ABBREVIATION, UNIT_VARIATION, OCCASION,
  SEMANTIC_MEANING, LONG_VERBOSE_QUERY, STOP_WORD_HEAVY, SPLIT_WORD.
  **Final count: 25 — every category except retired BROAD_CATEGORY.** Well above the
  12-16 target, deliberately, same as cotswoldoutdoor.com.
- Highest-signal picks for this host specifically:
  - **LOCALE_VARIATION** — German-run marketplace on a `.co.uk` domain, so UK/US term
    splits (trainers/sneakers, jumper/sweater, trousers/pants, pyjamas/pajamas) are the
    sharpest Zalando-specific test.
  - **SKU_MODEL_NUMBER** — Zalando prints an article number (`NI114D0A1-Q11` format) on
    every PDP; customers paste it back into search.
  - **UNIT_VARIATION** — UK vs EU shoe sizing ("size 9" vs "size 43").

## General learnings addendum
- **There is no way to add a site-specific *category*.** `QueryCategory` is a fixed enum in
  `src/models.py`; new values would ripple into the query generator, judge, and report
  renderer. When a user asks for "site-specific categories", express the site-specific
  character as **query content within existing categories** at Phase 3 instead (e.g.
  Zalando's article-number format inside SKU_MODEL_NUMBER, the site's own taxonomy wording
  like "Tracksuit bottoms"/"Print T-shirt" inside CATEGORY_MAPPING and DIRECT_MATCH).

## GIBBERISH — new category added 2026-09-16 (operator request, douglas.de audit)

`QueryCategory.GIBBERISH` was ADDED to the enum in `src/models.py` and mapped to
`CapabilityGroup.TYPO_TOLERANCE`. This is the first genuine addition to the enum —
previously the playbook said site-specific categories were impossible, and that stands:
GIBBERISH is not site-specific, it is a universal capability test, which is why it
earned an enum value rather than being filed inside TYPO.

**What it tests:** pure keyboard mash. **The correct answer is ZERO results.** A search
engine that returns a populated grid for gibberish has no no-results state at all. Two
consequences worth stating in any report: a badly-mistyping customer gets a dead end
dressed up as a result page, and the retailer's own search analytics cannot separate
real demand from noise or bot traffic.

**How to write the queries** (4 is enough; since 2026-10-30 `query_generator.build_gibberish` writes them in code — no LLM — and caps the category at 4, reallocating any extra budget):
1. A long mash, 50+ chars — e.g. `sfjhdshdssjhdfdsshsdhgsddgshdghshdksghskgdhgshkhkghkskhksdnsidssi`.
2. A keyboard-row run in the site's locale — `qwertzuiop` for a DE/AT/CH site (also CZ/SK/HU, and fr-CH: Swiss keyboards are QWERTZ), `azertyuiop` for FR/BE, `qwertyuiop` elsewhere. Region in `SiteContext.locale` decides first, then language.
3. A mixed consonant mash — `xkvbnmqwertzasdfg`. (Code uses `xkvbnmwrtsdfg`: the original example shares x/q/z with (4), which defeats the no-shared-characters pairing.)
4. A repeated-letter mash **sharing no characters with (3)** — `zzzqqqxxxyyy` (code: `zzzqqqjjjyyy`).
   Pairing (3) and (4) is the sharp test: if two inputs with no characters in common return
   the SAME products, the engine is serving a generic fallback list rather than matching
   anything. On douglas.de they shared 2 of the top 6.

**douglas.de result (2026-09-16): 0/4 correct.** All four returned 98-100 results, no
"Meintest du", no zero state. The count clustering at ~98-100 across unrelated inputs is
itself the tell of a capped default list.

## Selector behaviour as of 2026-10-30 (code changes)

- **Structured call** (`_call_llm`, phase `categories`, `AUDIT_MODEL_CATEGORIES`). Static rules and the
  category library live in the system prompt; the library count is computed (26 offerable = every enum
  value except retired BROAD_CATEGORY). `CATEGORY_DESCRIPTIONS` now covers every enum value including
  GIBBERISH (the CLI demo used to KeyError).
- **Site-type override is real now.** When the LLM corrects `site_type`, `site_context.site_type` is
  updated and the selection is re-asked against the NEW type's defaults (a second call); the first
  round's adds/removes were reasoned against the wrong defaults and are discarded. The change is
  recorded in `provenance['categories_site_type_override']`.
- **Bounds enforced in code: 10–18.** Too many → the latest additions are dropped first; too few → removed
  defaults are restored first. BROAD_CATEGORY is rejected in code even if the LLM adds it. An operator who
  wants 20–25 (cotswold, zalando) edits the list after Phase 2 as before.
- **No silent fallback.** `provenance['categories']` = `llm` or `fallback: <error>`; with
  `AUDIT_STRICT_LLM=1` (default) a failed call raises. Also recorded: `categories_model`,
  `categories_prompt_sha256`, `categories_generated_at`, `categories_adjustments` (each add/remove with its reason).

## When you learn something new

After every Phase 2 edit, append a per-site profile (which categories to force-include or
force-drop for this host and why) or a By-site-type refinement if it generalizes.
