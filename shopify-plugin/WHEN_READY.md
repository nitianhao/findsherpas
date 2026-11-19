# Shopify app build handoff

## Status and trigger

As of 2026-10-19, the owner plans to add more search audits before building the Shopify app. The project is paused at planning. Start implementation when the owner says they are ready; do not assume a calendar date or a required number of additional audits.

## Product decision already made

Build a self-serve Shopify app for nontechnical store owners. After installation and any optional third-party connector setup, it must run without the owner's involvement: understand the catalog, test the search experience shoppers actually use, verify evidence, present plain-language findings with practical next steps, and rerun on schedule. The free tier must provide complete useful examples. Paid plans can add breadth, history, monitoring, and guided fixes. Use deterministic, catalog-backed checks first and tightly budget any AI calls. No routine merchant report may wait for expert review.

The [research and product plan](RESEARCH_AND_PRODUCT_PLAN.md) is the detailed product brief. Recheck current Shopify APIs, app requirements, billing, and provider integration terms when implementation starts.

## Evidence at pause

- `public/report/` has 14 completed published audit pages. Their titles claim 854 tested queries in total.
- `src/audit/reports/` has full raw JSON for eight of those audits, containing 480 query judgments. The other six published audits currently have HTML only: Lyko, Miinto, Nordic Nest, Sportamore, The Reformation, and Woodie's.
- `src/audit/kb/` has 119 calibration examples in German and Swedish JSONL files. These guide the current AI judge; they are not a human-verified benchmark or a deterministic rules database.
- Douglas and Zalando have partial local checkpoints and are not counted as completed audits.
- The audit pipeline and its calibration playbooks live under `src/audit/`. The `shopify-plugin/` TypeScript code is only a placeholder; no Shopify app, billing, connector, or evaluation engine has been built here yet.
- An eight-step **research evaluation runner** and a dated copy of the audit knowledge now live under `shopify-plugin/evaluation/`. It reuses the main Python evaluator and stops at reviewed judgments. This is a research tool, not the automated merchant app.

These numbers are a dated snapshot. Inventory again on resumption; do not carry the counts forward as current facts.

## While adding audits

For each audit, retain its raw `*_data.json`, report, store/domain, audit date, language, search provider or storefront search surface, and notes about any expert-corrected judgments. Keep evidence that a supposedly missing product was actually available, especially for zero-result and constraint cases. Raw query/result data is more useful for a future benchmark than a polished report alone.

The existing `src/audit/reports/` directory is a runtime artifact location and is ignored by Git. Before relying on new audit data for the app, verify that the raw files are preserved in a durable location. Do not assume a public HTML report preserves all the result and catalog evidence needed for machine evaluation.

Store diversity matters more than hitting an arbitrary count: product categories, catalog sizes, languages, native Shopify versus third-party search, and difficult cases where the existing judge has made mistakes. Expert corrections should be kept separately from automatic judgments so they can become verified benchmark cases.

## First work when the owner says “ready”

1. Inventory all completed audits and raw artifacts again, including the new ones. Identify Shopify stores and which search surface each actually uses.
2. Recover what is possible from HTML-only reports, then create a provisional common dataset without labeling unreviewed AI judgments as truth.
3. Select and verify a representative gold set with the owner. Reserve whole stores as holdouts for later accuracy checks.
4. Define the first narrow, catalog-backed deterministic checks and the evidence required for each merchant-facing claim.
5. Build the Shopify app's automatic native-search path and a merchant-friendly free report. Test it with nontechnical store owners before expanding to paid depth or third-party connectors.
6. Measure accuracy, merchant comprehension, cost per scan, and unattended operation. Expand the research program and product only where the evidence supports it.

Do not begin by copying the current prompt-example knowledge base into production. It is useful research material, but its entries were not all independently verified.
