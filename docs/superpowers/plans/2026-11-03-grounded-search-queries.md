# Grounded Danish Search Queries Implementation Plan

**Goal:** Generate reviewable Danish query/control suites from the nine accepted Imerco candidate modes, without running searches.

**Spec:** `docs/experiments/search-detective-imerco-2026-11-03/README.md`, query construction milestone.

**Architecture:** Read immutable accepted candidates, revalidate their source facts, let the LLM select an eligible anchor and draft Danish wording, and derive executable requirements in code. Independently review wording against facts and preserve accepted/rejected drafts, prompts, costs, and hashes. Conditional-price positives reverse roles: an unconditional under-budget product is eligible; the member-only offer is a contrast for a nonmember.

**Files:** Extend `src/audit/src/candidates/runner.py` to permit a stage-specific system prompt; add `src/audit/src/candidates/query_cases.py`, `src/audit/tests/test_candidate_queries.py`, and experiment outputs/documentation.

**Constraints:** Existing Python/API infrastructure; no dependencies; no search execution, publishing, or store changes; no arbitrary revenue claims; missing anchor alone is not failure; refresh time-sensitive facts before execution. Budget at most 12 calls / $2 for this stage; use exact checkpoint cache on resume.

**Review focus:** Rejected candidates cannot seed tests; unit conversions preserve magnitude and dimensions preserve axes; pack size differs from per-item capacity; nonmember price context must not use member-only positives; no invented conditions or anchor-only pass rules.

- [x] Add failing tests for source rejection, price roles, requirements and conversions, malformed/extra drafts, review rejection, cache behavior, and unsupported numeric query values.
- [x] Implement stage-specific model prompts without changing existing candidate behavior.
- [x] Implement brief compilation, draft validation, grounded success rules, independent wording review, and checkpoint CLI.
- [x] Run focused tests, real LLM generation/review on the accepted run, and an actual cached resume.
- [x] Run the appropriate offline suite and preserve portable results, including rejected drafts and limitations.

**Decisions:** One selected anchor per mode; two queries per suite except specificity (three). Unit conversion controls use the source unit, tests use an equivalent unit. Nonmember budget is strictly below 500 DKK as already agreed. Evidence refresh is required at later execution, not simulated by this drafting stage.

Execution: nine suites / 19 query-control entries accepted after independent wording review; four real API requests, estimated $0.122982. Cached resume made zero new API requests. No searches executed.
