# Scanner round-two report — 2026-11-19

**15 visually verified proof cards across 6/12 stores** (50% of the cohort; 6/8 stores with readable catalog controls). The failures are ordinary typo, spacing and price-requirement failures. Five candidate failures were rejected, and two diagnostic candidates lacked usable screenshots. No unreviewed candidate is published as a proof card.

All twelve stores were attempted with headed Chromium. Five show Shopify storefront evidence: Finisterre, Passenger, Watery, Dedoles and Connox. The [cohort CSV](docs/scanner-validation/stores-round2.csv) spans GB, DE, CZ, SK, PL, DK and SE, with outdoor/apparel, swimming, instruments, streetwear and home design. These are specialist prospects, **not a verified €10–100M revenue sample**; revenue qualification remains outstanding. Komputronik was removed before scanning after its corporate report showed it exceeded the intended size range.

No InstantDB writes, email sends or git pushes were performed. The authorized sibling dotenv was read without printing credentials; sibling source files were not modified. The database payload builder was tested with a mocked transaction only. Local commits require the worktree’s normal shared Git metadata updates.

## Probe changes

Ideas come from [the failure-mode library](docs/search-failure-modes.md): F001–F005/F007, F018/F019/F021/F022/F025/F026/F028, F041–F043 and F057. Requested merged/split-word checks also cover F013, which is supplementary to the library’s 30 approved modes. This is not an implementation of all 30 modes; autocomplete, stock/variant feasibility and full navigation/filter audits remain outside this battery.

- Generate several merged navigation phrases, genuine compound splits, locale-aware inflections, synonyms, natural/problem queries, brand/model terms, observed codes, misspelled brands, diacritics and formatting/unit/abbreviation variants. Controls are literal observed navigation or product titles. Conditional deterministic examples include `12oz` / `12 oz` / `12 ounce`, `TV-Möbel` / `Fernsehmöbel`, and codes observed outside the first three ranking targets.
- Reorder explicit catalog-title attributes into longer shopper queries; price limits qualify a product already observed below the limit. Validate returned top-three prices and literal title attributes. Missing color/gender/material/size data stays unknown. No invented shoe size, material or color is accepted, and narrowing counts do not prove compliance.
- Execute exact-name and top-three ranking checks, catalog-product coverage, brand/model and code probes. Results overlap/product identity replaces count-ratio success. Nonzero disjoint samples are inconclusive. All nine capability groups now have an explicit result or applicability/technical-error explanation.
- Use one bounded Haiku 4.5 generation call per readable scan. Reject invented control terms, unsupported constraint/brand words and supposed compound splits that rewrite the term. Semantic hypotheses remain partial until their catalog meaning is verified. A product-card brand can generate deterministic brand/model and brand-typo checks.
- Add per-finding `severity`, `confidence`, `verified` and `review_note`. A proof requires a repeated high-confidence failure, a positive control, two distinct screenshots and explicit visual approval. Both benchmark export and the database payload builder enforce this gate.
- Fix discovery/extraction hazards encountered on these stores: actionless JS search forms, country/footer/CTA menu labels, hidden zero-state templates, recommendation padding, custom product grids and Connox shadow-DOM cards. Save unique full-query capture names, rendered/raw HTML, sanitized API count summaries and capture timestamps; retry one transient browser failure. Failed discovery seeds and gibberish recommendation cards are not automatic search failures.

The final records combine full scans, independent headed rechecks and conservative rescoring of saved observations. The report’s scores are **adjudicated**: unreviewed or invalid failure candidates are partial; extraction errors remain errors. Original runtime runs remain local under ignored `scanner_output/round2-*`; [the source-run map and complete probe records](docs/scanner-validation/round2/results.json), [review decisions](docs/scanner-validation/round2/reviews.json) and versioned screenshots preserve the review trail. The early capture-filename collision was fixed and covered by regression tests; affected Passenger evidence was discarded and a complete fresh battery was run.

## Per-store results

A failure means at least one verified failure in this sampled battery, not that the entire search engine is broken. Country is the storefront/cohort country, not an assertion about delivery eligibility. Browser geo prompts sometimes indicated Czechia; Finisterre/Connox prices were EUR, Passenger GBP, Watery DKK and Rock Point CZK. Each proof uses its observed currency and paired storefront state.

