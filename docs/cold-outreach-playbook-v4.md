# Find Sherpas — Cold Outreach Playbook v4 (Boutique Edition)

> Source: FindSherpas_ColdOutreachPlaybook_v4.docx  
> Imported: April 2026  
> Author: Michal Pekarcik

---

## Start Here: Boutique Reality Check

This playbook was designed to scale. You don't need scale — you need **2–3 excellent clients**.

### Your Actual Target Numbers

| Stage | Boutique Target | Notes |
|---|---|---|
| Companies researched & audited | 30–50 total | Not per month — total. Pick carefully. |
| Sequences launched | 30–50 total | 5–10 per week over 6–10 weeks |
| Positive replies (8–12%) | 3–6 replies | Quality targeting raises this significantly |
| Calls booked (50% of replies) | 2–4 calls | The audit does most of the selling before the call |
| Clients signed (60–70% of calls) | 2–3 clients | This is your goal — stop here, deliver well, get referrals |

### Your 90-Day Roadmap

| Phase | Weeks | Focus | Output |
|---|---|---|---|
| Setup | 1–2 | Deliverability infrastructure, profiles, CRM, first 20-company prospect list | Ready to send |
| First Wave | 3–6 | Launch 20–25 sequences. Observe what language resonates. Refine Email 1. | First replies, first calls |
| Close Wave 1 | 7–9 | Follow up on warm leads, run discovery calls, close first client | Client #1 signed |
| Second Wave | 8–11 | 20–25 more sequences with refined copy and ICP from wave 1 learnings | Client #2 signed |
| Third Wave | 10–13 | Final push, referrals from existing clients, inbound from LinkedIn | Client #3 signed |

### What to Skip (Overkill for boutique scale)

- Inbox warm-up ramp table (you will never reach 75/day)
- A/B testing framework with statistical thresholds
- Sales Navigator ($99/month)
- LinkedIn 'at scale' section and InMail strategy
- Multi-contact same company protocol

### What to Pay Full Attention To

- **Every word of the email copy in the sequences**
- The Tiered Deliverable Model and the 2-page exec summary (Appendix A)
- The Reply Playbook and Post-Summary Nurture
- The Discovery Call Framework and Post-Call Protocol
- Appendix A and B (exec summary + forwardable brief templates)
- Legal compliance basics

---

## Part 0: Pre-Launch Technical Setup

> Do not send a single cold email until all items here are complete.

### Email Infrastructure

1. Set up a **separate outreach subdomain** — never send cold email from your primary domain.
   - Use `outreach.findsherpas.com` or `mail.findsherpas.com`
2. Configure **SPF, DKIM, and DMARC** records before sending anything
   - SPF: `v=spf1 include:sendgrid.net ~all`
   - DKIM: set up through your sequencing tool (Instantly, Lemlist, or Apollo)
   - DMARC: start with `p=none` for monitoring
3. Verify all three with **MXToolbox** before sending

### Inbox Warm-Up

- Week 1: Warm-up tool only. No outreach.
- Week 2: Warm-up + 5–8 real sequences. Monitor spam folder daily.
- Week 3+: Up to 10–15 sequences per week.
- Keep bounce rate below 2%.

### Legal Compliance

**CAN-SPAM (US)**
- Subject lines must not be deceptive
- Physical mailing address in every email
- Clear opt-out in every email
- Honor opt-out within 10 business days

**GDPR (EU/UK)**
- Use Legitimate Interest (LI) basis — document it
- Include company name, contact's right to opt out in every email
- Store permanent record of all opt-outs in CRM

**CASL (Canada)**
- Need implied or express consent
- Implied consent: prospect has published email publicly for business purposes
- Include opt-out + physical address in every email
- When in doubt, skip Canadian contacts

**Opt-out line (use this, not "unsubscribe"):**
> P.S. If you're not the right person for this, or you'd simply prefer I stop reaching out, just let me know and I'll take you off my list.

