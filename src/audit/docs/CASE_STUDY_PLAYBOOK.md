# Case Study Playbook — the deep, guided audit variant

> **This is an OVERLAY, not a fork.** The `synthetic-search-audit` skill and the eight
> per-phase playbooks (`DISCOVERY_`, `CATEGORIES_`, `QUERIES_`, `FETCHER_`, `SCORING_`,
> `JUDGE_`, `REPORT_`, `PUBLISH_PLAYBOOK.md`) remain the single source of truth for the
> procedure and for every phase's accumulated knowledge. **Read them exactly as normal.**
> This file records ONLY what a case-study run does *differently*.
>
> **Nothing here changes the default audit.** A prospect audit run without the case-study
> switches behaves byte-for-byte as before. If you find yourself copying phase steps into
> this file, stop — that's the fork we're avoiding (cf. project memory
> "Audit docs single source").
>
> Companion docs: `ARCHITECTURE.md` (how the code is built), `SKILL.synthetic-search-audit.md`
> (how to run it).

---

## Why this variant exists

The default audit is a **sales artifact**: run at volume, aimed at a prospect who has never
heard of us, optimised for speed-to-published-report.

A case study is a **marketing artifact**: it lands on
[`findsherpas.com/case-studies`](../../../app/(site)/case-studies), is read by people
evaluating whether we know what we're doing, and stays up indefinitely. It is written once,
read many times. That inverts the trade-offs — depth and defensibility beat throughput, and
the operator (Michal) drives it step by step rather than approving a pipeline.

---

## The four deltas

### Delta 1 — Model tier: one step up, everywhere

Every LLM call moves up one tier. Rationale: the failure modes that cost us most in a case
study are subtle judgement calls (is this *really* a search defect, or a catalog gap?) and
narrative quality — exactly where the cheaper models soften and generalise.

| Phase | Module | Default (unchanged) | Case-study |
|---|---|---|---|
| 1 Discovery — refinement pass | `src/discovery.py` | `claude-haiku-4-5-20251001` | `claude-sonnet-5` |
| 2 Categories | `src/category_selector.py` | `claude-haiku-4-5-20251001` | `claude-sonnet-5` |
| 3 Queries | `src/query_generator.py` | `claude-sonnet-4-6` | `claude-opus-5` |
| 4 Fetcher — LLM extraction | `src/fetcher.py` | `claude-haiku-4-5-20251001` | `claude-sonnet-5` |
| 6 Judge | `src/judge.py` | `claude-sonnet-4-6` | `claude-opus-5` |
| 7 Report | `src/report_generator.py` | `claude-sonnet-4-6` | `claude-opus-5` |

Phase 5 scoring is **unchanged** — Voyage `rerank-2.5`, not an LLM. Judge-KB embeddings stay
on `voyage-3.5`.

**Mechanism (implemented).** Each module reads an env var whose default is the current
production constant, e.g. `_MODEL = os.environ.get("AUDIT_MODEL_JUDGE", "claude-sonnet-4-6")`.
A run with no env vars set is bit-identical to before; a case-study run layers
`.env.casestudy` on top of `.env`. One codebase, no forked modules.

| Env var | Module |
|---|---|
| `AUDIT_MODEL_DISCOVERY` | `src/discovery.py` |
| `AUDIT_MODEL_CATEGORIES` | `src/category_selector.py` |
| `AUDIT_MODEL_QUERIES` | `src/query_generator.py` |
| `AUDIT_MODEL_FETCHER` | `src/fetcher.py` |
| `AUDIT_MODEL_JUDGE` | `src/judge.py` |
| `AUDIT_MODEL_REPORT` | `src/report_generator.py` |

**Watch-outs carried over from the per-phase playbooks:**
- `JUDGE_PLAYBOOK` records that *every* alternative judge model evaluated so far **softened
  CRITICAL calls**. Opus is a stronger model, not a harsher one — do not assume severity
  counts will hold. Compare Phase 6 output against the calibration rules in that playbook
  before accepting them.
- **Judge KB is split read/write for case-study runs** (decided; implemented). The judge
  **reads** the shared `kb/{lang}.jsonl` — the Sonnet-era anchors still help consistency, and
  reading never mutates them — but **writes** Opus-judged verdicts to `kb-casestudy/{lang}.jsonl`
  so they can't shift the calibration every future default audit sees. Two env vars in
  `judge_kb.py`: `AUDIT_KB_DIR` (read) and `AUDIT_KB_HARVEST_DIR` (write, defaults to the read
  dir). Relative values resolve against `src/audit/`, not the cwd. Unset both = the original
  single-store behaviour. To isolate reads too, set `AUDIT_KB_DIR=kb-casestudy` — then
  case-study run #1 gets no anchors at all, and the benefit compounds only from run #2.
  `scripts/kb_prune.py` operates on the **read** store, so prune the case-study store by
  setting `AUDIT_KB_DIR=kb-casestudy` for that command.
