# Judge Playbook — Phase 6 knowledge base

> **Read this BEFORE running Phase 6 (`judge_all_queries`).** It records severity-calibration
> rules and override patterns per site and in general, so the judge stays consistent across
> audits. When the user overrides a judgment, capture the rule here.
>
> Companion docs: `ARCHITECTURE.md`, `SCORING_PLAYBOOK.md` (thresholds feeding the judge),
> and the `synthetic-search-audit` skill. Operational memory for the **judge** phase.

---

## How to use this file

1. Before Phase 6, read the **Calibration rules** and any **Per-site profile** so the
   severity bar matches prior decisions for this host.
2. Run the judge; report severity counts, failure-mode distribution, and every CRITICAL
   (query, failure_mode, evidence, recommended_fix).
3. **Cost-saving:** if results change after judging, re-judge only the **affected queries**
   and patch the checkpoint — never re-judge the whole set.
4. After any override, record the calibration rule that produced it.

---

## Calibration rules (apply to every site)

- **A DIRECT_MATCH query that redirects straight to the matching product's PDP is a PASS,
  not a failure.** When the search engine resolves an exact-title query to a single,
  unambiguous result by sending the shopper directly to that product's page (no
  intermediate results grid at all), that is the *best possible* outcome for a DIRECT_MATCH
  query — better than showing a one-item results grid, since it removes a click. The fetcher
  surfaces this as a normal 1-result `SearchResult` (see `_PDP_REDIRECT_HOSTS` /
  `_try_extract_pdp_as_result` in `src/fetcher.py`) with the PDP's `<h1>` as the title — judge
  it exactly like any other DIRECT_MATCH result: rank-1 title contains the query → PASS. Do
  not flag the redirect itself as a defect, missing grid, or anything to call out. (Confirmed
  on cotswoldoutdoor.com: exact-title queries for `Garmin Fenix 8 Pro AMOLED Sapphire 51mm GPS
  Smartwatch` and other featured items redirect straight to the PDP — same behavior as
  baechli-bergsport.ch, see FETCHER_PLAYBOOK.)
- **POOR_RANKING is CRITICAL only when the customer's FIRST result is off-topic
  (`top1 < 0.30`)** — not on a relative reranker gap alone. Relevant-but-reordered results
  are not a CRITICAL; don't over-flag them. (Carried from project memory
  "judge-ranking-calibration".)
- **POOR_RANKING at MINOR severity is a PASS — never report it.** A minor ranking issue
  means all results are on-topic and the shopper saw a relevant item near the top; the only
  difference is sub-0.1 reranker-score reordering (e.g. a corrected typo or brand+category
  query). Enforced deterministically in `_judge_single_query` (POOR_RANKING/MINOR → OTHER/PASS).