**Full footer template:**
```
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
[Physical address — required for CAN-SPAM]
P.S. If you'd prefer I stop reaching out, just say so and I'll remove you from my list.
```

### Boutique Tool Stack

| Tool | Option | Est. Cost/Month |
|---|---|---|
| Sequencing + warm-up | Instantly Starter | $37 |
| Email verification | Hunter.io Free / Paid | $0–49 |
| CRM | HubSpot Free | $0 |
| Video (optional) | Loom Free | $0 |
| Prospect research | LinkedIn Free + Apollo Free | $0 |
| **Total** | | **$37–86** |

---

## Part 1: Strategic Foundation

### The Audit-Led Outreach Model

Your LLM-powered scoring tool runs a custom search audit for each prospect before you reach out. By the time they receive your first email, you have already done the work. You are not pitching — you are delivering.

### The Tiered Deliverable Model

| Tier | Deliverable | When to Offer |
|---|---|---|
| 1 — Cold Hook | 2-page Executive Summary | Email 1 — offered as the immediate CTA |
| 2 — On Interest | Full 39-page Technical Audit | After they reply or agree to a call |
| 3 — Post-Call | 39-page Audit + 2-week fix roadmap walkthrough | After discovery call to close engagement |

### ICP Segmentation

| | Tier 1 | Tier 2 |
|---|---|---|
| Revenue | $20M–$60M | $60M–$200M |
| Buyer | CEO or Founder | VP E-Commerce, VP Product, or CTO |
| Sales cycle | 3–6 weeks | 6–16 weeks |
| Best sequence | B or C | A or B |

### Trigger-Based Prospect Prioritization

- New VP E-Commerce or VP Product hire (within 90 days)
- Recent platform migration (Shopify Plus, Salesforce Commerce Cloud, MACH)
- Active job posting for 'Site Search Engineer' or 'Search Relevance'
- Recent funding round
- Recent catalog expansion (new categories, cross-border launch)

### Personalization Variables

| Variable | Description | Example |
|---|---|---|
| [First Name] | Recipient's first name | Thomas |
| [Brand] | Company name | Shop Apotheke |
| [Score] | X of 6 capabilities passed | 0/6 |
| [Top3Rate] | % where best result IS in top 3 | 38% |
| [Outside3Rate] | % where best result is NOT in top 3 (= 100 − Top3Rate) | 62% |
| [Avg Position] | Average best result position | #6 |
| [Worst Query] | Single most dramatic failing query | coll |
| [Worst Pos] | Position of best result for worst query | #15 |
| [Wrong Product] | What appeared at #1 for worst query | pureSGP Kollagen Peptide |
| [Cap Count] | Number of capabilities rated Critical | 4 |
| [Title] | Recipient's job title | VP E-Commerce |

> **POLARITY REMINDER**: [Top3Rate] is LOW for poorly performing search. [Outside3Rate] is the inverse (high). Never mix them up.

### Send Timing

- Best days: **Tuesday, Wednesday, Thursday**
- Best times: **7–9am or 4–6pm** in recipient's time zone
- Avoid: Dec 20–Jan 3, national holidays, Q4/Black Friday

### Before-You-Send QA Checklist

- [ ] Audit is complete, human-reviewed, accurate for this specific prospect
- [ ] All [VARIABLES] populated — Email 1 requires: [Score], [Outside3Rate], [Worst Query], [Worst Pos]
- [ ] [Top3Rate] and [Outside3Rate] polarity is correct (not swapped)
- [ ] Subject line variant selected
- [ ] LinkedIn connection request drafted and scheduled for Day 2
- [ ] Social proof line selected and appropriate for this prospect's vertical
- [ ] Opt-out line present in email footer
- [ ] Sequence paused on reply — CRM rule is active before first send

### THE ONE RULE

> The moment a prospect replies — stop the sequence immediately and respond as a human. Positive, negative, or referral — it doesn't matter. Respond within 2 hours during business hours.

---

## Part 2: The Three Sequences

