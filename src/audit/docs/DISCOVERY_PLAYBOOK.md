# Discovery Playbook — Phase 1 knowledge base

> **Read this BEFORE running Phase 1 (`discover_from_search_url`).** It records what
> the discovery step gets wrong per site and in general, so we don't re-learn the same
> corrections each audit. When the user corrects a discovery result, add the learning here.
>
> Companion docs: `ARCHITECTURE.md` (how the pipeline is built) and the
> `synthetic-search-audit` skill (how to run it). This file is operational memory for
> the **discovery** phase specifically.

---

## How to use this file

1. Before Phase 1, check whether the target host has a **Per-site profile** below. If it
   does, you already know the correct `site_type`, the working `search_url_template`, and
   which brands/categories discovery tends to hallucinate or miss — apply them and present
   the corrected `SiteContext` to the user up front.
2. If the host is new, run discovery, present all fields, and capture the user's
   corrections. Once confirmed, **write a new per-site profile** below.
3. Fold any cross-site pattern the user teaches (not site-specific) into **General
   learnings**.

---

## General learnings (apply to every site)

| Field | Common failure | What to do |
|---|---|---|
| **site_type** | Discovery mis-classifies (e.g. a department store read as SERVICES_EXPERIENCES). The downstream category/query generation keys off this, so a wrong type poisons everything after it. | Sanity-check against the nav: broad goods catalog across departments → MARKETPLACE_MIXED; single physical-product catalog → PHYSICAL_GOODS; bookings/appointments/experiences → SERVICES_EXPERIENCES. Correct before saving. |
| **search_url_template** | The single most important field — every query is built from it. A wrong template (wrong param name, missing path, encoded `{}`) silently breaks the entire fetch. | Confirm it matches the live search URL the user gave, with `{}` where the query goes. Test it mentally: `template.format("test")` should equal a real search URL. |
| **brands** | Discovery invents brands the site does not carry, or misses house brands. | Verify against a real brand/`/brands` page when one exists. Drop hallucinated brands; they cause hallucinated queries in Phase 3. |
| **nav_categories** | Pulls marketing nav ("New", "Sale", "Gift Guide") instead of real product departments. | Prefer real catalog departments over promotional nav entries. |
| **featured_items** | Misses signature/hero products that make the best test queries. | Add the site's signature products if the user names them — they anchor realistic queries. |
| **LLM refinement is the default (both entry points)** | The rule-based extractors are noisy: brand names land in `nav_categories`, `featured_items` fills with nav/legal/cart junk, and `site_type` is wrong (see next row). | `_refine_with_llm` (`AUDIT_MODEL_DISCOVERY`, default `claude-haiku-4-5-20251001`) runs at the end of **both** `discover_from_search_url` and `discover_site` (shared `_build_site_context`): it re-derives `site_type`, splits brands out of nav, cleans nav to real departments, and keeps only real products in `featured_items`. Since 2026-10-30 it is a structured call (no JSON parsing, 4000 max tokens) and every returned brand/nav/item must appear in the scraped lists or page text — anything else is dropped and listed in `provenance['refine_dropped']`. **No silent fallback:** a failure sets `provenance['refine'] = 'fallback: <error>'`, and with `AUDIT_STRICT_LLM=1` (default) discovery raises instead. Set `AUDIT_STRICT_LLM=0` to accept heuristic fields. Still review its output; it can miss user-known signature products. |
| **`_detect_site_type` experiential-noun bias** | The heuristic counts distinct substring hits over the scraped **homepage**. It over-weights experiential nouns (experience/heritage/café/visit/events/gifting) and can't see purchase signals — prices and add-to-cart live on **product pages**, not the homepage — so goods retailers with lifestyle/café/visitor framing score `service≥3 & goods≤1` and get misclassified as SERVICES_EXPERIENCES. English-only literal substrings also zero out non-English sites. | A goods retailer that *also* runs cafés/experiences is still a goods retailer → MARKETPLACE_MIXED or PHYSICAL_GOODS. The Haiku pass now corrects this; the heuristic is only the fallback. |


### Discovery behaviour as of 2026-10-30 (code changes — read before Phase 1)