- **Occasion/category query that returns zero but matches an existing site category →
  CATEGORY_MAPPING_FAILURE (not NO_SEMANTIC_UNDERSTANDING).** Before labelling a zero/semantic
  failure, check the site's `nav_categories`: if the query resembles a real category the site
  carries (e.g. "Father's Day gift ideas" vs the site's "Father's Day Gifting" category), the
  failure is that search can't map the query to its own merchandised category — sharper and
  more fixable. Enforced via `_resembles_site_category` in `_judge_single_query` (pass
  `site_categories` from Phase 1 `nav_categories`); severity is unchanged. **EXEMPT
  SEMANTIC_MEANING queries** — conceptual sentences by design, so an incidental category word
  ("…house feel like a home") must NOT downgrade a real semantic failure to category-mapping;
  they stay NO_SEMANTIC_UNDERSTANDING. **NATURAL_LANGUAGE is now exempt too** (same reason):
  Huckberry "something to keep my food cold on a camping trip" → 0 results was being
  mislabeled CATEGORY_MAPPING_FAILURE because the token "cold" naively matched the
  "Cold Weather Accessories" category — which is the OPPOSITE intent (staying warm, not
  cooling food; the real need is a cooler). Conversational queries carry incidental category
  tokens; reclassifying on them produces wrong, sometimes semantically-opposite category
  citations. Both SEMANTIC_MEANING and NATURAL_LANGUAGE stay NO_SEMANTIC_UNDERSTANDING.
- **Conversational/subjective-zero cluster is normalized to NO_SEMANTIC_UNDERSTANDING.** A
  NATURAL_LANGUAGE, SEMANTIC_MEANING, or SUBJECTIVE_ATTRIBUTE query that returns nothing usable
  (zero OR garbage) is, at root, the engine failing to understand a conceptual/qualitative
  phrase — not merely an empty page. The LLM labels some ZERO_RESULTS_OR_GARBAGE and others
  NO_SEMANTIC_UNDERSTANDING; mixing the two across one cluster reads as inconsistent. Enforced
  deterministically in `_judge_single_query`: for these THREE categories, ZERO_RESULTS_OR_GARBAGE
  → NO_SEMANTIC_UNDERSTANDING (severity unchanged, typically CRITICAL). All three are also exempt
  from the category-mapping reclassifier. Example: Huckberry "cozy sweatshirts for lounging" → 1
  garbage result (an outdoor fleece) → CRITICAL/NO_SEMANTIC_UNDERSTANDING (the subjective "cozy"
  + multi-word phrasing collapsed retrieval despite a stocked Sweatshirts category).
- **CATEGORY_MAPPING_FAILURE requires a genuine ZERO result, not weak filler.** The
  category-mapping reclassifier (matching the query to a real site category) now only fires
  when the engine returned NOTHING (`not results`). When the engine DID return items but they
  are weak/wrong-type filler (results present, low relevance, head noun absent — e.g. "jacket
  not synthetic" → 15 Arc'teryx shirts/shorts at ~0.39), that is the engine failing to
  UNDERSTAND the query, not failing to reach a category → **NO_SEMANTIC_UNDERSTANDING**
  (MODERATE via the weak-filler guard; CRITICAL if max relevance < 0.25). Previously the
  reclassifier fired on any NO_SEMANTIC_UNDERSTANDING and pasted a false "returned no usable
  results" claim onto a non-empty result set.
- **Any CATEGORY_MAPPING test-category query that returns 0/garbage → CATEGORY_MAPPING_FAILURE
  (not ZERO_RESULTS_OR_GARBAGE).** These queries are built as colloquial terms for REAL site
  categories, so a zero IS the mapping failing — even when the query shares no words with the
  category name (e.g. "bedtime wear" → "Sleep & Loungewear"), which is the hardest and most
  important case and the one nav-token matching can't catch. Enforced deterministically in
  `_judge_single_query` (by test category). Severity unchanged (typically CRITICAL).
- **Clustered near-equal scores ≠ PASS when the whole set is weak.** The "cosmetic reorder
  among near-equal results → PASS" logic ONLY applies when results are actually relevant. If
  the BEST result is itself weak (max relevance < ~0.45) AND the query's core product term
  appears in no result title, the scores are clustered because every item is *irrelevant* —
  the engine returned filler of the wrong product type (e.g. "luxury throws" → beauty gift
  sets, zero throws). That is a relevance failure (NO_SEMANTIC_UNDERSTANDING; CRITICAL if max
  < 0.25 else MODERATE), NOT a pass. Enforced via the weak-filler guard in `_judge_single_query`
  (`_core_terms_absent` + `MIN_RELEVANT_TOP`). EXEMPT: BRAND_SEARCH, and any query that matches a
  known Phase-1 brand (`_query_targets_brand`) — a brand name legitimately may not appear in titles
  (e.g. "Craie-Studio" → leather bags), so low relevance + core-terms-absent there is expected, not
  filler. Token matching is singular/plural stem-based (`_token_match`), NOT prefix-based — prefix
  matching produced false hits like "studio"≈"stud".
- **Dropped head-noun on a multi-word query → PARTIAL_KEYWORD_MATCH (not PASS / not POOR_RANKING).**
  When the engine matches only a SUBSET of a multi-word query and drops the core product noun
  (e.g. "winter coat sale" → winter **socks**: kept "winter", dropped "coat"), that is
  PARTIAL_KEYWORD_MATCH. Severity MODERATE (CRITICAL if the core term is essentially absent).
  Don't excuse off-intent filler as "catalogue limits" when the dropped term clearly has
  inventory (cross-check categories/other queries — Avoca has plenty of coats). The judge LLM
  tends to over-excuse this as a tail-ordering nuance; weight the dropped term explicitly.
  **This also applies when the MAJORITY of the page matches only the secondary term even if a
  couple of correct items rank at the top** (e.g. "throws grey" → 2 grey throws at #1–2 but
  socks/boxers/a soft toy fill #3–11: the engine kept "grey" and dropped "throws" for most
  slots → PARTIAL_KEYWORD_MATCH, NOT a PASS and NOT POOR_RANKING). Judge the WHOLE page, not
  just the first result: if most results match only one query term and not the head noun, it's
  a partial-query failure regardless of what ranked #1–2.
- **DUPLICATE_FLOODING severity = flooding MAGNITUDE, not LLM guess; MINOR when the top of
  the page is relevant.** When relevant *distinct* products already occupy the top visible
  slots and a model is merely repeated in the mid/lower page, that is MINOR — the shopper
  sees good results first; only assortment breadth below the fold is compressed. It is only
  MODERATE when one model dominates (top_count ≥ 5 or distinct-ratio ≤ 0.40, i.e. flooding
  reaches into the top slots). The judge LLM over-rates mid-page flooding as MODERATE.
  Enforced deterministically in `_judge_single_query`: `_flooding_severity` is **authoritative**
  for DUPLICATE_FLOODING (severity is SET to it, both directions — the LLM both inflates
  mid-page flooding and under-rates top-dominating flooding). Keyed on top_count / unique-ratio:
  top_count ≥ 5 OR ratio ≤ 0.40 → MODERATE (flooding reaches the top slots); top_count ≥ 3 →
  MINOR. Examples (Huckberry): "fleece pullover" (relevant pullovers at #1-3, Relwen Half-Zip
  3× at #4-8 → top_count 3, ratio 0.80) = MINOR; "beanie" (10/15 slots from 3 models, Japanese
  Rib Knit Beanie 5× with dupes at #1-6 → top_count 5) = MODERATE.
- **PLURAL_SINGULAR: plural resolved + flooding-only → PASS.** This category tests one thing —
  does the engine resolve the plural to the right product type? When it does (on-category
  results) and the only remaining issue is variant flooding, that capability has passed; the
  flooding is incidental and must not drag it below PASS (e.g. Huckberry "hoodies" → 15 hoodies,
  one model 3× → PASS, flooding kept as a note). Enforced deterministically (PLURAL_SINGULAR +
  DUPLICATE_FLOODING → OTHER/PASS). NOTE the deliberate contrast with BRAND_SEARCH, where variant
  flooding DOES stay MINOR (brand assortment breadth matters there) — flooding's weight is
  category-dependent. Off-category flooding is unaffected (already reclassified to POOR_RANKING).
- **TYPO / SYNONYM: capability resolved + flooding-only → PASS (user calibration, Imerco).**
  Like the PLURAL_SINGULAR rule, a TYPO or SYNONYM query tests one thing — does the engine
  correct the misspelling / map the synonym and return the right product type? When it does
  (all results on-brand/on-category, best item at/near #1) and the ONLY remaining issue is
  variant flooding (same model repeated as colour/size variant cards), that capability has
  passed; the flooding is incidental and must not drag it below PASS — at ANY flooding severity
  (MINOR or MODERATE). Keep the flooding as a merchandising note. (Imerco: "Le Crueset gryder"
  → Le Creuset Signature Gryde 6×; "Holmegaad vase" → Cocoon Vase 7×; "kasserolle" → Le Creuset
  Kasserolle 3×; "dækkeservietter" → RAW by Aida variants — all overridden MODERATE/MINOR
  DUPLICATE_FLOODING → PASS.) NOT yet enforced deterministically — apply as a manual override
  when reviewing TYPO/SYNONYM queries. Contrast with BRAND_SEARCH, where variant flooding stays MINOR.
  - **Extends to ABBREVIATION when the abbreviation IS resolved (user calibration, Cotswold).**
    Same logic: an ABBREVIATION query tests whether the engine expands the short form (e.g.
    "TNF" → "The North Face"). When it does — all results on-brand/on-type — and the only
    remaining issue is variant flooding (same model repeated as colour/size cards), the
    capability has passed → PASS, flooding kept as a note. (Cotswold: "TNF jacket" → 15 The
    North Face jackets, Quest Jacket 3×/3× → PASS.)
  - **Extends to FACET_EXTRACTION when the constraint IS satisfied (user calibration, Imerco).**
    If a FACET query's constraint is met by 100% of results (e.g. "skål keramik" → all ceramic/
    porcelain bowls) and the only remaining issue is variant flooding, that's PASS too — facet
    satisfied + flooding-only. This is distinct from the facet-NOT-extracted case (e.g. "gryder
    sort", "krus hvid" where off-colour items leak), which stays MODERATE/CONSTRAINT_DROPPED.
- **Thin category coverage → at least MINOR, even when on-topic (user calibration, Imerco).**
  When a CATEGORY_MAPPING (or category-level) query returns only a handful of on-topic results
  for a category that the site clearly merchandises broadly, that under-retrieval is a real gap
  — don't PASS it just because the few results are relevant. Common cause: a split-word form
  ("badeværelse tilbehør") not treated as equivalent to the site's compound category name
  ("Badeværelsestilbehør"), so most of the assortment is missed. Rate MINOR (MODERATE if the
  thin set also skews to a sub-type). (Imerco: "badeværelse tilbehør" → 4 results, all on-topic
  but mostly toothbrushes, for a broad bathroom-accessories category → MINOR.) Fix is compound/
  split-word equivalence at query parse time.
- **Thin match padded with off-category filler → POOR_RANKING/MODERATE (the correct result is
  the SHORT set).** When a query genuinely matches only a few products and the engine pads the
  page to a fixed size with unrelated low-relevance items, that is a failure — the right
  behavior is to return only the genuine matches (an honest short result set). Don't excuse the
  filler as benign just because the real matches lead. Example: Huckberry "Heli" → 2 Helinox
  products (correct, at #1-2) then 13 off-category items (body oil, manuka honey, eye cream,
  sunglasses, shoes at ~0.33-0.38) padding to 15 → MODERATE/POOR_RANKING, NOT MINOR/DUPLICATE_FLOODING.
  Often a manual call — the filler's relevance can sit just above the 0.30 off-category floor,
  too close for a clean deterministic rule, so judge the page holistically: if most slots are
  unrelated product types padding a thin match, it's a precision failure.
- Severity should track **customer impact / bounce risk**, not cosmetic ranking
  imperfection. If the shopper still finds a relevant item near the top, it isn't CRITICAL.
- Distinguish a **search-engine failure** from a **catalog gap**: the site genuinely not
  carrying an item is not the same as the search failing to surface an item it has. Judge
  the engine, not the inventory.
  - **Verify existence before failing a specific zero-result.** For a zero on a SPECIFIC
    multi-attribute / exact query (brand+type+colour, an exact product, a typo'd brand+type),
    do NOT auto-rate it a failure — first confirm the exact combination actually exists in the
    catalogue (cross-check earlier queries, or verify live). If it does NOT exist, returning
    zero is CORRECT behaviour → **PASS (catalog gap), not CRITICAL**. (Avoca example: "American
    Vintage top black" → 0; verified the brand has no black top — the brand's range is colourful
    prints. PASS, not a search failure.) The judge LLM tends to assume inventory exists and
    over-rate these as CRITICAL — surface them for verification.

- **A PARTIAL_QUERY/prefix that returns generic noise-filler must be VERIFIED against the live brand page, not auto-PASSed on a catalog-existence hunch (user calibration, Cotswold).** The auto-judge tends to PASS a prefix query whose results are all off-brand filler by (a) hedging "maybe the brand isn't stocked → merchandising gap, not search defect" and (b) reading the uniformly-low, clustered relevance as "cosmetic reorder among near-equal results." Both are traps. When a brand prefix returns the host's generic noise set (on Cotswold: Bridgedale socks + Garmin smartwatches at ~0.30–0.36 — the same filler that appears for every unresolvable query), do NOT pass it: first confirm live whether the brand is stocked (run the FULL brand name as a search — if it redirects to a populated `/brands/<brand>.html`, the brand exists). If the brand IS stocked and the prefix surfaced none of its products, that is CRITICAL/NO_FUZZY_MATCHING, identical to the rule below — the "near-equal scores" framing is meaningless when every result is off-brand filler. (Cotswold: `vivob` → 0 Vivobarefoot products despite 8 live on the brand page; `patago` → 0 Patagonia despite 15 — both CRITICAL.)
- **Rule extends to PARTIAL_QUERY/prefix-matching: target brand/product completely ABSENT from every result → CRITICAL/NO_FUZZY_MATCHING (user calibration, Bergzeit).** Same logic as the TYPO/MERGED_WORDS/SPLIT_WORD rule below, applied to prefix queries: when a PARTIAL_QUERY is a genuine prefix of a real brand/product (e.g. "Patago" → "Patagonia", "Mamm" → "Mammut") but the engine matches the prefix as an arbitrary substring inside UNRELATED words instead of recognizing it as a brand prefix (e.g. "Patago" matched "Pentago"/"Otago"/"Patan" — random words sharing letters; "Mamm" matched "Hammer" via the substring "amm"), and as a result the target brand/product is completely absent from all results, that is a failed prefix/fuzzy-matching capability → CRITICAL/NO_FUZZY_MATCHING. Don't let a clean #1-vs-best-available relevance gap of 0.000 (within the wrong fallback set) excuse it as PASS — the gap-of-zero only measures internal consistency of an already-wrong result set, not whether the right brand was found at all. Check first: is the actual target entity present ANYWHERE in the 15 results? If not, CRITICAL regardless of how internally well-ordered the wrong results are.
- **Head noun/product type completely ABSENT from every result on a TYPO/MERGED_WORDS/SPLIT_WORD query → CRITICAL/NO_FUZZY_MATCHING, not POOR_RANKING (user calibration, Bergzeit).** POOR_RANKING presumes the correct item(s) ARE in the result set, just ordered badly. When the engine fails to normalize a misspelled/split/merged token back to the real word at all, and as a result the actual product type the customer is searching for (the head noun) does not appear in ANY result — only loosely-related category fragments or off-type filler — that is a failed normalization/fuzzy-matching capability, not a ranking defect. Don't soften this to MODERATE/POOR_RANKING just because the returned items aren't wildly off-category (e.g. hiking apparel/bags for a hiking-SHOES query) — check explicitly whether the head noun's actual product type is present anywhere in the page. If it's absent from all results, rate CRITICAL/NO_FUZZY_MATCHING regardless of how the LLM frames it. (Bergzeit: `Wandersch uhe`, a mid-word split of `Wanderschuhe`, returned zero actual shoes — only Wanderhosen/Wanderjacken apparel and bag accessories at weak relevance, max 0.516 — auto-judged MODERATE/POOR_RANKING, overridden to CRITICAL/NO_FUZZY_MATCHING.) **Apply this check first**, before falling back to the ranking-displacement framing, whenever a TYPO/MERGED_WORDS/SPLIT_WORD query's results don't contain the literal target product type. **Severity for this pattern is CRITICAL, not MODERATE — confirmed across both TYPO/SPLIT_WORD and NATURAL_LANGUAGE (Bergzeit).** `ich suche warme Schuhe für lange Bergtouren` (head noun "Schuhe"/shoes absent from all 7 results — gloves, eyewear, trousers instead) was auto-judged MODERATE/NO_SEMANTIC_UNDERSTANDING; user escalated to CRITICAL, keeping the failure_mode. The failure_mode (NO_FUZZY_MATCHING / NO_SEMANTIC_UNDERSTANDING) is usually right when the LLM gets this far; the systematic miscalibration is the SEVERITY, which should default to CRITICAL whenever the literal target product type is verified absent from every result, regardless of query category.
- **FACET/constraint not extracted is at least MODERATE, never MINOR (user calibration, Manufactum).** For FACET_EXTRACTION (and single-constraint MULTI_ATTRIBUTE) queries, when the verdict is FACET_NOT_EXTRACTED / CONSTRAINT_DROPPED — i.e. the engine matched the facet as a free-text keyword instead of applying it as a hard filter, so off-constraint items leak in — that is a **functional failure of the facet capability**, not a cosmetic ordering nit. The fact that keyword overlap happens to surface some on-constraint items at the top does NOT downgrade it: the constraint isn't enforced, so the query has effectively failed for any shopper relying on the filter. Rate **MODERATE** minimum (CRITICAL if the constraint is violated across most of the page / the top is off-constraint). The judge LLM tends to rate these MINOR when the top few results happen to match — override up. (Manufactum: "Umhängetasche braun" and "Tischleuchte schwarz" — top results correct but colour leaks deeper → raised MINOR→MODERATE.)
  - **HARD RULE — a FACET/MULTI_ATTRIBUTE query PASSES ONLY IF 100% of returned results satisfy the constraint (user calibration, Manufactum).** A clean top of page does NOT excuse the unenforced constraint. If the constraint were truly applied as a hard filter, ZERO results would violate it; **a single off-constraint item ANYWHERE in the set — top, middle, or buried in the tail — proves it's a soft keyword match, not a filter → MODERATE/CONSTRAINT_DROPPED.** The position, count, and relevance of the leak are all irrelevant: presence of ANY inconsistent/violating result = constraint failure. Do not weigh "but the top results are correct" or "it's only 1-2 items deep down" — those are not mitigations. (Manufactum: "Umhängetasche aus Leder" → canvas at #8-9 → MODERATE; "Kochtopf aus Kupfer" → non-copper Cuvée at #3-4 → MODERATE; "Tischleuchte aus Glas" → wood lamp at #1 + non-glass lamps deeper → MODERATE; "Tischleuchte schwarz" → 1 orange at #6 → MODERATE; "Umhängetasche braun" → cognac/taupe deeper → MODERATE.) Escalate to CRITICAL if the violations dominate (≥~80% of the page) or the top result itself is off-constraint.

- **NEGATIVE_INTENT fully ignored = CRITICAL (user calibration, Manufactum).** When the excluded term appears in essentially ALL results (≥~80%, and especially 100%), the negation capability is entirely absent — the engine ran the query as if the "nicht/ohne/kein" weren't there. That is CRITICAL, not MODERATE. Do NOT soften to MODERATE on a "maybe it's a catalog gap" hunch: first check whether non-excluded inventory exists (cross-check other queries / live); if it does, returning 100% excluded items is a hard negation failure. (Manufactum: "Tasche nicht Leder" → 15/15 leather; linen/canvas/aluminium bags exist elsewhere in catalogue → CRITICAL.) Only treat as a softer finding if you've confirmed there is genuinely no non-excluded inventory, in which case the correct behaviour is an honest "no results" message, not silently showing excluded items.
  - **The same negation failure also manifests as severe UNDER-retrieval — also CRITICAL.** When the engine treats the excluded term as a POSITIVE AND-keyword (e.g. `Gartenleuchte nicht solar` → matches `Gartenleuchte AND nicht AND solar`), the result set collapses to near-zero (1–2 items) instead of returning the full non-excluded assortment. Even if the one returned item happens to satisfy the constraint, this is the negation capability failing exactly as in the flooding case — same root cause (no exclusion parsing), opposite symptom. Rate CRITICAL: the shopper effectively cannot browse the non-excluded inventory. Don't let "the 1 result is technically correct" downgrade it to MODERATE. (Manufactum: "Gartenleuchte nicht solar" → 1 result; the catalogue clearly has many non-solar garden lights.)

### DIRECT_MATCH judging (exact product title)

- **Automatic fail (enforced in code):** the rank-#1 title MUST contain the exact query
  text. No results, or query text not in the #1 title → automatic FAIL (a shopper named a
  precise product and didn't get it first). Implemented as a deterministic guard in
  `_judge_single_query`, not left to the LLM.
- Ideal outcome is **a single result** (the exact product). PASS.
- PASS ONLY IF the exact product is #1 AND every other result is **near-identical**: either
  (a) a colour/size variant of that same product, OR (b) a member of the **same named
  series/collection** — same title pattern AND same line/brand (e.g. "1960's Space Exploration
  Sheep Mug" + "1970's Hippy Sheep Mug" + "1990's Pretty Sheep Mug" @ €14.95 = PASS).
- **Same product listed more than once is a PASS, NOT DUPLICATE_FLOODING.** When the exact
  product is at #1 and the *other* result slots are the SAME product (identical display title
  — separate catalog IDs / colour-size variants of the identical item, e.g. Huckberry
  "Schmidt Brothers 4-Piece BBQ Tool Set" returning two listings of that exact set at $100),
  that is the ideal exact-match outcome, not flooding. The variant-flooding override must not
  fire here. Enforced deterministically in `_judge_single_query`: the DIRECT_MATCH guard now
  has a PASS branch — exact query in #1 title AND the exact query appears in EVERY result title
  → `OTHER`/`PASS`, clearing any earlier flooding/ranking verdict. (DUPLICATE_FLOODING is for
  ONE model's colour/size variants crowding out *distinct* products on a broad query, not for
  an exact product-title query legitimately resolving to its own product.)
- **FAILURE** (PARTIAL_KEYWORD_MATCH) if the set contains ANY other result — even with the
  exact item at #1. This includes a **different brand** (always leakage), a **different
  product line** with a different name, or items that merely **share a category** ("hand
  wash", "mug"). Same category ≠ near-identical. (Avoca example: "Shea Verbena Hands & Body
  Liquid Soap" returned other-brand/other-line washes — "Palm Wild Hand Wash", "Geranium Hand
  & Body Wash" — = FAIL, not a pass.) Severity scales with how much of the set is leakage.

- **DIRECT_MATCH near-miss — exact product at #2 behind a same-line sibling → MINOR/PARTIAL_KEYWORD_MATCH, not MODERATE (user calibration, Cotswold).** The DIRECT_MATCH auto-fail (exact title not at #1) correctly fires, but severity should track customer impact: when the exact product IS present and visible just one slot down (#2), and the item ranked above it is a near-identical sibling from the SAME named series (e.g. "Scarpa Womens Mojito GTX Shoes" → #1 "Scarpa Womens Mojito **Wrap** GTX Shoes" £180, #2 the exact "Mojito GTX" £170), the shopper still finds the exact product immediately — that's a small ordering imperfection, not a degraded/bounce-risk experience. Rate MINOR, keep failure_mode PARTIAL_KEYWORD_MATCH. (Reserve MODERATE+ for when the exact product is buried deeper, absent, or displaced by a DIFFERENT brand / off-line product.)

- **Synonym-equivalent product NAMES depress reranker scores without a real relevance miss → don't read the gap as POOR_RANKING (user calibration, Cotswold).** When the query term and the catalogue's title term are exact synonyms for the SAME garment/product (e.g. "gilets" vs titles that say "Vest" — a vest *is* a gilet; same family as the bächli "Hemden"→"Shirt" loanword case), Voyage rewards the literal token match, so the few items literally titled with the query word score high (~0.75) and the synonym-titled items score low (~0.47) — but BOTH are the correct product type. The auto-judge reads the resulting score gap (here 0.289) as a material POOR_RANKING and the synonym item at #1 as a miss. It isn't: the #1 is a correct answer, the whole page is on-type, and the plural/term resolved fine → PASS (note the cosmetic "literal-term items rank below synonyms" as merchandising). **Check whether the query word and the title word are synonyms for the identical product before treating a reranker score gap as a ranking failure** — applies to PLURAL_SINGULAR/SYNONYM/CATEGORY queries in any language, not just loanwords.

- **PRICE_ANCHORED zero → NO_SEMANTIC_UNDERSTANDING (price-parse failure), not CATEGORY_MAPPING_FAILURE (user calibration, Cotswold).** When a price-anchored query ("waterproof jacket under £100", "day hiking pack under £50", "walking boots over £150") returns zero, the auto-judge tends to reclassify it CATEGORY_MAPPING_FAILURE because the product-term half ("waterproof jacket") resembles a real site category. That's the wrong root cause: the product term alone returns plenty of stock — it's the price clause ("under £100") that kills the query, because the engine matches "under"/"£100" as literal AND-keywords no title contains. The real, more fixable finding is that search has no price-range parsing → NO_SEMANTIC_UNDERSTANDING (CRITICAL). Same as the SEMANTIC/NATURAL_LANGUAGE exemptions from the category-mapping reclassifier: a price clause is a constraint the engine can't interpret, not a taxonomy-mapping gap. (Confirm by testing the product term alone — if it returns results, the price clause is the AND-killer.)

- **A SPLIT_WORD "success" can be FAKED by a brand/word collision — verify the FULL category returned, not just that a couple of on-type items appear (user calibration, Cotswold).** `jack et` (split of "jacket") auto-PASSed with the judge asserting "the engine rejoined jack+et into jacket." It did NOT: it matched the token "jack" → the **Jack Wolfskin** brand and returned only 3 Jack Wolfskin items — with a Kids Pompom **Beanie** at #1. The two jackets at #2/#3 were coincidence (the brand makes jackets), not rejoining. The tell: a real rejoin to "jacket" returns the site-wide multi-brand jacket assortment (hundreds, as the bare word does); a thin single-brand set whose #1 is off-type means the split was never normalized — a token collided with a brand/other word. **Before passing a SPLIT_WORD/MERGED_WORDS query, check (a) is the result set the full expected category or a thin brand-coincidence set, and (b) is rank #1 actually the target product type.** If thin + off-type #1, it's failed normalization (MODERATE/NO_FUZZY_MATCHING), not a pass. Distinct from the legit bergzeit "Wandaschuhe→Handschuhe" PASS, where the garbled word was genuinely closer to a real word and the engine returned a CLEAN, FULL set of that word's products.

> **CRITICAL — playbook ≠ judge prompt.** The judge LLM does NOT read these `.md` playbooks.
> At runtime it only sees the prompt hard-coded in `_build_prompt` (`src/judge.py`) plus
> calibration examples harvested into the per-language KB (`judge_kb`). A calibration rule
> only changes the verdict once it is written into the **prompt** (and/or harvested into the
> KB). When you add a rule here, you MUST also encode it in `_build_prompt`, or the judge
> will keep ignoring it. Keep this doc and the prompt in sync.

### BRAND_SEARCH judging

- Primary test = **brand precision**. All results the queried brand (no other-brand bleed) → PASS.
- **Flagship buried (note, not a defect):** if results are all on-brand but dominated by
  peripheral/accessory items while the brand's signature/flagship products are absent from
  the top (e.g. "Barbour" → pet accessories/umbrellas/trinkets, no wax jackets — which we
  know exist), keep **PASS** but record a "flagship products buried/absent" merchandising
  note in the evidence.
- Escalate above PASS only when a **different brand leaks in** → BRAND_BLEED.
- **Variant flooding still applies to BRAND_SEARCH (MINOR), even when brand precision is
  perfect.** A brand-only query that returns the same few models repeated across many slots
  (e.g. Huckberry "YETI" → 7 distinct products in 15 slots, Camino Tote 3×/Rambler 3×) is
  MINOR/DUPLICATE_FLOODING — the wasted real estate compresses the brand assortment the
  shopper sees. Do NOT suppress this to PASS just because there's no brand bleed; brand
  precision passing and variant flooding are independent dimensions. (Flooding severity is
  the authoritative `_flooding_severity` magnitude — MINOR here, MODERATE if it dominates the top.)
- **Off-category leakage is NOT duplicate flooding — even when the junk is repeated.**
  DUPLICATE_FLOODING is only correct when the REPEATED items are on-category/relevant and the
  sole problem is repetition. If the flooded product is itself OFF-category (low relevance,
  wrong product type for the query — e.g. Huckberry "travel bag" → Ripa Ripa swim shorts /
  CAMP sunglasses at ~0.21 repeated down the page), the real, more important finding is
  **category/relevance leakage → POOR_RANKING (MODERATE)**, not DUPLICATE_FLOODING. The engine
  returning and repeating off-category items is a precision failure, not benign variant
  flooding. Enforced deterministically in `_judge_single_query`: when a DUPLICATE_FLOODING
  verdict's flooded top-title scores below `_OFF_CATEGORY_REL` (0.30), it is reclassified to
  POOR_RANKING/MODERATE. On-category flooding (fleece pullover 0.39, beanie 0.82, YETI 0.80)
  is unaffected because its flooded items score above the floor.
- **Insignificant flooding (a couple of 2× dupe pairs) → PASS, not DUPLICATE_FLOODING.** The
  LLM sometimes flags DUPLICATE_FLOODING for trivial repetition (e.g. Huckberry "leather jacket"
  → 15 on-topic Schott leather jackets with two 2× pairs). When the most-repeated model occupies
  fewer than `_FLOOD_MIN_COUNT` (3) slots, `_flooding_severity` returns None and the clamp now
  clears the verdict to OTHER/PASS — a few dupes among otherwise on-topic, well-ranked results
  is not a defect. (A real ranking/relevance problem would carry its own non-flooding verdict.)
- **Brand verifiability (manual-verification gate).** Brand precision is only confirmable
  when the brand name appears in the result titles. If the brand is absent from ALL titles
  (e.g. "Never Fully Dressed dress", "Jellycat soft toy" — titles carry product names, not
  the brand), the automated verdict is a guess that could mask brand-bleed. **Do NOT
  auto-pass.** The judge flags these `[MANUAL VERIFICATION REQUIRED]` (deterministic guard
  `_brand_search_unverifiable` in `_judge_single_query`), and during the workflow you MUST
  surface them to the user for manual brand confirmation before finalizing. A correct-looking
  PASS here is luck, not verification.
  - **Brand isolation now uses the Phase-1 brand list (bugfix).** `_brand_search_unverifiable`
    previously isolated the brand only by stripping a fixed list of trailing product nouns, so
    a query whose product noun wasn't in that list (e.g. "Snow Peak **cookware**") failed to
    isolate "Snow Peak" and FALSE-flagged `[MANUAL VERIFICATION REQUIRED]` even though every
    title began with "Snow Peak". It now first checks whether a known site brand (passed as
    `site_brands`) is a substring of the query and, if so, verifies that brand against the
    titles directly (trailing-noun stripping is the fallback). Always pass `site_brands` to the
    judge so multi-word brands with arbitrary product nouns verify correctly.

### CONSTRAINT_DROPPED detection (the judge sees ONLY titles + price)

The judge has no images, no structured colour/size/material facets, no stock status — just
the **result title text**, the **price**, and the Voyage relevance score. This is the
weakest part of judging and fails often, so detect dropped constraints with **literal
title rules** (now enforced in the judge prompt):

- **Colour**: query names one colour → if ANY result title contains a *different* colour,
  CONSTRAINT_DROPPED.
- **Exclusion** ("… not Y" / "… without Y"): take the term after "not"/"without" → if it
  appears in result titles, CONSTRAINT_DROPPED. **Faux/imitation X still violates "not X"**
  ("Faux Leather" violates "not leather" — still leather-look). Severity by how much of the
  page violates: **≥80% violating = CRITICAL** (negation entirely ignored), ≥50% = MODERATE.
  Enforced deterministically for NEGATIVE_INTENT (`_exclusion_violation_fraction`) so exclusion
  failures are scored consistently regardless of the LLM.
  - **Category-level exclusions ARE now detected deterministically.** A CATEGORY exclusion
    ("gifts for her **not jewellery**" → results titled "Bracelet/Earrings/Necklace", never
    "jewellery") evades a literal substring check. `_exclusion_violation_fraction` now expands
    the excluded term via `_CATEGORY_SUBTYPES` (jewellery → bracelet/earring/necklace/pendant/…)
    when the term is a known category the site carries (gated on `site_categories`), so a
    100%-jewellery page scores 100% violations → CONSTRAINT_DROPPED/CRITICAL automatically.
    Extend `_CATEGORY_SUBTYPES` as new categories appear; the literal-substring path remains the
    fallback for material/colour exclusions ("not wool", "not leather").
- **Size / fit / fabric / material / any single attribute**: query names one value → if ANY
  title contains a *different* value of that same attribute, CONSTRAINT_DROPPED.
- **Price limit**: any result priced above the limit → CONSTRAINT_DROPPED.
- One offending title is enough; cite it. Severity scales with how many results violate.
- **Hard limitation:** if the constrained attribute never appears in any title, the judge
  **cannot** confirm a violation — it must not invent one, and falls back to relevance. This
  biases toward FALSE NEGATIVES, so constraint scores are a *floor* on the real problem.
  Mitigated upstream: query generation now emits **single-constraint** constraint queries
  (see QUERIES_PLAYBOOK) and biases toward title-visible constraints (colour, price).
- **Title-invisible constraint → flag for MANUAL REVIEW, don't silently pass.** When a
  MULTI_ATTRIBUTE / FACET colour or material constraint appears in NONE of the result titles
  (e.g. "black boots" → boot titles rarely state colour), the automated PASS is a guess —
  the engine may or may not have honoured the constraint, and we can't tell from titles. Do
  NOT silently pass these: the judge now appends `[MANUAL VERIFICATION REQUIRED]` (deterministic
  guard `_unverifiable_constraint_token` in `_judge_single_query`, using the `_MA_COLOURS` /
  `_MA_MATERIALS` vocab), mirroring the BRAND_SEARCH unverifiable gate. During the workflow,
  **surface these to the user for manual confirmation** before finalizing. (Skipped when a
  CONSTRAINT_DROPPED violation is already detected — there a conflicting value WAS title-visible.)
  Example: Huckberry "black boots" → 15 boots, "black" in no title → flagged; user manually
  confirmed the boots are black → PASS.

---

## Per-site profiles

### baechli-bergsport.ch (Bächli Bergsport)
- **Off-category filler at ranks #2-6 overridden PASS → MODERATE/POOR_RANKING (user calibration).** `Regenjacke` (SYNONYM) → #1 correct rain jacket (0.80, verified against live screenshot — this IS the real site ranking, not a fetch artifact), but #3-6 are a hip pack, two backpacks, and a repair kit — none of which belong on a rain-jacket query at all. The LLM judge defaulted to PASS via the "cosmetic reorder among near-equal results" rule because displacement=0 (the customer's #1 was already best). User overrode: those off-category items have no legitimate reason to occupy top-of-page real estate just because the customer's #1 happened to be correct — applies the existing "thin match padded with off-category filler → POOR_RANKING/MODERATE" calibration rule even though it wasn't an exact case match (the match here isn't "thin" — 15 results — but several of them are flatly wrong product types). **Generalizes:** don't let a correct #1 alone justify PASS when several of the next handful of slots are off-category filler; check the WHOLE visible page, not just whether displacement is 0.
- **Self-contradictory judgment overridden to PASS (user calibration) — weak-filler guard misfired on a low-score-but-correct-category case.** `Hemden` (PLURAL_SINGULAR) auto-judged MODERATE/NO_SEMANTIC_UNDERSTANDING with boilerplate "returned filler unrelated to the requested product type," but the SAME judgment's own evidence text said the opposite: all 15 results are genuine shirts/blouses, exactly matching the query. Root cause: titles use English loanwords ("Shirt", "Overshirt", "Blouse") rather than the German query term "Hemden", so the reranker scores stayed low (max 0.40) even though the category mapping is 100% correct — the low-score deterministic guard fired on score alone without verifying the category match was actually wrong. **Generalizes:** before accepting a NO_SEMANTIC_UNDERSTANDING/filler verdict, read the evidence text itself — if it explicitly says "all results are on-topic," the failure_mode/severity is wrong regardless of what triggered it deterministically. Cross-language title vocabulary (loanwords) is a known source of false-low reranker scores that should not be read as a category-mapping failure.
- **Same self-contradiction recurs on MULTI_ATTRIBUTE colour queries; user wants explicit flag-for-manual-review going forward, not a silent call either way.** `Hardshell-Jacke rot` (MULTI_ATTRIBUTE, colour constraint) hit the identical contradictory pattern as `Hemden` (failure_mode said filler/NO_SEMANTIC_UNDERSTANDING, evidence said "all 7 on-topic, cosmetic reorder") AND separately, none of the 7 titles mention any colour at all, so the colour constraint itself is title-invisible/unverifiable. User called it PASS but explicitly said: **in future, when the constraint can't be confirmed from the title (colour/material/etc. absent from every result), surface it for manual verification instead of deciding unilaterally** — don't resolve the ambiguity yourself, ask. Applies the existing `[MANUAL VERIFICATION REQUIRED]` mechanism (already used for BRAND_SEARCH) — extend the same "ask, don't guess" posture to title-invisible MULTI_ATTRIBUTE/FACET constraints during one-by-one review.
- **`Sport-BH schwarz` confirmed CONSTRAINT_DROPPED on manual check (user calibration).** Same title-invisible colour case as `Hardshell-Jacke rot` (none of the 9 sport-bra titles state colour) — but when flagged for manual review here, the user confirmed via live check that many results are NOT black. Overridden PASS → MODERATE/CONSTRAINT_DROPPED. **Lesson: title-invisible colour constraints split both ways** — `Hardshell-Jacke rot` was confirmed fine, `Sport-BH schwarz` was confirmed violated. There is no shortcut; each title-invisible colour/material case needs its own manual check, the outcome is not predictable from the query category alone.
- **`W Pullover` confirmed PARTIAL_KEYWORD_MATCH despite a correct #1 (user calibration) — applies the existing "majority of page matches only secondary term" rule.** Auto-judge said PASS because #1 was the best available pullover match (0.83) and displacement was 0. But only ~5/15 results are actual pullovers; the other ~10 are T-shirts/shirts that match only the gender token "W" — the head noun "Pullover" was dropped for the majority of the page. This is the exact case the existing QUERIES_PLAYBOOK/JUDGE_PLAYBOOK rule covers ("throws grey" → 2 grey throws at #1-2 but socks fill #3-11 → PARTIAL_KEYWORD_MATCH, not PASS), just with a single-token gender constraint instead of colour. **Generalizes:** for ABBREVIATION/MULTI_ATTRIBUTE queries with two tokens (a head noun + a modifier like gender/colour), don't let a correct #1 alone excuse a page where the modifier dominates and the head noun is largely absent — count how many results actually match the head noun, not just whether the top result does.
- **Zero-result judging needs a SPECIFIC reason, not just "0 results" restated (user instruction).** When judging zero-result queries, don't accept a generic ZERO_RESULTS_OR_GARBAGE/filler label — investigate why via the live site (header counts, the bare brand/term alone, sibling queries that DID work) and assign the most specific failure_mode the evidence supports. On baechli-bergsport.ch this surfaced real distinctions: `alpibreak Jacke`/`Kraszewski Weste` looked like catalog gaps at first (the brands genuinely don't sell that garment type) but user classified them NO_SEMANTIC_UNDERSTANDING anyway — the engine still ought to handle a brand+category AND-miss more gracefully than a hard zero. `Pull+over` returning 0 while bare `Pullover` returns 251 isolated the cause to one specific unstripped character. `PL Weste` returning 0 while both `PL` (502, noisy) and `Weste` (many) work alone isolated an AND-overlap failure, not a retrieval problem. **Generalizes:** for every zero, test the query's components in isolation (bare brand, bare category, bare modifier) before assigning a failure_mode — the isolated results tell you whether it's a synonym/mapping gap, a character-normalization gap, an AND-logic gap, or a genuine catalog gap.
- **Compound/merged-word and split-word zeros get NO_FUZZY_MATCHING labeled as "failed normalization" (user instruction).** For MERGED_WORDS and SPLIT_WORD zero-result queries specifically, the user's preferred framing is "failed normalization" (the engine doesn't normalize the broken/merged token back to a real word) rather than a generic fuzzy-matching label — use that phrasing in evidence text even though the enum value stays NO_FUZZY_MATCHING (no dedicated enum exists).
- **Season-word + category combo zeros are NO_SEMANTIC_UNDERSTANDING, not CATEGORY_MAPPING_FAILURE (user instruction).** SEASONAL_OCCASION zeros (e.g. `Winterhose Expedition`) were initially proposed as CATEGORY_MAPPING_FAILURE (the category exists, just not reached) but the user reclassified to NO_SEMANTIC_UNDERSTANDING — treating the season token as a literal AND-keyword instead of contextual intent is a semantic failure, not a taxonomy-mapping gap. Keep CATEGORY_MAPPING_FAILURE reserved for colloquial-term-for-an-existing-category cases (LOCALE_VARIATION, single-word CATEGORY_MAPPING) where there's no extra modifier token confusing the match.
- **`Herbst Fleecepullover` overridden PASS → MINOR/thin-coverage (user calibration).** Auto-judge said PASS because both 2 returned results were on-topic with perfect ordering — but the site carries ~24 real fleece pullovers (confirmed via the `Fleecejacke` query earlier in this same audit), so 2 results for a seasonal multi-word phrasing is severe under-retrieval, not a small catalogue. **Generalizes:** a perfect 2-result page is not automatically a PASS just because both results are correct — cross-check the result count against what OTHER queries in the same audit proved the catalogue actually holds before accepting a thin result as "the catalogue is just small."

### cotswoldoutdoor.com (Cotswold Outdoor)
- **Colour facets are SOFT-matched, not hard-filtered — verify via image alt-text, not titles (user calibration).** Cotswold product titles NEVER state colour, so a colour MULTI_ATTRIBUTE/FACET query ("rucksack blue") trips the `[MANUAL VERIFICATION REQUIRED]` guard. To verify, read the colour from the product image `alt` text live (e.g. Playwright `img[alt]` on `/lister.html?q=rucksack%20blue`) — the alt carries the colourway (e.g. "Waterfront Blue/Tequila Sunrise"). Finding so far: the colour term DOES bias retrieval (most results are the blue colourway, unlike price queries which hard-fail to zero), but it is NOT a hard filter — at least one off-colour item leaks at a prominent rank (rucksack blue → TNF Borealis "Granite Grey/Dust Orange" at #2). Per the 100%-or-fail facet rule, that single leak → MODERATE/CONSTRAINT_DROPPED. Treat Cotswold colour facets as soft keyword bias, not applied filters; still verify each via image alt-text rather than assuming.

### huckberry.com (Huckberry)
- **Fjallraven has NO backpacks at Huckberry (verified live).** Huckberry's Fjallraven range is apparel only (Buck Fleece, Abisko shirts, Vidda trousers/shorts) — a "Kanken" search returns only Fjallraven apparel, and "backpack" returns other brands (Filson/GORUCK/Osprey/Arc'teryx). So "Fjallraven backpack" → 8 Fjallraven apparel items is a **catalog gap (brand+type combo with no inventory), not a search-engine failure**. Rated MINOR/PARTIAL_KEYWORD_MATCH (the head-noun "backpack" drop is mildly suboptimal — better to show other-brand backpacks or signal the gap — but the engine can't return a product that doesn't exist). General lesson (already in calibration rules): for any brand+type zero/low result, verify the combo exists live before rating it a failure.

---

### bergzeit.de (Bergzeit)
- **Hard CONSTRAINT_DROPPED CRITICAL-escalation rule wasn't applied despite both trigger conditions firing — judge under-rated MINOR (caught at judge time).** `Fahrradhelm unter 80 Euro` (price ceiling €80): ALL 15 results violate (cheapest €97.60, max €349.95) AND the top result itself is off-constraint (€99.50) — both independently satisfy the existing "Escalate to CRITICAL if violations dominate (≥80% of page) or the top result itself is off-constraint" rule in the CONSTRAINT_DROPPED section, yet the auto-judge rated MINOR, reasoning that the *internal* ranking among the (all wrong) returned results was near-optimal. User escalated to CRITICAL. **Generalizes:** the "internal ranking is fine" framing must NOT offset a 100%-violation/top-violates case — those two triggers override ranking-quality framing entirely, they are not inputs into a severity average. Check the dominance/top-violation triggers FIRST and independently of how well-ordered the (wrong) result set is.
- **Title-invisible colour constraint on MULTI_ATTRIBUTE silently auto-PASSed instead of flagged (caught at judge time) — the `[MANUAL VERIFICATION REQUIRED]` guard didn't fire.** `Damen Laufschuhe blau` (colour constraint "blau") returned 15 on-topic women's running shoes, but NONE of the titles mention any colour. The judge's own evidence said "the colour attribute does not appear in any product title... cannot be confirmed... but since all results are on-topic, this does not constitute a dropped-constraint failure" — i.e. it resolved the ambiguity itself instead of flagging, exactly the failure mode the `_unverifiable_constraint_token` guard exists to prevent (see CONSTRAINT_DROPPED detection section). User flagged for manual verification per policy. **Generalizes / code gap to investigate:** the guard apparently didn't trigger for this colour token ("blau") — check whether `_MA_COLOURS` vocab includes German colour terms, or whether the guard only fires for English. Until confirmed fixed, manually check any non-English MULTI_ATTRIBUTE colour/material query where the constraint is absent from all titles — don't trust the deterministic guard to catch it. **Resolved on manual check: confirmed PASS** — the products ARE correctly blue despite the title not stating colour. A second title-invisible colour case (`Herren Softshelljacke schwarz`/black) on the same audit was also confirmed PASS by the user. **Unlike bächli (where title-invisible colour cases split both ways), on bergzeit.de colour matching has now checked out correct twice in a row — treat bergzeit.de colour constraints as reliably honored even when absent from titles, and don't re-flag every individual title-invisible colour case on this host going forward** (still flag the FIRST one on a fresh audit of a different host; this trust is host-specific, not universal).
- **SYNONYM mapping to a generic supercategory instead of the specific intended subtype is PARTIAL_KEYWORD_MATCH, not PASS, even when every result is loosely "on-topic" (user calibration).** `Turnschuhe Damen` (colloquial for casual sneakers, mapping to the site's `Freizeitschuhe` category) auto-judged PASS because all 15 results were "women's shoes" — but checking the titles, only 1/15 (an adidas Freizeitschuhe, buried at rank #10) was actually the correct shoe TYPE; the other 14 were hiking/trekking boots (Hanwag, Salomon GTX) that only share the generic tokens "Damen"/"Schuhe". The judge's "all on-topic, cosmetic reorder" framing was too coarse — it treated the whole women's-footwear catalog as one topic instead of checking whether the SPECIFIC subtype the synonym maps to was actually retrieved. **Generalizes:** for SYNONYM/CATEGORY_MAPPING queries, don't accept "broadly the right department" as on-topic — verify what fraction of results match the SPECIFIC subtype the synonym is supposed to resolve to; if that's a small minority (here 1/15) with the rest being a different, broader/adjacent subtype, it's PARTIAL_KEYWORD_MATCH (head-noun/specific-intent dropped), the same family as the existing "majority of page matches only secondary term" rule.
- **A TYPO query that collides with an unrelated real word, where the engine matches that real word, is a PASS, not a search failure (user calibration).** `Wandaschuhe Herren` (intended as a drastic respelling of `Wanderschuhe Herren`, hiking shoes) was garbled enough that by edit distance it landed closer to the unrelated real German word `Handschuhe` (gloves) than to the intended target. The engine returned 15 genuine, well-ranked gloves. The auto-judge initially called this MODERATE/NO_SEMANTIC_UNDERSTANDING with a self-contradictory rationale (called the results "filler unrelated to the requested product type" then talked itself into excusing it as "the ideal ranking"). User overrode to PASS: correctly resolving a garbled string to its nearest REAL dictionary word is correct fuzzy-matching behavior — the fault is in the TYPO query's construction (too aggressively garbled), not the search engine. **Generalizes:** before judging a TYPO/garbled-spelling zero or off-topic result as a failure, check whether the garbled string is actually closer (by edit distance / shared letters) to a different real word than to the intended target — if so, and the engine matched that other real word well, it's a PASS, and the lesson goes back to QUERIES_PLAYBOOK (don't over-garble TYPO queries into colliding with unrelated real words).

### lyko.com (Lyko — Swedish multi-brand beauty)
- **SPONSORED (SPONSRAD) top results are ad placements, not organic ranking — exclude them from ranking judgment (user calibration, key rule).** Lyko injects 1–2 paid "SPONSRAD" products at the very top of most commercial search results (recurring promoted brands seen across unrelated queries: Löwengrip, Rexona, and often the By Lyko house brand). These are ads, outside the search engine's organic ranking. Judging POOR_RANKING on them would fail nearly every query and make the audit unusable. **Rule:** when the off-brand/off-category items at the top are sponsored placements AND the ORGANIC results below are on-topic/correctly ranked, the query is a PASS. Only rate POOR_RANKING when the ORGANIC (non-sponsored) ranking is genuinely wrong. (Query 9 `ansiktsolja hudvård`: top-2 sponsored self-tan/shower, organic = face oils → PASS.) To apply: identify sponsored slots (the recurring promoted brands at rank #1–2, or verify the SPONSRAD badge live) and judge the remaining organic set.
- **DIRECT_MATCH false-fail from featured-item title punctuation (user calibration).** `Beauty of Joseon Glow Serum Propolis + Niacinamide 30 ml` auto-failed MODERATE/PARTIAL_KEYWORD_MATCH because the on-site title is `Beauty of Joseon Glow Serum: Propolis+Niacinamide 30 ml` (colon, no spaces around `+`) — the exact product WAS at #1 (rel 0.95) with its Duo/60ml variants at #2/#3. User confirmed PASS. Same class as Manufactum's "use the on-site name or the judge false-fails." **Fix at source:** Phase-1 `featured_items` for Lyko must use the exact on-site title spelling (colon, `Propolis+Niacinamide` no spaces). When a DIRECT_MATCH auto-fail's only discrepancy vs the #1 title is punctuation/spacing, it's a PASS, not a leakage failure.
- **Exclusion/negation is NOT enforced — systemic, MODERATE/CONSTRAINT_DROPPED (user calibration, verified twice).** Lyko treats "utan/inte/parfymfritt/silikonfri" as soft keywords, not filters. Confirmed: `schampo parfymfritt` (fragranced shampoos interleaved, live) and `hårbalsam utan silikon` (OGX Coconut Milk Balsam contains dimethicone per its INCI, yet returned). When the excluded attribute is TITLE-VISIBLE (parfymfritt/perfume free appears in titles) judge from titles; when TITLE-INVISIBLE (silikon), the LLM auto-passes on relevance — don't trust it: spot-check 1-2 results' INCI on the product page (search element textContent for `dimethicone`/`…cone`/`siloxane`). Any violating result = CONSTRAINT_DROPPED. MODERATE by default; CRITICAL only if ≥80% verified violating. Systemic NEGATIVE_INTENT weakness — call it out once in the report rather than re-deriving each query.
- **Auto-judge over-PASSes weak-filler NATURAL_LANGUAGE queries because Lyko never returns zero (user calibration).** Lyko always returns a full loosely-related fallback set, so the LLM defaults to "near-equal scores → cosmetic reorder → PASS" even when the whole page is off-intent filler. Apply the existing weak-filler rule: if the results are the wrong product type for the intent (e.g. `något som gör huden mer lysande och jämn` → self-tan, hair/nail supplements, nail polish; NO brightening skincare despite it being stocked) and max relevance is weak (~0.45–0.50), it's NO_SEMANTIC_UNDERSTANDING/MODERATE, not PASS. Read the actual product types on the page, don't trust the score-gap framing. Contrast with genuinely-good NL queries (`serum mot stora porer` → pore serums; `torr hud på vintern` → moisturizers = real PASS).
- **Swedish gender token `herr` (men) collides with English "her" (women) — real PARTIAL_KEYWORD_MATCH (user calibration).** `doft herr` (men's scent) returned an organic top of Gosh **"For Her"** (women's) fragrances/deodorants; men's fragrances buried at #12-14. The engine matched `doft` + the English word "her" inside the product names and inverted the gender intent. Rate MODERATE/PARTIAL_KEYWORD_MATCH (gender token dropped, majority of page matches only the secondary term). Watch other Swedish gender/loanword tokens for the same substring collision (`herr`, `dam`) on this multilingual catalog.
- **Gender/recipient intent is dropped systemically (user calibration) — MODERATE/PARTIAL_KEYWORD_MATCH.** Confirmed twice: `doft herr` (men → women's Gosh "For Her") and `present till pojkvän parfym` (boyfriend/male → majority women's fragrances: Women'secret ×4, Narciso For Her, Prada Donna). The engine matches the product/occasion tokens but ignores the recipient-gender token (`herr`, `pojkvän`). Even when a couple of correct-gender items rank at #1-2 (pojkvän case: Hugo Boss men's at #1-2), if the MAJORITY of the page is the wrong gender it's PARTIAL_KEYWORD_MATCH (correct top-2 keeps it MODERATE, not CRITICAL). Recurring theme worth a report callout.
- **DIRECT_MATCH on Lyko returns the full brand-related grid, and that's fine.** An exact-title query returns the exact product at #1 then the rest of that brand's related line (variants, other serums/creams) — normal e-commerce behavior, not leakage. PASS as long as the exact product leads. (Query 1: COSRX Snail 96 Essence → exact #1, all 15 COSRX → PASS.)

## When you learn something new

After every Phase 6 override, append a Calibration rule (if it generalizes) or a per-site
profile (host-specific severity expectations). One override = one rule.
