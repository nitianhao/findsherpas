# Search improvement ideas

Brainstorm recorded 2026-11-03. This document preserves context across agents and harnesses. These are research directions, not an approved implementation plan.

## Objective

Evolve search evaluation into an optimization system that proves why shoppers fail, identifies the smallest useful fix, and verifies that it works. Aim for expert-quality findings that can eventually become a product.

Leave the Shopify plugin out of scope for now.

## Existing foundations

- Established evaluator: `src/audit/`, with operating instructions in `src/audit/docs/SKILL.synthetic-search-audit.md` and engineering reference in `src/audit/docs/ARCHITECTURE.md`. Discovery → categories → queries → fetch → score → judge → report, with manual checkpoints or an automated orchestrator.
- Agentic shopper prototype: `src/audit/src/shopper_agent.py`; results in `src/audit/reports/_shopper_prototype/`. A browser agent pursues shopping goals; a separate judge evaluates the session. Currently separate from the established pipeline.
- Earlier proposals: `docs/audit-improvement-ideas.md` covers result purity, constraint compliance, attribute drift, diversity, specificity ladders, and top-result trust. `src/audit/docs/IMPROVEMENT_PROPOSALS.md` covers evaluator improvements and the initial shopper experiments.

The workflows complement one another: systematic probes expose failures; a shopper investigates the experience.

Important existing observation: shopper ability changes the verdict. In the prototype's boots task, one model failed while another found a suitable product. Separate agent limitations from site failures, and do not let a highly capable agent's persistence hide a poor customer experience.

## 1. Investigate backwards from failures

Automate the investigation an expert performs after a bad result: try synonyms, remove constraints, inspect categories, locate actual products, and identify which part broke.

Example:

“Waterproof walking boots under £120” fails → “walking boots” works → a qualifying product exists → adding “waterproof” loses it → inspect product attributes and the search response.

Produce an evidence-backed diagnosis: missing attribute, vocabulary mismatch, retrieval failure, ranking problem, or interface friction. Distinguish confirmed causes from hypotheses. Public storefront access may support only a hypothesis; catalog and configuration access can confirm more.

Experiment: investigate ten existing failures. Measure how many yield a confirmed cause and an actionable fix.

## 2. Establish suitable products independently of search

Judging returned products does not reveal good products that were never retrieved. Build a small verified answer set using category pages, product details, and eventually a catalog feed.

This can expose:

- Suitable products that are effectively invisible through search.
- Missing sizes or variants hidden behind superficially relevant results.
- Apparently successful searches that omit the strongest options.
- Genuine assortment gaps versus search failures.

Without a sufficiently complete catalog, report “known suitable products missed” rather than claim complete recall. Verify decisive attributes and availability; do not infer them from title similarity alone.

This is a foundational dependency for trustworthy evaluation and diagnosis.

## 3. Test relationships between queries

Extend specificity ladders into controlled tests of expected relationships:

- Adding a budget should preserve known qualifying products.
- A harmless typo should preserve the intended product.
- Changing “waterproof” to “not waterproof” should change the answer.
- A synonym should preserve intent; a different product type should not.

The model proposes meaningful variations; verified products and explicit rules check outcomes. Avoid assuming that rankings or result counts must behave monotonically when only product eligibility is guaranteed.

Experiment: five verified shopping needs, each with eight controlled variations. Identify the exact change that breaks retrieval or constraint handling.

## 4. Measure shopper effort, not just eventual success

A powerful agent can rescue a poor site through persistence. Eventual success alone should not make the site pass.

Evaluate under explicit effort budgets: one search, one reformulation, a limited number of product inspections. Record unnecessary actions and whether the shopper can verify the decisive requirement.

Example finding: “The product is findable, but only after three reformulations and opening six products.”

Treat these as synthetic usability measurements until validated against real shoppers. Confirm failures with repeat runs and inspect whether agent or interface behavior caused them. Browser agents alone are not a differentiator; evidence quality and diagnosis matter.