| Area | Behaviour | Why |
|---|---|---|
| **Language / locale** | `_detect_language` returns `(language, BCP-47 locale, source)`. Order: `<html lang>` (English included) → `og:locale` → the hreflang entry whose href **is this page** (canonical/current URL) → locale path segment (`/sv/`, `/de-ch/`) → single-language ccTLD → multilingual ccTLD (.ch/.be/.ca/.lu) narrowed by the page's function words → function words alone → English. `SiteContext.locale` is filled (e.g. `de-CH`); `provenance['language']` names the source. | The old order skipped `lang="en"` and took the first non-English hreflang (en-GB page with a de-DE alternate → German), counted ä/ö as Nordic before checking German (German pages → Swedish), and hard-mapped .ch→German, .be→French. |
| **Currency** | `SiteContext.currency` (ISO-4217) from JSON-LD `priceCurrency`, then price meta tags, then price text (€, £, $, ¥, zł, Kč, CHF, SEK, DKK, NOK, PLN, CZK, `kr` resolved by locale: sv→SEK, da→DKK, nb→NOK; `$` by region). Unknown stays empty. Sampled result prices are a last resort. | Query generation writes price queries with the market's currency word. |
| **Catalog sample** | `catalog_sample` (~150 titles) = homepage titles + 5–8 seed searches built from the top nav departments (promo/editorial labels like Sale/Neu/Marken skipped; brands top up a thin nav) + the seed page, merged round-robin and deduped. Seeds go through the fetcher's public API (`fetch_all_outcomes`, untrusted outcomes ignored; falls back to `fetch_all_results`). Pass `sample_catalog=False` for a fast run; `fetch_fn=` to stub. `provenance['catalog_sample']` says how many seeds returned titles. | The seed query's results page alone biased every downstream phase (Zalando ~70% footwear, lyko all "Fresh", douglas all mascara). |
| **SKU codes** | JSON-LD `sku` / `mpn` / `gtin*` on Product/Offer nodes (seed page + homepage) are stored as JSON in `provenance['catalog_codes']`. SKU_MODEL_NUMBER queries are built only from these. | Generator-invented model numbers ("AM90", "NB 574") were plausible, not real. |
| **Fetch fallback** | `_fetch_html`: static fetch first; Playwright on any `requests.RequestException`, a bot-challenge marker (Cloudflare/Imperva/PerimeterX; weak markers like "captcha" only on near-textless pages), or a near-empty page (<200 chars of visible text). | Only `HTTPError` used to fall back; timeouts, resets and 200-status challenge pages went straight to parsing. |
| **`parse_search_url`** | Known search params are accepted with an empty value (`?utm_source=news&q=` → `q`); `utm_*`/`gclid`/`fbclid` are dropped from the template; `lang`, `sort`, `currency`, `page`, `country`… are never guessed as the search term; path-based search (`/search/<term>`, `/suche/<term>`, `/sok/<term>`…) yields `/search/{}`. | `?utm_source=news&q=` used to return `utm_source={}`, which sent every query into a tracking param. |
| **Site-type heuristic** | Keyword hits are whole-word (`book` no longer matches `facebook`, `spa`/`space`, `rent`/`current`); the price signal counts kr, zł, Kč, CHF, SEK etc. | Substring hits inflated the services score. |

The per-site "refinement fails to parse" notes below (manufactum.de, baechli-bergsport.ch, bergzeit.de) describe the pre-2026-10-30 JSON-text call. They are kept as history; with the structured call a failure now raises (strict) or is recorded in `provenance['refine']`.

---

## Per-site profiles

### avoca.com (Avoca — Irish department-store retailer)
- **site_type:** `MARKETPLACE_MIXED`. Heuristic mis-classified it as `SERVICES_EXPERIENCES` because of café/"Experience"/"Heritage"/"Visit Us" nav. It is a broad multi-department goods retailer (women's/men's fashion, beauty, homeware, food, gifts) that also carries third-party brands.
- **search_url_template:** `https://avoca.com/search?q={}` (correct as derived).
- **brands (verified):** American Vintage, Barbour, Craie Studio, HK Living, Jellycat, Love Beth, Never Fully Dressed, Waterdrop, FRNCH (+ Avoca house label). The rule-based scraper left these in `nav_categories`; Haiku split them out correctly. FRNCH was recovered from page text (not in the raw nav list).
- **featured_items (signature products, user-supplied):** `Stone Snow Esia Single Breasted Jacket`, `1960's Space Exploration Sheep Mug`, `Shea Verbena Hands & Body Liquid Soap`. **These three double as exact-match queries in Phase 3 — see QUERIES_PLAYBOOK.**
- **Language:** English.