| Store | Country / vertical | Platform evidence | Overall | Verified cards | Battery cost USD | Store runtime |
|---|---|---|---|---:|---:|---:|
| [finisterre.com](docs/scanner-validation/round2/finisterre_com.json) | GB / outdoor clothing | Shopify | fail | 1 | $0.010654 | 486.2s |
| [passenger-clothing.com](docs/scanner-validation/round2/passenger-clothing_com.json) | GB / outdoor clothing | Shopify | fail | 3 | $0.005053 | 341.3s |
| [watery.dk](docs/scanner-validation/round2/watery_dk.json) | DK / swimming | Shopify | fail | 1 | $0.006081 | 402.6s |
| [dedoles.sk](docs/scanner-validation/round2/dedoles_sk.json) | SK / clothing | Shopify | error | 0 | $0.006605 | 309.5s |
| [kytary.cz](docs/scanner-validation/round2/kytary_cz.json) | CZ / musical instruments | unknown | error | 0 | $0.000000 | 15.4s |
| [rockpoint.cz](docs/scanner-validation/round2/rockpoint_cz.json) | CZ / outdoor | unknown | fail | 5 | $0.004931 | 368.4s |
| [8a.pl](docs/scanner-validation/round2/8a_pl.json) | PL / outdoor | unknown | blocked | 0 | $0.000000 | 21.7s |
| [doorout.com](docs/scanner-validation/round2/doorout_com.json) | DE / outdoor | unknown | error | 0 | $0.000000 | 32.2s |
| [naturzeit.com](docs/scanner-validation/round2/naturzeit_com.json) | DE / outdoor | unknown | fail | 4 | $0.003150 | 220.6s |
| [connox.de](docs/scanner-validation/round2/connox_de.json) | DE / home design | Shopify | fail | 1 | $0.004998 | 349.8s |
| [designtorget.se](docs/scanner-validation/round2/designtorget_se.json) | SE / home design | unknown | partial | 0 | $0.005851 | 381.0s |
| [supersklep.pl](docs/scanner-validation/round2/supersklep_pl.json) | PL / streetwear | unknown | error | 0 | $0.000000 | 15.2s |

Battery cost/runtime are the full source scans used for these records; Finisterre uses two full scans to repair transient errors. Browser-only follow-ups cost $0 in LLM calls and are additional runtime. Dedoles had readable products but incomplete exact/control extraction, so its result remains error/incomplete. Neither Dedoles nor Designtorget has a verified proof card; this does not establish that their search is good.

## Per-capability results

P = pass on the observed sample; ~ = partial/inconclusive; F = visually verified failure; E = technical error or not reached. For an unreachable store, E does not mean a search-quality failure. Every readable store has all nine capability groups represented, including follow-up brand/model, code, abbreviation, unit-format and diacritic checks. Probe-level omissions are recorded with explicit sampled-catalog reasons in each JSON; they are not claims that the full store lacks that feature.

| Store | Basic | Typo | Language | Locale/format | Compound | Constraints | Brand/model | Coverage/rank | Zero recovery |
|---|---|---|---|---|---|---|---|---|---|
| finisterre.com | P | P | E | P | F | E | E | P | P |
| passenger-clothing.com | P | F | ~ | P | F | ~ | P | P | P |
| watery.dk | P | ~ | P | P | ~ | F | P | P | P |
| dedoles.sk | E | E | P | P | ~ | ~ | P | E | ~ |
| kytary.cz | E | E | E | E | E | E | E | E | E |
| rockpoint.cz | P | F | ~ | P | F | F | ~ | P | P |
| 8a.pl | E | E | E | E | E | E | E | E | E |
| doorout.com | E | E | E | E | E | E | E | E | E |
| naturzeit.com | P | ~ | ~ | P | F | F | P | P | P |
| connox.de | P | P | P | P | P | F | P | P | ~ |
| designtorget.se | P | ~ | P | P | P | ~ | ~ | P | P |
| supersklep.pl | E | E | E | E | E | E | E | E | E |

