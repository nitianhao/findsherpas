# ColourPop evaluation handoff

**Status:** selected as the first US Shopify research evaluation. No evaluation step has been run yet. Continue in a new session.

## Target

- Store: ColourPop, US beauty retailer.
- Starting search-results URL: <https://colourpop.com/search?q=lipstick>
- Why selected: a broad beauty catalog with shades, finishes, formulas, named collections, and variants. This should produce useful tests of exact product discovery, synonyms, constraints, and full-page ranking.
- Shopify evidence: [Shopify's ColourPop article](https://www.shopify.com/blog/214945353-seed-beauty-kylie-cosmetics). The site's search page also returned HTTP 200 and Shopify storefront assets in the lightweight shortlist check on 2026-10-19. Recheck current behavior during discovery; do not infer which search engine powers the visible results.

## Scope for this run

Use the [eight-step research evaluation workflow](README.md) under `shopify-plugin/evaluation/`. Stop after step 8, **Judge**. Do not generate a narrative/client report, publish a page, or update the CRM.

The workflow is gated: read the corresponding copied playbook, run one step, show the saved checkpoint and relevant findings to the owner, accept corrections, and proceed only when the owner approves that step. At the first-fetch gate, compare extracted products and order with the live ColourPop search page before the full fetch.

Write checkpoints to `shopify-plugin/evaluation/runs/<run-id>/`. The runner reads the **copied** calibration files and writes auto-harvested examples to that run's `proposed_calibration/`; do not merge those suggestions into the baseline without expert review. Record generalizable corrections in the **copied** playbooks at `shopify-plugin/evaluation/knowledge/playbooks/`.

## First action in the new session

From `/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/shopify-plugin`:

```bash
../src/audit/.venv312/bin/python evaluation/run.py start 'https://colourpop.com/search?q=lipstick' --id colourpop-us-01
```

Then inspect `evaluation/runs/colourpop-us-01/01_preflight.json` with the owner. Once approved, read `evaluation/knowledge/playbooks/DISCOVERY_PLAYBOOK.md` and run:

```bash
../src/audit/.venv312/bin/python evaluation/run.py discover colourpop-us-01
```

If `colourpop-us-01` already exists when the new session begins, use `evaluation/run.py status colourpop-us-01` and resume from its next incomplete step. Do not overwrite saved checkpoints.

## Prompt to use in the new session

> Continue the first US Shopify research evaluation for ColourPop. Read `shopify-plugin/evaluation/COLOURPOP_HANDOFF.md` and `shopify-plugin/evaluation/README.md`. Use the copied playbooks and the eight-step gated runner. Start with the pre-flight step if no run exists, show each checkpoint for my expert review, and stop after step 8 judgments. Do not create or publish a report.