- **Sequence A — Direct & Data-Driven**: Numbers first. Best for VP/CTO (Tier 2)
- **Sequence B — Consultative & Warm**: Peer-to-peer practitioner tone. Best for CEOs, Founders, Tier 1
- **Sequence C — Bold & Provocative**: Pattern interrupt. Best for founders and growth operators

Each sequence = **5 email touches + 2–3 LinkedIn touches = 7–8 actions over 16–17 days**.

---

## Sequence A — Direct & Data-Driven

| Day | Channel | Action |
|---|---|---|
| Day 1 | Email | Email 1 — Scorecard Hook |
| Day 2 | LinkedIn | Connection Request |
| Day 3 | LinkedIn | Soft touch: Like/comment |
| Day 4 | Email | Email 2 — Specific Failure + Social Proof |
| Day 7 | LinkedIn | DM — reference emails, offer exec summary |
| Day 10 | Email | Email 3 — Benchmark Gap + Objection Pre-emption |
| Day 16 | Email | Email 4 — Hard Breakup |

**Email 1 — Day 1**
```
Subject: [Brand]: [Score] search capabilities passed

Hi [First Name],

I ran [Brand]'s site search through 40 realistic customer queries
last week using our scoring tool.

The results:
  — [Score] of 6 core capabilities passed
  — [Outside3Rate]% of searches: best result outside the top 3
  — Searching "[Worst Query]" requires scrolling to position
    [Worst Pos] to find the right product

Search users convert at 1.8–3x the rate of browsers. When search
misfires, that multiplier disappears — and the revenue with it.

I put together a full 39-page audit with a prioritized fix roadmap.
Happy to send you the 2-page executive summary now — and walk
through the full report if it's useful.

Worth sending?

Michal Pekarcik
Founder, Find Sherpas
findsherpas.com

P.S. The top 3 fixes alone are usually enough to make the call
worthwhile — the 39 pages are there if you want the depth.
If you'd rather I stop reaching out, just say so.
```

**LinkedIn Connection Request — Day 2**
```
Hi [First Name] — I've been doing e-commerce search audits and
[Brand]'s site caught my attention. Would love to connect.
```

**Email 2 — Day 4**
```
Subject: The "[Worst Query]" problem on [Brand]

Hi [First Name],

Quick follow-up.

Most striking finding from your audit: searching "[Worst Query]"
on [Brand] returns [Wrong Product] at #1. The right product?
Buried at position [Worst Pos].

That's a ranking failure, not a catalog failure — you have
the right products, they're just not surfacing correctly.

I worked through the same configuration pattern for a mid-market
health & beauty retailer with a similar catalog. Search CVR
improved 34% within 6 weeks of the fix.

This pattern appears across [Cap Count] capabilities in [Brand]'s
audit. It's fixable, usually in 2–4 weeks.

Is [specific day] at [time] open for 30 minutes?

Michal

P.S. This ranking pattern repeats across [Cap Count] of the 6
capabilities I tested — not just the one query above.
```

**LinkedIn DM — Day 7**
```
Thanks for connecting, [First Name]. I sent a couple of emails
about [Brand]'s search audit — wanted to make sure they
didn't get lost.

The headline: [Score]/6 capabilities tested are failing.
Happy to send the 2-page exec summary if useful.
```

**Email 3 — Day 10**
```
Subject: [Brand] vs. the industry benchmark

Hi [First Name],

One more data point:

  Industry target (Baymard Institute, 2023):  80%+ in top 3
  [Brand]'s current score:                    [Top3Rate]%

This applies regardless of your current platform — Algolia,
Klevu, Searchspring, Elasticsearch, or native Shopify. These
are ranking configuration issues, not infrastructure problems.
No platform rebuild required.

Search users are roughly 30% of traffic but generate a
disproportionate share of revenue. Every failed search is a
customer who got the wrong result — or left.

Should I send the 2-page exec summary so you can review it
before we connect?

Michal

P.S. Happy to answer any questions over email if 30 minutes
feels premature right now.
```