Observed supplemental successes include Connox `CH24` → 11 products, with the known CH24 chair retrieved; `Kave Home Onix Fernsehmöbel` → 34 versus its TV-Möbel control → 23; Naturzeit’s misspelled `Craghopers …` → the same qualifying shirt; Rock Point `Obleceni` → 10,000; and Finisterre’s `12 oz` / `12 ounce` variants retrieving the known traveller. These are retrieval checks, not proof that every returned product is relevant or that equivalent queries have identical coverage. No exact-product ranking failure was verified.

## Verified proof cards

Counts are displayed product totals, not category/editorial totals; Rock Point’s 10,000 may be a display cap, not a catalog census. `≥5` is a documented extracted lower bound rather than a claimed catalog total. Every row was visually checked with its control; zeros and price violations were repeated in fresh browser contexts. Severity describes the observed dead end/constraint violation, not estimated commercial impact.

| Store / probe | Query → products | Positive control → products | Severity / confidence | Screenshots |
|---|---|---|---|---|
| finisterre.com / merged_words | `OtherAccessories` → **0** | `Other Accessories` → **≥5** | high / high | [Query](docs/scanner-validation/round2/evidence/finisterre_com-1a5482407a-query.png) · [Control](docs/scanner-validation/round2/evidence/finisterre_com-a8480f2fac-control.png) |
| passenger-clothing.com / typo | `Jacekts` → **0** | `Jackets` → **56** | high / high | [Query](docs/scanner-validation/round2/evidence/passenger-clothing_com-f488dc965f-query.png) · [Control](docs/scanner-validation/round2/evidence/passenger-clothing_com-bfdc4ddef9-control.png) |
| passenger-clothing.com / merged_words | `InsulatedJackets` → **0** | `Insulated Jackets` → **56** | high / high | [Query](docs/scanner-validation/round2/evidence/passenger-clothing_com-47236f8d18-query.png) · [Control](docs/scanner-validation/round2/evidence/passenger-clothing_com-0298b6bc37-control.png) |
| passenger-clothing.com / merged_words | `WaterproofJackets` → **0** | `Waterproof Jackets` → **56** | high / high | [Query](docs/scanner-validation/round2/evidence/passenger-clothing_com-99151227cf-query.png) · [Control](docs/scanner-validation/round2/evidence/passenger-clothing_com-614b4b26b1-control.png) |
| watery.dk / price_constraint | `Watery vandtæt bum bag - Talia - Orange under 96` → **5** | `Watery vandtæt bum bag - Talia - Orange` → **13** | medium / high | [Query](docs/scanner-validation/round2/evidence/watery_dk-c199853179-query.png) · [Control](docs/scanner-validation/round2/evidence/watery_dk-2420d80a1a-control.png) |
| rockpoint.cz / typo | `Obleeční` → **0** | `Oblečení` → **10000** | high / high | [Query](docs/scanner-validation/round2/evidence/rockpoint_cz-3e6a6f2864-query.png) · [Control](docs/scanner-validation/round2/evidence/rockpoint_cz-8861ba26df-control.png) |
| rockpoint.cz / typo | `Bundy, kabtáy a vesty` → **0** | `Bundy, kabáty a vesty` → **1289** | high / high | [Query](docs/scanner-validation/round2/evidence/rockpoint_cz-77acc1aa44-query.png) · [Control](docs/scanner-validation/round2/evidence/rockpoint_cz-945e70598d-control.png) |
| rockpoint.cz / merged_words | `Kalhotyakraťasy` → **0** | `Kalhoty a kraťasy` → **1602** | high / high | [Query](docs/scanner-validation/round2/evidence/rockpoint_cz-059011182a-query.png) · [Control](docs/scanner-validation/round2/evidence/rockpoint_cz-09caf078d5-control.png) |
| rockpoint.cz / merged_words | `Kalhotyalegíny` → **0** | `Kalhoty a legíny` → **1096** | high / high | [Query](docs/scanner-validation/round2/evidence/rockpoint_cz-c3930208ff-query.png) · [Control](docs/scanner-validation/round2/evidence/rockpoint_cz-fb641e608c-control.png) |
| rockpoint.cz / price_constraint | `RAFIKI LEDGE do 2989` → **0** | `RAFIKI LEDGE` → **4** | high / high | [Query](docs/scanner-validation/round2/evidence/rockpoint_cz-0e3e892458-query.png) · [Control](docs/scanner-validation/round2/evidence/rockpoint_cz-a75c4977e5-control.png) |
| naturzeit.com / merged_words | `HardshelljackenundRegenjacken` → **0** | `Hardshelljacken und Regenjacken` → **260** | high / high | [Query](docs/scanner-validation/round2/evidence/naturzeit_com-e5727bda17-query.png) · [Control](docs/scanner-validation/round2/evidence/naturzeit_com-a16d6bc627-control.png) |
| naturzeit.com / merged_words | `FahrradjackenundFahrradwesten` → **0** | `Fahrradjacken und Fahrradwesten` → **17** | high / high | [Query](docs/scanner-validation/round2/evidence/naturzeit_com-8920402f22-query.png) · [Control](docs/scanner-validation/round2/evidence/naturzeit_com-06809679a3-control.png) |
| naturzeit.com / merged_words | `WanderhosenundTrekkinghosen` → **0** | `Wanderhosen und Trekkinghosen` → **119** | high / high | [Query](docs/scanner-validation/round2/evidence/naturzeit_com-cf74cbd64d-query.png) · [Control](docs/scanner-validation/round2/evidence/naturzeit_com-feec37d8dc-control.png) |
| naturzeit.com / price_constraint | `NosiLife Alma Long Sleeved Shirt Women unter 71` → **0** | `NosiLife Alma Long Sleeved Shirt Women` → **1** | high / high | [Query](docs/scanner-validation/round2/evidence/naturzeit_com-64096667ac-query.png) · [Control](docs/scanner-validation/round2/evidence/naturzeit_com-1c906823ab-control.png) |
| connox.de / price_constraint | `Kave Home Onix TV-Möbel unter 1143` → **3455** | `Kave Home Onix TV-Möbel` → **23** | medium / high | [Query](docs/scanner-validation/round2/evidence/connox_de-76cd7994ff-query.png) · [Control](docs/scanner-validation/round2/evidence/connox_de-d29af52b72-control.png) |

