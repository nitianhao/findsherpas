# Search Candidate Pilot Implementation Plan

> **For agentic workers:** Execute the approved bounded candidate-builder milestone in this session. Use the experiment record as the source of truth; no query generation, scoring, reporting, or publication.

**Goal:** Create and exercise an LLM-driven, evidence-grounded candidate builder for the ten Imerco failure modes.

**Architecture:** A Python CLI uses checkpointed, budgeted structured model calls for category planning, product selection, fact extraction, mode matching, and independent evidence review. Offline replay consumes captured product text; fresh discovery consumes only observed category/product links and saves source evidence. Deterministic validation rejects bad references and unsupported quotations, verifies numeric normalization, and reports incomplete coverage.

**Tech Stack:** Existing Python 3.12 audit environment, Pydantic, requests, BeautifulSoup, existing Anthropic client adapter. No dependencies added.

**Spec:** `docs/experiments/search-detective-imerco-2026-11-03/README.md`

## Global Constraints

- Products first, queries second; this milestone stops before query generation.
- No search-based product discovery, no Shopify plugin work, no writes to the store.
- Seven category pages, 40 detail pages, 30 counted API requests maximum; batches up to five products.
- Preserve sources, exact quotations, unknowns, offer eligibility, separate dimensions and pack capacity.
- Configurable model and conservative currency budget; save checkpoints and never silently overwrite a run.

## Review Focus

- Hallucinated product IDs or quotes must be rejected and cannot cover a mode.
- A present quote can still be misinterpreted; independent reviewer and abstention remain necessary.
- Budget exhaustion/failure must leave saved evidence and uncovered-mode reasons.
- Resume must invalidate incompatible inputs or code/prompts and avoid duplicated paid calls.
- Category-only discovery and replay are different evaluations; do not report replay as autonomous discovery.

### Task 1: Evidence contracts and validation

Files: `src/audit/src/candidates/contracts.py`, `src/audit/src/candidates/validation.py`, `src/audit/tests/test_candidates.py`.

- [x] Write failing tests for quote/reference rejection, units, axes, pack quantity, conditional pricing, and review rejection.
- [x] Implement schemas, ten mode requirements, deterministic grounding and candidate checks.
- [x] Run focused tests and confirm failures are rejected without turning unknowns into negatives.

### Task 2: Budgeted LLM workflow and checkpoint CLI

Files: `src/audit/src/candidates/runner.py`, `src/audit/src/candidates/__main__.py`, `src/audit/src/candidates/collection.py`.

- [x] Add tests for request/currency caps, failed calls, cached resume/input changes, and observed-link restrictions.
- [x] Implement bounded independent category/product collection and fact/review stages, using `structured_call()` and zero SDK retries for explicit request accounting.
- [x] Implement replay/live CLI, saved call requests/responses, source hashes, prompt/model metadata, coverage report, and usage accounting.
- [x] Run all focused tests and a real saved-evidence LLM replay. Run fresh discovery if replay and available budget permit; record limitations rather than force coverage.

### Task 3: Verify and record the experiment

Files: experiment `README.md`, portable run summaries/evidence.

- [x] Run appropriate offline tests and inspect actual model-generated facts and candidate decisions.
- [x] Record commands, model, observed coverage, cost estimates/rates, corrections, and unresolved limitations.
- [x] Keep unrelated work untouched; do not commit or push unless requested.

## Execution record

Implemented directly in the current workspace, preserving unrelated changes. All 18 focused tests and 299 audit tests pass. Three curated replay iterations and two autonomous live collections were recorded; final re-evaluation of 35 autonomously selected products accepted nine modes. The same final command resumed without new API requests. See the experiment implementation-results document for costs, rejected claims, and the remaining either/or representation issue. No query generation, search tests, publication, commit, or push occurred.
