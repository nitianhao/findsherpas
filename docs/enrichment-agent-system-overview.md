# Ecommerce Lead Enrichment Agent --- System Overview

## Inputs

Two workbooks:

-   US_Ecommerce_Prospects_SiteSearch.xlsx
-   EU_Ecommerce_Prospects_SiteSearch.xlsx

Total companies: **877**\
Target roles per company:

-   CEO
-   Head of Product
-   Head of Ecommerce
-   Head of Growth / CMO

Total enrichment targets: **3,508 role slots**

------------------------------------------------------------------------

# Pipeline Architecture

## 1. Workbook Normalization

Module: src/enrichment/io/workbookService.ts

Responsibilities:

-   Normalize column structure
-   Handle regional differences
-   Create backups
-   Convert rows to normalized objects

------------------------------------------------------------------------

## 2. Task Planning

Module: src/enrichment/planning/taskPlanner.ts

Generates deterministic enrichment tasks.

Priority scoring considers:

-   Missing fields
-   Existing partial data
-   Role importance

------------------------------------------------------------------------

## 3. Website Discovery

Module: src/enrichment/discovery/companyWebsiteDiscovery.ts

Uses **Playwright** to visit:

-   About pages
-   Contact pages
-   Careers
-   Team pages
-   Impressum

Extracts:

-   emails
-   LinkedIn URLs
-   person candidates

Observation:\
Ecommerce sites rarely list leadership.\
Website scraping mainly helps **email discovery**.

------------------------------------------------------------------------

## 4. Search Discovery

Primary search provider:

**Brave Search API**

Module: src/enrichment/search/adapters/braveSearchAdapter.ts

Typical queries:

site:linkedin.com/in "Company Name" CEO\
site:linkedin.com/in "Company Name" "Head of Ecommerce"\
site:linkedin.com/in "Company Name" "Head of Product"\
site:linkedin.com/in "Company Name" "Head of Growth"

Produces:

-   LinkedIn candidate URLs
-   titles
-   snippets
-   ranking signals

------------------------------------------------------------------------

## 5. Identity Parsing

Module: src/enrichment/matching/identityParser.ts

Extracts:

-   person name
-   role hints
-   company matches
-   LinkedIn slug identity

Filters out noise such as:

-   product titles
-   marketing phrases
-   category names

------------------------------------------------------------------------

## 6. Candidate Ranking

Module: src/enrichment/matching/roleCandidateRanker.ts

Signals:

  Signal                 Score
  ---------------------- -------
  LinkedIn profile       +40
  Company match          +25
  Explicit role          +25
  Slug name match        +15
  Multiple search hits   +20

Penalties:

  Penalty            Score
  ------------------ -------
  No role evidence   -20
  LinkedIn post      -30

Role resolution output:

-   RESOLVED_STRONG
-   RESOLVED_PROBABLE
-   UNRESOLVED_WEAK
-   UNRESOLVED_NONE

------------------------------------------------------------------------

## 7. Email Inference

Modules:

-   emailPatternInference.ts
-   emailGenerator.ts
-   emailResolver.ts

Sources used:

-   observed emails from websites
-   domain pattern inference
-   fallback permutations

Typical patterns:

first.last@domain\
first@domain\
flast@domain\
firstlast@domain

Email confidence:

-   RESOLVED_PUBLIC
-   RESOLVED_INFERRED
-   WEAK
-   UNRESOLVED

Weak emails are **not written automatically**.

------------------------------------------------------------------------

## 8. Quality Gate

Module: src/enrichment/quality/personPlausibility.ts

Blocks false candidates such as:

-   Faherty Brand
-   Sustainable Dresses
-   Preisgekrönter Onlineshop

Positive signals:

-   2--3 name tokens
-   LinkedIn slug match
-   title case formatting
-   role evidence

Negative signals:

-   company name overlap
-   ecommerce keywords
-   marketing phrases
-   article/post titles

------------------------------------------------------------------------

## 9. Writeback Eligibility

Module: src/enrichment/quality/writebackEligibility.ts

Rules:

  Condition                    Action
  ---------------------------- ----------------
  Valid person + strong role   write name
  LinkedIn present             write LinkedIn
  Email strong/probable        write email
  Weak email                   block

Overwrite protection:

overwriteExisting = false

------------------------------------------------------------------------

# Automatic Writeback

Module: src/enrichment/writeback/workbookWriteback.ts

Writes only approved fields.

Dry run result:

14 approved writes

Actual writes applied:

  Type                Count
  ------------------- -------
  CEO names           4
  CEO LinkedIn        5
  Head of Product     1
  Head of Ecommerce   2
  Head of Growth      2
  Emails              0

Total safe writes: **14**

Backups created automatically before write.

Verification confirmed:

14/14 persisted correctly.

------------------------------------------------------------------------

# Manual Review System

Exports created:

docs/review-queue.csv\
docs/review-queue.md\
docs/review-queue.json

Total review items: **18**

Buckets:

  Bucket                                  Count
  --------------------------------------- -------
  EMAIL_INFERRED_WEAK                     9
  SEARCH_GOOD_LINKEDIN_BUT_ROLE_UNCLEAR   4
  ROLE_WEAK_WITH_CANDIDATE                3
  EXISTING_CELL_BLOCKED_NEW_VALUE         1
  EMAIL_UNRESOLVED_BUT_DOMAIN_KNOWN       1

------------------------------------------------------------------------

# Manual Review Workflow

Human review file:

docs/review-queue-for-human-review.csv

Reviewer fills:

humanDecision\
humanNotes

Allowed decisions:

-   APPROVE_CANDIDATE
-   APPROVE_ROLE_ONLY
-   APPROVE_ROLE_AND_LINKEDIN
-   APPROVE_EMAIL_ONLY
-   KEEP_EXISTING
-   REJECT_CANDIDATE
-   NEEDS_MORE_RESEARCH
-   SKIP

Then process:

npm run enrichment:review:process

Outputs:

docs/manual-review-approved-actions.json\
docs/manual-review-summary.md

Approved decisions can feed another writeback pass.

------------------------------------------------------------------------

# Current System Performance

Total companies: 877\
Total role targets: 3,508

Automatic safe writes:

14

Manual review opportunities:

18

Most promising unlock:

CEO email verification such as:

jocelyn.gailliot@tuckernuck.com\
dario.rendulic@manufactum.de\
cheryl.kaplan@mgemi.com

------------------------------------------------------------------------

# System Capabilities

The enrichment agent can now:

-   discover executives
-   extract LinkedIn profiles
-   infer email patterns
-   block bad candidates
-   write safely to Excel
-   generate review queues
-   process human decisions

This architecture mirrors internal enrichment pipelines used by
commercial lead data platforms.
