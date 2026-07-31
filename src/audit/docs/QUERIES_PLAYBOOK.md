# Queries Playbook — Phase 3 knowledge base

> **Read this BEFORE running Phase 3 (`generate_queries`).** It records query-generation
> failure patterns (hallucinated products, unrealistic phrasing, locale issues) per site
> and in general, so we don't re-catch the same bad queries each audit. When the user
> flags or rewrites a query, capture the reason here.
>
> Companion docs: `ARCHITECTURE.md` and the `synthetic-search-audit` skill. This file is
> operational memory for the **query generation** phase specifically.

---

## How to use this file

1. Before Phase 3, check the **Per-site profile** and **General learnings**. Pre-emptively
   filter the known-bad query shapes for this host/locale before showing the list.
2. Present queries grouped by category, each with its rationale.
3. To remove: filter the list. To regenerate for a category: re-run `generate_queries` with
   only that category and merge with the kept queries.
4. After the user edits, record what made a query bad (and what good looks like for this site).

---

## General learnings (apply to every site)

| Pattern | Symptom | Fix |
|---|---|---|
| **Hallucinated product/brand names** | A query names a specific product or brand the site doesn't carry (often seeded by a hallucinated brand from Phase 1). Guarantees a zero-result that misreads as a search failure. | Cross-check named entities against verified brands/featured_items. Drop or replace. Fix the Phase 1 brand list too. |
| **Unrealistic phrasing** | Queries read like a marketer, not a shopper ("premium artisanal hand-crafted X"). Real users type short, sometimes misspelled, intent-led terms. | Prefer the phrasing a real customer would type for this catalog. |
| **Locale/language mismatch** | Queries in the wrong language or with wrong locale spelling for the target market. | Match the site's primary market language and local product vocabulary. |
| **All-easy or all-hard** | Every query is a trivial single-word match (inflates pass rate) or every query is an edge case (deflates it). | Keep a spread: head terms, multi-word intent, synonyms, and a few genuinely hard edge cases. |
| **No BROAD_CATEGORY; OCCASION (was USE_CASE)** | BROAD_CATEGORY (user typing the site's own term, e.g. "knitwear") is retired — don't generate it; use CATEGORY_MAPPING (colloquial/different term) instead. The intent category is now `OCCASION` ("gift for dad", "housewarming present"), distinct from SEASONAL_OCCASION (date/event-driven). | Generate CATEGORY_MAPPING and OCCASION; never emit BROAD_CATEGORY. |
| **Signature `featured_items` → exact-match queries** | The exact product names a user supplies as `featured_items` in Phase 1 are known-good catalog entries. Search must return them on an exact-title query; if it doesn't, that's a real, high-signal failure. | Inject each Phase 1 `featured_items` entry verbatim as an exact-match query (its own category / EXACT_PRODUCT_TITLE). Do not paraphrase — use the exact title so a miss is unambiguous. |

## Per-category generation rules (apply to every site)

These are hard rules — the generation prompt enforces them, and you should verify the output respects them before showing the list:

- **BRAND_SEARCH** — brands must be real brands present on the website (from the verified Phase 1 `brands` list). Never invent a brand.
- **CATEGORY_MAPPING** — the mapped-to category must be a real category that exists on the site. Never map to a category the site doesn't have.
- **DIRECT_MATCH** — use ONLY the exact `featured_items` product titles, verbatim, one query each. Generate at most as many as there are featured items; if fewer than requested, generate FEWER — never pad with a brand+category phrase ("Jellycat soft toy"), a product type, or any invented product. The judge auto-fails DIRECT_MATCH if the #1 result title doesn't contain the exact query, so a non-exact query would be a guaranteed false failure.
- **PLURAL_SINGULAR** — use the *harder* direction: give the PLURAL form, favouring terms whose plural is dissimilar from the singular (e.g. "scarves" not "scarf", "knives" not "knife"). Singular is usually the engine's default, so the dissimilar plural is the real test.
- **SPECIAL_CHARACTER** — insert a special character *anywhere inside a real query term* to test normalization (e.g. "Cr&aie Studio", "h*ats"). Do NOT just pick terms that happen to contain "&"; the point is to see whether the engine strips/normalizes the injected character. **Hard rule, repeatedly violated:** the character must land *inside* a single word (e.g. "wal*king boots", "ruck&sack"), never between two separate words ("gore tex & softshell") and never just a real apostrophe/hyphen that's already part of a brand's official spelling ("Arc'teryx", "fjäll-räven" are NOT special-character tests — they're just the brand's real name). The test only works if the character is an artificial injection whose stripping/normalization you can verify.
- **SPLIT_WORD — hard rule, repeatedly violated:** the split must fall *mid-word*, at a point that is NOT a real morpheme/compound boundary. "soft shell jacket" (splits the compound "softshell" at its natural seam) and "back pack" (splits "backpack" at its compound seam) are NOT valid SPLIT_WORD tests — the engine likely already tokenizes compounds at that seam, so it's not testing arbitrary split tolerance. Pick a single, ideally non-compound word and break it at an arbitrary internal point, e.g. "s hoes" (shoes), "jack et" (jacket), "trous ers" (trousers), "Wanderho sen" (not "Wander hosen").
- **MULTI_ATTRIBUTE — hard rule, repeatedly violated:** exactly ONE base product term plus ONE constraint, full stop. Never stack gender+category+colour or gender+tech+category. The point is to test whether the engine extracts/honours one added constraint without dropping it (and to see if it silently drops the constraint when the result list ignores it) — a second or third stacked constraint makes the result un-judgeable (titles + price can't verify which constraint failed). Good: "walking boots brown", "rucksack waterproof", "fleece jacket medium". Bad: "women's waterproof jacket black" (3 constraints), "men's Gore-Tex walking boots" (3 constraints).
- **Constraint queries are SINGLE-constraint** — FACET_EXTRACTION, NEGATIVE_INTENT, PRICE_ANCHORED, and MULTI_ATTRIBUTE each carry a real base product term plus **exactly ONE** constraint (one colour OR one material OR one size OR one exclusion OR one price limit) — never several stacked. **The generator still routinely violates this for MULTI_ATTRIBUTE** — it emitted stacked colour+material/colour+fit queries ("black boots leather", "olive green pants slim") on Huckberry despite the rule. Always inspect MULTI_ATTRIBUTE output and rewrite any stacked query down to a single title-visible constraint (e.g. "black boots", "leather jacket", "canvas tote bag", "wool sweater") before proceeding. Reason: the judge sees only titles + price, so it can only verify one constraint reliably; stacked constraints produce un-judgeable queries. Prefer constraints whose value would appear in a product title (colour, material, price) over invisible ones (fit, stock). MULTI_ATTRIBUTE was redefined to single-constraint (now overlaps FACET_EXTRACTION by design). See the matching CONSTRAINT_DROPPED detection rules in JUDGE_PLAYBOOK.

---

## General learnings (continued)

| Pattern | Symptom | Fix |
|---|---|---|
| **TYPO too subtle** | Generator defaults to a single dropped/transposed letter ("Hardshel-Jacke"), which reads as barely a typo. | Ask for more drastic, phonetically realistic misspellings (consonant swaps like v→f, doubled syllables, dropped vowels) — e.g. "Pullofer" for Pullover, "Imprägnirung" for Imprägnierung. |
| **SPLIT_WORD splits at the compound seam, not mid-word** | Generator defaults to separating a real compound noun at its natural boundary ("Hard shell Jacke" = Hard+shell+Jacke, "Trail running Jacken" = Trail+running+Jacken). That's just spacing out a compound the engine likely already tokenises — not a real test of arbitrary word-break tolerance. | Split a single (non-compound) word at an arbitrary mid-word point that is NOT a morpheme boundary, e.g. "Wanderho sen" (not "Wander hosen"), "Pullov er", "Imprägni erung". |
| **One product noun ("Jacke") dominates the query set** | When the generator is given a nav list dominated by jacket subtypes, it defaults to "Jacke" across nearly every category (TYPO, SPLIT_WORD, MULTI_ATTRIBUTE, ABBREVIATION, SPECIAL_CHARACTER, LOCALE_VARIATION, SEASONAL_OCCASION, PRICE_ANCHORED all skewed jacke-heavy here), reading as generic/repetitive rather than a varied audit. | After generation, scan the full query list for term concentration. If one noun appears in >40-50% of non-DIRECT_MATCH/non-BRAND_SEARCH queries, manually swap roughly half of those instances to other real catalog nouns (Hose, Weste, Pullover, Shirt, BH, Unterwäsche) before showing the list. |

## Per-site profiles

### baechli-bergsport.ch (Bächli Bergsport)
- User flagged after first generation: TYPO misspellings too subtle (single dropped letter), SPLIT_WORD was splitting compound nouns at their natural seam instead of mid-word, and "Jacke" dominated most categories. Rewrote TYPO to use phonetic/multi-letter misspellings (Wanderhozen, Pullofer, Reperaturmaterial, Imprägnirung) and SPLIT_WORD to break single words mid-word away from any compound boundary (Wanderho|sen, Pullov|er, Imprägni|erung, Reparaturma|terial). Manually rebalanced MULTI_ATTRIBUTE, ABBREVIATION, SPECIAL_CHARACTER, LOCALE_VARIATION, SEASONAL_OCCASION, CATEGORY_MAPPING, PRICE_ANCHORED to swap roughly half their jacket-themed queries for Hose/Weste/Pullover/BH equivalents.
- **Verified brands:** alpibreak, boreal, eZeefit, Kraszewski.
- **Locale:** German (Swiss) — Franken/CHF price phrasing is a good locale test for PRICE_ANCHORED.

### avoca.com (Avoca)
- **Exact-match queries (verbatim, required):** these Phase 1 `featured_items` must each be run as an exact-title query —
  - `Stone Snow Esia Single Breasted Jacket`
  - `1960's Space Exploration Sheep Mug`
  - `Shea Verbena Hands & Body Liquid Soap`
- **Verified brands** for brand/brand-bleed queries: American Vintage, Barbour, Craie Studio, HK Living, Jellycat, Love Beth, Never Fully Dressed, Waterdrop, FRNCH, Avoca (house). Do not name brands outside this set.
- **Locale:** English (Irish retailer) — UK/IE spelling (colour, jewellery).

### manufactum.de (Manufactum)
- **Exact-match queries (verbatim, required):** `Tischleuchte Sonnenglas® (Generation 6)`, `Bio-Spätburgunder Tor zum Paradies 2018`, `Binokulare Kopfbandlupe mit Glaslinsen`, `Sonnenleder kleine Umhängetasche`. DIRECT_MATCH wants 4; with only 3 featured items the generator hard-fails (`Missing required coverage: DIRECT_MATCH: 1`) — supply 4 verified exact titles.
- **Verified brands:** CHICO Hängematten, Heimgart, Armedangels, Sonnenleder (house/featured). Don't name brands outside this set.
- **Locale:** German. Good locale-variation tests: Swiss `ss`↔`ß` (e.g. `Fussball` vs `Fußball`), umlauts. Avoid plain queries dressed up as locale variants (`Körperpflege Creme` was not a real variant).
- **MULTI_ATTRIBUTE stacking:** generator stacked size+material/colour+dryness on every MULTI_ATTRIBUTE query — rewrite each to a single title-visible constraint before fetching.

---

### imerco.dk (Imerco — Danish kitchen & home goods)
- **Exact-match queries (verbatim, required):** `D106 Bakketop Bakkebord`, `Bernadotte Hvidvinsglas - 6 stk.`, `MAN Body Shower og Viking Repair`, `iD3® Fjerkræssaks`.
- **Verified brands** for brand/typo/partial queries: Royal Copenhagen, Holmegaard, Bodum, Eva Solo, Stelton, Zwilling, Fiskars, Rosendahl, Kähler, Georg Jensen, Le Creuset, Scanpan, Bitz, Lyngby Porcelæn, Aida, Pillivuyt, WMF, Brabantia, Kochblume.
- **Locale:** Danish. Good edge tests: æ/ø/å handling, compound vs split words (salatskål vs salat skål), word-order (kopper og krus).
- **SPECIAL_CHARACTER:** user wants the special char inserted *mid-word* in every query (e.g. `Le Creu*set`, `Georg Jen&sen`, `Kähler kera*mik`) — not an ampersand sitting between two words. Rewrite any "Georg & Jensen"-style output.

---

### bergzeit.de (Bergzeit)
- User flagged after first generation (same pattern as baechli-bergsport.ch): TYPO too subtle (single dropped/transposed letter), SPLIT_WORD breaking compound nouns at their natural seam instead of mid-word, SPECIAL_CHARACTER using an ampersand/hyphen mirroring a site category label *between* two words instead of a real special character injected *inside* a single word.
  - Rewrote TYPO to drastic multi-letter/phonetic respellings: `Wandaschuhe` (Wanderschuhe), `Mamuth` (Mammut), `Zalomoon` (Salomon, S→Z swap + doubled vowel), `Farradhellm` (Fahrradhelm).
  - Rewrote SPLIT_WORD to break mid-word away from the compound seam: `Wandersch uhe` (not Wander|schuhe), `Trekkings chuhe` (not Trekking|schuhe), `Fahrradh elm` (not Fahrrad|helm), `Basec aps` (not Base|caps).
  - Rewrote SPECIAL_CHARACTER to insert a real character (`*`, `&`, `#`, `$`) *inside* a single real term: `Wanderschu*he`, `Sal&omon`, `Fahrrad#helm`, `Trekking$schuhe`.
- **Verified brands** for brand/typo queries: Patagonia, Vaude, Salomon, Mammut, The North Face, Arc'teryx, Jack Wolfskin, Salewa, Scarpa, Schöffel, Deuter, Black Diamond, Petzl, Ortovox, Garmin, Osprey, Icebreaker, Smartwool, Hoka, Merrell (full catalog has 500+ brands at `/marken/`).
- **Locale:** German.
- **TYPO over-garbling can collide with an unrelated real word (caught at judge time, see JUDGE_PLAYBOOK).** `Wandaschuhe Herren` (meant as a drastic respelling of `Wanderschuhe`) was garbled enough to land closer by edit distance to the unrelated real word `Handschuhe` (gloves) than to the intended target — the engine correctly matched gloves, which read like a failure until checked. **Lesson:** when drastically garbling a TYPO query, sanity-check the result isn't closer to a different real word in the same language than to the intended term; if it is, the test is invalid (not a search defect either way) — soften the garbling or pick a different base word.

### lyko.com (Lyko — Swedish multi-brand beauty/cosmetics)
- **Exact-match queries (verbatim, required):** `COSRX Advanced Snail 96 Mucin Power Essence 100 ml`, `Beauty of Joseon Glow Serum Propolis + Niacinamide 30 ml`, `The Ordinary Niacinamide 10% + Zinc 1%`, `Skin1004 Madagascar Centella Ampoule 55 ml`.
- **Verified brands** for brand/typo/partial queries: NIVEA, Wella Professionals, Beauty of Joseon, ACO, COSRX, The Ordinary, Skin1004, Purito, Medicube, Klairs, Milk Makeup, Kérastase, Garnier, L'Oréal Paris, Antipodes, Rexona, By Lyko (house). Don't name brands outside the verified set.
- **Locale:** Swedish. Good locale tests: EN beauty term vs SV equivalent (`shampoo`↔`schampo`, `moisturiser`↔`ansiktskräm`, `colour`↔`färg`). Avoid plain SV queries dressed as locale variants.
- **SPECIAL_CHARACTER — generator violated the mid-word-injection rule on every query:** it emitted `niacinamide 10% + zinc` (% / + are part of the real product name, not an injection), `beauty-of-joseon serum` (hyphens between words), `hår & hudvård` (ampersand between two words). Rewrote to inject a char *inside a single real term*: `niac*inamide`, `scha&mpo`, `parf#ym`. Always rewrite beauty SPECIAL_CHARACTER output this way.
- **FACET volume queries must use REALISTIC volumes per product type (caught at judge time).** `foundation 100 ml` is a bad facet test — foundations are ~30 ml, so no product satisfies "100 ml"; the engine matched "100" to shade numbers (100 Ivory) and only sponsored 100ml self-tan/sun-lotion leaked. Use type-appropriate volumes (foundation 30 ml, shampoo 250/500 ml, serum 30 ml, body lotion 400 ml) so the facet is actually satisfiable and the test is valid.
- **MULTI_ATTRIBUTE — generator stacked 2 constraints on 3 of 4:** `serum med niacinamide för fet hud` (ingredient+skin-type), `schampo för färgat hår Wella` (hair-type+brand), `parfym herr 50 ml` (gender+volume). Rewrote to single title-visible constraint: `serum niacinamide`, `schampo färgat hår`, `parfym 50 ml`. For beauty, prefer ingredient or volume (title-visible) over skin-type/scalp-type (not in title).

## When you learn something new

After every Phase 3 edit, append a per-site profile (good/bad query shapes, vocabulary,
entities to never name) or a General-learnings row if it generalizes across sites.