## 5. Test proposed fixes and their side effects

For a diagnosed failure, propose a specific intervention: attribute enrichment, synonym, variant grouping, or ranking change. Replay affected tasks and a regression set.

Expert value lies in side effects: a synonym can rescue one query while making another too broad. Distinguish exact products, substitutes, and complementary accessories rather than treating all semantic similarity as relevance.

Candidate fixes can be tested in a local sandbox. Proving production impact requires access to the actual engine and eventually live experiments. Keep simulated improvements separate from demonstrated site improvements.

## Recommended first experiment: search detective

Choose one store and establish ten verified shopping needs.

1. Run the established evaluator and the shopper workflow.
2. Investigate disagreements and failures.
3. Produce three findings, each containing:
   - A reproducible failure.
   - Proof that a suitable product exists.
   - A supported diagnosis, with uncertainty stated.
   - A proposed fix and regression cases.
4. Ask an experienced search practitioner to assess whether each finding is correct and worth fixing.

Primary success criterion: accepted, actionable findings, not the number of failures generated.

Revenue prioritization should follow actual site-search demand and behavioral data when available. Synthetic test frequency or external keyword volume is not a substitute for internal search traffic or proof of revenue impact.

The potential product is the complete loop: discover → prove → diagnose → propose → verify → monitor regressions.

## Research references

- WebMall: shopping-agent evaluation includes vague needs, compatibility, and multi-shop journeys. https://wbsg-uni-mannheim.github.io/WebMall/
- Amazon ESCI: distinguishes exact matches, substitutes, complements, and irrelevant products. https://www.amazon.science/code-and-datasets/shopping-queries-dataset-a-large-scale-esci-benchmark-for-improving-product-search

These sources provide context; the experiments and product directions above are proposals for this project, not established results.

## Open context for the next session

No experiment has been selected or run as part of this brainstorm. No product code was changed.

A useful next discussion: identify a real manual consulting investigation where expert reasoning uncovered something a normal audit missed. Use it to sharpen the first experiment and its acceptance criteria.

## Failure-mode library follow-up (2026-11-03)

The user accepted 30 initial failure modes and requested broader coverage, with only borderline cases shown in chat for review. See [Search failure-mode library](search-failure-modes.md) for accepted modes, additional candidates, reliability rules, and review status. No search logs are expected; use store-grounded tests plus exploratory shopper investigations.

## Imerco experiment handoff

See [the experiment record and proposed LLM workflow](experiments/search-detective-imerco-2026-11-03/README.md) for the complete session record, ten difficult candidate mappings, portable evidence, feasibility assessment, checkpoint contracts, and proposed validation. Product discovery is complete for this exploratory run; autonomous LLM discovery and the ten search tests have not been run.

## Current experiment status — 2026-11-04

The historical open-context notes above are superseded. Candidate discovery, grounded query generation, search execution, evaluation, and the unit investigation have now run for Imerco; see the linked experiment record. Following the user's feedback about commercial relevance, we also completed a [30-query ordinary-shopping experiment](experiments/ordinary-search-imerco-2026-11-04/results.md).

It found one recurring online-stock ordering opportunity across two categories, plus localized variant concentration and phrase coverage. It did not establish three widespread conversion failures or measure revenue impact. The reusable LLM workflow and its evaluator limitations are documented with the saved evidence.

## Expanded stock experiment — 2026-11-05

Completed the [fifty-query availability-ranking study and local simulation](experiments/stock-ranking-imerco-2026-11-05/results.md). The frozen cohort had no confirmed unavailable first-product cases; separate repeats showed yesterday's glass ordering had changed while the broad vase case persisted. The conservative rule changed nine lower result orders, adding two available exact products to top-three exposure, and preserved all ten named-product orders. This supports a limited merchandising experiment, not a broad conversion-uplift claim. Persistent findings across time should be required before promoting snapshot anomalies into client priorities.
