/**
 * Applies all stress-tested sequence template fixes to the live CRM (InstantDB).
 *
 * Run with:
 *   npm run crm:update-sequences
 *
 * Safe to re-run — saveSteps deletes and recreates steps atomically.
 */

import { readFileSync } from "fs";
import { resolve } from "path";

// Load .env.local before any module that reads env vars at init time
try {
  const envPath = resolve(process.cwd(), ".env.local");
  for (const line of readFileSync(envPath, "utf-8").split("\n")) {
    const eq = line.indexOf("=");
    if (eq > 0 && !line.startsWith("#")) {
      const key = line.slice(0, eq).trim();
      const val = line.slice(eq + 1).trim();
      if (key && !(key in process.env)) process.env[key] = val.replace(/^["']|["']$/g, "");
    }
  }
} catch { /* .env.local missing — assume vars are already in environment */ }

// ─── Sequence IDs (from crm-sequences-export.md) ────────────────────────────

const SEQ_A = "9fa450d1-1378-4b18-92ce-63a162de7ca6"; // Direct & Data-Driven
const SEQ_B = "d55b28f3-845d-4b5f-9cfa-4f2073cfb856"; // Consultative & Warm
const SEQ_C = "0cf47441-59b3-4397-97f8-379c2dc37a50"; // Bold & Provocative

// ─── Sequence A ──────────────────────────────────────────────────────────────

const seqASteps = [
  {
    step_order: 1,
    delay_days: 0,
    subject_template: "Quick question about {{brand}} search",
    body_template: `Hi {{first_name}},

I ran {{brand}}'s search through {{query_count}} real customer queries last week and one pattern stood out.

— {{outside_3_rate}}% of searches returned the best match outside the top 3
— Relevant products exist — they're just being outranked
— Search Quality Score: {{score}}/100

That's usually a ranking configuration issue, not a platform or catalog problem.

I put the report here:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Worth forwarding to whoever owns search?

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 2,
    delay_days: 3,
    subject_template: "{{worst_query}} on {{brand}}",
    body_template: `Hi {{first_name}},

Quick follow-up on the "{{worst_query}}" query.

{{wrong_product}} is showing at #1, while more relevant products are buried around position {{worst_pos}}.

Same ranking pattern repeats across {{cap_count}} critical capability groups I tested.

The report page has the query evidence and prioritized fixes:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Is search/ranking owned by you or someone else?

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 3,
    delay_days: 6,
    subject_template: "{{brand}} vs. benchmark",
    body_template: `Hi {{first_name}},

One more data point:

Baymard benchmark: 80%+ of searches should return the best match in top 3.
{{brand}} currently: {{top_3_rate}}% — a {{gap}}-point gap.

Interesting pattern across audits: single-word category queries push relevant products outside the top results — popularity signals end up outranking relevance.

{{search_platform_sentence}}

The report is here if useful:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Worth forwarding to whoever owns search?

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 4,
    delay_days: 6,
    subject_template: "{{brand}} — closing the loop",
    body_template: `Hi {{first_name}},

Last note. The {{brand}} audit is here:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

If someone else owns search at {{brand}}, the link is ready to forward.

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
];

// ─── Sequence B ──────────────────────────────────────────────────────────────

const seqBSteps = [
  {
    step_order: 1,
    delay_days: 0,
    subject_template: "Something I noticed about {{brand}}'s search",
    body_template: `Hi {{first_name}},

I ran {{brand}}'s search through {{query_count}} real customer queries last week and one result stood out.

{{outside_3_rate}}% of searches returned the best match outside the top 3. Relevant products exist — they're just being outranked.

I specialize only in fixing on-site search ranking for ecommerce teams — not a general consultant.

I put the report here:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Worth forwarding to whoever owns search?

Michal Pekarcik
Founder, Find Sherpas

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 2,
    delay_days: 4,
    subject_template: "What a customer sees on {{brand}}",
    body_template: `Hi {{first_name}},

To make it concrete — a customer searches "{{worst_query}}" on {{brand}}:

They see {{wrong_product}} at #1, while more relevant products are buried around position {{worst_pos}}.

The report page shows the query evidence and fixes:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

If search isn't your domain at {{brand}}, feel free to forward the link to whoever owns it internally.

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 3,
    delay_days: 6,
    subject_template: "Is search on {{brand}}'s roadmap?",
    body_template: `Hi {{first_name}},

Genuine question: is improving search conversion something you're looking at this year?

{{search_platform_sentence}}

If it is, the report is here:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Is search/ranking owned by you or someone else?

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 4,
    delay_days: 6,
    subject_template: "Leaving this with you, {{first_name}}",
    body_template: `Hi {{first_name}},

Last note.

If improving search conversion is something you return to, the {{brand}} findings are specific and waiting here:
{{report_url}}

If someone else at {{brand}} owns search, a name or redirect is just as welcome.

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
];

// ─── Sequence C ──────────────────────────────────────────────────────────────

const seqCSteps = [
  {
    step_order: 1,
    delay_days: 0,
    subject_template: "Saw something odd on {{brand}}",
    body_template: `{{first_name}},

I ran {{brand}}'s search through {{query_count}} real queries.

  {{outside_3_rate}}% of searches: best match outside top 3
  "{{worst_query}}": relevant products buried around position {{worst_pos}}
  Search Quality Score: {{score}}/100

Relevant products exist. Ranking is the issue.

I only fix on-site search ranking — that's the whole focus, not a side service.

Report:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Michal
Find Sherpas

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 2,
    delay_days: 3,
    subject_template: "{{brand}} query test",
    body_template: `{{first_name}},

Pattern worth flagging: single-word category queries on {{brand}} consistently push relevant products outside the top results. Popularity signals are outranking relevance.

"{{worst_query}}" is the sharpest example — {{wrong_product}} is shown at #1, while more relevant products are buried around position {{worst_pos}}.

Same pattern repeats across {{cap_count}} critical capability groups.

The query evidence is here:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Is search/ranking owned by you or someone else?

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 3,
    delay_days: 6,
    subject_template: "{{brand}} search result question",
    body_template: `{{first_name}},

Baymard (2023): 70% of ecommerce sites can't handle basic search variations — typos, partial queries, synonyms. {{brand}} is currently at {{top_3_rate}}% top-3 accuracy, {{gap}} points behind the 80%+ best-in-class threshold.

{{search_platform_sentence}}

Otherwise — report page and specific fixes:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
  {
    step_order: 4,
    delay_days: 4,
    subject_template: "Last one, {{first_name}}",
    body_template: `If {{brand}}'s search ever becomes a priority, the findings are waiting here:
{{report_url}}

It shows the exact queries/results, not a generic teardown.

If someone else owns search, happy to hand it to them instead.

Michal

--
Michal Pekarcik  |  Find Sherpas  |  findsherpas.com
Lucni 19, 130 00, Prague, Czech Republic`,
  },
];

// ─── Run ─────────────────────────────────────────────────────────────────────

async function main() {
  // Dynamic import ensures env vars are loaded before adminDb initializes
  const { saveSteps } = await import("@/lib/crm/queries/sequences");

  const sequences = [
    { id: SEQ_A, name: "A — Direct & Data-Driven", steps: seqASteps },
    { id: SEQ_B, name: "B — Consultative & Warm",  steps: seqBSteps },
    { id: SEQ_C, name: "C — Bold & Provocative",   steps: seqCSteps },
  ];

  for (const seq of sequences) {
    process.stdout.write(`Updating Sequence ${seq.name}... `);
    await saveSteps(seq.id, seq.steps);
    console.log("done");
  }

  console.log("\nAll sequences updated.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