Price proof details: Naturzeit’s qualifying shirt is €58.47 below €71; Rock Point’s four qualifying trouser variants are 2,490 Kč below 2,989 Kč (the search also incorrectly rewrites `2989` to `289`); Watery returns a black Talia bag at 99.95 DKK despite `under 96`, while the requested orange bag is 79.96 DKK; Connox’s qualifying TV unit is €952 below €1,143, but the budget query broadens from 23 to 3,455 products and includes a €1,343 cabinet in the first three. A separate clear Connox control capture exposes the qualifying price. Finisterre explicitly labels its zero-page fallback as “Most Loved Gear”; those cards are not counted as search hits. Rock Point’s merged queries sometimes find categories while their product tab remains zero.

Some Passenger newsletter/market prompts remain in its captures, but the query, explicit no-results text, positive total and relevant control cards are visible. No form was submitted. Proof hashes are recorded in the [evidence manifest](docs/scanner-validation/round2/evidence-manifest.json).

## False positives and review outcome

**22 distinct candidate findings reviewed: 15 accepted, 5 rejected, 2 unverifiable.** The operational candidate false-positive share is **5 / (15 + 5) = 25%** among adjudicable candidates; the two unusable diagnostic captures are excluded from that denominator. Across all 22 reviewed candidates, 22.7% were rejected and 9.1% were unverifiable. This is a development/triage false-discovery measure, not a population-wide statistical false-positive rate. All 15 retained proof cards were checked; there are no known false cards in the retained set.

- **Two catalog-gap false positives:** `RAFIKI LEDGE bunda` and `RAFIKI CRIMP alpinistická bunda`. The control screenshots identify both models as trousers; Haiku invented “jacket”. Both were downgraded and the generator now rejects unsupported brand/model query words.
- **Three invalid navigation candidates:** `Seacrh` versus utility label `Search`, and merged `ExploreWomen's` / `ExploreMen's`. These test UI wording rather than ordinary product vocabulary. Utility/CTA filters now prevent them from becoming catalog probes.
- **Two unverifiable diagnostic candidates:** an early Passenger demographic typo and a different budget query shared overwritten query/control filenames. They were withheld, not credited as real failures. Unique hashed capture names, distinct-file proof gating and a two-query capture regression fix that defect. The final Passenger run has three different, fully reviewed product-category findings.