**Email 4 — Day 16 (Breakup)**
```
Subject: Closing the loop on [Brand]

Hi [First Name],

My last note on this.

If you'd like the audit: reply 'send it' and I'll drop the link
in your inbox — 39 pages, 40 queries tested, prioritized
roadmap, built specifically for [Brand]. No call required.

If search isn't a focus right now, no problem. The door
stays open.

Michal

P.S. If someone else owns site search at [Brand],
a redirect is just as welcome.
```

---

## Sequence B — Consultative & Warm

| Day | Channel | Action |
|---|---|---|
| Day 1 | Email | Email 1 — Practitioner Opener |
| Day 2 | LinkedIn | Connection Request |
| Day 3 | LinkedIn | Soft touch: Comment on relevant post |
| Day 5 | Email | Email 2 — Customer Experience + Forwardable Offer |
| Day 7 | LinkedIn | DM — reference emails, offer exec summary |
| Day 11 | Email | Email 3 — Direct Question + Social Proof |
| Day 17 | Email | Email 4 — Leave the Report |

**Email 1 — Day 1**
```
Subject: Something I noticed about [Brand]'s search

Hi [First Name],

I spent a few years building and optimizing search at scale
before starting Find Sherpas — and I have a habit of noticing
things others miss.

I ran [Brand]'s search through a structured audit last week.
[Score] of 6 core capabilities aren't working as intended.

The products your customers want are there — they're just not
ranking correctly.

I put together a 2-page executive summary with the key findings.
Happy to send it over now — no call required for that.

Worth sending?

Michal Pekarcik
Founder, Find Sherpas
findsherpas.com

P.S. If you'd prefer the full 39-page technical audit, that's
available too — the summary is just faster to review first.
If you'd rather I stop reaching out, just let me know.
```

**Email 2 — Day 5**
```
Subject: What [Brand]'s customers are actually experiencing

Hi [First Name],

To make this concrete:

A customer visits [Brand] and searches "[Worst Query]".
They see [Wrong Product] at #1.
What they were looking for is at position [Worst Pos].

Most customers in that situation scroll briefly, get frustrated,
and either buy the wrong thing or leave.

You have the right products. The search engine just isn't
ordering them correctly.

If you're not the right owner for search at [Brand], I've put
together a 1-page brief that's easy to forward to whoever is.
Happy to send that instead.

Worth 30 minutes to look at the full findings?

Michal

P.S. This ranking pattern repeats across [Cap Count] capability
areas — the query above is just the most dramatic example.
```

**LinkedIn DM — Day 7**
```
Hi [First Name], I sent a couple of emails about [Brand]'s
search — wanted to make sure they reached you.

Main finding: [Score]/6 capabilities failing. I can send a
2-page summary or a 1-page version you can forward internally.
Either useful?
```

**Email 3 — Day 11**
```
Subject: Is search on [Brand]'s roadmap this year?

Hi [First Name],

Genuine question: is improving search conversion something
you're looking at in 2026?

I ask because I recently worked through the same configuration
issue with a similar-size retailer — their search CVR improved
34% in the first 6 weeks without touching the platform.

This applies regardless of your current search tool —
Algolia, Klevu, or native. It's a configuration fix, not
a platform switch.

If yes — I can send the 2-page summary and we go from there.
If no — completely fine, and I'll stop reaching out.

Michal

P.S. Happy to answer any questions over email if a call
feels like too much right now.
```

**Email 4 — Day 17**
```
Subject: Leaving this for you

Hi [First Name],

Last note from me.

[Brand]'s search audit is complete — 39 pages, 40 queries,
prioritized recommendations. It's yours whether or not we
ever speak. Reply 'send it' and I'll drop the link.

If search is someone else's domain at [Brand],
a name or redirect is just as welcome.

Wishing [Brand] the best,
Michal
```

---

## Sequence C — Bold & Provocative

