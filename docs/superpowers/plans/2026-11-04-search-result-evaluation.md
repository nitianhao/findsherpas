# Search result evaluation plan

Evaluate the saved November 3 Imerco searches on November 4. Preserve result ordering; fetch current product details with identity checks. Use an API model to extract only needed product facts with exact quotations, then independently audit those facts. Compare accepted normalized facts to query requirements in code. Unknown facts remain unknown.

Files: add `src/audit/src/candidates/evaluate_results.py`, tests for decisive violations, unknowns, material composition, numeric equivalents, baseline attribution, and price eligibility. Reuse existing collection, budgets, fact grounding, and cache infrastructure.

- [x] Collect and preserve product sources for all 103 unique returned products (117 result entries).
- [x] Extract and independently audit facts in bounded API batches; numeric comparisons and aggregation are deterministic.
- [x] Use the execution-time anchor evidence for repeated empty searches. Accept alternatives; never require a specific anchor to appear.
- [x] Report per-result constraints, per-step findability, result contamination, and per-suite baseline/test findings.
- [x] Verify critical failures, run meaningful tests, save portable evidence and a concise report.

Budgets: at most 50 model requests / $5 for evaluation. No query reruns, publishing, configuration changes, or revenue estimates. Product-detail verification time differs from saved query execution time and must remain explicit.

Completed: 103 product detail pages; 178 grounded facts, 177 independently accepted; four failures, three passes, one mixed case, one baseline-inconclusive case. 35 API requests (~$0.965), cached resume made no new requests; 322 offline tests passed. No queries rerun or reports published.
