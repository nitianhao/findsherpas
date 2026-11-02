# Fetcher Playbook — site learnings & silent-failure patterns

> **Read this BEFORE running any fetch (Phase 4a).** It records what works and what
> doesn't per site and in general, so we don't re-debug the same fetcher failures
> each audit. When you solve a new fetcher problem, add an entry here.
>
> Companion docs: `ARCHITECTURE.md` (how the pipeline is built) and the
> `synthetic-search-audit` skill (how to run it). This file is operational memory
> for the **fetch** phase specifically.

---

## How to use this file

1. Before Phase 4a, check whether the target host has a **Per-site profile** below.
   If it does, you already know the fetch mode, the correct results container, and
   the known traps — apply them and skip the trial-and-error.
2. If the host is new, run the **General silent-failure checklist** during the 4a
   gate, and once it passes, **write a new per-site profile** capturing: fetch mode,
   the real results-grid selector, what the wrong containers were, price quirks, and
   ordering behaviour.
3. Site-specific extractors live in `src/fetcher.py` → `_try_site_specific()` and
   short-circuit ahead of the generic strategy sweep (`_extract_results`, the
   site-specific block runs first and wins when it returns results).

---

## Fetch outcomes — every query gets a status (2026-10)

An empty result list used to mean five different things (blocked, timed out, crashed,
redirected, genuinely zero) and downstream every one of them scored as an automatic
CRITICAL "your search returns nothing". `fetch_all_outcomes(queries, template,
max_results=15, evidence_dir=None, on_outcome=None)` now returns
`{query: FetchOutcome}`; `fetch_all_results` is a thin legacy wrapper (`{q: results}`)
for the old runner scripts. **Read the status, never the list length.**

| Status | Meaning | Trusted for scoring? |
|---|---|---|
| `ok` | Results extracted from the search page. | yes |
| `partial` | Page reports N hits, we read fewer than min(N, k). Usually page size (12 tiles shown of 384), sometimes a render lapse. | yes |
| `redirect` | Search left the results page: one product (PDP) → 1 result; category/brand landing → that page's grid. | yes |
| `zero_confirmed` | The page itself says "no results" (or a known no-results path / the search API says 0). `results=[]`, `total_hits=0`. | yes |
| `zero_unverified` | Nothing extracted and no no-results message. Render lapse, unknown layout, stale SSR, silent bot wall. | **no** |
| `blocked` | Bot wall / WAF / rate limit (Akamai, DataDome, PerimeterX, Cloudflare, Imperva, AWS WAF, captcha, Shopify `/challenge`, HTTP 400/401/403/405/429/5xx on a near-empty page, a <5 KB body with no product links). | **no** |
| `timeout` | Fetch or readiness wait exceeded its limit and nothing usable was read. | **no** |
| `error` | Transport failure / exception / nothing loaded. | **no** |

Untrusted outcomes are excluded from scoring (`excluded_reason='fetch_unverified'`)
and listed in the report's "Not scored" appendix. `attempts` = fetches made (0 = never
fetched because the site probe failed or the site kept blocking). `evidence` is a short
reason, plus `[evidence: <path>.html.gz, <path>.png]` when `evidence_dir` was given
(gzipped HTML for every attempt; with Playwright also a viewport screenshot taken
after scrolling back to the top; filenames are a slug of the query + a short hash).

**How a page is read (`_analyse_page`, in this order):**
1. Known no-results destination path (cotswold `/lister/no-results`) → `zero_confirmed`.
2. Block signatures, WAF status codes, tiny product-less body → `blocked`. Classified on
   every path: static responses, every browser in the Playwright loop (signature-only
   there, because a SPA shell is tiny for the first seconds), and the final capture.
   The Playwright `goto` status is recorded; a 403 whose rendered page shows ≥3 product
   links is NOT a block (headed-challenge hosts).
3. Redirected (token comparison, below) onto a product page → `redirect`, 1 result.
4. `page_state()` finds a no-results marker → `zero_confirmed`, `[]`, **even if a carousel
   was extracted** (phantoms). All extraction is skipped, cached selectors included.
5. Extract (dedicated extractor, else cached selectors → generic sweep → grounded LLM).
6. Nothing extracted and no marker → `zero_unverified` (or `timeout` if the readiness
   wait timed out). There is no longer any "authoritative empty list" — a dedicated
   extractor returning `[]` is a zero only when the page also shows its marker.

**`page_state(html, url, visible_text, query)` — generic, every host:**
- Marker = multilingual no-results regex over `<title>` + visible text outside
  header/nav/footer/autocomplete/minicart overlays and outside `hidden` /
  `display:none` nodes (Playwright passes the browser's own `innerText`, which also
  honours CSS). EN/DE/SV/NO/DA/NL/FR/IT/ES/PT/PL/CS/FI: "no results", "we couldn't find
  any", "keine Treffer", "keine Ergebnisse", "inga träffar", "ingen resultater",
  "geen resultaten", "aucun résultat", "nessun risultato", "brak wyników",
  "žádné výsledky", "ei tuloksia", "Suchergebnis für »x« (0)", …
- **Zero counts are word-bounded: `\b0\s+results\b`.** "10 results" / "100 Treffer"
  never read as zero (the old `/0 results/` waits did). End-of-list messages
  ("Keine weiteren Ergebnisse", "No more results") are not markers.
- Hit count (`total_hits`) from the title, h1–h3 and count/result/total elements:
  `384 results`, `1.234 Artikel`, `Products (12)`. "Strong" words (results, Treffer,
  Ergebnisse, träffar, resultater, …) count anywhere; "weak" ones (items, Artikel,
  products) only in the title/h1/count elements — product names contain them. The
  query text is blanked first ("pack of 6 items" ≠ 6 hits). A strong count smaller
  than the tiles read trims the padding ("3 results" + 12 tiles → 3).
