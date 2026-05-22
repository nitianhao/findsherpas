"""
Persona simulation HTML report — two-layer edition
Reads persona_simulation_combined.json (output of persona_simulation_aggregate.py)
and generates a self-contained HTML report for Redcare stakeholder presentation.

Layer 1: aggregate findings across 30 sessions
Layer 2: individual session cards (all 30)

Usage:
    python3 scripts/persona_simulation_report2.py
"""
from __future__ import annotations

import html as _html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMBINED_JSON = ROOT / "reports" / "persona_simulation" / "persona_simulation_combined.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PERSONA_LABELS = {
    "anxious_young_mother":        "Anxious Young Mother",
    "wellness_optimizer":          "Wellness Optimizer",
    "elderly_patient":             "Elderly Patient / Caregiver",
    "acute_self_treater":          "Acute Self-Treater",
    "alternative_medicine_seeker": "Alternative Medicine Seeker",
}

PERSONA_FIRST_NAMES = {
    "anxious_young_mother":        "Lena, 29 — Berlin",
    "wellness_optimizer":          "Mia, 34 — München",
    "elderly_patient":             "Werner, 71 — rural Bavaria",
    "acute_self_treater":          "Jonas, 31 — Hamburg",
    "alternative_medicine_seeker": "Petra, 48 — Baden-Württemberg",
}

PERSONA_SITUATION = {
    "anxious_young_mother": "11pm. Her 8-month-old daughter won't sleep. She needs something safe, natural, without a prescription.",
    "wellness_optimizer": "She knows exactly what she needs. KSM-66 extract, not generic ashwagandha. Laborgeprüft. Vegan certified. If the search returns pharma generics, she's gone.",
    "elderly_patient": "New medication list from yesterday's cardiology visit. He needs to reorder chronic meds. Exact pack sizes matter — he matches what his prescription says.",
    "acute_self_treater": "Sore throat since this morning. The Apotheke closed at 6pm. He's ordering for tomorrow morning delivery. No time for reformulations.",
    "alternative_medicine_seeker": "Her Heilpraktiker recommended a specific potency. She searches by potency and manufacturer, not by brand. If the engine can't parse D12, she leaves.",
}

PERSONA_STAKE = {
    "anxious_young_mother":        "A child's wellbeing and a mother's trust",
    "wellness_optimizer":          "€110 monthly basket — primary item to Amazon, rest stays",
    "elderly_patient":             "€45/month chronic medication reorder stream",
    "acute_self_treater":          "First impression and a one-time conversion",
    "alternative_medicine_seeker": "High-loyalty customer who buys multiple remedies per session",
}

PERSONA_ABANDON = {
    "anxious_young_mother":        "docmorris.de or the Apotheke at Hauptbahnhof tomorrow morning",
    "wellness_optimizer":          "amazon.de for the primary item; returns for secondary basket",
    "elderly_patient":             "calls shop-apotheke customer service — or drives to the Apotheke",
    "acute_self_treater":          "dm, Rossmann, or the 24h Apotheke at the station",
    "alternative_medicine_seeker": "apo-rot.de or weleda.de directly",
}

PERSONA_COLORS = {
    "anxious_young_mother":        "#7c3aed",
    "wellness_optimizer":          "#0284c7",
    "elderly_patient":             "#059669",
    "acute_self_treater":          "#dc2626",
    "alternative_medicine_seeker": "#d97706",
}

STATE_COLORS = {
    "FOUND":   ("#16a34a", "#dcfce7", "Found"),
    "PARTIAL": ("#b45309", "#fef3c7", "Partial"),
    "NOTHING": ("#dc2626", "#fee2e2", "Nothing"),
}

OUTCOME_CONFIG = {
    "CONVERTED":   ("#16a34a", "#dcfce7", "Converted"),
    "SPLIT_BASKET": ("#b45309", "#fef3c7", "Split basket"),
    "ABANDONED":   ("#dc2626", "#fee2e2", "Hard abandon"),
}