Additional extraction defects—homepage recommendations mistaken for results, hidden empty-state text, noisy card titles and sample counts presented as totals—were corrected or conservatively marked inconclusive. They are agent/extractor problems, not store failures. Non-reviewed semantic hypotheses and unknown attributes remain partial.

## Blocks and incomplete stores

- **8a.pl:** genuine Cloudflare verification wall after the bounded headed wait; [reviewed screenshot](docs/scanner-validation/round2/evidence/8a_pl-blocked.png). No search-quality judgment.
- **doorout.com:** homepage navigation timed out. This is recorded as a technical timeout, not proven bot protection.
- **kytary.cz and supersklep.pl:** no reproducible search URL was discovered, including an interactive submission attempt against the observed JS search inputs. These are scanner discovery limitations, not proven bot blocks.
- **Dedoles:** partial extraction/control/ranking evidence; no verified failure. Intermittent connection refusals also affected Finisterre and some follow-ups. They remain errors and were never converted into zeros.

## Cost, runtime and validation

- Selected source full batteries: **$0.047323** in estimated Haiku cost; **2944.0s** summed store runtime (49.1 minutes, not wall time).
- All token-logged development and validation calls: **20 Haiku calls, $0.104039**. One early interrupted call predates token logging: its input usage is unknown; its configured 1,700-token output cap bounds its output component at $0.0085. The exact all-attempt invoice total is therefore unavailable. [Cost ledger](docs/scanner-validation/round2/cost-log.json).
- Pricing uses $1/M input and $5/M output tokens for Haiku 4.5 ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)); estimates are not a provider invoice. Browser extraction and all standalone proof/capability rechecks used no LLM.
- Initial complete 12-store headed cohort wall time: **1073.7s** (17.9 minutes). All local headed capture attempts span **2026-11-19 22:00:15 CET–2026-11-19 22:57:42 CET** (57.5 minutes), including diagnostics, retries and overlapping processes. Implementation, manual review and report preparation are additional.
- Final regression run: **171 passed, 1 skipped, 38 subtests passed**. Existing TestQuery collection and datetime deprecation warnings remain. Checks cover grounded generation, relevance versus counts, constraints, proof export gates (including a mocked database payload), false zero/recommendation handling, capture uniqueness, catalog filtering, model/brand/unit/diacritic wiring and existing audit extraction/discovery.

```bash
cd src
PYTHONPATH="$PWD:$PWD/audit" scanner/.venv/bin/python -m pytest scanner \
  audit/tests/test_fetcher_flow.py audit/tests/test_fetcher_extraction.py \
  audit/tests/test_fetcher_status.py audit/tests/test_discovery.py -q
```

Re-run the cohort from the worktree root:

```bash
python3 scripts/validate-scanner-round2.py \
  --stores docs/scanner-validation/stores-round2.csv \
  --output "$PWD/scanner_output/round2-new" --workers 3 \
  --env-file /path/to/authorized/src/audit/.env
```

## Recommended next fixes

1. Hydrate a small product-detail sample for explicit size availability, selected variant/color, materials, compatibility and SKU/MPN. Current title/price evidence cannot establish hidden variant attributes; unknowns must remain unknown.
2. Improve JS search-entry discovery for Kytary/Supersklep and readiness handling for Doorout/Dedoles; keep those technical failures separate from search failures. Reuse parsed DOM evidence to reduce extraction runtime.
3. Stabilize per-store market/session state and dismiss late marketing overlays before proof capture. Re-run paired controls when live inventory or prices change; distinguish product totals, categories, articles and sample lower bounds everywhere.
4. Expand catalog/category coverage before selecting models and linguistic pairs. Validate morphology, synonyms and problem-language against explicit catalog descriptions; do not promote a Haiku suggestion to catalog truth. Add real-traffic prioritization before treating unusual reformulations as important opportunities.
5. Repeat the fixed battery on a fresh, revenue-qualified cohort before publishing benchmark prevalence. Group related typo/spacing/price cards per store; these 15 cards are not 15 independent commercial incidents and imply no conversion or revenue estimate.