- `POOR_RANKING` calibration (project memory "Judge ranking calibration"): CRITICAL only when
  the customer's FIRST result is off-topic (top1 < 0.30). A more articulate model is better at
  *arguing* for a severity — that is not evidence the severity is right.

### Delta 2 — Guided, not gated

The default skill gates at phase boundaries. A case-study run is **operator-driven at a finer
grain**: the operator may intervene inside a phase (rewrite an individual query, re-judge one
result set, direct a specific deep dive).

The base rule still holds and is if anything stricter here: **one step, report, stop.** Never
chain. "Run it" authorises exactly the step asked for. When the operator says "judge one by
one", that means one query per turn (project memory "Audit judge one by one").

### Delta 3 — Thoroughness over throughput

- **Query set:** larger than the default ~20–30 where the catalog justifies it. Breadth of
  *capability coverage* matters more than raw count — a case study that only demonstrates
  retrieval failures is thin.
- **Phase 4a is a hard visual gate** (project memory "Audit 4a stop-and-confirm"): show
  extracted results, wait for visual approval against the live site. On a bot-protected host
  this is where the run lives or dies.
- **Verify every claim that will appear in public.** The report playbook's rule — the "you
  carry it" claim must be *verifiable* — is doubled here. A case study is published under our
  name against a named retailer; a false "they don't stock X" claim is a credibility event,
  not a report edit. Check the live site for each headline finding.
- **Screenshots:** the cover screenshot is mandatory for the report (see `REPORT_PLAYBOOK`).
  A case study additionally wants *evidence* screenshots of the specific failing searches.

### Delta 4 — A second deliverable

The default run ends at Phase 8 (published report + CRM registry). A case-study run keeps
Phase 8 **and adds** an MDX case study.

- **Location:** `content/case-studies/{slug}.mdx`
- **Rendered by:** [`app/(site)/case-studies/page.tsx`](../../../app/(site)/case-studies/page.tsx)
  (index) and the `[slug]` route
- **Frontmatter type:** `CaseStudyFrontmatter` in [`lib/content.ts`](../../../lib/content.ts)

Mapping from the audit artifacts:

| Frontmatter field | Source |
|---|---|
| `title`, `excerpt`, `seoTitle`, `seoDescription` | written, not derived |
| `date` | audit completion date, ISO |
| `client` | `site_context.site_name` |
| `industry` | derived from `site_context.site_type` + nav departments |
| `problem` | the headline retrieval finding — dead-end rate, not a ranking stat |
| `approach` | the audit method in plain language, **without** exposing automation/LLM/scraper details |
| `outcome` | what the findings imply. **Do not invent uplift numbers.** |
| `stack` | the site's detected search platform, where known |
| `reportUrl` | the published `findsherpas.com/report/{slug}/` URL |
| `tags`, `featured` | editorial |

**Public-writing constraints — these are the ones that differ from a client report:**
- The client report is unbranded and confidential-by-default (unlisted + `noindex`). A case
  study is the opposite: public, indexed, and it names the retailer. **Confirm with the
  operator that naming the retailer is intended before publishing.** An audit run without the
  retailer's involvement is legitimate to publish as observed public behaviour of a public
  website, but that is a deliberate editorial call, not a default. Because the retailer is
  named, every finding is an on-the-record claim about a company that did not commission the
  audit — hold each one to "could we show the screenshot and re-run the search live?"
- No fabricated outcomes. We measure a site's search at a point in time; unless we ran the
  fix, we do not claim an uplift. `outcome` describes the size of the problem and what fixing
  it addresses.
- Brand voice from `ARCHITECTURE.md` applies unchanged: short sentences, direct assertions,
  no hedging. Banned: leverage, synergy, optimize, robust, exciting, deep dive, fascinating,
  powerful, unique.
- Screenshots and quoted queries are the evidence. A case study without a reproducible
  example is an opinion piece.

---

## Per-case-study profiles

### decathlon.co.uk (Decathlon UK) — IN PROGRESS, Phase 0 complete

- **Published under its own name — approved by the operator (2026-08-08).** The case study
  names Decathlon. Every finding must therefore be reproducible on the live site by a reader.

- **Search URL template:** `https://www.decathlon.co.uk/search?Ntt={}` — verified live in the
  browser (`?Ntt=running%20shoes` → "7,542 results for 'running shoes'", real products
  returned: `ASICS Men's running shoe, Asics Gel-Windhawk`, `DECATHLON MEN'S JOGFLOW 100.1
  RUNNING SHOES`). The `?q=` variant does not work.