### manufactum.de (Manufactum — German durable-quality-goods retailer)
- **site_type:** `MARKETPLACE_MIXED`. Broad multi-department catalog (garden, kitchen, home, household, office, books, clothing, food, body care) of long-lasting, traditionally-made goods; also carries third-party brands.
- **search_url_template:** `https://www.manufactum.de/suche/?q={}` (correct as derived).
- **Haiku refinement fails to parse** on this site (JSON parse error mid-response) → falls back to heuristic, which leaves brands/featured empty and pulls marketing nav. Clean nav manually: drop `SALE`, `NEU`, `Journal`, `Herstellerporträts`, `Startseite`; keep real departments.
- **brands (user-supplied):** CHICO Hängematten, Heimgart, Armedangels.
- **featured_items (signature products, user-supplied, double as exact-match queries):** `Tischleuchte Sonnenglas® (Generation 6)`, `Bio-Spätburgunder Tor zum Paradies 2018`, `Binokulare Kopfbandlupe mit Glaslinsen`.
- **Language:** German.

### imerco.dk (Imerco — Danish kitchen & home goods retailer)
- **site_type:** `PHYSICAL_GOODS` (broad homeware catalog: kitchenware, tableware, glass, furniture, lamps, bath, personal care). Could also be argued MARKETPLACE_MIXED; user kept PHYSICAL_GOODS.
- **search_url_template:** `https://www.imerco.dk/search?query={}` (correct as derived).
- **brands:** discovery returns almost nothing (only picks up the brand matching the seed query — e.g. "Kochblume" from a `koch` search). Real signature brands to add: Royal Copenhagen, Holmegaard, Bodum, Eva Solo, Stelton, Zwilling, Fiskars, Rosendahl, Kähler, Georg Jensen, Le Creuset, Scanpan, Bitz, Lyngby Porcelæn, Aida, Pillivuyt, WMF, Brabantia.
- **featured_items (user-supplied, double as exact-match queries):** `D106 Bakketop Bakkebord`, `Bernadotte Hvidvinsglas - 6 stk.`, `MAN Body Shower og Viking Repair`, `iD3® Fjerkræssaks`.
- **Language:** Danish.

### baechli-bergsport.ch (Bächli Bergsport — Swiss mountain/outdoor-sports gear retailer)
- **site_type:** `PHYSICAL_GOODS`. Heuristic mis-classified as `SERVICES_EXPERIENCES` because nav contains "Beratung" (advice) and "Erlebnis" (experience); actual catalog is outdoor apparel/gear (jackets, pants, shirts, base layers, care products) — same experiential-nav-bias pattern as avoca.com (see General learnings).
- **search_url_template:** `https://www.baechli-bergsport.ch/de/suche/search?Query={}` (correct as derived).
- **Haiku refinement fails to parse** on this site (unterminated JSON string) → falls back to heuristic, which returns empty `brands` and a thin `featured_items` (just one real product + a gift card). Same failure mode as manufactum.de — clean/supply manually.
- **brands (user-supplied):** alpibreak, boreal, eZeefit, Kraszewski.
- **featured_items (signature products, user-supplied, double as exact-match queries):** `Tech Trail Utility Printed Woven SS`, `Nano-Air Ultralight Full-Zip Hoody W`, `Flex Vrt W 21`, `Footprint Badawi Long 6P`.
- **Language:** German (Swiss site, `/de/` path).
- **Brand category mismatch discovered at judge time:** the user-supplied brands `alpibreak` and `Kraszewski` are real (verified live, products exist), but NOT apparel brands — `alpibreak` is a camping-food brand (Pancake Mix, Bircher Müesli, Hummus) and `Kraszewski` is a climbing-guidebook publisher. BRAND_SEARCH queries combining either with a garment category (`alpibreak Jacke`, `Kraszewski Weste`) correctly return 0 — this is a catalog-category mismatch baked into the Phase-1 brand list, not a search defect. **Lesson for future Phase-1 reviews on this kind of multi-category retailer (outdoor gear + food + media):** when the user supplies a brand list, verify each brand's actual product category (search the bare brand name) before pairing it with an apparel/gear term in Phase 3 query generation — a brand+category combo query is only a valid search-engine test if the brand plausibly carries that category.

---

