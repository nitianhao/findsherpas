# Research evaluation workflow

This is a **separate copy of the audit knowledge** for the future Shopify app. It supports the first eight steps of the main project's evaluation workflow and stops after query judgments. It does not generate a client report, publish a page, or update the CRM.

For the first US candidate stores, see the [Shopify store shortlist](US_SHOPIFY_SHORTLIST.md).
The first selected evaluation has its own [ColourPop handoff](COLOURPOP_HANDOFF.md) for a new session.

The research workflow is deliberately gated: run one command, review its output, correct the checkpoint if needed, then run the next command. These human checks help build the benchmark; the eventual merchant app must operate without them.

## What is copied and what is reused

- `knowledge/playbooks/`: exact snapshots of the six operational playbooks used in steps 2–8.
- `knowledge/calibration/`: independent copies of the current German and Swedish JSONL prompt examples.
- `knowledge/archive/raw/`: eight complete raw audit JSON files.
- `knowledge/archive/html/`: all 14 published audit HTML pages, including the six without local raw JSON.
- `knowledge/MANIFEST.json`: original paths and SHA-256 checksums for the 30 copied files.

The runner reuses the main project's Python evaluator under `../../src/audit/src/` and its local Python environment. Source code and credentials are **not** copied. Changes to either knowledge copy do not change the main project's playbooks or calibration files. The archived reports are research evidence, not verified gold labels. See [knowledge notes](knowledge/README.md).

## Setup

Run from `find-sherpas/shopify-plugin/` on the Mac:

```bash
PYTHON=../src/audit/.venv312/bin/python
$PYTHON evaluation/run.py --help
```

The existing audit environment needs its normal site-access and API credentials. The runner loads `../src/audit/.env` if present. Discovery, query generation, fetching, scoring, and judging may make network or paid model calls; `start` and `status` do not. If the audit virtual environment is missing, recreate it from `../src/audit/requirements.txt` and install Playwright support when a site requires browser rendering.

## Steps

Use a **real search-results URL** with a visible query parameter. Replace `<run-id>` in later commands with the ID printed by step 1. Read the copied playbook named below **before** that step. Stop after each step for expert review and amend its JSON checkpoint before continuing when necessary.

| Step | Command | Review and copied knowledge |
| --- | --- | --- |
| 1. Pre-flight | `$PYTHON evaluation/run.py start 'https://store.example/search?q=boots'` | Confirm it is a real search page and the query/template are correct. No network request. |
| 2. Discovery | `$PYTHON evaluation/run.py discover <run-id>` | Read `DISCOVERY_PLAYBOOK.md`; check site type, search URL, language, categories, brands, and featured items. |
| 3. Categories | `$PYTHON evaluation/run.py categories <run-id>` | Read `CATEGORIES_PLAYBOOK.md`; add or remove inappropriate test categories. |
| 4. Queries | `$PYTHON evaluation/run.py queries <run-id>` | Read `QUERIES_PLAYBOOK.md`; remove invented products and weak or misclassified tests, then replace them as needed. |
| 5. First-fetch check | `$PYTHON evaluation/run.py probe <run-id>` | Read `FETCHER_PLAYBOOK.md`; compare one extracted result list with the live site, including product titles, links, count, order, and fetch mode. Fix extraction before proceeding. |
| 6. Fetch and clean | `$PYTHON evaluation/run.py fetch <run-id>` | Read `FETCHER_PLAYBOOK.md` and `SCORING_PLAYBOOK.md`; inspect zero results, junk, non-product pages, and remaining extraction errors. Raw and cleaned checkpoints are saved separately. |
| 7. Score | `$PYTHON evaluation/run.py score <run-id>` | Read `SCORING_PLAYBOOK.md`; review low scores and cases where wording or invisible attributes could make scores misleading. Re-fetch or correct only affected queries where necessary. |
| 8. Judge | `$PYTHON evaluation/run.py judge <run-id>` | Read `JUDGE_PLAYBOOK.md`; inspect all critical findings, catalog-gap claims, and ambiguous constraints. Correct wrong verdicts and preserve the rationale. **Stop here.** |

Run status at any point with `$PYTHON evaluation/run.py status <run-id>`. Checkpoints are stored under `evaluation/runs/<run-id>/`. The runner refuses to overwrite an existing checkpoint, protecting expert edits and paid results. Edit the relevant JSON checkpoint when making a correction; append a generalizable lesson or site profile to the **copied** playbook in `evaluation/knowledge/playbooks/`. Do not automatically edit the main project's playbooks.

The judge reads the copied calibration files. The current Python judge also auto-harvests candidate examples; this runner redirects those into the run's `proposed_calibration/` folder. They are **unverified suggestions**. Review them before deliberately adding any to `knowledge/calibration/`.

## End state

An evaluation is complete here when `08_judgments.json` has been reviewed and the run retains its input, intermediate evidence, and corrections. There are **no steps 9 or 10** in this workflow: no narrative report and no publication. Do not call the main project's `orchestrator.py` for this research workflow, because it continues into report generation and publishing.

The research checkpoints can later be imported into a verified benchmark. Do not treat an unreviewed AI verdict or an HTML-only summary as ground truth.
