# Search Audit — product improvements (proposals, 2026-10-30)

Written after a full review of the pipeline and of 480 historical verdicts across 8 published
audits. The engineering fixes from that review are already in the code. This file is the list
of **product** changes that were not practical when the tool was built, ranked by
impact on how convincing a report is. Each one needs an operator decision, and most need a
paid evaluation run first.

What the historical data says. These numbers decide the ranking below:

- 116 of 142 CRITICAL verdicts (82%) were zero-result pages. 54 of the 122 zero-result
  evidence texts claimed that the store stocks the item, with no proof.
- About 23% of the non-zero verdicts in a 40-query hand-graded sample were over-severe. Most were
  ranking calls driven by the reranker's literal-token preference: a title that doesn't repeat
  "Damen" or "Fleece" scores low even when it is the right product.
- 68% of CRITICALs came from long-tail query types (natural language, occasion, negation,
  price). The headline rate is real, but it describes an adversarial probe set, not traffic.
- All 14 published reports show raw relevance numbers to the prospect (5–17 per page).

---

## 1. Graded relevance labels instead of reranker scores (highest impact)

Today the Voyage cross-encoder score drives the stats ("best match at #6"), the ranking verdicts
and the KPIs. It can't see price, negation, gender or synonyms ("gilet" vs "vest"), and its
scores aren't calibrated across queries or languages.

**Proposal:** one structured call per query labels every result 0–3, TREC-style
(0 off-topic · 1 related · 2 relevant · 3 exact), with a one-line reason. KPIs become
standard IR metrics computed from the labels:

- NDCG@10
- precision@5 (labels ≥ 2)
- position of the first relevant result
- share of zero-relevant first pages

The reranker stays as a cheap disagreement signal: a large gap between label and score sends
the query to review.

- Model: `claude-haiku-5-5` costs about $0.03 per 60-query audit; `claude-sonnet-5-5` about $0.60.
- Calibration set: the human overrides already recorded in JUDGE_PLAYBOOK.md, plus the 40
  hand-graded verdicts from the review. That is enough for a first agreement score.
- What it fixes: the over-severe ranking calls, the "Pass with best match at #6.4" contradiction,
  and a KPI a search director recognises (NDCG).

## 2. Proof panels from control searches

**Already wired:** every zero-result query with a `target_term` now gets a control search. When the
control also returns nothing, the query is marked `catalog_gap` and left out of the score. When it
returns products, the evidence quotes them.

**Product step:** render that proof as a side-by-side panel in the report:

> "kinderstiefel wasserdicht" → **0 results** · "Kinderstiefel" → 48 results, e.g. *Viking
> Jolly GTX*.

This is the most persuasive single artefact the tool can produce, because it is undeniable.

## 3. Screenshot evidence and a vision check

The fetcher can now save gzipped HTML and a screenshot per query (`evidence_dir`).

**Proposal:**

- (a) Show a cropped SERP thumbnail for every risk case: "what your customer sees".
- (b) Have a vision model confirm the page state for the probe query, every zero or thin result,
  and a 10% sample. It answers {no-results page shown? count header? does the extracted top 5
  match in order? sponsored tiles?}. This automates the Phase 4a manual gate and catches the
  scraped-widget failure (Cotswold: 6 different queries "returned" the same socks).
- Cost: under $0.50 per audit on `claude-sonnet-5-5`.

## 4. Search-engine fingerprinting and platform-specific fixes

**Proposal:** intercept the site's search API responses in Playwright (Algolia, Klevu,
Constructor, Bloomreach, Doofinder, Searchspring, Boost, Nosto, Shopify predictive search).
That gives:

- the real hit count and engine order, which settles "zero vs extraction failure" for good;
- the engine identity, which changes the roadmap from generic advice to recipes for that
  platform ("Algolia: add a one-way synonym `gilet → vest` in Rules", "Shopify Search &
  Discovery: synonym group").

Prospects take a recipe for their own stack far more seriously, and it shortens the sales call.

## 5. Weight the headline by demand

"40% of tested searches fail" is honest but easy to dismiss ("nobody types that"). Two cheap
fixes:

- Report **head-query health** (brand, category, product names) separately from
  **edge-case robustness** (typos, negation, natural language). Root-cause grouping is already
  in `report_stats.root_causes`.
- Weight queries by market search volume. The Ahrefs connector is already available in this
  workspace (keywords-explorer volume by country), so category terms and brands in the site's
  market get real volumes. The report then says: "the searches that fail account for roughly
  N% of category search demand in Sweden". If the prospect shares a site-search export, use
  that instead.

## 6. Peer benchmark from our own dataset

The report has a `peer_benchmark` hook. Fill it from the 25-site dataset, anonymised by vertical
and market (already approved in the positioning decisions): "You vs the median of 9 Nordic
fashion retailers". This replaces third-party citations we had to remove because they could
not be traced. The benchmark table now shows "Find Sherpas target" values; confirm those are
targets we're happy to own.

## 7. Re-test loop as a product

Run directories now freeze the query set, checkpoints, model ids, rules version and token
usage. That makes a **before/after re-audit** cheap: re-fetch the same queries and
re-judge them under the same rules. Then:

- turn "we'll re-run these 60 searches after your fix" into the report's CTA;
- offer a scheduled monthly re-audit (a cron or Managed Agents scheduled deployment) as a
  retainer that tracks NDCG and the dead-end rate over time.

## 8. Second opinion on CRITICAL verdicts only

Earlier evaluations found that cheaper judge models soften CRITICALs. The opposite approach is
cheap: keep the current judge, and send only CRITICALs and auto-capped borderline cases to
`claude-opus-5-5` ($4/$20 per MTok) for an independent verdict. If the two disagree, the
query goes to manual review; the verdict is never softened automatically. That is about 15 calls
per audit, under $1.

## 9. Model and cost refresh (needs the existing `--model` eval harness)

| Phase | Today | Candidate | Price change |
|---|---|---|---|
| Judge | claude-sonnet-4-6 ($3/$15) | claude-sonnet-5-5 ($2/$10) | −33% |
| Queries | claude-sonnet-4-6 | claude-sonnet-5-5 | −33% |
| Discovery / categories / fetcher extraction | claude-haiku-4-5 ($1/$5) | claude-haiku-5-5 ($0.10/$0.50) | −90% |

The static judge rules now sit in a cached system prompt, so most judge input tokens are
billed at the cache-read rate.

Before switching:

- Re-run the judge harness and confirm that CRITICALs are not softened. That was the reason for
  staying on Sonnet 4.6.
- Note that 5-series models ignore `temperature` (`llm_compat` already drops it), so run-to-run
  variance rises slightly.
- Use the Batch API for full-set judging (50% off) whenever judging is not done "one by one".

**Platform note:** Anthropic SDK 1.x sends API version `2026-10-21`, which rejects `temperature`
on every model. The pinned SDK 0.x is unaffected. When upgrading, make
`llm_compat.supports_temperature` return False.

## 10. Use the site's own autocomplete as a query source

Predictive-search endpoints (Shopify `/search/suggest.json`, Algolia query-suggestions indexes,
and similar) expose what real shoppers type. Seeding 10–15 of the 60 queries from them answers
"nobody types that" before the prospect can say it.

## 11. Mobile SERP pass

Most search traffic is mobile, and mobile grids show 2–4 products above the fold, not 15.
Fetching with a mobile viewport and reporting "what's in the first screen" gives a sharper,
more visual headline.

---

## Open operator decisions from this review

1. **SPECIAL_CHARACTER / SPLIT_WORD redefinition.** Proposed: test diacritic and punctuation
   normalisation ("Bachli" vs "Bächli", "t shirt" vs "t-shirt", "loreal") and compound-seam
   splits ("Wander schuhe"), not injected `*`/`#` or mid-word splits ("jack et"). The proposed
   versions are what shoppers really type, so a miss is harder to dismiss. Not implemented,
   because it reverses rules taught in the playbook.
2. **Benchmark targets.** The report shows "Find Sherpas target" values (under 10% dead ends,
   80%+ relevant in the top 3, best match at #1–2) instead of untraceable third-party numbers.
   Confirm we own these.
3. **Re-publish the 14 live reports.** They show raw relevance numbers to prospects. Re-rendering
   needs the reports regenerated through the new pipeline (structured roadmap + sanitised
   evidence), and ideally re-judged under the new rules.
4. **Strict LLM mode** (`AUDIT_STRICT_LLM=1`, the default) now stops a run when discovery or
   category selection can't reach the model, instead of silently falling back. Set it to `0` to
   allow a recorded fallback.
