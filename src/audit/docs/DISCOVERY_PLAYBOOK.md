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
| **Haiku refinement is now the default** | The rule-based extractors are noisy: brand names land in `nav_categories`, `featured_items` fills with nav/legal/cart junk, and `site_type` is wrong (see next row). | A Haiku pass (`_refine_with_haiku`, `claude-haiku-4-5-20251001`) runs automatically at the end of `discover_from_search_url`: it re-derives `site_type`, splits brands out of nav, cleans nav to real departments, and keeps only real products in `featured_items`. Fails safe to heuristic values. Still review its output; it can miss user-known signature products. |
| **`_detect_site_type` experiential-noun bias** | The heuristic counts distinct substring hits over the scraped **homepage**. It over-weights experiential nouns (experience/heritage/café/visit/events/gifting) and can't see purchase signals — prices and add-to-cart live on **product pages**, not the homepage — so goods retailers with lifestyle/café/visitor framing score `service≥3 & goods≤1` and get misclassified as SERVICES_EXPERIENCES. English-only literal substrings also zero out non-English sites. | A goods retailer that *also* runs cafés/experiences is still a goods retailer → MARKETPLACE_MIXED or PHYSICAL_GOODS. The Haiku pass now corrects this; the heuristic is only the fallback. |

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

## When you learn something new

After every Phase 1 correction, append either a per-site profile (site_type fix, working
template, brands to add/drop, signature items) or a General-learnings row if it's a
cross-site pattern. One correction = one entry.
