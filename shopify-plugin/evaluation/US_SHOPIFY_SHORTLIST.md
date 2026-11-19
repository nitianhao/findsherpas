# First five US Shopify stores to evaluate

**First selected store:** ColourPop. See the [new-session handoff](COLOURPOP_HANDOFF.md). The evaluation has not started.

Shortlist checked 2026-10-19. These are **candidates**, not completed evaluations or claims that their search is poor. None appears in the 14 completed audit reports copied here. Each sample search URL returned HTTP 200 with a search page during a lightweight check. The active search engine, visible result order, catalog evidence, and extraction quality still need verification in steps 2 and 5 of the [research workflow](README.md).

The selection prioritizes different product and query problems over brand fame. Shopify has documented each brand's use of its platform; that does not prove its current search widget uses Shopify's native search.

| Priority | Store and sample search URL | Why it adds useful evaluation cases | Shopify evidence |
| --- | --- | --- | --- |
| 1 | [ColourPop — “lipstick”](https://colourpop.com/search?q=lipstick) | Beauty: shades, finishes, formulas, named collections, and product-versus-variant matching. Large result sets test ranking and constraint handling. | [Shopify on ColourPop](https://www.shopify.com/blog/214945353-seed-beauty-kylie-cosmetics); [ColourPop's Southern California history](https://colourpop.com/pages/about-us) |
| 2 | [Chubbies — “shorts”](https://www.chubbiesshorts.com/search?q=shorts) | Apparel: inseam, fit, activity, color, prints, and men's versus women's queries. Useful for checking whether one correct top result hides a poor full page. | [Shopify case study](https://www.shopify.com/case-studies/chubbies) |
| 3 | [Blueland — “refill”](https://www.blueland.com/search?q=refill) | Household products: refill versus starter kit, product compatibility, scent, bundle size, and problem-led searches. Tests whether practical intent is understood. | [Shopify case study](https://www.shopify.com/case-studies/blueland); [Blueland company site](https://www.blueland.com/pages/about-us) |
| 4 | [Kizik — “shoes”](https://kizik.com/search?q=shoes) | Footwear: size, width, gender, age, model names, and “hands-free” functional intent. Gives us a focused catalog with many variants. | [Shopify case study](https://www.shopify.com/case-studies/kizik); [Kizik on its Utah origin](https://kizik.com/en-cv/blogs/news/kizik-opens-flagship-retail-store-in-home-state-of-utah) |
| 5 | [Brooklinen — “sheets”](https://www.brooklinen.com/search?q=sheets) | Home textiles: bed size, fabric, warmth, bundles, and material synonyms. Worth including for a different purchase vocabulary; its result page may require browser rendering during extraction. | [Shopify case study](https://www.shopify.com/case-studies/brooklinen); [Brooklinen on its Brooklyn origin](https://www.brooklinen.com/pages/about) |

## Order and evaluation notes

Start with ColourPop because its public search page exposes many product links and a broad query space. Chubbies and Blueland give very different intent and attribute patterns. Kizik adds size and model constraints. Brooklinen is valuable for material and size language but may take extra work at the first-fetch gate: its server response showed a result count but few product links without browser rendering.

At step 5, confirm that extracted results match the live shopper experience. A successful HTTP response alone is insufficient. Record whether each site uses native Shopify search or a third-party engine before making any platform-specific conclusions. If a store blocks reliable observation or no longer uses Shopify, substitute another candidate rather than forcing an invalid audit.

Bombas was considered but its sample search returned an automated security checkpoint (HTTP 429) during this check, making it a weaker first-wave candidate despite Shopify's [case study](https://www.shopify.com/case-studies/bombas).
