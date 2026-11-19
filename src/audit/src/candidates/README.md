# Experimental search candidate builder

Run from `src/audit/` with the existing `.venv312` environment and `.env`. The pilot uses the existing Anthropic adapter; no new dependencies. It does not generate queries or execute search tests.

## Saved evidence replay

```sh
.venv312/bin/python -m src.candidates \
  --replay ../../docs/experiments/search-detective-imerco-2026-11-03/evidence/products.json \
  --out reports/imerco_dk/candidate_replay_new \
  --max-usd 3
```

This makes real LLM API calls but no storefront requests. It evaluates extraction and matching on supplied products, not autonomous discovery.

## Fresh category-first discovery

```sh
.venv312/bin/python -m src.candidates \
  --live --out reports/imerco_dk/candidate_live_new --max-usd 3
```

The Imerco adapter discovers actual homepage navigation, lets the model choose up to seven categories, lets it select up to five product links per category, and fetches details. No fixed product IDs and no use of the store's search. Static HTML only in this pilot; empty/unsupported layouts are logged rather than treated as empty catalogs. At most 35 selected detail pages (below the design's 40-page ceiling).

Both paths extract facts in batches of five, ground exact quotes and numeric values, propose mode mappings, validate required facts, and independently review the proposals against source text. One bounded re-extraction pass may repair non-contiguous or absent quotations; rejected evidence is retained, and repaired claims must pass all checks again. Independent review is a separate call to the same model, not independent human verification. `verified_candidate` means accepted by the pilot's checks; it is not ground truth or a site failure verdict. A candidate product demonstrates a satisfiable need, not the only acceptable search result.

## Budgets and checkpoints

Default model: `claude-sonnet-4-6`; override with `--model` or `AUDIT_MODEL_CANDIDATES`. Other models require explicit `--input-rate` and `--output-rate` (USD per million tokens). Default Sonnet 4.6 rates are 3 input / 15 output, checked 2026-11-03 against https://platform.claude.com/docs/en/models/sonnet-4-6/overview . Usage includes cache writes/reads. Estimates are not billing records.

- Maximum 30 API requests; SDK retries disabled. Failed or ambiguous requests retain a conservative maximum cost reservation.
- Maximum input 65 KB per model call and 6,500 output tokens (selection calls: 1,200). Preflight cost reservation includes input bytes, schema/framing allowance, output ceiling, and cache-write pricing. This is a conservative planning estimate rather than an API-enforced billing cap.
- A separate-call review must accept all required evidence. Critical no-coating claims additionally require an explicit negative statement; PFAS-free does not qualify. Danish kr/DKK price units normalize to DKK in this Imerco-only pilot. The review schema asks for the reason before the approval boolean.
- Every model request/response, exact prompt, model, source, rejected fact, proposal, review, usage, and coverage outcome is saved. No secrets are included in checkpoints.
- Reuse the identical command with `--resume` to reuse completed calls. Code/model/budget/input changes require a new output folder. Edited product checkpoints are rejected. Failed/pending calls require inspection and a new run rather than automatic rebilling.
- Existing output folders are not silently reused. Treat checkpoints as immutable; reviewed corrections belong in a new input/run.
- Reports retain uncovered modes, collection errors, and rejected claims. Missing or unknown evidence never becomes proof of a search defect.

## Outputs

`manifest.json`, `products.json`, `facts.json`, `proposals.json`, `report.json`, and `calls/*.json`. Live mode also writes `sources/*`, observed navigation, category link pools, collected products, and collection errors. Report/source trees are gitignored; copy reviewed summaries and evidence to the experiment documentation for portable handoffs.

`report.json` gives per-mode status, reasons, accepted candidates, fact evidence, and cost estimates. A completed run can legitimately have incomplete mode coverage. `incomplete` means a budget or execution failure; accepted stages remain saved. Process exit code is nonzero for an incomplete pipeline, not merely for an uncovered mode.

## Verification

```sh
.venv312/bin/python -m unittest tests.test_candidates -v
.venv312/bin/python -m unittest discover -s tests -t .
```

See `docs/experiments/search-detective-imerco-2026-11-03/README.md` at the repository root for the experiment design, evidence requirements, historical manual baseline, and recorded live results. Cross-store adapters, active coverage top-ups, automated conflict resolution, and search execution remain later work. A separate query-generation stage is described below.

## Grounded Danish query stage

Accepted candidates can now feed a separate drafting stage:

```sh
.venv312/bin/python -m src.candidates.query_cases \
  --input reports/imerco_dk/accepted_candidate_run \
  --out reports/imerco_dk/query_suites_new
```

The stage revalidates source facts, compiles requirements, generates Danish queries with controls, and independently reviews wording. It executes no searches. It uses a stage-specific system prompt with the same budget/cache infrastructure (12 calls / $2), and supports unchanged-command `--resume`. See the experiment's `query-generation-results.md` for recorded outputs and intended execution rules.

## Result evaluation stage

Use `python -m src.candidates.evaluation_sources --execution <saved-execution-dir> --out <evaluation-dir>` to collect identity-checked detail pages, then `python -m src.candidates.evaluate_results --experiment <experiment-dir> --out <evaluation-dir>` to extract/audit facts and compute requirement matches. Saved query order is preserved; no searches are rerun. See the experiment `evaluation-results.md` for exact commands, evidence, tested limits, and how mixed/unknown results are handled.

## Controlled volume investigation

`python -m src.candidates.unit_investigation --experiment <experiment-dir> --out <new-dir>` runs representation/token controls from the verified volume case, preserves query-bound public hit metadata, repeats key queries, and tests local normalized-capacity filtering. `--analyze-only` reuses saved captures without requests. This pilot handles one explicit exact volume and abstains on ranges/inequalities; it changes no store settings. See the experiment `unit-investigation-results.md`.

## Ordinary shopping cohort

`python -m src.candidates.ordinary_search --out <experiment-dir> --stage plan|search|contexts|evaluate` uses independently collected category inventory to draft and review 30 ordinary searches before capture. `search` refuses existing observations; `evaluate` reuses identical cached calls. The module currently targets Imerco and five fixed categories. Collection, product verification, and repeat-search scripts plus exact commands are saved under `docs/experiments/ordinary-search-imerco-2026-11-04/` at the repository root. See `results.md` there for findings, reproducibility, and remaining automation limitations, including hidden goals and incomplete/disputed labels. No demand or conversion impact is inferred from the synthetic cohort.

## Expanded stock-ranking experiment

`python -m src.candidates.stock_experiment --out <new-dir> --stage collect|plan|search|evaluate|simulate|verify` runs a fifty-query Imerco cohort across ten independently observed categories. The stages freeze the reviewed query plan, capture ten hits per query, review relevance, simulate stable availability preference within trusted exact-result blocks, and verify changed top-one product pages plus repeat candidate queries. Named-product orders are pinned; weaker/unknown relevance and unknown stock are barriers. Simulation consumes judged relevance and is not an independent production relevance test. Model calls are bounded by disjoint batch quotas (70 requests / $8 aggregate maximum). See the repository experiment record `docs/experiments/stock-ranking-imerco-2026-11-05/README.md` for exact commands and scope.