### bergzeit.de (Bergzeit — German outdoor/mountain-sports gear retailer)
- **site_type:** `PHYSICAL_GOODS`. Heuristic/Haiku misclassified as `SERVICES_EXPERIENCES` (same experiential-nav-bias pattern as avoca.com/baechli-bergsport.ch). Real catalog is broad outdoor apparel/footwear/gear (climbing, skiing, cycling, camping, hiking) across Damen/Herren/Kinder/Ausrüstung departments.
- **search_url_template:** `https://www.bergzeit.de/search/?q={}&ms=true` (correct as derived; keep the `&ms=true` suffix).
- **Haiku refinement fails to parse** on this site (unterminated JSON string) → falls back to heuristic with empty `brands` and junk in `featured_items` (a "Deine Suche nach »X« (N Artikel)" result-count string, not a product). Same failure mode as manufactum.de/baechli-bergsport.ch — clean manually.
- **brands:** discovery returns `[]`. Real brand list lives at `https://www.bergzeit.de/marken/` — a huge (500+) third-party brand catalog, not just house brand. Scrape `a[href^="/marken/"]` links for the full list; seeded with well-known names: Patagonia, Vaude, Salomon, Mammut, The North Face, Arc'teryx, Jack Wolfskin, Salewa, Scarpa, Schöffel, Deuter, Black Diamond, Petzl, Ortovox, Garmin, Osprey, Icebreaker, Smartwool, Hoka, Merrell.
- **featured_items (signature products, user-supplied, double as exact-match queries):** `Herren Hiking T-Shirt`, `Bergzeit Classic Lace Kletterschuhe`, `Herren Pedroc TW Air HYB Jacke`, `Falconer 2Vi Mips Fahrradhelm`, `Damen Ophir 3 Slide 2.0 Klettergurt`.
- **Language:** German.

### cotswoldoutdoor.com (Cotswold Outdoor — UK outdoor gear & clothing retailer)
- **site_type:** `MARKETPLACE_MIXED`. Broad outdoor catalog (Men/Women/Kids clothing, footwear, camping, climbing, snowsports, travel) plus many third-party brands — discovery got this right without correction.
- **search_url_template:** `https://www.cotswoldoutdoor.com/lister.html?q={}` (correct as derived).
- **brands (discovery-derived, accurate):** Ayacucho, Patagonia, Rab, Mountain Equipment, The North Face, Arc'teryx, Oakley, Montane, Columbia, Fjällräven, Vivobarefoot, Ray-Ban, Scarpa, Meindl, Merrell, Salomon, Lowa, Hoka, Osprey, Garmin, Vango, MSR, Sea to Summit.
- **featured_items:** discovery returned empty; user-supplied signature products (double as exact-match queries): `Garmin Fenix 8 Pro AMOLED Sapphire 51mm GPS Smartwatch`, `Scarpa Womens Mojito GTX Shoes`, `Rab Kit Bag II - 80L`, `Superfeet All Purpose Support Medium Arch Insoles`.
- **Language:** English.

