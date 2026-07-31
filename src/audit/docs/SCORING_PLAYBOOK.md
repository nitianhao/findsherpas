# Scoring Playbook — Phase 5 knowledge base

> **Read this BEFORE running Phase 5 (junk cleanup + `score_results`).** It records
> cleanup/scoring patterns per site and in general, so we don't re-debug the same poisoned
> results and threshold calls each audit. When the user adjusts cleanup or scoring, capture
> it here.
>
> Companion docs: `ARCHITECTURE.md`, `FETCHER_PLAYBOOK.md` (upstream fetch traps that show
> up here), and the `synthetic-search-audit` skill. Operational memory for the **score** phase.

---

## How to use this file

1. Before Phase 5, check the **Per-site profile** for known junk titles, poisoned-result
   URL patterns, and accurate-but-low-count quirks for this host.
2. Run the junk cleanup pass, re-index ranks (1-based) per query, save back to phase 4 + 5
   checkpoints, and report how many junk entries were removed.
3. Then `score_results` on the **cleaned** data and report the standard stats.
4. After any correction, record the new junk title / poisoned pattern / low-count truth.

---

## General learnings (apply to every site)

**Junk titles to strip** (extend per locale): `"Show more"`, `"Compare products"`,
`"Sign in"`, `"Register"`, `"Accept all"`, `"Clear all"`, `"Go to cart"`, `"Categories"`,
`"Brands"`, `"Forgot password?"`, plus the Czech/Swedish sets recorded in the skill.

**Drop a result when:** title is a known junk string · URL is missing/empty · URL starts
with `#` (anchor/modal, not a product page).

**Poisoned results (silent fetch failure surfacing at scoring):** URLs containing
`policies.google.com`, `business.safety.google`, or privacy-policy paths; or a query where
ALL results are non-product pages. For each: verify on the live site whether real results
exist → extract them, or set results to `[]` if genuinely zero. Re-score only fixed queries.

**Thresholds to report:** queries with **0 results**; average relevance per category;
queries where **top result relevance < 0.3** (the bounce-risk signal — feeds Phase 6
CRITICAL calibration, see `JUDGE_PLAYBOOK.md`).

**Low count ≠ under-collection:** narrow multi-word queries can genuinely return few real
results. Verify card count against the live results container before treating low counts as
a fetch problem (cf. ahlens.se in `FETCHER_PLAYBOOK.md`).

**Do NOT score zero-result queries — it wastes money (hard rule).** A query with `[]`
results has nothing to relevance-score, but feeding it to `score_results` still incurs LLM
cost for no signal (its score is trivially 0 / top-relevance 0). Filter zero-result queries
OUT before calling `score_results`, score only the non-empty ones, then merge the empties
back as `[]` for the report/judge. The zeros are still reported and judged (they're the core
findings) — they just skip the paid scoring step. Same logic applies in Phase 6: re-judge
only changed queries, never the whole set.

---

## Per-site profiles

### huckberry.com (Huckberry)
- **Genuine zeros on conversational/intent queries (verified live).** Huckberry's search does literal multi-token matching and collapses to ZERO results on natural-language, occasion/gift, and semantic queries — even "gift for dad who loves grilling" and "warm jacket for hiking in cold weather" return nothing. Spot-checked 3 zeros live (headed Chromium): all showed 0 product tiles and the marker **"couldn't find any products that match your search"**. These are real search failures, NOT false zeros / extraction bugs — the `_try_huckberry` dedicated extractor + authoritative-empty are faithful. Treat the 0-result cluster (NATURAL_LANGUAGE, OCCASION, SEMANTIC_MEANING, SEASONAL_OCCASION) as genuine CRITICAL findings, not collection problems.
- **No junk to clean.** The dedicated product-tile extractor yields only real products (0 junk titles, 0 missing/anchor URLs, every result has a `/store/` URL + price). The junk-cleanup pass is a no-op for this host.
- **Accurate low counts:** exact-match `featured_items` legitimately return 1–2 (e.g. "YETI Tundra 35 Cooler" → 2 near-identical listings; "Osprey Campcore Transporter Gear Tote 60L" → 1). Don't treat these as under-collection.

---