| Day | Channel | Action |
|---|---|---|
| Day 1 | Email | Email 1 — The Verdict |
| Day 2 | LinkedIn | Connection Request |
| Day 3 | LinkedIn | Soft touch |
| Day 4 | Email | Email 2 — Revenue Frame + Social Proof |
| Day 6 | LinkedIn | DM — ultra-short TLDR |
| Day 9 | Email | Email 3 — Industry Context + Objection |
| Day 13 | Email | Email 4 — Hard Stop |

**Email 1 — Day 1**
```
Subject: [Brand]'s ranking configuration is leaking revenue

Hi [First Name],

I ran [Brand]'s site search through 40 real customer queries.

  [Score]/6 core capabilities:   failing
  Best result outside top 3:      [Outside3Rate]% of searches
  Worst case:                     "[Worst Query]" — right
                                  product at position [Worst Pos]

This isn't a platform problem. The catalog has the right products.
The ranking configuration isn't surfacing them correctly.

I put together a 39-page audit. Want the 2-page version now?

Michal Pekarcik
Find Sherpas | findsherpas.com

P.S. The full report is yours after a 30-minute call — plenty
to discuss just from the top 3 fixes.
If you'd rather I stop reaching out, just say so.
```

**Email 2 — Day 4**
```
Subject: The ranking problem on [Brand]

Hi [First Name],

Here's what the audit surfaced:

[Brand] has the right products. The issue isn't your
platform — it's that the platform's out-of-the-box defaults
aren't tuned for your specific catalog structure. The ranking
isn't surfacing the right products in the right order.

Example: "[Worst Query]" — right product at position [Worst Pos],
buried behind [Wrong Product] and others.

I fixed the same configuration pattern for a mid-market
retailer with a similar catalog size — search CVR improved
34% within 6 weeks. No platform change required.

This is fixable. 2–4 weeks. The audit has the roadmap.

30 minutes?

Michal

P.S. [Cap Count] of 6 capabilities tested have critical
ranking failures — not just the query I highlighted.
```

**LinkedIn DM — Day 6**
```
[First Name] — sent two emails about [Brand]'s search.
TLDR: [Score]/6 failing, [Outside3Rate]% of queries burying
the best result. Summary ready to share — useful?
```

**Email 3 — Day 9**
```
Subject: 70% of e-commerce sites have this problem. [Brand] is one of them.

Hi [First Name],

Baymard Institute (2023): 70% of e-commerce sites can't handle
basic search variations — typos, partial queries, synonyms.

[Brand] falls into that category. The gap between where you
are and best-in-class is smaller than you'd think.

Worth noting: this applies regardless of your search platform.
Algolia, Klevu, Constructor, Searchspring — all produce these
patterns when ranking configuration isn't tuned. It's not
a vendor problem.

I fix this specifically. Not as a service line inside a broader
engagement — as the whole focus.

Full audit. Full roadmap. 30 minutes.

Ready when you are.

Michal

P.S. Happy to send a 2-page summary if a call feels
like too much right now.
```

**Email 4 — Day 13**
```
Subject: Last one, [First Name]

Not going to pitch again.

If [Brand]'s search conversion ever becomes a priority —
the audit is waiting. 39 pages, specific to [Brand].

Reply 'send it'.

Michal
```

---

## Part 6: LinkedIn Playbook

### Profile (Must-Have Before Day 1)

- Professional headshot
- Customized URL: `linkedin.com/in/michalpekarcik`
- Headline: `On-site search optimization for e-commerce | Find Sherpas`
- About/Summary: 150–200 words, first-person, explains what you do and for whom

### Soft Touch Strategy (Day 3)

1. If prospect posted in last 14 days → Like or react to their post
2. If they haven't posted recently → Like a post from their company page
3. If neither is active → View their profile (they get a notification)

### LinkedIn DM Principles

- Under 3 sentences
- Always reference the email thread
- Offer the 2-page summary as CTA — never ask for a call in a cold DM
- If they accept connection but don't reply in 24h: send the DM once
- If they don't accept by Day 7: skip DM and continue with Email 3