- **BOT-BLOCKED — flagged for Phase 4a.** Plain `curl` with a desktop UA returns **403** on
  both `?Ntt=` and `?q=`. The static fetcher will fail. Expect to need Playwright mode. No
  Decathlon profile exists in `FETCHER_PLAYBOOK.md` yet — write one there (not here) once the
  4a gate passes.
- **Language:** English. **Locale:** UK.
- **Expected site_type:** `PHYSICAL_GOODS` or `MARKETPLACE_MIXED` — huge multi-sport catalog
  (own labels Kalenji/Quechua/Domyos/Tribord etc. plus third-party ASICS, Nike, Garmin…).
  Watch for the experiential-nav-bias misclassification documented in `DISCOVERY_PLAYBOOK`
  general learnings — Decathlon's nav carries "Sports", club/experience content.
- **Scale caveat:** 7,542 results for a two-word query. This is a very large catalog; a
  "zero results" finding here is far more damning than on a boutique, and a "buried at #N"
  finding far less so. Calibrate severity accordingly.

---

### douglas.de (Douglas) — IN PROGRESS, Phase 1 complete

- **Published under its own name — approved by the operator (2026-09-14).** The case study
  names Douglas. Every finding must therefore be reproducible on the live site by a reader.
- **Selected over Decathlon UK** for the big-name case study (operator call, 2026-09-14). The
  decathlon.co.uk profile below remains at Phase 0 and is not being progressed.
- **Search URL template:** `https://www.douglas.de/de/search?q={}` — verified live.
- **Bot-blocked to static fetch** (HTTP 400 WAF signature on every URL incl. homepage);
  Playwright mode required throughout. Full detail in `DISCOVERY_PLAYBOOK` / to be written
  into `FETCHER_PLAYBOOK` once the 4a gate passes.
- **Language:** German. Judge reads `kb/german.jsonl`, harvests to `kb-casestudy/german.jsonl`.
- **Scale caveat:** 677 results for a head term like `mascara`, 10,000 in Gesichtspflege alone.
  On a catalog this size a zero-result finding is damning; a "buried at #40" finding is weak.
  Calibrate severity accordingly (same reasoning as the Decathlon scale caveat).
- **SPONSORED-RESULTS STANCE (operator-approved, 2026-09-14).** Douglas interleaves paid
  placements (`Gesponsert`) into organic results — observed at ranks 6–7 on `mascara`. Rule:
  score sponsored results as-found, but **never call paid placement a relevance defect on its
  own**. Flag it only where sponsored slots push genuinely relevant organic results off the
  first screen. Rationale: paid placement is a commercial decision, not a search-quality
  defect, and a public case study that conflates the two is attackable. This is a
  case-study-specific editorial stance — do not apply it silently to default prospect audits.

---

## How to run one

```bash
cd "/Users/michalpekarcik/Cursor/FInd Sherpas/find-sherpas/src/audit"
set -a; source .env; source .env.casestudy; set +a
```

Then follow the `synthetic-search-audit` skill exactly as written, phase by phase, applying
the deltas above. Use `.venv312/bin/python` — the system python3.9 ships LibreSSL and fails
TLS on modern sites (project memory "Audit python venv TLS").

`.env.casestudy` is layered **on top of** `.env`, never instead of it. Sanity-check that the
overrides took before Phase 1:

```bash
.venv312/bin/python -c "import sys; sys.path.insert(0,'.'); from src import judge, judge_kb; print(judge._MODEL, judge_kb.kb_harvest_path('English'))"
```

Expect `claude-opus-5 …/kb-casestudy/english.jsonl`. A shell without the overrides prints
`claude-sonnet-4-6 …/kb/english.jsonl` — that's the default audit, and it must stay that way.

---

## Decisions taken

| Decision | Resolution | Date |
|---|---|---|
| Model override mechanism | Env-var-with-default per module. Smallest change that leaves the default path bit-identical; no forked modules. | 2026-08-08 |
| Judge KB isolation | Split read/write. Read shared `kb/`, harvest to `kb-casestudy/`. | 2026-08-08 |
| Naming the retailer publicly | **Yes** — Decathlon is named in the published case study. | 2026-08-08 |
| Case-study target switched to Douglas | Douglas chosen over Decathlon for the big-name case study. Decathlon profile stays at Phase 0. | 2026-09-14 |
| Naming Douglas publicly | **Yes** — Douglas is named in the published case study. | 2026-09-14 |
| Sponsored results | Score as-found; paid placement is not a relevance defect on its own. Flag only when it displaces relevant organic off screen one. | 2026-09-14 |

---

## When you learn something new

Append a **per-case-study profile** here for facts specific to this variant (editorial calls,
model behaviour differences, publishing decisions).

**Everything else goes in the per-phase playbook it belongs to.** A fetcher trap learned on
Decathlon is a `FETCHER_PLAYBOOK` entry, not a case-study entry — the default audit needs it
too. Only write here what would be *wrong* to apply to a default run.