### manufactum.de (Manufactum)
- **BRAND_SEARCH false-lows trace to the title, not the engine.** Manufactum keeps the manufacturer in a separate `data-test-sell-product-manufacturer` span, NOT in the product name. If the extractor emits name-only titles, Voyage `rerank-2.5` scores brand queries (e.g. "Armedangels") as near-misses — "Armedangels" → top relevance 0.23 (false bounce-risk / false CRITICAL) even though all 15 results are genuine Armedangels products. Fix is upstream in `_try_manufactum` (compose `brand + name`, see FETCHER_PLAYBOOK); after that BRAND_SEARCH avg went 0.49 → 0.78 and the <0.3 bounce flag cleared. **If you see a brand query scoring low, check the title has the brand before treating it as a ranking finding.**
- **No junk to clean** — the dedicated `data-test-*` extractor yields only real products (junk-cleanup pass removed 0).
- **Accurate low counts:** exact-match featured items legitimately return 1–3 (e.g. DIRECT_MATCH Sonnenglas → 3, Kopfbandlupe → 1). Not under-collection.

### baechli-bergsport.ch (Bächli Bergsport)
- **BRAND_SEARCH false-low, same root cause as manufactum.de.** `_try_baechli` emits title = product name only (brand lives in a separate `<p>` sibling, deliberately left out on the assumption the brand is also tested as its own standalone query). Result: `boreal` → top relevance 0.27 (titles "Alpha", "Alpha Lace"), `eZeefit` → 0.31 (titles "Ankle Bootie 2mm/Ultrathin") — both flagged as bounce-risk (<0.3) even though every result genuinely is that brand. User chose to leave the extractor as-is for this audit and **manually downgrade/override the judge's verdict on these two queries** at Phase 6 rather than re-fetching — don't auto-flag them as CRITICAL bounce-risk without that manual check.
- **No junk to clean** — dedicated extractor scoped to `div.grid.multiline.products article`, 0 junk removed.
- **Zero-result queries excluded from scoring per the hard rule** — 24/60 queries (TYPO 4/4, SPLIT_WORD 4/4, PRICE_ANCHORED 4/4, plus partial misses across MERGED_WORDS/BRAND_SEARCH/ABBREVIATION/SPECIAL_CHARACTER/LOCALE_VARIATION/SEASONAL_OCCASION/CATEGORY_MAPPING) were verified genuine (live-checked) and merged back as `[]` for the judge without incurring scoring cost.

### lyko.com (Lyko — Swedish multi-brand beauty)
- **The engine never returns a true zero** (verified live across 4 NL queries): for queries it can't parse it falls back to a large, loosely-related result set (e.g. `något som gör huden mer lysande och jämn` → 54 "produkter" of self-tan/deodorant/nail polish). So expect **0 zero-result queries** and **0 rank-1 relevance < 0.30** — this is real engine behavior, not under-collection. POOR_RANKING/bounce-risk (<0.30) will NOT be the driver of CRITICALs here.
- **Relevance score misses intent violations — the judge must catch them separately.** NEGATIVE_INTENT queries score HIGH because the returned products are on-type: `deodorant inte Rexona` → 0.71 with rank-1 an actual Rexona deo (violates the exclusion); `solskydd utan nano-partiklar` → 0.44. The reranker can't see negation. Flag NEGATIVE_INTENT by checking whether the excluded brand/ingredient appears in the top results, independent of the relevance score.
- **No junk to clean** — the dedicated `_try_lyko` extractor (post category-redirect fix) yields only real products; junk-cleanup removed 0.
- **Category averages (this run):** DIRECT_MATCH 0.95, BRAND_SEARCH/MULTI_ATTRIBUTE 0.85, TYPO/FACET 0.82 (strong); SPECIAL_CHARACTER 0.53, OCCASION 0.59, NATURAL_LANGUAGE 0.64 (weaker — abstract/occasion/gift intent + sponsored-deo pollution on perfume queries).
- **Accurate low counts:** `Beauty of Joseon serum` → 14 (brand genuinely has ~14 serums), not under-collection.

## When you learn something new

After every Phase 5 correction, append a per-site profile (host-specific junk titles,
poisoned patterns, accurate-low-count queries) or a General-learnings entry if it generalizes.