---

## Part 7: Reply Playbook

| Reply Type | Action | Template |
|---|---|---|
| Positive — 'Interested' | Stop sequence. Send 2-page exec summary. Follow up in 48h. | 'Great to hear — I'll send the 2-page summary now. Would [day] or [day] work for 30 minutes?' |
| Soft Positive — 'Send summary' | Stop sequence. Send summary. Follow up in 48h. | 'Here's the link: [link]. Happy to send the full 39-page audit as well. Does [day] work for a quick walkthrough?' |
| Referral | Thank them. Email named contact immediately. Reference referral. | 'Thank you — I'll reach out to [Name] directly and mention your name.' |
| Negative | Thank them. Remove. Log reason. Do not follow up. | 'Completely understood — I appreciate the response. I'll remove you from my list.' |
| Delayed | Log date. Create re-engagement reminder. | 'Noted — I'll check back in [month]. I'll keep the [Brand] audit on file.' |
| Platform Reply | Validate platform. Redirect to config layer. | '[Platform] is a strong choice. The audit surfaced issues in the ranking configuration layer — not the platform. Worth a 20-minute look?' |

### Report Delivery Protocol

1. Send a **hosted link** (Google Drive, Notion) — never a PDF attachment
2. Send **2-page exec summary first**; full 39-page on request
3. Follow up **48 hours** after sending
4. If no response: one more note in 5 days, then close

### Post-Summary Nurture Sequence

| Day | Action |
|---|---|
| Day 0 | Send 2-page exec summary with context |
| Day 2 | Follow-up: 'Did you get a chance to look at it?' |
| Day 7 | Value-add touch: share one additional insight not in the summary |
| Day 14 | Final close: 'Last note on this — audit is here whenever timing shifts.' |

---

## Part 8: Re-Engagement Sequence

Trigger 90 days after breakup email for prospects who: (a) did not unsubscribe, (b) opened at least two emails, or (c) replied 'follow up later'.

**Re-Engage Email 1**
```
Subject: Checking back in on [Brand]'s search

Hi [First Name],

I reached out a few months back about [Brand]'s search audit.
I said I'd leave the door open — this is me checking in.

I ran a quick re-check on [Brand]'s search last week.
The core findings from [Month] are still current —
[Outside3Rate]% of queries still have the best result
outside the top 3. The "[Worst Query]" issue is unchanged.

If now is a better time, the 2-page summary is ready to send.
Just reply.

Michal
```

**Re-Engage Email 2**
```
Subject: Is timing better now for [Brand]?

Hi [First Name],

Short one: has search moved up the priority list at [Brand]?

If yes — the audit is ready. Reply 'yes' and I'll send
the full report.

If not — no problem, I won't keep checking in.

Michal
```

---

## Part 9: Video Prospecting Variant (Loom)

Use for: Tier 2 accounts, prospects who opened emails but didn't reply, strong trigger signals.

**The Loom Formula (60 seconds):**
1. Open: 'Hi [First Name], quick screen share of something I found on [Brand]'s search — takes 60 seconds.'
2. Screen share: Type [Worst Query] into [Brand]'s search. Let wrong results load.
3. Narrate: what the customer was searching for vs. what they see.
4. Show scorecard briefly.
5. Close: 'The full audit has [Cap Count] issues like this with a fix roadmap. Worth 30 minutes?'

**Do not drop Loom link directly in email** — ask permission first:
```
Subject: 60-second screen share on [Brand]'s search

Hi [First Name],

I recorded 60 seconds of what happens when a customer
searches "[Worst Query]" on [Brand]'s site.

Mind if I drop the link here?

Or if you'd rather just read: the right product shows
up at position [Worst Pos]. The full audit has [Cap Count]
issues like this with a prioritized fix roadmap.

Michal
```

---

## Part 10: Discovery Call Framework

