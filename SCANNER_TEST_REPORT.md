# Scanner test report — 2026-11-19

Completed on macOS with Python 3.12 and headed Playwright Chromium. All three stores were reachable; no genuine bot-protection block remained after fixing false CAPTCHA detection. No InstantDB writes, emails or git pushes were performed. No sibling working files were modified; the authorized dotenv file was read. Creating the requested local commit also required Git to update this worktree’s shared metadata under the sibling `.git/worktrees/` directory.

## Fixes

- Corrected `ProbeResult` package exports; made `Scanner` a lazy export so module execution does not preload itself.
- Added `scanner.cli` with single and CSV batch modes, `--headed`/`--headless`, optional `--env-file`, and the root launcher `./scripts/scan-search`. Updated README setup and commands. Existing `python -m scanner.scanner` delegates to the same CLI.
- Replaced a call to nonexistent `fetch_search_results` and the unsafe generic fallback with headed browser capture and the audit fetcher's existing page analyzer. HTML, screenshots, HTTP status, redirects and search API evidence now come from the same visit. Queries and positive controls are cached within a scan; each domain has its own output directory.
- Discovered real search forms, followed Allbirds' JavaScript search link, excluded utility navigation such as B2B, preserved explicit zero totals, and distinguished unverified empties/errors from confirmed zeros.
- Updated Cotswold's changed product tile, title, price and readiness selectors while preserving old markup. Added Allbirds catalog-title and visible-total extraction. Fixed newsletter reCAPTCHA scripts misclassifying real results or explicit zeros as bot blocks. Used Bergzeit's catalog name/brand fields instead of sale badges and size text.
- Corrected Anthropic SDK argument compatibility and Haiku 4.5 cost accounting; retained whole product names, removed invented SKU fallbacks and arbitrary compound splits, and used locale-aware plural generation.
- Prevented extraction errors and missing positive controls from becoming search passes/failures. Constraint narrowing is only partial evidence: fewer hits do not prove color or price compliance.

## Verification and reproduction

```bash
cd src
PYTHONPATH="$PWD:$PWD/audit" scanner/.venv/bin/python -m pytest scanner \
  audit/tests/test_fetcher_flow.py audit/tests/test_fetcher_extraction.py \
  audit/tests/test_fetcher_status.py audit/tests/test_discovery.py -q
```

Validation: **142 passed, 1 skipped, 38 subtests passed**. The existing audit `TestQuery` class produces a harmless collection warning. New scanner regressions cover imports through collection, error aggregation, incomplete/unknown zeros, positive controls, same-visit evidence and caching, current storefront markup, false CAPTCHA detection, API compatibility/cost, and conservative constraint scoring.

From the worktree root:

```bash
./scripts/scan-search https://www.cotswoldoutdoor.com --country GB --vertical outdoor --headed
./scripts/scan-search --batch /path/to/stores.csv --output-dir ../scanner_output --headed \
  --env-file "$HOME/Cursor/FInd Sherpas/find-sherpas/src/audit/.env"
```

CSV columns: `domain,vertical,country`. Output paths are relative to `src/`. Only the optional query-generation calls use an LLM; browser discovery and result extraction are deterministic. APIs and credentials are never printed by the scanner.

## Final results

Scores below were recomputed from saved observations with the final scorer, including the conservative constraint rule. No queries or counts were changed during rescoring. Versioned JSON preserves every scored probe. Runtime includes discovery and browser visits; costs are token-based estimates for the selected validation runs, not a provider invoice.

| Store | Country / vertical | Overall | LLM cost (USD) | Runtime |
|---|---|---|---:|---:|
| [cotswoldoutdoor.com](docs/scanner-validation/2026-11-19/cotswoldoutdoor.json) | GB / outdoor | partial | $0.000842 | 134.2 s |
| [bergzeit.de](docs/scanner-validation/2026-11-19/bergzeit.json) | DE / outdoor | partial | $0.001646 | 132.0 s |
| [allbirds.com](docs/scanner-validation/2026-11-19/allbirds.json) | US / footwear | partial | $0.001226 | 160.5 s |

Selected-run total: **$0.003714**, **426.7 seconds** of store runtime. Haiku 4.5 uses $1/M input and $5/M output tokens ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)). All ten completed diagnostic/validation scan files together recorded **$0.010538** in estimated LLM cost; duplicate batch summaries are excluded. Browser-only screenshot rechecks cost $0 in LLM calls. Earlier runs retain their own results in local `scanner_output/` JSON.

| Capability | Cotswold Outdoor | Bergzeit | Allbirds (Shopify) |
|---|---|---|---|
| basic_retrieval | pass (3/3 passed) | pass (3/3 passed) | pass (3/3 passed) |
| typo_tolerance | pass (1/1 passed) | pass (1/1 passed) | pass (1/1 passed) |
| language_understanding | pass (2/2 passed) | pass (1/1 passed) | pass (2/2 passed) |
| locale_handling | pass (1/1 passed) | pass (1/1 passed) | Not tested |
| compound_handling | partial (1/2 passed, 1 partial) | pass (2/2 passed) | pass (2/2 passed) |
| constraint_handling | partial (0/1 passed, 1 partial) | partial (0/1 passed, 1 partial) | partial (0/1 passed, 1 partial) |
| brand_model_search | Not tested | Not tested | Not tested |
| coverage_ranking | Not tested | Not tested | Not tested |
| zero_result_handling | pass (1/1 passed) | pass (1/1 passed) | pass (1/1 passed) |