### lyko.com (Lyko — Swedish multi-brand beauty/cosmetics retailer)
- **site_type:** `MARKETPLACE_MIXED`. Broad multi-brand beauty catalog (skincare, hair, makeup, perfume, men's, health/wellbeing, gifts) carrying many third-party brands plus the By Lyko house label.
- **search_url_template:** `https://lyko.com/sv/sok?q={}` (correct as derived; `/sv/` = Swedish locale, `sok` = search).
- **Language:** Swedish. Run the audit in Swedish.
- **Seed-query bias warning:** if the discovery seed URL carries a real query (e.g. `?q=fresh`), the rule-based `brands` and `featured_items` get poisoned with products/brands matching that term (everything came back containing "Fresh"). Always swap featured_items to genuine signature products pulled from the live site, and treat a seed query as a URL-pattern example only, not a meaningful term.
- **featured_items (verified live, double as exact-match queries):** `COSRX Advanced Snail 96 Mucin Power Essence 100 ml`, `Beauty of Joseon Glow Serum Propolis + Niacinamide 30 ml`, `The Ordinary Niacinamide 10% + Zinc 1%`, `Skin1004 Madagascar Centella Ampoule 55 ml`. Lyko's signature strength is cult K-beauty/skincare — these anchor the most realistic exact-match queries.
- **brands (verified carried, live):** Beauty of Joseon, COSRX, The Ordinary, Skin1004, Purito, Medicube, Klairs, Milk Makeup, Kérastase, ACO, Wella Professionals, Garnier, NIVEA, L'Oréal Paris, By Lyko (house). Many more carried.
- **Product page slug pattern:** `/sv/{brand-slug}/{product-slug}` (no `/p/`). When extracting from search results, match `a[href^="/sv/"]` with a two-segment path, not a `/p/` pattern.

### douglas.de (Douglas — German/European beauty & lifestyle retailer)
- **site_type:** `MARKETPLACE_MIXED` — discovery got this right unaided. Beauty is the core
  (fragrance, make-up, face, body, hair) but the **Lifestyle** department carries electronics,
  luggage, bags, jewellery and wellness devices, so it is genuinely mixed, not pure beauty.
- **search_url_template:** `https://www.douglas.de/de/search?q={}` (correct as derived; verified
  live — `?q=mascara` → "677 ERGEBNISSE FÜR „MASCARA“" with real products).
- **Static fetch is blocked at the edge.** Plain `requests`/`curl` with a desktop UA returns
  **HTTP 400 "Bad Request - Request Too Long / The size of the request headers is too long"** —
  on the search URL *and* on the bare homepage. This is a WAF signature, not a real header
  problem (identical curl against other hosts returns 200). Discovery auto-fell back to
  Playwright and succeeded. Assume Playwright mode for every phase on this host.
- **Refinement pass returns empty `nav_categories`, `brands`, `featured_items`** (same failure
  family as manufactum.de / baechli-bergsport.ch / bergzeit.de) while still producing correct
  `site_name`, `site_type`, `search_url_template` and `primary_language`. Fill the three empty
  fields manually.
- **nav_categories (real departments, verified from header links):** Parfum, Make-up, Gesicht,
  Körper, Haare, Gesundheit & Wellness, Lifestyle, Männer, Geschenke, Luxus. Drop the
  promotional nav: Beauty Services, Goodies, Beauty Card, Filialen, Angebote, Neu & Trends,
  Sale, Adventskalender, Preis-Tipp, Outlet, Nachhaltigkeit, New Season New Beauty. `Marken`
  is the brand index, not a department; `Douglas Collection` is a brand, not a department.
- **brands: ~1,829 carried.** Full list at `https://www.douglas.de/de/brands`; scrape
  `a[href*="/b/"]` link text. Far too many to enumerate — curate a representative spread
  (prestige fragrance, mass beauty, haircare, K-beauty, house label) rather than the whole set.
- **BRAND-CATEGORY MISMATCH TRAP (important, cf. the baechli-bergsport lesson).** Because of the
  Lifestyle department, the brand list contains many **non-beauty** names: Apple, adidas, Mammut,
  Dakine, Travelite, American Tourister, Pinqponq, The Chesterfield Brand, Braun Büffel,
  Liebeskind, LLOYD, Strellson, Mockberg, Purelei, Valero Pearls, Elli, Heideman, Therabody,
  Medela, waterpik, 24Bottles, Ania Haie, Bentley, Porsche Design, Cartier. Pairing any of these
  with a beauty term in Phase 3 (`Mammut Mascara`, `Apple Parfum`) produces a query that
  legitimately returns 0 — a catalog fact, NOT a search defect. Verify a brand's actual product
  category before combining it with a category term.
- **Seed-query bias confirmed again** (cf. lyko.com): seeding discovery with `?q=mascara` skewed
  the candidate `featured_items` toward mascaras. Treat a seed query as a URL-pattern example only.
- **featured_items (verified live, double as exact-match queries):**
  `Beauty of Joseon Glow Serum Propolis + Niacinamide 30 ml`, `The Ordinary Niacinamide 10% + Zinc 1%`,
  `Biodance Bio Collagen-Real Deep Mask`, `Douglas Collection EXEPTION'EYES SUMMER Mascara`,
  `Lancôme Lash Idôle Volumen-Mascara`.
- **Result cards are unusually rich** — each carries brand, product line, variant name, product
  category, UVP vs. actual price, unit price, colour/size-variant count, and a `Gesponsert` flag.
- **Sponsored results are interleaved into organic** (observed at ranks 6–7 on `mascara`).
- **Language:** German. **Locale:** DE.

## When you learn something new

After every Phase 1 correction, append either a per-site profile (site_type fix, working
template, brands to add/drop, signature items) or a General-learnings row if it's a
cross-site pattern. One correction = one entry.