### Opening (first 3 minutes)
> 'Thanks for making time, [First Name]. I've already done a lot of the diagnostic work before this call — the audit shows [Score]/6 capabilities failing. I want to walk you through the two or three findings that are most likely to matter to you, and then figure out whether there's a fit here.'

### Discovery Questions (minutes 3–15)
- 'Who owns search at [Brand] day-to-day — engineering, product, or e-commerce?'
- 'When did you last make changes to your search configuration?'
- 'Do you track search CVR or zero-results rate in your analytics?'
- 'Is there a specific search problem you've been aware of that hasn't been fixed yet?'
- 'What would need to be true for you to prioritize this in Q[X]?'
- 'What's your current tech stack for search?'

### Presenting Findings (minutes 15–25)
1. Scorecard summary: '[Score]/6 passed, [Outside3Rate]% outside top 3'
2. Most dramatic query failure — then ask: 'Does this align with complaints your merchandising team has been raising?'
3. Benchmark comparison — then ask: 'Does the gap feel like a surprise, or something you've sensed for a while?'
4. Top 3 prioritized fixes with effort and impact estimates

### Closing (final 5 minutes)
- 'Does this feel like the right time to move forward?'
- 'Would it make sense to put together a scoped proposal?'
- 'Who else would need to be in the room?'

### Post-Call Protocol (send within 2 hours)
```
Subject: Following up from our call — [Brand] search audit next steps

Hi [First Name],

Really appreciate the time today. A few things I'll
follow up on as discussed:

1. [Specific finding they found most relevant]
2. [Action item or question they asked]
3. [Next step agreed — proposal, additional info, etc.]

I'll put together [the scoped proposal] and send it over by [date].

Michal
```

---

## Part 11: Metrics Targets

| Metric | Target | Below This = Problem |
|---|---|---|
| Open Rate | Directional comparison only | Use only to compare variants |
| Reply Rate (all) | 15–25% | <8%: body copy or targeting issue |
| Positive Reply Rate | 5–12% | <3%: offer or ICP mismatch |
| Meeting Booked Rate | 30–50% | <20%: CTA or credibility issue |
| Audit-to-Call Rate | 60–80% | <40%: report quality or framing |

### Boutique Diagnostics (Pattern Reading)

After each wave of 10–15 sends:
- Replies positive or negative? → ICP or tone issue
- Opening but not replying? → Email 1 body or CTA is the problem
- Not opening at all? → Subject line is the problem
- Calls but not closing? → Discovery call needs work, not the emails
- Sequence C getting more pushback? → Move people to Sequence B

---

## Appendix A: 2-Page Executive Summary Template

**Page 1:**
- Header: [Brand] Site Search Audit — Executive Summary | Find Sherpas | [Month, Year]
- Section 1 — Capability Scorecard (6 capabilities: pass/fail table)
- Section 2 — Top 3 Most Impactful Failures (query → wrong result → right result)
- Section 3 — Benchmark Gap: '[Brand] returns best result in top 3 for [Top3Rate]% of queries. Industry: 80%+. Gap: [X] points.'

**Page 2:**
- Section 4 — Top 3 Prioritized Fixes (problem, recommended change, effort, impact)
- Section 5 — Next Step CTA: 'Book a 30-minute call: [calendar link]'
- Footer: Michal Pekarcik | Find Sherpas | findsherpas.com | Confidential — prepared for [Brand]

---

## Appendix B: 1-Page Internal Forwardable Brief Template

Designed to be forwarded by your contact to whoever owns search internally.

- Header: [Brand] Search Opportunity Brief | Prepared by Find Sherpas | [Month, Year] | Forwarded by [Contact First Name]
- Section 1 — What Was Found (2–3 sentences with specifics)
- Section 2 — Business Impact (3 bullet points with data)
- Section 3 — What Can Be Done (no platform rebuild required, 2–4 weeks)
- Section 4 — Contact: Michal Pekarcik | findsherpas.com | [calendar link]

> Key principle: this document must stand completely alone. The person receiving the forward has zero prior context.