## Cotswold Outdoor

Search template: `https://www.cotswoldoutdoor.com/lister.html?q={}`. Confirmed gibberish query `xyzqwk12345nonsense` → **0**; positive control `Jackets` → **1036**. [Positive screenshot](docs/scanner-validation/2026-11-19/cotswoldoutdoor-positive.png) · [Zero-result screenshot](docs/scanner-validation/2026-11-19/cotswoldoutdoor-zero.png).

| Example proof card | Query → count | Control → count | Result |
|---|---|---|---|
| typo | `Jacekts` → 1036 | `Jackets` → 1036 | pass |
| synonym | `waterproof jacket` → 328 | `rain jacket` → 328 | pass |
| diacritics | `Fjallraven` → 214 | `Fjällräven` → 214 | pass |

Raw scan: `scanner_output/final/www.cotswoldoutdoor.com/cotswoldoutdoor_com_2026-11-19.json`.

## Bergzeit

Search template: `https://www.bergzeit.de/search/?q={}`. Confirmed gibberish query `xyzqwk12345nonsense` → **0**; positive control `Bekleidung` → **21945**. The later screenshot recheck shows **21944**, consistent with the small live-inventory variation observed during these runs. [Positive screenshot](docs/scanner-validation/2026-11-19/bergzeit-positive.png) · [Zero-result screenshot](docs/scanner-validation/2026-11-19/bergzeit-zero.png).

| Example proof card | Query → count | Control → count | Result |
|---|---|---|---|
| typo | `Beklediung` → 22019 | `Bekleidung` → 21945 | pass |
| synonym | `Kapuzenpullover` → 569 | `Hoodie` → 571 | pass |
| diacritics | `Gruezi Bag Damen Senseful DownWool Jacke` → 3 | `Grüezi Bag Damen Senseful DownWool Jacke` → 3 | pass |

Raw scan: `scanner_output/bergzeit-clean/www.bergzeit.de/bergzeit_de_2026-11-19.json`.

## Allbirds

Search template: `https://www.allbirds.com/search?q={}`. Confirmed gibberish query `xyzqwk12345nonsense` → **0**; positive control `Men's Shoes` → **71**. [Positive screenshot](docs/scanner-validation/2026-11-19/allbirds-positive.png) · [Zero-result screenshot](docs/scanner-validation/2026-11-19/allbirds-zero.png).

| Example proof card | Query → count | Control → count | Result |
|---|---|---|---|
| typo | `Men'sS hoes` → 73 | `Men's Shoes` → 71 | pass |
| synonym | `trainers` → 67 | `sneakers` → 67 | pass |
| plural_singular | `Men's Shoe` → 71 | `Men's Shoes` → 71 | pass |

Raw scan: `scanner_output/final/www.allbirds.com/allbirds_com_2026-11-19.json`.

## Screenshot checks and known problems

- Visually checked Cotswold's product listing/count and explicit no-products destination, Bergzeit's category total and no-results text, and Allbirds' 71-result heading and explicit no-results page. Allbirds' country modal initially obscured cards; its close button is now dismissed and the two supplemental screenshots above verify the fix. Bergzeit's late cookie banner is now declined before capture; its two screenshots are supplemental verifications of that fix. Allbirds identifies Shopify in its storefront cookie disclosure and uses Shopify product routes and CDN assets.
- A supplemental Cotswold scan found `WindproofJackets` → **0** versus `Windproof Jackets` → **507**; the screenshot confirms a real no-results page. See local `scanner_output/verified/www.cotswoldoutdoor.com/merged_words_WindproofJackets.png`. The earlier exact query `Rab Mens Microlight Alpine Jacket` reported five hits but rendered four distinct cards: it was conservatively marked inconclusive. The final run's Patagonia product query produced five extracted products for five reported hits.
- Scores measure a small probe battery, not overall search quality. Count ratios do not establish relevance or equality of result sets. LLM synonyms and compound pairs need human review; `raincoat` versus `rain jacket` is not guaranteed to have identical coverage. Constraint probes do not validate product colors or all prices and therefore cannot earn a pass from narrowing alone.
- Capabilities shown as **Not tested** are not passes. The current scanner does not execute every enum-defined capability: dedicated coverage/ranking, abbreviation, format-variant and standalone brand probes are not wired into this battery; SKU runs only when a code is observed. Diacritics are omitted when no relevant pair is available.
- Site inventories and personalization vary between visits. Bergzeit's Bekleidung total fluctuated between 21,938 and 21,945 during validation; each saved count corresponds to its own captured page. No unverified empty extraction is treated as a real zero.
- Browser rendering uses bounded waits rather than comprehensive retries; future markup changes may produce explicit extraction errors. The scanner reuses private audit extraction helpers, so audit API changes require regression testing. Unknown sites without an explicit total can still use the extracted sample size as a fallback; do not interpret such counts as catalog totals without screenshot verification.
- Full HTML/browser artifacts and diagnostic logs stay local in ignored `scanner_output/`; the six reviewed screenshots and three complete final JSON records are committed beside this report. The Next.js benchmark/teardown/CRM flows and database worker were not exercised, as this task authorized local scanner validation only.