FAILURE_MODE_LABELS = {
    "anxious_young_mother":        ["Age-gating failure", "Rx contamination", "Brand not found"],
    "wellness_optimizer":          ["Spec mismatch", "Pharma flood", "Certification gap"],
    "elderly_patient":             ["Pack size mismatch", "Generic noise", "Brand variant gap"],
    "acute_self_treater":          ["Brand displacement", "Rx contamination", "Non-product results"],
    "alternative_medicine_seeker": ["Conventional flood", "Potency gap", "Latin name gap"],
}

FIX_TABLE = [
    {
        "title": "Symptom → product semantic mapping",
        "effort": "High",
        "impact": "Critical",
        "description": "Natural language symptom queries return no OTC products. Build a symptom synonym map (Halsschmerzen → Rachentherapeutika, Rückenschmerzen → NSAR/Wärmepflaster) and feed into Algolia synonym config with colloquial German variants.",
        "affects": ["anxious_young_mother", "acute_self_treater"],
    },
    {
        "title": "Structured attribute indexing (form, potency, pack size)",
        "effort": "High",
        "impact": "Critical",
        "description": "Queries with form (Kapseln, Tropfen, Zäpfchen), homeopathic potency (D6, C30), or pack size (150g, 60 Stück) return size-mismatched or wrong-form results. Add these as structured Algolia facets and boost form-match when keyword appears in query.",
        "affects": ["wellness_optimizer", "elderly_patient", "alternative_medicine_seeker"],
    },
    {
        "title": "Negation handling (ohne / kein / nicht)",
        "effort": "Medium",
        "impact": "High",
        "description": "Queries containing 'ohne [ingredient]' or 'kein [substance]' are treated as additive terms, not exclusions. Add negation tokenizer at query-rewrite time; map excluded token to result demotion or hard exclusion filter.",
        "affects": ["anxious_young_mother", "wellness_optimizer", "alternative_medicine_seeker"],
    },
    {
        "title": "OTC / Rx contamination filter",
        "effort": "Medium",
        "impact": "High",
        "description": "Symptom-led queries for acute self-treaters surface Rx products prominently. Implement OTC intent classifier for symptom queries. Demote Rx results, boost OTC. Highest friction point for Jonas across all sessions.",
        "affects": ["acute_self_treater"],
    },
    {
        "title": "Life-stage routing (Baby / Kinder / Säugling)",
        "effort": "Medium",
        "impact": "High",
        "description": "Infant and toddler queries surface adult products or return low-confidence results. Detect life-stage signals and apply an age-group filter at retrieval time. Block adult-only formulations from baby queries.",
        "affects": ["anxious_young_mother"],
    },
    {
        "title": "Brand rescue layer reliability",
        "effort": "Low",
        "impact": "High",
        "description": "When natural language and symptom queries fail, all personas fall back to brand search as a rescue layer. This layer is also failing (Viburcol, Otrivin, Mepore, Agnucaston). Audit brand-name synonyms in Algolia. Highest ROI per engineering hour.",
        "affects": ["anxious_young_mother", "elderly_patient", "acute_self_treater", "alternative_medicine_seeker"],
    },
    {
        "title": "Latin / scientific name recognition",
        "effort": "Low",
        "impact": "Medium",
        "description": "Withania somnifera, Passiflora incarnata, Vitex agnus-castus, Arnica montana — these return irrelevant or empty results. Add scientific name → product category mappings. This unlocks an entire persona segment (Petra).",
        "affects": ["alternative_medicine_seeker", "wellness_optimizer"],
    },
]


def esc(s) -> str:
    return _html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
