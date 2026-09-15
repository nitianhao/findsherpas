# Positioning interview — Find Sherpas

Recorded 12 August 2026. A structured interview with Michal Pekarčík to establish what the
website should actually say, after the existing site was judged generic and was earning zero
clicks from Google.

Questions are as asked; answers are Michal's, lightly tidied for spelling only. Nothing here is
inferred — where a question went unanswered it is marked as such. This is the source of truth for
site copy: **do not invent credentials, metrics or claims beyond what appears below.**

---

## Baseline at the time of the interview

Google Search Console, 90 days to 2026-08-11 (`sc-domain:findsherpas.com`):

| Metric | Value |
| --- | --- |
| Clicks | 0 |
| Impressions | 123 |
| Distinct queries | 10 |
| Average position | 15.9 |
| URLs in sitemap | 9 |

The impressions came almost entirely from Google quality-rater-guideline phrases
("a query can have no more than three common interpretations") landing on the
query-interpretation framework page — research traffic, zero commercial intent.

Diagnosis: not a technical SEO problem. There was nothing to rank.

Other findings: `robots.txt` blocks `/report/`, so published audit reports are invisible to
Google; `/services` is indexed but absent from the sitemap (dead URL needing a redirect).

---

## 1. Where exactly did you do search?

All three are nameable publicly — this is Michal's CV, not client work.

| Company | Tenure | Role | Business |
| --- | --- | --- | --- |
| **Groupon** | 1.5 yrs | Product manager, search & relevance | Public US company, >$1B turnover, 14 markets, 100k+ SKUs |
| **Dr. Max** | 4 yrs | **Sole** product owner of search | 2nd biggest European pharmacy, 5 markets / 5 languages, €200M turnover, 100k+ SKUs |
| **Footshop** | 2 yrs | Product manager responsible for search | Fashion marketplace, 20 European markets, 15 languages, €50M turnover, 100k+ SKUs |

Roughly 7.5 years owning search across ~39 market–language combinations and three verticals.

## 2. What are the real numbers you personally moved?

- **Dr. Max** — ~12% improvement in search conversion rate, through relevance tuning.
- **Footshop** — zero-results cut by half, by introducing a strong synonym dictionary.
- **Footshop (Romanian)** — +4% search revenue, from fine-tuning declension and better query
  normalization.
- **Groupon** — introducing query suggestions decreased search abandonment.
  **Figures cannot be shared.** State the limit plainly rather than vaguely implying a number.

## 3. What did you do with your own hands, versus direct?

> "I did all of the above except writing code (which now I actually do using Claude Code)."

"All of the above" = synonym dictionaries, stopwords and normalization rules; ranking
configuration (boosts, attribute weights, tie-breakers, merchandising rules); index and schema
design (indexed fields, analyzers, tokenizers); querying raw search logs; building relevance test
sets and scoring result quality; designing and reading out A/B tests on ranking changes.

Positioning consequence: a **hands-on practitioner** who thinks like a product manager, not a
strategic advisor who delegated the work.

## 4. Which two or three are you genuinely elite at?

Strong at 2, 3, 4, 5 and 6 below. **#2 and #3 are the strongest** — "most companies don't know
how to do [these] properly."

1. Synonyms / stopwords / normalization
2. **Ranking configuration** ← strongest
3. **Index & schema design** ← strongest
4. Log analysis — finding failing queries in raw data
5. Relevance test sets and result scoring
6. A/B testing ranking changes and reading results

## 5. What do companies get wrong, and what do you do instead?

They don't do the full workflow:

1. Get the right data as searchable attributes
2. Deep query analysis to understand what people search for
3. **Classify the queries into specific groups**
4. **Fine-tune the relevance for each group**
5. **Properly A/B test**

The claim with teeth: most teams do steps 1 and 4 and skip 2, 3 and 5. Query classification and
A/B validation are the missing middle, which is why tuning never sticks.

## 6. Should the automated audit engine be the public differentiator?

**Option B — method public, machine private.**

Describe it publicly as structured relevance evaluation against a scored test set. Do **not**
reveal that it is automated or LLM-judged. Reason: paying clients get a deliberately "10x better
and more sophisticated" version, and Michal does not want it devalued as "just AI."

This resolves the open question flagged in `PRODUCT.md`.

## 7. How much has it been run, and on whom?

- ~**25 sites** audited end-to-end. Output personally reviewed for all of them.
- **None were paying clients.**
- Verticals: fashion, home & decor, electronics, sporting goods, baby.
- Markets: GB, NL, SWE, DEN, GER, SUI.
- Runs are stored in the CRM.

Note: only **8** runs have scored `_data.json` on disk in this repo; `report_slugs.json` lists
**14** published reports. The remaining runs' underlying data is in the CRM or unrecovered.

## 8. Can the 25 audits become a public benchmark study?

Yes, with conditions:

- **Anonymity: vertical + market labels only** ("a UK sporting goods retailer"). Sites are
  **not** to be named.
- All data was gathered **purely from public-facing sites** — scraped, no client data, no API
  access, no logins. Publishing is therefore clear.
- Named `/report/*` pages stay **noindexed permanently** and function as private outbound
  artifacts, not public content.

## 9. What has outreach produced?

> "Nothing, I haven't started outreach yet."