- Marker **and** an applied spelling correction ("Showing results for …", "Wir zeigen
  dir Ergebnisse für …", "stattdessen") with tiles → `ok`, results kept, evidence says
  so. Marker **and** a positive strong hit count without that → `zero_unverified`
  (ambiguous; verify by hand). A "Did you mean …?" suggestion alone does not undo a zero.
- Host profiles (`_HOST_PROFILES`) add markers, a hit-count regex, a PDP path rule and
  the readiness selectors. `douglas.de` disables the generic markers entirely (stale SSR
  "0 Ergebnisse" headings) and confirms a zero only by the title.

**Redirects (`_redirect_kind`)** compare the query's word tokens after `parse_qs` +
`unquote` + casefold (and ’ → ') against the destination's parameters (or path, when
the template puts the query in the path). `+` vs `%20`, `Arc'teryx` vs `Arc%27teryx`
and percent-encoded umlauts compare equal; the old `quote_plus` substring test did not.
`away` = query gone (PDP, brand page); `landing` = query kept as a parameter on a
non-search path (cotswold `?q=…&sred=1`, bergzeit `?bzsearch=…`, lyko `?fromsearch=…`).
Both are extracted on the destination on **every** host. A page is a PDP only on
positive evidence: `og:type=product`, a `product:price:amount` meta, exactly one
top-level JSON-LD Product with no ItemList, or the host's PDP path rule — a brand page's
`<h1>` never becomes a fake single result.

**Retries (`_fetch_with_retries`):** zero_unverified / timeout / error / thin (<3
results without a hit count that explains it) are re-fetched up to 3 attempts with
2 s / 5 s backoff on every host. A `zero_confirmed` is re-checked once (manufactum.de and
bergzeit.de flip between a no-hits page and real results for one URL). The best attempt
wins and `attempts` records the count. `blocked` is never retried (polling a WAF
escalates it, see douglas.de), and 3 blocked queries in a row stop the run — the rest
are marked `blocked` with `attempts=0`. Per-attempt cap 300 s, probe cap 600 s.
**Deferred:** a timed-out Playwright fetch keeps running in its daemon thread until the
process exits (threads cannot be killed). A subprocess-per-fetch model would fix it; not
done because it changes every Playwright call path.

**Readiness waits** are one table-driven `_wait_for_host_ready` returning
`grid | no_results | timeout` (no longer fail-open). A timeout with an empty capture
becomes `timeout`, never a zero.

**Ranking fidelity:** results stay in DOM order everywhere (the old `_card_score` sort in
`_try_product_cards` moved price-less real results below priced chrome). Repeated card
groups with the same signature under sibling parents are merged in DOM order (a grid
split around editorial blocks starts at its real rank 1, not at rank 25). Groups and
strategies are scored by mean quality × min(n, k), carousels/recommendation containers
(class or preceding heading: "Recommended for you", "Das könnte dir auch gefallen", "Du
kanske också gillar", …) are discounted, and among near-equal candidates the one
nearest the top of `<main>` wins — a 15-tile carousel no longer beats a 4-tile grid.

**Junk filter:** only unscoped strategies (generic sweep, LLM) use it. Dedicated
extractors and JSON-LD never do (short real names: "Talon 6", "Topf"). Cookie-banner
junk is matched by URL (`javascript:`, cookie/consent/privacy links) or exact banner
phrases, never by the word "cookie" in a title (cookie cutters are products). Dutch
"voor"/"binnen" title prefixes are no longer junk.

**Prices:** struck-through (`<del>/<s>/<strike>`, `line-through`), old/was/RRP/UVP/
compare/unit/per/instalment nodes are skipped; sale/current/final nodes are preferred;
`itemprop=price` first. The currency must sit against its amount — the symbol-after
form refuses a symbol followed by digits, so "(7) £240.00" is £240.00, not "7 £".

**JSON-LD:** ItemLists are walked once and sorted by `ListItem.position`; a Product's
children (`hasVariant`, `isRelatedTo`, `offers.itemOffered`, …) are never collected;
odd `@type`s (lists, IRIs, `schema:Product`), dict/list names and non-dict offers no
longer crash or duplicate.

**Sponsored tiles:** labels "Sponsored / Anzeige / Gesponsert / Sponsrad / Annonse /
Annonce / Werbung / Ad", `data-sponsored`, `*-sponsored` classes →
`SearchResult.sponsored=True`. The tile is kept at its rank (customers see it) and the
label is stripped from the title. "sponsored" is no longer a chrome class.

**LLM fallback (Haiku, `phase="fetcher"`, structured outputs via `llm_compat`):** the
query is no longer sent to the extraction or validation prompts (knowing it invited the
model to drop off-topic items, which makes a bad search look good). Every LLM item is
grounded: its normalised title must appear in the page's visible text and its URL in
the HTML, or it is dropped. The LLM container is chosen by product-link density (the
old "first div matching items?|grid" picked Tailwind `items-center` in the header).

**Search-engine API capture:** Playwright records responses from Algolia
(`*/1/indexes/*/queries`, `nbHits`), Klevu (ksearchnet), Constructor (cnstrc),
Bloomreach (dxpapi), Doofinder, Searchspring, Boost (mybcapps) and Nosto. The entry whose
own query equals ours supplies `total_hits` when the page shows none, confirms an empty
page as `zero_confirmed` when it reports 0 hits, and notes a top-hit mismatch in
`evidence`. Autocomplete/recommendation calls carry other queries and are ignored.

**Checkpointing:** `scripts/chunked_fetch.py` writes the checkpoint after every query
(tmp file + `os.replace`), stores the full outcome (`status`, `results`, …), probes once
per run, and on resume re-fetches everything not `ok`/`zero_confirmed` — including
legacy list-only entries. `MAX_RESULTS=15`. Usage:
`.venv312/bin/python scripts/chunked_fetch.py [phase1.json phase3.json out.json] [--evidence DIR]`.

**Drift fixed in this file (2026-10):** "dedicated extractor `[]` is authoritative" →
now only with a marker; "retries once on zero for dedicated hosts" → every host, up to
3; "drive `_fetch_with_mode` in a loop to checkpoint" → `fetch_all_outcomes(on_outcome=…)`
/ `chunked_fetch.py`; bergzeit "category-redirect TODO" and "no-hits title TODO" → done;
cotswold "PDP guard counts tiles" → it was a path rule, now the host profile's
`pdp_path`; manufactum "title = name span alone" → code prepends the manufacturer when
the name does not already start with it (BRAND_SEARCH needs it).

---

## General silent-failure patterns (apply to every site)

These are the ways the fetcher confidently returns junk. The 4a gate exists to catch them.

| Pattern | Symptom | Fix |
|---|---|---|
| **Wrong container — recommendations/cart** | Coherent set of products that are all off-topic vs the query (e.g. all beauty for a kids query). They come from a "You might also like" / mini-cart / cross-sell carousel, not the search grid. | Scope extraction to the real search-results container by id/class; exclude drawer/carousel containers. Add a site-specific extractor. |
| **Phantom results on a no-results page** | A query that returns "no hits" on the live site comes back with several results in the fetch — they're the no-results page's recommendation carousel ("Du kanske också gillar" / "Våra avdelningar"). Masks a real search failure (the most damaging audit error — a critical finding shown as a pass). | (1) Never fall through to cached/generic/LLM strategies on a dedicated host (`_DEDICATED_EXTRACTOR_HOSTS`), and let `page_state()` see the no-results marker first: marker → `zero_confirmed` with `[]` even when a carousel is present; no marker → `zero_unverified`, never an "authoritative" empty list. (2) Add a readiness wait so the real grid OR the no-hits marker is present before capture, else a slow render looks like zero AND triggers the junk fallback. |
| **JS-rendered site, static fetch returns 0/garbage** | Static probe returns 0 results or only chrome; site clearly has results in a browser. | Force Playwright. Confirm `playwright` + `playwright install chromium` are installed in `.venv312`. |
| **Nav/footer/cookie scraped as results** | Titles like "Logga in", "Visa fler", cookie text; URLs are `#` or policy links. | Junk filter + scope to results container. Verify titles look like products. |
| **Result order differs from the user's browser** | Fetched top-N order doesn't match what the user sees, even though each is internally consistent. | Verify empirically before blaming the site. Order can be deterministic-and-stable yet still differ from the user because of (a) the live catalog/ranking shifting over time, or (b) geo/IP-based ranking or stock-availability filters between the fetch host's egress IP and the user's. Do NOT assume "non-deterministic / personalized" without proof — sample the order over time in one session AND across headless/headed/real-UA configs first. (ahlens.se: tested identical across all four browser configs — see profile.) |
| **Locale price formats** | Prices truncated or missing — e.g. Swedish "1 000 kr" (non-breaking-space thousands separator) parsed as "000 kr". | Normalize `\xa0`/spaces before the price regex; parse price from the card's price line directly. |
| **Stale model id** | `404 not_found_error: model: claude-...` from `query_generator` / `judge` / `report_generator`. | These modules hardcode `_MODEL`. Keep them on the current Sonnet id (`claude-sonnet-4-6`). See also project memory "Audit LLM transport migration". |
| **Transient false zero on a client-rendered (dedicated-extractor) host** | A query that has real results returns 0 in the full batch run, while the same query returns results when re-fetched alone. The client-side grid (e.g. Boost) didn't finish rendering before capture during sequential Playwright runs (resource contention), and the readiness wait lapsed. On authoritative-empty hosts this silently scores as a search failure. | Every host now **retries zero_unverified / timeout / thin results up to 3× with backoff**, and re-checks a confirmed zero once (see "Fetch outcomes" above). Still: when reviewing Phase 4, spot-check any zero on a *known-present* item (esp. exact-match `featured_items`) before judging — a known product returning 0 is a false-zero suspect. (Avoca: the Shea Verbena soap exact-match returned a false 0 in the first full run; real answer is 10 with the exact product at rank 1.) |

**Always verify the 4a gate against a live browser load**, not just the fetcher's own
output. The fetcher can return a self-consistent set of wrong products.

**4a is a STOP-AND-CONFIRM gate (hard rule). Exact procedure, every time:**
1. Fetch **ONE example query's** result set — not the full fetch list. (One representative
   query is enough to validate the extractor.)
2. Once you have that result set, **open the browser yourself and visually confirm the
   first 3–4 results match the live site** (titles/prices/order). Do this before involving
   the user.
3. **Only then** present the results to the user for their confirmation.
4. **If the first attempt failed** (wrong/zero/garbage) and you then fixed it: even after
   the corrected run looks right, **automatically run ONE more query to double-check** —
   without being asked — before declaring 4a passed.

Do NOT chain into the full multi-query fetch until the user approves. The probe exists
precisely so both you (via browser) and the user eyeball the extraction before a full run.

**After the full fetch completes, always display every query that returned fewer than
15 results** (i.e. `< max_results`), grouped/listed with their counts, so the user can
manually review them. These thin/zero results are where false zeros and genuine search
failures both hide — surface the full list for human review before judging, not just
the zeros.

**ALWAYS save partial results incrementally — write the checkpoint after EVERY query,
not once at the end of the batch (hard rule).** The full fetch is long (esp. headed /
Cloudflare hosts at ~20–30s/query × ~60 queries), and a mid-list failure or an
externally-killed process must not throw away the work already done. Do NOT call
`fetch_all_results(...)` and only `json.dump` the whole dict at the end — if it dies at
query 45 you lose all 44. Use `fetch_all_outcomes(..., on_outcome=save)` (the callback
fires after every query) or `scripts/chunked_fetch.py`, which does exactly this with an
atomic write. Make the runner
**resumable**: load the existing checkpoint at startup and skip queries already present,
so a restart picks up where it left off instead of refetching. (For per-host fetch mode,
hosts like Huckberry force their mode internally so a fixed `SiteMode.PLAYWRIGHT_CHROMIUM`
in the loop is fine; otherwise probe once, then loop with the proven mode.)

---

## Per-site profiles

### douglas.de (Douglas — German beauty & lifestyle retailer)

**Fetch mode: NONE of the Python modes work. Transport is the in-app browser.**

- **What the Python fetcher now reports (2026-10):** the Akamai `Access Denied` page is
  classified `blocked` (`errors.edgesuite.net` / `Reference #`), and a page with no
  `.product-tile` is `zero_unverified` — never an empty "zero". Only
  `document.title == "Keine Ergebnisse gefunden | DOUGLAS"` makes a `zero_confirmed`
  (host profile; the generic "0 Ergebnisse" marker is disabled here because the SSR
  heading is a stale placeholder). Sponsored tiles ("Gesponsert") are flagged
  `sponsored=True`, kept at their rank.

- Akamai Bot Manager fronts the site. Every Python transport returns a 300-byte
  `Access Denied` page (`errors.edgesuite.net`, `Reference #18...`): plain
  `requests`/`curl` (which returns HTTP **400 "Request Too Long"** — a WAF
  signature, not a real header problem), headless Playwright Firefox/Chromium,
  **headed** Chromium, Playwright with `channel="chrome"`, and UA/locale spoofing.
  Adding `douglas.de` to `_HEADED_CHROMIUM_HOSTS` does NOT fix it.
- **What works:** same-origin `fetch()` executed inside a real browser session
  (the in-app browser), i.e. `fetch('/de/search?q=...', {credentials:'include'})`
  from a page already on `douglas.de`. Returns HTTP 200, ~2.3 MB of
  **server-rendered** HTML containing the full results grid — no client render
  needed, so `DOMParser` + the selectors below extract directly.

**RATE LIMIT — a ~45-REQUEST CEILING, NOT A PACING PROBLEM (confirmed twice).**
Two independent sessions were cut off at ~45 requests: the first at 700 ms spacing,
the second through a real Chrome profile at ~2-4 s spacing with a mix of navigations
and same-origin fetches. Slowing down did NOT raise the ceiling. Treat it as a
per-session/per-fingerprint request quota that resets after a cooldown.
- **Cooldown is long:** the first block outlasted 4, 9 and 10-minute checks and only
  cleared somewhere between 10 and 25 minutes.
- **Do NOT poll while blocked.** Repeated probes during the first block escalated the
  penalty — afterwards it re-triggered after a single request, whereas a clean
  ~25-minute wait restored full behaviour. Wait untouched, then probe ONCE.
- **Plan for it:** a 77-query audit takes at least two sessions with a ~25 min gap.
  Persist after every batch (see below) so a block costs nothing.

**TRANSPORT — Akamai blocks headless automation but not a real Chrome profile.**
Escalate in this order:
1. `fetch()` from the in-app browser on a douglas.de page — worked for ~45 queries,
   then returned 403 for the rest of the session even after the block lifted.
2. **Claude-in-Chrome (the user's real Chrome profile) — the reliable transport.**
   It sailed through when the in-app browser was still 403'd, which proves the block
   is **session/fingerprint-based, not IP-based** (both share one egress IP).
   Top-level `navigate` works; same-origin `fetch()` from a loaded douglas.de page
   also works and is cheaper (no page render).
   - The Chrome extension **blocks scripts that touch `sessionStorage`/cookies**, so
     you cannot accumulate results in storage there. Return each result instead.
   - `javascript_tool` output is capped at ~1.2 KB, which fits only ~8 compact result
     rows. To get all 15, keep the parsed document on `window` (`window.__d`) and make
     TWO extraction calls (rows 0-8, then 8-15) against that one fetch — do not refetch.
   - Compress titles by stripping Douglas's repeated noise: ` für Unisex|Weiblich|Männlich`
     and `Default Brand Line `. This is what makes 8 rows fit per call.
   - `decodeURIComponent` on `location.search` mangles `+` and `%` in the query, so key
     stored results by the ORIGINAL query string, never by the round-tripped one.

**Structure (verified live 2026-09-14):**
- Results grid: `.product-grid` — but there are **4 `.product-grid` blocks per
  page**, not one. Douglas chunks the result list around editorial/CMS components
  (e.g. 8 + 4 + 12 + 28 = 52 tiles). Concatenating them **in DOM order reproduces
  the customer's visual order** — verified against the rendered page.
- Tiles: `.product-grid .product-tile`. Dedupe by `a[href*="/p/"]` href.
- **SEO-footer trap:** a naive `a[href*="/p/"]` sweep finds ~72 links but only ~52
  are products; ~20 sit in `.seo-footer__column`. Scoping to `.product-grid`
  excludes them.
- **Title has no stable selector.** Inner nodes use hashed CSS-module classes
  (`_2e4ccc17b7339b01`), so `.product-tile__brand`/`__name` do not exist. The title
  lives in a visually-hidden leaf `<span>`. Extract structurally: **first childless
  descendant whose text is >15 chars, does not start with a digit, and contains no
  `€`**. Do NOT hardcode the hashed class — it changes on deploy.
  (`innerText` gives the title as line 1 on a *rendered* page, but `DOMParser`
  documents have no layout, so `textContent` concatenates everything — hence the
  structural rule.)
- **Price:** strip parenthesised unit prices (`(123,24 € / 1 kg)`) first, then take
  the **last** remaining `\d{1,3}(?:\.\d{3})*,\d{2} €` — with a UVP present the
  order is [UVP, selling price]; without one there is a single amount.
- **Sponsored:** tile text contains `Gesponsert`. Paid slots are interleaved into
  organic (seen at ranks 5–6).
- **PDP redirect:** a query matching one product redirects to `/de/p/<id>`; the
  destination IS the answer, extract as a 1-result list. `douglas.de` is registered
  in `_PDP_REDIRECT_HOSTS`. Both own-retail Art-Nr. (`687121`) and the internal URL
  id (`5009013008`) redirect; partner Art-Nr. (`M4078160`) returns a 1-result grid.

**Determinism:** organic ranking is stable — 3 SSR fetches and 2 rendered loads gave
identical ids at every position EXCEPT position 6, which is a rotating **sponsored**
slot. Do not report position-6 churn as ranking instability.

**THE RESULT HEADING IS CLIENT-RENDERED — NEVER TRUST IT FROM `fetch()` + `DOMParser`.**
This produced a false headline finding in the first Douglas run and had to be fully
re-collected. The `<h1>` result count and the "Meintest du" (did-you-mean) line are
populated during **client-side hydration**. Server HTML contains only i18n TEMPLATE
strings (`"Meintest du"`, `"Leider keine Treffer"`, `"{0} Treffer"`) from the JS bundle,
plus a stale/placeholder `0 Ergebnisse` heading. Consequences:
- A `fetch()`-derived heading of `0 Ergebnisse` means NOTHING. On re-check, `anastas`
  was really `101 Ergebnisse`, `feuchtigkeitsse` `157`, `sham#poo` `1394`, `abh brow` `97`.
- On those same queries the **product grid from `fetch()` was stale too** — `abh brow`
  returned 1 irrelevant Catrice lipgloss via fetch but 15 correct Anastasia Beverly Hills
  brow products when rendered. So a wrong heading is a reliable tell that the whole
  record is stale.
- **Rule: capture the heading, the did-you-mean line and the grid from a RENDERED page**
  (navigate + wait), not from `fetch()`. Use `fetch()` only where you have verified for
  that query that rendered and fetched agree.

**DOUGLAS HAS A REAL DID-YOU-MEAN, AND IT WORKS.** `0 Ergebnisse für „X"` followed by
`Meintest du: "Y" (N Treffer)` and N corrected results is CORRECT behaviour, not a defect
— do not report it as "claims zero while showing results". Verified working on
`lankome maskara` -> `"lancome mascara"` (30), `schampoo gegen schuppn` ->
`"shampoo gegen schuppen"` (27), `masca ra` -> `"mascara"` (678).
The real defect in this area is that the correction sometimes **inserts a spurious space**
and suggests nonsense: `shampoo 250 milliliter` -> `"shampoo 2 50 milliliter"` (4 junk hits),
`geschenk für meine mutter zum geburtstag` -> `"geschenk für m eine mutter zum geburtstag"`.

**SOME QUERIES ARE NON-DETERMINISTIC — SAMPLE BEFORE CALLING A ZERO.** The identical URL
returned a populated grid on some loads and `Keine Ergebnisse gefunden` on others, in the
same session, with 6-7s waits: `ich suche eine mascara die meine wimpern verlängert ohne zu
klumpen` gave ZERO,RESULTS,ZERO,ZERO,RESULTS,ZERO across 6 loads (4/6 zero). A control
(`mascara`) was stable at 52 tiles throughout, so this is query-specific, not a load race in
the harness. **Load any zero-result query at least 3x before recording it as a dead end**,
and record the observed rate rather than a single verdict.

**A genuine no-results page has: no `<h1>`, zero `.product-tile`, and `document.title` ==
`"Keine Ergebnisse gefunden | DOUGLAS"`.** Use the title as the positive marker.

**THE OLD `<h1>`-vs-grid NOTE (superseded, kept for context).**
Douglas has no conventional no-results page. Always capture the `<h1>` text
alongside the results; result count alone is meaningless on this host.
- `lankome maskara` → h1 says **"0 Ergebnisse"**, grid shows **15 correct Lancôme
  mascaras**. Same for `the ordianry niacinamid` (0 → 5 correct) and
  `schampoo gegen schuppn` (0 → 15 correct anti-dandruff shampoos). The engine finds
  the right products and tells the customer it found nothing.
- `qwertzuiop` (keyboard mash) → h1 says **"99 Ergebnisse"**, grid shows 99
  unrelated products (powder puff, JOOP! EdT, lash extensions, a bracelet).
- Consequence for the audit: a non-empty result list is NOT evidence of a hit, and
  a "0 results" heading is NOT evidence of a miss. **Relevance scoring, plus the h1
  text, are the signal — never the count.**

**Store results to disk after EVERY batch.** Keeping them only in page memory
(`window.__dgStore`) loses everything when the tab navigates or the pane closes —
this cost ~45 fetched queries once. Seed the in-page store from the on-disk
checkpoint at session start so the run is genuinely resumable, and never navigate
the tab mid-run (use `fetch()` for diagnostics too).



### baechli-bergsport.ch (Bächli Bergsport — Swiss mountain/outdoor-sports gear retailer)
- **Site type:** PHYSICAL_GOODS. Platform: **Rent-a-Shop** (Swiss ecommerce platform, server-rendered).
- **Fetch mode:** `static`. Fully server-rendered — no Playwright needed, fast.
- **Real results container:** `div.grid.multiline.products > article`. Per card: brand `<p>`, name `<h3><a href="...">`, price `<span>CHF <span>99.00</span></span>` (note: the price span has **no class** — generic price extractor's class-keyword match (`price`/`cost`/`amount`/`money`) misses it entirely, and the fallback regex doesn't recognize "CHF", so the generic strategy silently drops price on every result).
- **THE TRAP (caught at 4a, before any report) — PDP redirect on unique-match search:** when a query (e.g. an exact DIRECT_MATCH product title) matches **exactly one** product, the server redirects straight to that product's detail page instead of rendering a results grid. The pipeline's generic redirect handling (`_is_search_redirect`) treats ANY redirect-away-from-search as "no results for this query, skip" — which turned 3 of 4 genuine DIRECT_MATCH hits into false zeros (`Tech Trail Utility Printed Woven SS`, `Nano-Air Ultralight Full-Zip Hoody W`, `Flex Vrt W 21` all redirected to their PDP and were discarded). Verified live in a browser (user screenshot) that the redirect destination IS the correct single answer, not a dead end.
- **Fix in code:** added `_PDP_REDIRECT_HOSTS` + `_try_extract_pdp_as_result()` in `src/fetcher.py` — when a search-redirect is detected for a host in this set, instead of discarding, parses the PDP's `<h1>` (product name) and `product:price:amount`/`product:price:currency` OpenGraph meta tags into a 1-result list. Wired into all three redirect-handling call sites (static probe, Playwright probe, `_fetch_with_mode`). Also added `_try_baechli()` (grid extractor, parses `CHF <amount>` directly off card text since there's no price class) registered in `_try_site_specific()` and `_DEDICATED_EXTRACTOR_HOSTS`.
- **Verified at 4a (post-fix):** `Tech Trail Utility Printed Woven SS` → 1 (PDP-redirect path, CHF 79.00); `Nano-Air Ultralight Full-Zip Hoody W` → 1 (CHF 239.00); `Flex Vrt W 21` → 1 (CHF 339.00); `Footprint Badawi Long 6P` → 2 (ambiguous match, real grid, both with price); `boreal` (BRAND_SEARCH) → 2 real Boreal climbing shoes with price.
- **General lesson (applies beyond this host):** "redirected away from search" is not always "no results" — on platforms that short-circuit unique matches straight to the PDP, a redirect can BE the answer. Don't assume redirect-away-from-search ⇒ zero without checking the destination page in a browser first.
- **SECOND TRAP (caught reviewing a generic SYNONYM query against a live screenshot) — generic junk filter ate a real result mid-ranking:** `Regenjacke` initially fetched a result set whose rank 1-2 matched the live site but then diverged from rank 3 onward, with the live page's "Talon 6" (Osprey hip-pack, 7-char title) missing entirely. Root cause: `_try_baechli` was piping its output through the shared `_filter_junk_results()`, whose `len(title) < 8` heuristic (designed to drop nav/chrome junk on *unscoped* generic strategies) silently dropped genuine short product names. This is a more dangerous failure than a clean zero — the result set looked complete and self-consistent but was subtly wrong starting partway through the ranking, only catchable by a rank-by-rank visual diff against the live page, not by a result count check.
- **Fix in code:** `_try_baechli` no longer calls `_filter_junk_results()` — since it already scopes to the real `div.grid.multiline.products` container, every `<h3><a>` is a genuine product and no junk filter is needed.
- **General lesson:** a dedicated/scoped extractor should usually skip the generic junk filter entirely — that filter's heuristics (title length, junk-word lists) are tuned for *unscoped* strategies trying to separate products from nav/chrome on the whole page, and can false-positive on legitimately short real titles once you're already scoped to a confirmed results container. Always verify a "fixed" extractor by diffing its top 5-6 against a live screenshot rank-by-rank, not just checking the count or the first 1-2 results — a subtle mid-list drop survives a shallow check.
- **Brands (user-supplied):** alpibreak, boreal, eZeefit, Kraszewski.
- **Featured items (user-supplied, double as DIRECT_MATCH queries):** Tech Trail Utility Printed Woven SS, Nano-Air Ultralight Full-Zip Hoody W, Flex Vrt W 21, Footprint Badawi Long 6P.
- **Locale:** German (Swiss), CHF pricing.

### ahlens.se (Åhléns — Swedish department store)
- **Site type:** MARKETPLACE_MIXED (department store: dam/herr/barn, skönhet, inredning, leksaker). Discovery mis-classifies it as SERVICES_EXPERIENCES — correct it.
- **Fetch mode:** `playwright_chromium`. Static fetch returns 0 real results (client-rendered grid). Playwright + chromium required in `.venv312`.
- **Real results container:** `<section id="product-rain-section">` (inside `<div id="tab-products">`). Product cards have class token `group/product-card`; each card text is `brand / name / price`, with sale cards prepending a `-NN%` badge and adding `Rea` + a `Lägsta pris 30 dagar` original-price line.
- **THE TRAP (caused a bad published report):** the generic product-cards strategy grabbed the **mini-cart drawer's "Du kanske också gillar" recommendations** — a horizontal `flex overflow-x-scroll` carousel of `role="listitem"` divs full of `/produkter/skonhet/` beauty products — instead of the search grid. Result: every query scored against unrelated beauty recs. The cart-drawer products sit under the "Varukorg / Din varukorg är tom" panel, OUTSIDE `#product-rain-section`.
- **Fix in code:** `_try_ahlens()` in `src/fetcher.py`, registered in `_try_site_specific()`. Scopes to `#product-rain-section`, dedupes by product href, and parses price from the card's price line with `\xa0`/space normalization (handles "1 000 kr").
- **Title noise (verified on beauty queries):** card text can carry chrome that must be excluded from the title — a leading stock badge `Endast i varuhus` (in-store only), `Rea`, a `-NN%` discount badge, and a trailing variant-swatch block (`Produkten finns i färgerna:` followed by colour names and `+NN`). The extractor takes title = the lines BEFORE the first price line, then strips leading badge/label lines (`label_re` covers `endast i varuhus`, `produkten finns`, `fler färger`, `rea`, `lägsta pris`, etc.). Taking lines-before-price is what drops the post-price swatch block cleanly.
- **Result count is accurate:** narrow multi-word queries genuinely return few results (e.g. "Clinique hudvård dam känslig hud" → 3 cards, confirmed against live `#product-rain-section`). Don't assume low counts mean under-collection — verify card count in the section. The page header text is ground truth: "X träffar på" / "Inga träffar på". (Variant SKUs of one product count separately — e.g. "grytor och pannor" → 4 hits = 4 colour/size variants of the same Le Creuset kettle.)
- **No-results page (CRITICAL):** a genuine no-hits query renders NO `#product-rain-section` and shows "Inga träffar på \"…\"" plus a "Du kanske också gillar" recommendation carousel. The generic fallback would scrape those recs as phantom results and hide the search failure. Fixed via (a) authoritative-empty for the host in `_extract_results` (`_has_dedicated_extractor`), and (b) `_wait_for_ahlens_ready()` which waits for the grid OR the "Inga träffar" marker before capture (called in both Playwright fetch paths, before the quick_probe/scroll split). Always re-fetch the whole set after this kind of fix — earlier batches are contaminated.
- **Ordering:** **Deterministic, not personalized.** Verified identical order across headless/headed × real-UA/no-UA, and stable within a session from ~1.2s (no client-side re-rank after initial render; scrolling doesn't change it). The order CAN still drift vs a user's screenshot over time as the live catalog/ranking changes (e.g. new seasonal Mini Rodini stock inserted at rank 3), and possibly via geo/IP-based ranking/stock filters. If order matters, pin down temporal-vs-geo before changing code — do not assume non-determinism. (Earlier mistaken claim of non-determinism was due to comparing runs taken at different times as the catalog shifted.)
- **Brands:** `/varumarken` lists ~1000+ real brands; use it to seed/verify brands. Note Nike, Chanel, Polarn O. Pyret are NOT carried.
- **Seed-query note:** `?q=barn` returns "Inga träffar på barn" (zero hits) — it's only a URL-pattern example, not a representative query.

### avoca.com (Avoca — Irish department-store retailer, Shopify)
- **Site type:** MARKETPLACE_MIXED. Platform: **Shopify** + **Boost AI Search & Discovery** widget.
- **Fetch mode:** `playwright_chromium`. The Boost results grid is injected client-side; a static/quick probe captures ZERO cards (looks like a false no-results page). A readiness wait is required.
- **Real results container:** `div.boost-sd__product-item` cards. Per card: title `.boost-sd__product-title`, price `.boost-sd__product-price` (text like "Regular price €59.99 €59.99"; sale price under `.boost-sd__product-price--sale`), link `a.boost-sd__product-link` → `/products/<handle>`. Prices are euros (€).
- **THE TRAP (caught at 4a, before any report):** with no dedicated extractor, the generic + LLM strategies returned **0 results for real queries** ("knitwear", "Barbour") because they ran before the Boost grid rendered — and the no-results control still leaked **1 phantom** via the LLM strategy. Both are silent failures.
- **Fix in code:** `_try_avoca()` in `src/fetcher.py`, registered in `_try_site_specific()`; host added to `_DEDICATED_EXTRACTOR_HOSTS` (authoritative-empty → real no-results returns `[]`, no fallback). `_wait_for_avoca_ready()` waits for `.boost-sd__product-item` OR the "0 results found" / "couldn't find results" marker before capture (wired into both Playwright fetch paths).
- **No-results page:** renders zero `boost-sd__product-item` and shows "Showing 0 result" / "0 results found for \"…\"" / "We are sorry! We couldn't find results". Scoping to the card selector is therefore naturally authoritative.
- **Verified at 4a:** exact title → 1 (correct product+price), "knitwear"/"Barbour"/"scarves" → 10 real products each, no-results control → 0.

### huckberry.com (Huckberry — multi-brand outdoor/menswear lifestyle, React SPA)
- **Site type:** MARKETPLACE_MIXED.
- **Fetch mode:** **headed Chromium, forced.** Huckberry sits behind a Cloudflare "Just a moment..." JS challenge. Static fetch → 403; *headless* Playwright (firefox or chromium) → the challenge interstitial, classified as `cloudflare` → "all browsers blocked". A **non-headless** Chromium session passes the managed challenge on its own in ~2–6s. Wired via `_HEADED_CHROMIUM_HOSTS = ("huckberry.com",)`: launches `headless=False`, forces Chromium (Firefox binary often missing for the installed PW version anyway), and runs `_wait_for_cloudflare_clear()` (polls until the "Just a moment" title/marker is gone) BEFORE block-classifying. A Chromium window opens and drives itself during the fetch.
- **Real results container:** each product tile has a content block with `a.ProductTileContent__brand-link` (brand), a product-name anchor → `/store/<brand>/category/p/<id>-<slug>`, and `span.ProductTileContent__price` ("$NNN"). Extractor `_try_huckberry` climbs from each brand link to the ancestor holding the price, dedupes by the numeric product id (products recur across a featured row + the main grid). `_wait_for_huckberry_ready()` waits for a price span/brand link OR a "couldn't find"/"no results" marker before capture.
- **TITLE = brand + product name (deliberate, not a bug).** On the card the brand and the product name are SEPARATE DOM elements — the bare on-card title is just "Tundra 35 Cooler" with "YETI" rendered above it as a brand link. `_try_huckberry` composes `"{brand} {name}"` (unless the name already leads with the brand) so DIRECT_MATCH / `featured_items` queries that include the brand (e.g. "YETI Tundra 35 Cooler", "Schmidt Brothers 4-Piece BBQ Tool Set") match — the judge auto-fails DIRECT_MATCH if the rank-1 title doesn't contain the exact query. Same convention as `_try_ahlens` / `_try_bergzeit`. Downstream (scoring/judge): the brand in the title faithfully reflects what's shown on the card; don't treat the brand prefix as injected noise.
- **Authoritative-empty:** registered in `_DEDICATED_EXTRACTOR_HOSTS`. A genuine no-results page renders ZERO brand links / price spans and a "We couldn't find …" marker → returns `[]`, no fallback. The LLM fallback is now skipped for ALL dedicated-extractor hosts (`if len(results) < 5 and not _has_dedicated_extractor(url)`) so thin-but-real result sets (e.g. exact-match "YETI Tundra 35 Cooler" → 2) aren't padded with recommendation chrome.
- **Verified at 4a:** exact BBQ set → 2 (exact at rank 1); "YETI" → 15; "fleece pullover" → 15; "Gozn" (partial) → 15 all Gozney; long NL query "warm jacket for hiking in cold weather" → **0**; gibberish control → 0. The NL zero looks genuine (Huckberry's keyword search doesn't handle conversational queries) — watch NL/SEMANTIC queries in Phase 4/5 as real findings, but spot-check a couple against the live site before judging.
- **Must run via `.venv312`** (python3.12); system python3.9/LibreSSL fails TLS.

### manufactum.de (Manufactum — German durable-quality-goods retailer)
- **Site type:** MARKETPLACE_MIXED (Garten/Küche/Wohnen/Haushalt/Büro/Bücher/clothing/food).
- **Fetch mode:** `playwright_chromium` (SSR-ish but the pipeline settles on Playwright; works fine).
- **THE TRAP (caught at 4a, before any report):** on a genuine no-results query the header reads `Suchergebnis für »…« (0)` but the page is padded with a large fallback/recommendation grid (oak furniture, shoes, …). The generic strategy scraped 5 of those phantoms — masking a real search failure as a poor non-zero result. The NL query `ich suche eine schöne Lampe für das Wohnzimmer` reproduces it: header `(0)`, ~92 phantom tiles, zero lamps.
- **Authoritative signal = the header count.** The h1 is `Suchergebnis für »<q>« (N)`. `_try_manufactum` parses `(N)` and returns `[]` when `N==0`. Host added to `_DEDICATED_EXTRACTOR_HOSTS` so the empty short-circuits generic/LLM fallbacks.
- **STABLE selectors are `data-test-*` attrs** (CSS-module class names like `mf-SVlBJ1YF` are hashed per build — do NOT use them): card `div[data-test-sell-product-tile="true"]`, link `a[data-test-sell-product-link="true"]` (`/<slug>-a<id>/`), name `span[data-test-sell-product-name="true"]`, price `span[data-test-stelar-price-price="true"]`.
- **Title = manufacturer + product name** unless the name already starts with the manufacturer (code, since the Armedangels BRAND_SEARCH false misses; this line used to say "name span alone"). The header `(N)` now caps the tiles read at N, and an unparseable header returns `[]` → `zero_unverified` — the extractor never scrapes "all tiles" without a count. Dedup by href path (strips `?v=` variant params; distinct colour SKUs have distinct `-a<id>` paths and are kept).
- **Price:** German format `39,90 €` / `1.099,00 €`, taken verbatim from the price span. Sale items show two prices; the price span carries the current/regular price (sale price not separately captured — fine for relevance scoring).
- **Fix in code:** `_try_manufactum` in `src/fetcher.py`, registered in `_try_site_specific()` and `_DEDICATED_EXTRACTOR_HOSTS`.
- **Verified at 4a:** `Armedangels` → 15 (order+prices match live; those shirts/caps really are all 39,90 €), `Tischleuchte schwarz` → 15 real lamps (varied prices), no-results NL query → 0 (was 5 phantoms before the fix).
- **FALSE-ZERO FLAKINESS (verify zeros against the live header count):** Manufactum intermittently renders the no-hits state for a query that genuinely HAS results during sequential Playwright runs — the single dedicated-host retry-on-zero is NOT always enough (`Tasche nicht Leder` returned 0 in the batch AND on the first manual retry, but the live header says **36**; it recovered on the 2nd retry). After the full fetch, take the live header `(N)` for every zero-result query (cheap: `fetch()` the search URL, regex `Suchergebnis für …\((\d+)\)`); any query with header `N>0` but fetched 0 is a false zero — re-fetch it (loop up to ~4×) and patch the checkpoint. On this run, 20/21 zeros were genuine, 1 (`Tasche nicht Leder`) was a false zero.
- **DIRECT_MATCH caution:** site product names omit suffixes a user might add — live name is `Tischleuchte Sonnenglas®`, NOT `…(Generation 6)`. Featured-item exact-match queries must use the on-site name or the judge false-fails DIRECT_MATCH (rank-1 title won't contain the extra text).

### imerco.dk (Imerco — Danish kitchen & home goods, Next.js client-rendered)
- **Site type:** PHYSICAL_GOODS (broad homeware: kitchenware, tableware, glass, furniture, lamps, bath, personal care).
- **Fetch mode:** `playwright_chromium`. Search grid is client-rendered. `wait_until='networkidle'` TIMES OUT (continuous background network) — use `domcontentloaded` + a fixed wait if probing manually.
- **THE TRAP (caught at 4a):** generic strategy extracts the products + URLs fine but **drops ALL prices** — Imerco prices live in separate hashed-class spans (`ProductPrices_emphasized__*`), not in the card text the generic parser reads. Result would be a price-less fetch. Fixed with a dedicated extractor.
- **STABLE selectors = class-name PREFIXES** (CSS-module suffixes are hashed per build; match by substring):
  - card: `div[class*="ProductHit_wrapper"]`
  - link: `a[class*="ProductHit_card"]` → `/<slug>?id=<id>` (relative; prefix `https://www.imerco.dk`)
  - brand: `span[class*="NewProductCard_brand"]`, name: `span[class*="NewProductCard_name"]`
  - price: first `span[class*="ProductPrices_emphasized"]` (member + non-member each render as an emphasized span; first = displayed price). Danish format "699,95" → store as "699,95 kr".
- **Title = brand + name** (e.g. "Eva Trio Stainless Steel Gryde") so BRAND_SEARCH / DIRECT_MATCH (which include the brand) match.
- **No-results page:** renders ZERO `ProductHit_wrapper` cards and header "0 resultater", NO phantom recommendation carousel using that class → scoping to the card class is naturally authoritative. Registered in `_DEDICATED_EXTRACTOR_HOSTS`.
- **Fix in code:** `_try_imerco` in `src/fetcher.py`, registered in `_try_site_specific()` and `_DEDICATED_EXTRACTOR_HOSTS`.
- **Verified at 4a:** exact `D106 Bakketop Bakkebord` → 2 (correct product, 2 colour variants, prices); `Scanpan` → 15 all-Scanpan with prices; `krus hvid` → 15 white mugs with prices (1 cosmetic missing price at rank 1, sold-out-state card); gibberish → 0.
- **Minor known gap:** occasional card (e.g. sold-out) has no `ProductPrices_emphasized` span → price falls back to `_extract_price`, may be None. Cosmetic; doesn't affect relevance scoring (title-driven).

### bergzeit.de — search-to-category-page redirect (semantic queries)
- **Site type:** PHYSICAL_GOODS (German outdoor/mountain-sports gear retailer). Already had a dedicated extractor (`_try_bergzeit`), registered in `_DEDICATED_EXTRACTOR_HOSTS`, `_CLIENT_RENDERED_PRICE_HOSTS` (Playwright required for prices).
- **THE TRAP (caught reviewing the post-fetch thin/zero list, before judging) — search redirects to a FILTERED CATEGORY PAGE, not a PDP:** 4 multi-word German queries (`Regenjacke Herren`, `Regenhose Damen`, `Arc'teryx Herren`, `günstige Fahrradhelme Kinder`) all fetched as **0 results**, surviving the dedicated-host retry-on-zero unchanged (4/4 retries still 0). Live-header check confirmed real, large result counts (70–508 "Artikel"). Root cause: Bergzeit's search engine semantically resolves these queries by **redirecting from `/search/?q=...` to a filtered taxonomy page** (e.g. `/bekleidung/jacken/hardshelljacken-regenjacken/?bzsearch=...&filter.gender=Herren`, `/marken/arcteryx/?bzsearch=...&filter.gender=Herren`) — a real, on-topic category+filter landing page with the matching products, NOT a no-results page and NOT a unique-product PDP. The generic `_is_search_redirect` handling treats ANY redirect away from `/search/` as "no results, skip", discarding a perfectly good answer.
- **Distinguish from the baechli-bergsport.ch PDP-redirect trap:** that case redirects to a single product page (unique match); this case redirects to a multi-product CATEGORY listing page (broader semantic match). Both are "redirect ≠ zero", but the extraction differs — a category-page redirect should be run back through the same `_try_bergzeit` card extractor (the destination page has the identical product-card markup as the search grid), not a PDP-specific parser.
- **DONE (2026-10):** every redirect, on every host, is now extracted on the destination (`_redirect_kind` = `landing` → REDIRECT with the grid). Original manual fix, kept for context: for a redirected URL, re-run `_try_bergzeit(soup, max_results)` against the redirected page's HTML directly — it extracts cleanly (15/15 results, correct titles/prices) because the category page reuses the same card markup as `/search/`. **TODO for next bergzeit audit:** wire this into `_fetch_with_mode`/`_is_search_redirect` as a general case (any redirect for a `_DEDICATED_EXTRACTOR_HOSTS` host should retry the SAME extractor against the destination page before concluding "no results", not just the PDP-specific path).
- **SECOND TRAP (caught at judge time, NOT at 4a) — phantom recommendation results on a genuine no-results page.** `was soll ich beim Wandern im Winter anziehen` (NATURAL_LANGUAGE) fetched as 12 results in the full Phase 4 run, but the live page title is literally `Deine Suche ergab leider keine Treffer` (no results) — a genuine zero. The 12 phantom results (a tank top, summer T-shirts, a Patagonia trucker cap, short cycling bibs — nothing winter-hiking-relevant) were a recommendation carousel scraped by the generic/fallback path on the no-hits page, not real search results. This masked a real CRITICAL search failure as a passable moderate-relevance result. **The 4a gate did not catch this because the probe queries used at 4a (an exact product title + a brand) both had real results** — conversational/NL queries are exactly the kind of query likely to genuinely return zero on this engine, and weren't probed. **Lesson:** for NATURAL_LANGUAGE/SEMANTIC_MEANING/conversational queries specifically, spot-check any non-trivial result count against the live page's title/header text (`Deine Suche ergab leider keine Treffer` is the authoritative no-hits marker for this host) — don't trust a non-empty result list at face value for this query type, since the 4a probe doesn't exercise it. **DONE (2026-10):** "keine Treffer" is a generic `page_state` marker (plus a bergzeit profile marker) → `zero_confirmed` with `[]`; `_try_bergzeit` no longer falls back to whole-page `/p/` anchors (that fallback was where the carousel came from) — no results wrapper → `[]` → `zero_unverified`.
- **THIRD TRAP — genuine search-backend flakiness, not a fetch bug (caught when the user manually checked the live URL after a judge override).** `Wanderjacke unter 100 Euro` (PRICE_ANCHORED) was independently re-fetched 3 times in a row: attempts 1-2 showed the no-hits page (phantom carousel), attempt 3 showed a real, correct result (4 genuine CMP Wanderjacken, all priced 53,95-69,95 €, satisfying the price constraint). The user saw the correct 4-result state live and flagged the CRITICAL/zero verdict as wrong; re-fetching confirmed the backend itself is non-deterministic for this query — same flakiness class as manufactum.de's "Tasche nicht Leder" false-zero (see that entry), but here on bergzeit.de and on a query that legitimately has BOTH a real-result state and a no-hits state depending on which backend instance/cache answers. **Lesson:** when a user disputes a zero/CRITICAL verdict with a specific live observation, don't just re-verify once — retry the live fetch 3-5x before concluding either way, since the live "ground truth" itself may be flaky, not just the local fetch.
- **General lesson (extends the baechli lesson):** "redirected away from search" is not always "no results" in EITHER direction — it can be a unique-PDP shortcut (baechli) or a semantic-category-page shortcut (bergzeit). Always inspect the destination page content before discarding a redirect as a search failure; if the destination renders real product cards, extract from it.
- **Verified fix:** `Regenjacke Herren` → 15 (Hardshelljacken & Regenjacken Herren grid), `Regenhose Damen` → 15, `Arc'teryx Herren` → 15 (brand page filtered to Herren), `günstige Fahrradhelme Kinder` → 15 (Fahrradhelme filtered to Kinder).

### cotswoldoutdoor.com (Cotswold Outdoor — UK outdoor gear & clothing retailer)
- **Site type:** MARKETPLACE_MIXED. Platform: server-rendered React tile grid (`lister.html?q=...`), no Cloudflare gate.
- **Fetch mode:** `playwright_firefox` settled by the probe; works fine.
- **Real results container:** `div[data-testid="product-tile-vertical"]`. Link: first `a[href*="/p/"]`. Title: `div[class*="product-tile__title"]` (brand `<strong>` + name span concatenated). Price: `span[data-testid="product-tile-vertical-price-actual-price"]` (current/sale price), falling back to `span[data-testid="product-tile-vertical-price-previous-price"]` (RRP) if no actual-price span.
- **THE TRAP (caught at 4a) — review-count digit collides with the price symbol:** each card also renders a star-rating review count (e.g. "0", "7", "15") immediately before the price block. The generic price regex's symbol-after alternative (`\d[\d.,]*\s?[$€£¥...]`) matches the EARLIER, WRONG pattern "7 £" (count + symbol) instead of the real "£240.00" later in the same text, because regex `search` returns the leftmost match. Verified live: `Arc'teryx` brand search showed correct titles/URLs but ranks 2, 6, 12 had `price="7 £"`, `"15 £"`, `"4 £"` instead of real prices.
- **Fix in code:** `_try_cotswoldoutdoor()` in `src/fetcher.py`, registered in `_try_site_specific()` and `_DEDICATED_EXTRACTOR_HOSTS`. Scopes directly to the price `data-testid` span — sidesteps the full-text regex entirely, so the review-count collision can't happen.
- **SECOND TRAP — DIRECT_MATCH (exact-title) queries redirect straight to the PDP, no grid at all** (same pattern as baechli-bergsport.ch's PDP-redirect trap). Verified: `Garmin Fenix 8 Pro AMOLED Sapphire 51mm GPS Smartwatch` redirects to `/p/garmin-fenix-8-pro-amoled-sapphire-51mm-gps-smartwatch-....html`. **This is correct, desirable search behavior, not a defect** — see JUDGE_PLAYBOOK's calibration rule (PDP-redirect on DIRECT_MATCH = PASS). Host added to `_PDP_REDIRECT_HOSTS`. Cotswold's PDP has no OpenGraph price meta tags (unlike Bächli), so `_try_extract_pdp_as_result` falls back to the PDP's own `[data-testid="product_price-actual-price"]` (falls back further to `product_price-previous-price`, the RRP).
- **THIRD TRAP — a non-unique query (e.g. a bare brand name) ALSO redirects, but to a multi-product brand/category LISTING page, not a PDP.** Verified: `Arc'teryx` (BRAND_SEARCH) redirects to `/brands/arcteryx.html`, a real grid with the same `product-tile-vertical` tile markup as the search results page — not a unique-match shortcut. `_try_extract_pdp_as_result` now guards against this: if the redirected page contains more than one `product-tile-vertical` card, it returns `[]` (refusing to fabricate a single fake result from the category page's `<h1>`) instead of falling through to the dedicated grid extractor. Implemented generically in `_probe_site`/`_fetch_with_mode`: when a redirect isn't a unique-match PDP, `_has_dedicated_extractor(url)` hosts re-run `_try_site_specific()` against the redirected page's HTML directly — this is the generalized version of the bergzeit.de "category-page redirect" TODO (now wired into code, not manual).
- **FOURTH TRAP — the category-redirect fallback (fix for the third trap) initially reintroduced the classic "phantom recommendations on a no-results page" failure.** `waterproof jacket under £100` (PRICE_ANCHORED) redirects to `https://www.cotswoldoutdoor.com/lister/no-results.html?q=...` — a genuine zero — but that page renders a "you might also like" carousel using the IDENTICAL `product-tile-vertical` tile markup as the real grid (all 10 carousel links carry `&rrec=true`). The new category-redirect fallback (added for the Arc'teryx brand-page case, third trap above) blindly re-ran `_try_cotswoldoutdoor` against any non-PDP redirect destination, so it scraped this carousel as 10 fake results — none of which were jackets, none under £100, e.g. rank 1 was £13 socks and rank 2 was a £999.99 Garmin watch. **Verified live in a browser** that the redirect target really is `/lister/no-results.html`.
- **Fix in code:** added `_NO_RESULTS_PATH_MARKERS` (`{"cotswoldoutdoor.com": "/lister/no-results"}`) + `_is_authoritative_no_results(final_url)` in `src/fetcher.py`. The category-redirect fallback at all three redirect call sites (`_probe_site` static + Playwright, `_fetch_with_mode`) now skips re-running the dedicated extractor when the destination matches this marker — falls straight through to the genuine `[]`/zero path instead.
- **General lesson:** any new "redirect destination might have real results" fallback must independently re-check for the authoritative-no-results signal before extracting — don't assume "not a PDP" implies "must be a real listing." A recommendation carousel can reuse a real results-grid's markup on EITHER a no-results page OR (as seen here) a PDP's "related products" section; the only reliable signal was the destination URL path, not tile presence/count.
- **Verified at 4a (post-fix, all three traps):** `Arc'teryx` brand redirect → real 15-result Arc'teryx grid from `/brands/arcteryx.html`, correct prices on every rank. `Garmin Fenix 8 Pro AMOLED Sapphire 51mm GPS Smartwatch` (DIRECT_MATCH) → 1 PDP-extracted result, title exact match, price present. `waterproof jacket under £100` → 0 (genuine no-results, no longer phantom-padded).
- **FIFTH TRAP (CRITICAL — silent false zeros across the whole audit) — Firefox aborts the `&sred=1` category redirect.** Many keyword queries (`backpack`, `Salmoon walking boots` typo→Salomon, `TNF jacket`→The North Face, and most semantic/occasion/price queries) don't land on `/lister.html` — the server bounces them client-side to a curated category page with a `?...&sred=1` param (e.g. `backpack` → `/c/equipment/rucksacks.html?q=backpack&sred=1`). **Playwright Firefox dies on this redirect with "Network Protocol Error: a network protocol violation that cannot be repaired"**, capturing only a ~6KB stub → 0 tiles → false zero. The probe settled on Firefox because the FIRST probe query was a PDP-redirect (DIRECT_MATCH) that happens to work in Firefox, masking the problem; every redirecting query in the batch then silently returned 0. **Chromium follows the same redirect cleanly** → full 1.1MB category page, 49 tiles, correct prices. Note `_is_search_redirect` returns False for these because `?q=` is preserved in the destination, so they flow through the *normal* extract path, not the redirect-fallback path — the dedicated extractor works fine once the right browser delivers real HTML.
- **Fix in code:** added `_PREFER_CHROMIUM_HOSTS = ("cotswoldoutdoor.com",)` + `_prefers_chromium(url)` in `src/fetcher.py`; `_fetch_with_playwright`'s browser-selection block forces Chromium-only ordering for these hosts (so the probe settles on `PLAYWRIGHT_CHROMIUM` and every subsequent `_fetch_with_mode` call reuses Chromium). Also added `_wait_for_cotswold_ready()` (waits for `div[data-testid="product-tile-vertical"]` or the no-results page) wired into both `_fetch_with_playwright` and `_fetch_on_context`, to absorb the post-redirect hydration delay.
- **General lesson:** when a site does client-side query-preserving redirects to category pages, pick the probe browser by testing a *redirecting* query, not just the first query — a DIRECT_MATCH/PDP probe can mask a browser-specific redirect failure and poison the whole batch with silent zeros. If a site shows a suspicious cluster of zero-result queries, re-test one in Chromium before trusting them as genuine.
- **Cookie consent dialog blocks a manual/static read of the page** (a "Yes, I accept" overlay) — Playwright's own probe handles this fine (doesn't block extraction), only matters if inspecting the page by hand in a real browser.
- **Brands:** Ayacucho, Patagonia, Rab, Mountain Equipment, The North Face, Arc'teryx, Oakley, Montane, Columbia, Fjällräven, Vivobarefoot, Ray-Ban, Scarpa, Meindl, Merrell, Salomon, Lowa, Hoka, Osprey, Garmin, Vango, MSR, Sea to Summit.
- **Locale:** English (UK), GBP pricing (£).

### lyko.com (Lyko — Swedish multi-brand beauty/cosmetics, client-hydrated prices)
- **Site type:** MARKETPLACE_MIXED. Search URL `https://lyko.com/sv/sok?q={}`. Locale: Swedish, SEK ("kr"), comma decimals ("178,50 kr").
- **Fetch mode:** `playwright` (server-renders product cards + URLs statically, but **hydrates prices client-side**). Host added to `_CLIENT_RENDERED_PRICE_HOSTS` so the probe does NOT short-circuit to STATIC (static returns 15 priced-less results, which previously looked "good enough" and skipped Playwright → every price missing).
- **Real results container:** product anchors `a.link-product-page` (fallback: `a[href^="/sv/"]` matching `^/sv/[^/]+/[^/]+$`, i.e. `/sv/{brand}/{product}`). Each product appears twice (image link + price link) → dedupe by href.
- **THE TRAP (caught at 4a) — price is NOT inside the anchor.** The displayed price is a classless `<span>` in the anchor's **parent card div**, not in the anchor text. `_try_lyko`'s original anchor-text price regex found nothing → all prices null even under Playwright. Fix: read price from `link.find_parent()` text (climb one more level if no "kr" there).
- **Price selection (current vs original):** cards show multiple "kr" values. Current/display price = `Reapris N kr` (Combo Deal campaign price) if present; otherwise the first standalone `N kr` AFTER stripping the original-price lines `Rek. pris N kr` / `Rekommenderat pris N kr` / `Utan kampanj N kr` / `Utan paketpris: N kr`. (Verified: Combo Deal → Reapris wins; WOW-pris → sale price, not the "Rek. pris" original.)
- **Title badge noise:** card text prefixes the product name with promo badges that leak into the title — strip `Combo Deal N%`, `WOW-pris`, `Gåva på köpet`, `Sponsrad`, `Nyhet`, `Rek. pris`, `Rekommenderat pris`, `Se villkor på produktsidan`, and any `N kr` price fragments. `_try_lyko` now strips all of these (title = brand + product name, e.g. "Beauty of Joseon Glow Serum: Propolis+Niacinamide 30 ml").
- **SECOND TRAP (caught reviewing the post-fetch thin list) — search redirects to a CATEGORY PAGE, extractor scrapes filter chips not products.** Queries like `herrparfym` (CATEGORY_MAPPING) and `parf#ym` (SPECIAL_CHARACTER, normalized → "parfym") redirect `/sv/sok?q=...` → `/sv/parfym/herrparfym?fromsearch=...` — a real, on-topic category landing page (correct search behavior). BUT on category pages products use a **hashed anchor class** (e.g. `Ik6U8l`, not `link-product-page`) and **deeper URLs** (`/sv/parfym/herrparfym/parfum/{slug}`), so `_try_lyko`'s old fallback (`^/sv/[^/]+/[^/]+$`, exactly 2 segments) missed them and instead matched the 2-segment **category-filter chips** (`/sv/parfym/damparfym`, `/sv/parfym/body-mist`, ...) → 7 priceless chip "results". Reliable discriminator: **a product card's parent contains a `kr` price; a category chip does not.**
- **Fix in code:** `_try_lyko` fallback now collects `a[href^="/sv/"]` with ≥3 path segments AND a `kr` price in the parent card (via `_card_text` helper, climbs ≤2 levels); title falls back to card text when the anchor wraps only the image; also strips `Kampanj N%` badge and the `KÖP` button word. Post-fix: `herrparfym` → 15 real Hugo Boss/YSL perfumes, `parf#ym` → 15 perfume/body-mist products. After any full fetch, scan the checkpoint for chip contamination (≥2 results whose title is a bare category name like "Damparfym"/"Body Mist"/"Deodorant", or >50% missing price) and re-fetch those queries.
- **Authoritative-empty:** registered in `_DEDICATED_EXTRACTOR_HOSTS` — a genuine no-results query returns `[]`, no fallback scrape. (Verify zero-result queries against the live "X produkter" / "Inga träffar" header before judging.)
- **Minor known price glitch:** a product whose name contains a dotted code (e.g. "By Lyko Oh My Dye … C4.10") can leak the code digits into the price field ("4.10 139 kr"). Cosmetic, single-card; doesn't affect title-driven relevance scoring.
- **Special-character normalization is strong:** `niac*inamide` (mid-word `*`) returned The Ordinary Niacinamide at rank 1 — the engine strips the injected char. Good sign for SPECIAL_CHARACTER scoring.
- **Verified at 4a (post-fix):** exact `COSRX Advanced Snail 96 Mucin Power Essence 100 ml` → 15, exact at rank 1 (120 kr Combo Deal), ranks 1–2 match live; `NIVEA` → 15 priced NIVEA products; `niac*inamide` → 15 niacinamide products, clean titles. Live header for the COSRX query was "22 produkter".

### zalando.* (Zalando — every market)
- **Fetch mode:** headed Chromium on every `zalando.*` host (`_HEADED_CHROMIUM_HOSTS` matches `"zalando."`): headless gets a 403 / soft "Not Found" with zero products.
- **No-results marker:** `Try a different search term or check the spelling.` (host profile) → `zero_confirmed`. The no-results page pads itself with "Recommended for you" / "Most popular - Our customers bought" carousels in the same `<article>` markup — the phantom set rotates between runs.
- **Grid scope (2026-10):** `<article>`s from `[data-testid="product-count"]` down to the first carousel heading. No count header → `[]` → `zero_unverified` (never the whole page's articles). Readiness waits for the count header or the marker (20 s).
- **PDP:** an exact article code redirects to the PDP (`og:type=product`); now caught generically by `_extract_pdp` → 1 result, `redirect`.
- **Titles:** card text is line-structured; brand + name = last two lines before the first `€` line. Hashed class names — never select on them.

### colourpop.com (ColourPop — Shopify, US beauty)
- **Fetch mode:** headed Chromium with `channel="chrome"` (real Chrome binary).
- **Grid:** `#product-grid main-product`, title `h2 a[href*="/products/"]`, price from "Regular price $N". Hidden recommendation blocks live outside `#product-grid`.
- **No-results marker:** `0 items` (host profile, word-bounded); readiness waits for the grid or that text.

### Existing site-specific extractors (see `src/fetcher.py`)
- **groupon** — `_try_groupon`: deal cards via `/deals/` anchors; title from `<h3>`.
- **lyko.com** — `_try_lyko`: see full profile above (Playwright for prices; price from parent card; badge-stripped titles).
- **bergzeit.de** — `_try_bergzeit`: `/p/<slug>/<id>/` anchors scoped to the results list (excludes footer voucher teasers); client-rendered prices → must use Playwright (`_CLIENT_RENDERED_PRICE_HOSTS`).
- **zalando.*** / **douglas.de** / **colourpop.com** / **manufactum.de** / **imerco.dk** / **avoca.com** / **huckberry.com** / **ahlens.se** / **baechli-bergsport.ch** / **cotswoldoutdoor.com** — see their profiles above. Per-host markers, hit-count regexes, PDP path rules and readiness selectors live in `_HOST_PROFILES`.

---

## When you add a new site

Append a profile with at minimum: fetch mode, the real results-grid selector, the
wrong containers you ruled out, price/locale quirks, and ordering behaviour. Wire the
extractor into `_try_site_specific()` so it short-circuits the generic sweep.