:root{
  --primary:#e4002b;--fg:#0a0a0a;--muted:#6b7280;--border:#e5e5e5;
  --accent:#fff1f2;--secondary:#f9fafb;--bad:#dc2626;--warn:#d97706;
  --ok:#16a34a;--radius:0.75rem;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:15px;line-height:1.65;color:var(--fg);background:#fff;-webkit-font-smoothing:antialiased}
.page{max-width:960px;margin:0 auto;padding:0 36px 80px}
section{padding:52px 0;border-top:1px solid var(--border)}
section:first-of-type{border-top:none}
h1{font-size:2.5rem;letter-spacing:-0.03em;line-height:1.15;margin-bottom:14px;font-weight:800}
h2{font-size:1.5rem;margin-bottom:20px;font-weight:700;letter-spacing:-0.01em}
h3{font-size:1.05rem;font-weight:700;margin-bottom:10px}
p{margin-bottom:14px;color:var(--fg)}
a{color:inherit}
.label{font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--primary);margin-bottom:10px}
/* Cover */
.cover{padding:68px 0 56px}
.cover-meta{font-size:0.875rem;color:var(--muted);margin-bottom:32px}
/* Headline grid — 5 cells */
.headline-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:28px 0}
.hn{background:var(--secondary);border:1px solid var(--border);border-radius:var(--radius);padding:24px 18px;text-align:center}
.hn .n{font-size:2.9rem;font-weight:800;letter-spacing:-0.04em;line-height:1}
.hn .nl{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;margin-top:8px;color:var(--muted)}
.hn.bad .n{color:var(--bad)}
.hn.warn .n{color:var(--warn)}
.hn.ok .n{color:var(--ok)}
/* Hook */
.hook{background:var(--accent);border-left:4px solid var(--primary);padding:26px 30px;border-radius:6px;margin:28px 0;font-size:1.05rem;line-height:1.75}
/* Aggregate tables */
.agg-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin:28px 0}
.agg-block{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.agg-block-title{font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);padding:12px 16px;background:var(--secondary);border-bottom:1px solid var(--border)}
/* Heatmap table */
.heatmap{width:100%;border-collapse:collapse}
.heatmap th{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);text-align:left;padding:10px 14px;border-bottom:1px solid var(--border);background:var(--secondary)}
.heatmap td{padding:9px 14px;border-bottom:1px solid var(--border);font-size:0.85rem;vertical-align:middle}
.heatmap tr:last-child td{border-bottom:none}
.cell-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}
/* Friction bars */
.friction-row{display:grid;grid-template-columns:160px 1fr 40px;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--border)}
.friction-row:last-child{border-bottom:none}
.friction-bar-wrap{background:var(--secondary);border-radius:20px;height:8px;overflow:hidden}
.friction-bar{height:8px;border-radius:20px;background:var(--bad)}
/* Category failure table */
.cat-table{width:100%;border-collapse:collapse}
.cat-table td,.cat-table th{padding:8px 14px;border-bottom:1px solid var(--border);font-size:0.85rem}
.cat-table th{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);background:var(--secondary)}
.cat-table tr:last-child td{border-bottom:none}
/* Session cards */
.session-grid{display:flex;flex-direction:column;gap:32px}
.session-card{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.session-header{display:grid;grid-template-columns:1fr auto;align-items:start;gap:20px;padding:22px 28px;background:var(--secondary);border-bottom:1px solid var(--border)}
.session-persona-dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:8px;vertical-align:middle;flex-shrink:0}
.session-name{font-size:1.05rem;font-weight:800;margin-bottom:3px}
.session-theme{font-size:0.78rem;color:var(--muted);margin-bottom:10px;letter-spacing:0.02em}
.session-situation{font-size:0.88rem;color:var(--fg);line-height:1.6;font-style:italic}
.session-stake{font-size:0.78rem;color:var(--muted);margin-top:5px}
.outcome-badge{font-size:0.74rem;font-weight:700;padding:6px 14px;border-radius:20px;white-space:nowrap;text-align:center;letter-spacing:0.02em}
.session-body{padding:28px 28px 22px}
/* Timeline */
.timeline{position:relative;display:flex;flex-direction:column;gap:0;margin-bottom:24px}
.tl-step{display:grid;grid-template-columns:44px 1fr;gap:0;position:relative}
/* vertical connector line between steps */
.tl-step:not(:last-child) .tl-rail::after{
  content:'';position:absolute;left:21px;top:38px;bottom:0;width:2px;
  background:var(--border);z-index:0
}
.tl-rail{position:relative;display:flex;flex-direction:column;align-items:center;padding-top:6px}
.tl-node{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.78rem;font-weight:800;z-index:1;flex-shrink:0;border:2px solid transparent}
.tl-content{padding:4px 0 28px 14px}
/* query as hero text */
.tl-query{font-family:'SF Mono',ui-monospace,monospace;font-size:1.02rem;font-weight:700;color:var(--fg);margin-bottom:4px;line-height:1.3;word-break:break-word}
.tl-intent{font-size:0.76rem;color:var(--muted);margin-bottom:10px;letter-spacing:0.01em}
/* state pill — wide, below the query */
.tl-state-pill{display:inline-flex;align-items:center;gap:6px;font-size:0.75rem;font-weight:700;padding:4px 12px;border-radius:20px;margin-bottom:10px;letter-spacing:0.04em}
.tl-state-pill .pill-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
/* result evidence — compact, only when failure */
.tl-evidence{background:var(--secondary);border-radius:6px;padding:10px 14px;margin-bottom:4px;font-size:0.82rem}
.tl-evidence-label{font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);margin-bottom:6px}
.tl-evidence-item{display:flex;align-items:baseline;gap:6px;margin-bottom:3px;line-height:1.35}
.tl-evidence-item:last-child{margin-bottom:0}
.tl-rank{font-size:0.7rem;color:var(--muted);flex-shrink:0;width:16px}
.tl-title{color:var(--fg)}
.tl-title.bad{color:var(--bad);font-weight:600}
/* reformulation arrow between steps */
.tl-reformat-arrow{display:flex;align-items:center;gap:8px;padding:6px 0 6px 58px;font-size:0.75rem;font-weight:600;color:var(--muted);letter-spacing:0.03em}
.tl-reformat-arrow::before{content:'↓';font-size:1rem;color:var(--warn)}
/* tolerance cap */
.tl-tolerance-cap{margin:0 0 20px 0;padding:8px 14px;background:#fefce8;border:1px solid #fde68a;border-radius:6px;font-size:0.78rem;font-weight:600;color:#92400e;display:flex;align-items:center;gap:8px}
/* Session conclusion */
.session-conclusion{border-radius:8px;padding:16px 20px;font-size:0.9rem;line-height:1.6}
.r-bad{color:var(--bad);font-weight:600}
/* Fix section */
.fix-card{border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;margin-bottom:14px}
.fix-title{font-weight:700;margin-bottom:6px;font-size:0.98rem}
.fix-meta{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px}
.fix-desc{font-size:0.9rem;margin-bottom:10px;line-height:1.6}
.fix-personas{display:flex;gap:8px;flex-wrap:wrap}
.fix-persona-tag{font-size:0.72rem;font-weight:600;padding:3px 10px;border-radius:12px}
/* Persona legend */
.persona-legend{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:32px}
.persona-legend-item{display:flex;align-items:center;gap:6px;font-size:0.82rem;font-weight:500}
/* Run divider */
.run-divider{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);padding:14px 0 4px;margin-bottom:8px;border-bottom:1px solid var(--border)}
/* Footer */
footer{padding:32px 0;color:var(--muted);font-size:0.8rem;text-align:center;border-top:1px solid var(--border);margin-top:20px}
/* Insight callout */
.insight{background:#f0f9ff;border-left:4px solid #0284c7;padding:18px 22px;border-radius:6px;margin:20px 0;font-size:0.92rem;line-height:1.7}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def outcome_badge(outcome: str) -> str:
    c, bg, label = OUTCOME_CONFIG.get(outcome, ("#555", "#eee", outcome))
    return f'<div class="outcome-badge" style="color:{c};background:{bg};border:1px solid {c}33">{esc(label)}</div>'


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------
def build_cover(agg: dict, date_str: str) -> str:
    n = agg["total_sessions"]
    c = agg["converted"]
    s = agg["split_basket"]
    a = agg["abandoned"]
    avg_ref = agg["avg_reformulations"]
    rev = agg["estimated_revenue_lost"]
    fail_pct = round((s + a) / n * 100)
    conv_pct = round(c / n * 100)

    return f"""
<section class="cover">
  <div class="label">Persona Search Simulation · shop-apotheke.com</div>
  <h1>30 simulated search sessions.<br>{fail_pct}% did not end in a clean conversion.</h1>
  <div class="cover-meta">{esc(date_str)} · 2 independent run sets · {agg['total_queries']} queries across 5 personas · live results from shop-apotheke.com</div>

  <div class="hook">
    We simulated <strong>{n} real search sessions</strong> across five shopper archetypes, each with their own vocabulary,
    patience level, and reformulation behaviour. Sessions ran in two independent batches to verify
    that observed failures are <strong>consistent patterns, not one-off results</strong>.
    <br><br>
    Only <strong>{c} of {n} sessions ({conv_pct}%) ended in a clean conversion</strong>.
    <strong>{s} sessions resulted in split-basket behaviour</strong> — the shopper stayed on site but routed their
    primary purchase to a competitor. These sessions look healthy in analytics. They aren't.
    <strong>{a} sessions hard-abandoned</strong> to a physical Apotheke, docmorris.de, or Amazon.
    Across the session set, estimated revenue impact: <strong>€{rev}</strong>.
  </div>

  <div class="headline-grid">
    <div class="hn ok"><div class="n">{c}</div><div class="nl">Converted</div></div>
    <div class="hn warn">
      <div class="n">{s}</div>
      <div class="nl">Split basket<br><span style="font-size:0.62rem;font-weight:400">invisible in analytics</span></div>
    </div>
    <div class="hn bad"><div class="n">{a}</div><div class="nl">Hard abandoned</div></div>
    <div class="hn"><div class="n" style="color:var(--fg)">{avg_ref}</div><div class="nl">Avg reformulations</div></div>
    <div class="hn bad"><div class="n">€{rev}</div><div class="nl">Est. revenue lost</div></div>
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Aggregate findings section
# ---------------------------------------------------------------------------
def build_aggregate_section(agg: dict) -> str:
    persona_stats = agg["persona_stats"]
    friction = agg["entry_friction_by_persona"]
    cat_fail = agg["category_failure_rates"]

    # --- Persona outcome heatmap ---
    rows = ""
    for pk, ps in persona_stats.items():
        color = PERSONA_COLORS[pk]
        n = ps["sessions"]
        c = ps["converted"]
        s = ps["split_basket"]
        a = ps["abandoned"]
        conv_rate = round(c / n * 100)
        avg_ref = ps["avg_reformulations"]
        rev = ps["revenue_lost"]
        modes = ps.get("failure_modes", [])

        conv_color = "var(--ok)" if conv_rate >= 60 else ("var(--warn)" if conv_rate >= 40 else "var(--bad)")
        rows += f"""
<tr>
  <td><span class="cell-dot" style="background:{color}"></span><strong>{esc(PERSONA_LABELS[pk])}</strong></td>
  <td style="text-align:center"><strong style="color:{conv_color}">{conv_rate}%</strong></td>
  <td style="text-align:center">{c}/{n}</td>
  <td style="text-align:center">{s}</td>
  <td style="text-align:center">{a}</td>
  <td style="text-align:center">{avg_ref}</td>
  <td style="text-align:center">€{rev}</td>
</tr>
"""

    heatmap = f"""
<div class="agg-block" style="grid-column:1/-1">
  <div class="agg-block-title">Session outcomes by persona (30 sessions)</div>
  <table class="heatmap">
    <thead><tr>
      <th>Persona</th>
      <th style="text-align:center">Conv. rate</th>
      <th style="text-align:center">Converted</th>
      <th style="text-align:center">Split basket</th>
      <th style="text-align:center">Abandoned</th>
      <th style="text-align:center">Avg ref.</th>
      <th style="text-align:center">Rev. lost</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""

    # --- Entry friction ---
    friction_rows = ""
    for pk, rate in sorted(friction.items(), key=lambda x: -x[1]):
        pct = round(rate * 100)
        color = PERSONA_COLORS[pk]
        bar_color = "var(--bad)" if pct >= 70 else ("var(--warn)" if pct >= 50 else "var(--ok)")
        friction_rows += f"""
<div class="friction-row" style="padding:9px 14px">
  <div style="font-size:0.82rem;font-weight:600"><span class="cell-dot" style="background:{color}"></span>{esc(PERSONA_LABELS[pk].split()[0])}</div>
  <div class="friction-bar-wrap"><div class="friction-bar" style="width:{pct}%;background:{bar_color}"></div></div>
  <div style="font-size:0.82rem;font-weight:700;color:{bar_color}">{pct}%</div>
</div>
"""

    entry_block = f"""
<div class="agg-block">
  <div class="agg-block-title">Entry query friction (Q1 ≠ FOUND)</div>
  <div style="padding:4px 0">{friction_rows}</div>
</div>
"""

    # --- Category failure rates ---
    cat_rows = ""
    for cat, rate in list(cat_fail.items())[:8]:
        pct = round(rate * 100)
        bg = "var(--bad)" if pct >= 70 else ("var(--warn)" if pct >= 50 else "var(--ok)")
        cat_rows += f"""
<tr>
  <td><code style="font-size:0.8rem">{esc(cat)}</code></td>
  <td style="text-align:right">
    <span style="display:inline-block;background:{bg};color:#fff;font-size:0.72rem;font-weight:700;padding:2px 8px;border-radius:10px">{pct}% failure</span>
  </td>
</tr>
"""

    cat_block = f"""
<div class="agg-block">
  <div class="agg-block-title">Query category failure rates</div>
  <table class="cat-table">
    <thead><tr><th>Query type</th><th style="text-align:right">PARTIAL + NOTHING rate</th></tr></thead>
    <tbody>{cat_rows}</tbody>
  </table>
</div>
"""

    # --- Insight callout ---
    insight = """
<div class="insight">
  <strong>Cross-run consistency confirms these are structural failures, not flukes.</strong><br>
  The same failure patterns — brand displacement, spec mismatch, entry-query friction — appeared
  across both independent run sets. Wellness Optimizer (Mia) had the highest entry friction at 83%:
  her very first query almost never returns a product she trusts, forcing repeated reformulation
  even before the brand-rescue layer. Acute Self-Treater (Jonas) abandoned 3 out of 5 sessions
  because his symptom queries either returned books or Rx-only products.
</div>
"""

    return f"""
<section>
  <div class="label">Aggregate findings — 2 runs · 30 sessions</div>
  <h2>Consistent failures, confirmed across two independent simulation runs</h2>
  <p>Each run used entirely different query sets for the same personas. Failures that appear in both runs are structural — not edge cases.</p>
  {insight}
  <div class="agg-grid">
    {heatmap}
    {entry_block}
    {cat_block}
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Session card builder (handles both run1 and run2 formats)
# ---------------------------------------------------------------------------
def _evidence_block(top5: list, state: str, result_count: int) -> str:
    """Show compact evidence only when the state is PARTIAL or NOTHING."""
    if state == "FOUND":
        return ""
    if not top5:
        return '<div class="tl-evidence"><div class="tl-evidence-label">Results</div><div style="color:var(--muted);font-style:italic;font-size:0.82rem">No results returned</div></div>'

    BAD_KW = {"buch", "book", "roman", "modafinil", "zopiclon", "rezeptpflichtig", "verschreibungspflichtig"}
    items_html = ""
    for i, r in enumerate(top5[:3]):
        title = r.get("title", "")[:75]
        is_bad = any(kw in title.lower() for kw in BAD_KW)
        title_cls = "tl-title bad" if is_bad else "tl-title"
        items_html += f'<div class="tl-evidence-item"><span class="tl-rank">#{i+1}</span><span class="{title_cls}">{esc(title)}</span></div>'

    return f'<div class="tl-evidence"><div class="tl-evidence-label">What the engine returned ({result_count} results)</div>{items_html}</div>'


def build_session_card(session: dict) -> str:
    pk = session.get("persona_key") or session.get("key", "")
    name = PERSONA_FIRST_NAMES.get(pk, pk)
    theme = session.get("theme", "Run 1")
    outcome = session.get("session_outcome", "ABANDONED")
    ref_used = session.get("reformulations_used", 0)
    basket = session.get("basket_value", 0)
    color = PERSONA_COLORS.get(pk, "#6b7280")
    out_c, out_bg, out_label = OUTCOME_CONFIG.get(outcome, ("#555", "#eee", outcome))
    situation = PERSONA_SITUATION.get(pk, "")
    stake = PERSONA_STAKE.get(pk, "")
    abandon_dest = PERSONA_ABANDON.get(pk, "")

    # ── Header ──────────────────────────────────────────────────────────────
    ref_label = f"{ref_used} reformulation{'s' if ref_used != 1 else ''}"
    header = f"""
<div class="session-header">
  <div>
    <div class="session-name">
      <span class="session-persona-dot" style="background:{color}"></span>
      {esc(name)}
    </div>
    <div class="session-theme">{esc(PERSONA_LABELS.get(pk, pk))} &nbsp;·&nbsp; {esc(theme)}</div>
    <div class="session-situation">{esc(situation)}</div>
    <div class="session-stake" style="margin-top:6px">At stake: {esc(stake)}</div>
  </div>
  <div style="text-align:center;min-width:110px">
    {outcome_badge(outcome)}
    <div style="font-size:0.72rem;color:var(--muted);margin-top:8px">{ref_label}</div>
    <div style="font-size:0.72rem;color:var(--muted)">basket: €{basket}</div>
  </div>
</div>
"""

    # ── Timeline ─────────────────────────────────────────────────────────────
    queries = session.get("queries", [])
    tl_steps = []
    tl_html = '<div class="timeline">'

    for i, q in enumerate(queries):
        state = q.get("state", "NOTHING")
        step_n = q.get("step", i + 1)
        q_str = q.get("query", "")
        intent = q.get("intent_label", "")
        top5 = q.get("top5", [])
        result_count = q.get("result_count", len(top5))
        prev_state = queries[i - 1].get("state", "FOUND") if i > 0 else "FOUND"

        s_color, s_bg, s_label = STATE_COLORS.get(state, ("#555", "#eee", state))

        # Insert "reformulated ↓" arrow if previous step failed
        if i > 0 and prev_state in ("PARTIAL", "NOTHING"):
            tl_html += f'<div class="tl-reformat-arrow">reformulated</div>'

        evidence = _evidence_block(top5, state, result_count)

        tl_html += f"""
<div class="tl-step">
  <div class="tl-rail">
    <div class="tl-node" style="background:{s_bg};color:{s_color};border-color:{s_color}44">{step_n}</div>
  </div>
  <div class="tl-content">
    <div class="tl-query">{esc(q_str)}</div>
    <div class="tl-intent">{esc(intent)}</div>
    <div class="tl-state-pill" style="background:{s_bg};color:{s_color};border:1px solid {s_color}44">
      <span class="pill-dot" style="background:{s_color}"></span>{s_label}
    </div>
    {evidence}
  </div>
</div>
"""
        tl_steps.append(state)

    tl_html += "</div>"

    # ── Tolerance cap (if outcome wasn't CONVERTED) ───────────────────────────
    cap_html = ""
    if outcome != "CONVERTED":
        cap_html = f'<div class="tl-tolerance-cap">⚑ Reformulation tolerance reached — session exited</div>'

    # ── Conclusion ───────────────────────────────────────────────────────────
    if outcome == "CONVERTED":
        conclusion_body = f"Search succeeded. The engine served a result {esc(name.split(',')[0])} could act on."
        c_border = "var(--ok)"
        c_bg = "#f0fdf4"
    elif outcome == "SPLIT_BASKET":
        conclusion_body = (
            f"Session stayed on-site — but the primary item was lost to <strong>{esc(abandon_dest)}</strong>. "
            f"<strong>This session looks like a success in session analytics. The basket value was not captured.</strong>"
        )
        c_border = "var(--warn)"
        c_bg = "#fffbeb"
    else:
        conclusion_body = (
            f"After {ref_used} failed reformulation(s), {esc(name.split(',')[0])} left for "
            f"<strong>{esc(abandon_dest)}</strong>. Estimated revenue lost: <strong>€{basket}</strong>."
        )
        c_border = "var(--bad)"
        c_bg = "#fff1f2"

    conclusion_html = f"""
<div class="session-conclusion" style="background:{c_bg};border-left:4px solid {c_border}">
  <strong style="display:block;margin-bottom:4px">{out_label}</strong>
  {conclusion_body}
</div>
"""

    body = f'<div class="session-body">{tl_html}{cap_html}{conclusion_html}</div>'
    return f'<div class="session-card">{header}{body}</div>'


# ---------------------------------------------------------------------------
# Sessions section — grouped by run
# ---------------------------------------------------------------------------
def build_sessions_section(sessions: list[dict]) -> str:
    run1 = [s for s in sessions if s.get("_run", "").endswith("_data.json") and "run2" not in s.get("_run", "")]
    run2 = [s for s in sessions if "run2" in s.get("_run", "")]

    def cards_for(run_sessions: list[dict]) -> str:
        return "".join(build_session_card(s) for s in run_sessions)

    return f"""
<section>
  <div class="label">Session by session — all 30 sessions</div>
  <h2>Every session, every query, every result</h2>
  <p>Cards are grouped by run. Same failure patterns appear in both independent runs — confirming structural gaps rather than query-specific edge cases.</p>

  <div class="persona-legend">
    {"".join(
        f'<div class="persona-legend-item"><span class="cell-dot" style="background:{PERSONA_COLORS[pk]};width:12px;height:12px;border-radius:50%;display:inline-block"></span>{esc(PERSONA_LABELS[pk])}</div>'
        for pk in PERSONA_LABELS
    )}
  </div>

  <div class="run-divider">Run 1 — 5 sessions (initial validation set)</div>
  <div class="session-grid">
    {cards_for(run1)}
  </div>

  <div class="run-divider" style="margin-top:40px">Run 2 — 25 sessions (extended set, entirely different queries)</div>
  <div class="session-grid">
    {cards_for(run2)}
  </div>
</section>
"""


# ---------------------------------------------------------------------------
# Fix prioritization section
# ---------------------------------------------------------------------------
def build_fix_section() -> str:
    cards = ""
    for fix in FIX_TABLE:
        effort = fix["effort"]
        impact = fix["impact"]
        effort_color = {"Low": "var(--ok)", "Medium": "var(--warn)", "High": "var(--bad)"}[effort]
        impact_color = {"Critical": "var(--bad)", "High": "var(--warn)", "Medium": "var(--ok)"}[impact]
        border_color = effort_color

        persona_tags = "".join(
            f'<span class="fix-persona-tag" style="background:{PERSONA_COLORS[pk]}22;color:{PERSONA_COLORS[pk]};border:1px solid {PERSONA_COLORS[pk]}44">'
            f'{esc(PERSONA_LABELS[pk].split()[0])}</span>'
            for pk in fix["affects"]
        )

        cards += f"""
<div class="fix-card" style="border-left:4px solid {border_color}">
  <div class="fix-title">{esc(fix['title'])}</div>
  <div class="fix-meta">
    Effort: <span style="color:{effort_color}">{effort}</span>
    &nbsp;·&nbsp;
    Impact: <span style="color:{impact_color}">{impact}</span>
    &nbsp;·&nbsp; affects {len(fix['affects'])} persona(s)
  </div>
  <div class="fix-desc">{esc(fix['description'])}</div>
  <div class="fix-personas">{persona_tags}</div>
</div>
"""

    return f"""
<section>
  <div class="label">Fix prioritisation</div>
  <h2>Root causes, by engineering effort</h2>
  <p>Each fix unblocks multiple persona sessions simultaneously. Ordering is by effort — lowest-effort, highest-ROI fixes first. All are backed by 30-session evidence, not a single run.</p>
  {cards}
</section>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not COMBINED_JSON.exists():
        print(f"Combined JSON not found: {COMBINED_JSON}")
        print("Run persona_simulation_aggregate.py first.")
        sys.exit(1)

    print(f"Loading: {COMBINED_JSON}")
    data = json.loads(COMBINED_JSON.read_text(encoding="utf-8"))
    agg = data["aggregate"]
    sessions = data["sessions"]

    date_str = datetime.now().strftime("%B %d, %Y")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    out_dir = ROOT / "reports" / "persona_simulation"
    out_dir.mkdir(parents=True, exist_ok=True)

    html_parts = [
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>shop-apotheke.com — Persona Search Simulation (30 sessions)</title>',
        f'<style>{CSS}</style></head><body><div class="page">',
        build_cover(agg, date_str),
        build_aggregate_section(agg),
        build_sessions_section(sessions),
        build_fix_section(),
        f'<footer>Persona Search Simulation · shop-apotheke.com · {date_str} · 2 runs · 30 sessions · live data</footer>',
        '</div></body></html>',
    ]

    html = "\n".join(html_parts)
    out_path = out_dir / f"persona_simulation_{ts}_report_combined.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written: {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