**Critical context:** there are zero customers because there is zero outreach and zero traffic —
not because the website was failing to convert. No website converts an audience of nobody. Any
site work must be paired with a distribution plan.

The 25 audited sites are already 25 warm outbound targets with a personalised artifact attached.

## 10. Pricing

> "I don't want to show any prices, this will be a boutique agency where I will consult for them."

No public pricing. High-touch, personally delivered. The site's job is credibility with a small
number of the right people, not lead volume or checkout.

The Starter / Growth / Enterprise Stripe tiers are **deprecated legacy** and are to be ignored
and removed.

## 11. Which channels?

**Outbound primary. Content a smaller secondary source.**

Consequence: the site is a credibility destination for someone who has just received an email
from Michal. It must survive a sceptical 90-second check by a Head of Product who has never
heard of him. It is not a discovery engine.

## 12. Who is the target?

- **Geography** — Western/Northern Europe + UK
- **Company size** — €10–100M revenue per year
- **Buyer** — any of Head of Product, Head of Ecommerce, Head of Digital, CTO
- **Awareness** — must work for teams who know their search is broken *and* those who don't

The last point is the hardest constraint: unaware buyers don't respond to "your search is
broken," so the page needs an early **demonstration** rather than an argument.

## 13. Who do you lose to?

1. **The search vendor itself** — conflicted; will never say the problem is the configuration.
2. **Engineers who understand the tech but not relevance** — can tune a query DSL, have never
   classified queries by intent or A/B tested a ranking change. This is the sharpest wedge.
3. **No budget allocated** — nobody has priced the cost of bad ranking, so it never becomes a
   line item.

## 14. How much can be changed?

- **Name** — keep "Find Sherpas."
- **Voice** — rewrite from "we" to **"I"**, with name, face and CV.
- **Design** — complete revamp. The existing design was called "very AI slop."
- **Pages** — all changeable, **except the blog articles, which must be kept.**

---

## Decisions taken from the interview

**Direction: personal authority as the foundation, the anonymized benchmark study as the
flagship, public teardowns as the ongoing content unit.** Chosen over a CV-only site (too easily
matched by any credible consultant) and over a heavy interactive "instrument" site (risks
exposing the private pipeline).

**Dataset:** aggregate all available runs into the benchmark before launch.

**Site structure agreed:** `/` · `/benchmark` (flagship) · `/method` (absorbs both `/frameworks`
pages) · `/about` · `/writing` (blog preserved) · `/contact` (replaces `/book-a-call`) ·
`/report/*` (noindexed, private outbound artifacts).
Cut: `/search-check`, `/case-studies`, `/stripe/*`, `/services` (redirect).

**Call to action:** "Send me three queries from your search that feel wrong, and what you
expected to see" — replacing "Book a call," which asked maximum commitment from a stranger.

---

## Benchmark findings from the 8 runs with scored data

Six capabilities, ~60 real queries per site, scored against customer intent:

| Capability | Critical | Moderate | Minor | Pass |
| --- | ---: | ---: | ---: | ---: |
| Language understanding | 6 | 2 | 0 | 0 |
| Shopping context | 6 | 2 | 0 | 0 |
| Filters & constraints | 6 | 2 | 0 | 0 |
| Product discovery | 2 | 6 | 0 | 0 |
| Typo tolerance | 2 | 5 | 0 | 1 |
| Brand & model search | 1 | 2 | 2 | 3 |

**7 of 8 sites carried at least one Critical failure.** The one capability most sites pass is
brand and model search — precisely the query type vendors demo. That contrast is the headline.

### Real failures worth quoting (unedited, from the runs)

- `keep drinks cold at the beach` → four identical *Beach* Camp Collar **Shirts**. The engine
  matched "beach" and dropped the intent. (Outdoor & apparel retailer, US.)
- `waterprooftrousers` → a Rab **jacket**, a kit bag, two pairs of **socks**. The compound was
  never split. (Outdoor retailer, UK.)
- `walkinboots` → three pairs of **socks** and a kit bag. (Outdoor retailer, UK.)
- `durable walking boots` → **"Sorry, no products matched"**, with a suggestion to check
  spelling — on a retailer whose own navigation contains a Footwear category. Real screenshot on
  file. (Outdoor retailer, UK.)

---

## Rejected design directions, and why

Recorded so they are not proposed again.

1. **Research note** (warm cream, high-contrast serif, hairline rules) — rejected: generic.
2. **Instrument** (near-black, monospace, single bright accent) — rejected: generic.
3. **Editorial contrast** (huge grotesque, serif body, black on white) — rejected: generic.

All three were the standard AI-default design clusters rather than choices derived from the
subject.

4. **Result Set / "wrong highlight"** — accent yellow used only to mark what the engine matched.
   Rejected: still read as a document about search, "very boring."
5. **Wireframe loop with line-art product glyphs** — rejected: looked like a mockup prototype.
6. **Annotated real screenshot with the brand redacted** — rejected: "that's not it."

**Accepted:** a Remotion-rendered animation of a realistic but fictional retailer ("NORTHAM"),
showing a customer typing `black dress for winter wedding` and receiving sundresses, leggings and
a ceramic vase, before the results resolve into black occasion dresses. Built in
`remotion/`, output at `public/video/search-loop.webm`.

Principle established: **search is abstract, so the site must show the failure rather than
describe it.**
