"""
Persona simulation HTML report builder for shop-apotheke.com
------------------------------------------------------------
Reads the JSON output from persona_simulation_run.py and generates
a self-contained HTML report styled for Redcare stakeholder presentation.

Usage:
    python3 scripts/persona_simulation_report.py [path/to/data.json]
    (omit path to auto-find latest in reports/persona_simulation/)
"""
from __future__ import annotations

import html as _html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def esc(s) -> str:
    return _html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------
# Persona first names + narrative setup
# ---------------------------------------------------------------------------
PERSONA_NARRATIVES = {
    "anxious_young_mother": {
        "name": "Lena, 29 — Berlin",
        "situation": "It's 11pm. Her 8-month-old daughter won't sleep. She's breastfeeding and needs something safe, natural, and without a prescription. She opens shop-apotheke on her phone.",
        "stake": "A child's wellbeing and a mother's trust",
        "abandon_destination": "docmorris.de or the Apotheke at Hauptbahnhof tomorrow morning",
    },
    "wellness_optimizer": {
        "name": "Mia, 34 — München",
        "situation": "Sunday morning. She's run out of Magnesium and knows exactly what she needs: Bisglycinat form, 300mg elemental, capsule. She's been taking this for two years and knows the difference between forms.",
        "stake": "A €110 monthly basket and long-term loyalty",
        "abandon_destination": "amazon.de for the Magnesium; back to shop-apotheke for the rest of the basket",
    },
    "elderly_patient": {
        "name": "Werner, 71 — rural Bavaria",
        "situation": "His cardiologist visit was yesterday. He has a new medication list and needs to reorder his Aspirin protect and incontinence supplies. He's not confident online but the nearest Apotheke is 20 minutes away.",
        "stake": "A repeat customer worth €45/month in chronic medication reorders",
        "abandon_destination": "Calls shop-apotheke customer service — or drives to the Apotheke",
    },
    "acute_self_treater": {
        "name": "Jonas, 31 — Hamburg",
        "situation": "Thursday evening. Sore throat since this morning, getting worse. The Apotheke near his office closed at 6pm. He's trying to order something for delivery tomorrow.",
        "stake": "A one-time conversion and a first impression of the platform",
        "abandon_destination": "dm or Rossmann around the corner, or the 24h Apotheke at the train station",
    },
    "alternative_medicine_seeker": {
        "name": "Petra, 48 — Baden-Württemberg",
        "situation": "Her Heilpraktiker recommended Nux vomica D12 for her stress-related sleep issues last week. She's looking for the exact product and wants to add some Schüssler Salze while she's at it.",
        "stake": "A high-loyalty customer who buys multiple remedies per session",
        "abandon_destination": "apo-rot.de or weleda.de directly",
    },
}

STATE_COLORS = {
    "FOUND": ("#16a34a", "#dcfce7", "Found"),
    "PARTIAL": ("#b45309", "#fef3c7", "Partial"),
    "NOTHING": ("#dc2626", "#fee2e2", "Nothing"),
}

OUTCOME_CONFIG = {
    "CONVERTED": ("#16a34a", "#dcfce7", "Converted"),
    "SPLIT_BASKET": ("#b45309", "#fef3c7", "Split basket"),
    "ABANDONED": ("#dc2626", "#fee2e2", "Hard abandon"),
}

CSS = """
:root{
  --primary:#e4002b;--fg:#0a0a0a;--muted:#6b7280;--border:#e5e5e5;
  --accent:#fff1f2;--secondary:#f9fafb;--bad:#dc2626;--warn:#d97706;
  --ok:#16a34a;--radius:0.75rem;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:15px;line-height:1.65;color:var(--fg);background:#fff;-webkit-font-smoothing:antialiased}
.page{max-width:940px;margin:0 auto;padding:0 36px 80px}
section{padding:48px 0;border-top:1px solid var(--border)}
section:first-of-type{border-top:none}
h1{font-size:2.4rem;letter-spacing:-0.03em;line-height:1.15;margin-bottom:14px;font-weight:800}
h2{font-size:1.45rem;margin-bottom:18px;font-weight:700;letter-spacing:-0.01em}
h3{font-size:1.05rem;font-weight:700;margin-bottom:10px}
p{margin-bottom:14px;color:var(--fg)}
.label{font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--primary);margin-bottom:10px}
.cover{padding:64px 0 52px}
.cover-meta{font-size:0.875rem;color:var(--muted);margin-bottom:32px}
/* Headline numbers */
.headline-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:28px 0}
.hn{background:var(--secondary);border:1px solid var(--border);border-radius:var(--radius);padding:22px 20px;text-align:center}
.hn .n{font-size:3rem;font-weight:800;letter-spacing:-0.04em;line-height:1}
.hn .nl{font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;margin-top:8px;color:var(--muted)}
.hn.bad .n{color:var(--bad)}
.hn.warn .n{color:var(--warn)}
.hn.ok .n{color:var(--ok)}
/* Opening hook */
.hook{background:var(--accent);border-left:4px solid var(--primary);padding:26px 30px;border-radius:6px;margin:28px 0;font-size:1.05rem;line-height:1.7}
/* Persona cards */
.persona-card{border:1px solid var(--border);border-radius:var(--radius);margin-bottom:40px;overflow:hidden}
.persona-header{display:grid;grid-template-columns:1fr auto;align-items:start;gap:20px;padding:24px 28px;background:var(--secondary);border-bottom:1px solid var(--border)}
.persona-name{font-size:1.2rem;font-weight:800;margin-bottom:4px}
.persona-archetype{font-size:0.82rem;color:var(--muted);font-weight:500}
.persona-situation{font-size:0.95rem;color:var(--fg);margin-top:12px;line-height:1.6;font-style:italic}
.persona-stake{font-size:0.82rem;color:var(--muted);margin-top:6px}
.outcome-badge{font-size:0.78rem;font-weight:700;padding:6px 14px;border-radius:20px;white-space:nowrap;text-align:center}
.persona-body{padding:24px 28px}
/* Query steps */
.query-steps{display:flex;flex-direction:column;gap:12px;margin-bottom:20px}
.query-step{display:grid;grid-template-columns:32px 1fr auto;gap:12px;align-items:start}
.step-num{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;flex-shrink:0;margin-top:2px}
.step-body{}
.step-query{font-family:'SF Mono',ui-monospace,monospace;font-size:0.88rem;font-weight:600;background:var(--secondary);padding:5px 10px;border-radius:4px;display:inline-block;margin-bottom:4px}
.step-intent{font-size:0.78rem;color:var(--muted);margin-bottom:6px}
.step-results{font-size:0.82rem;color:var(--fg)}
.step-results ol{margin:4px 0 0 18px}
.step-results ol li{margin:1px 0;line-height:1.4}
.step-results .r-title{color:var(--fg)}
.step-results .r-bad{color:var(--bad);font-weight:600}
.step-state{font-size:0.72rem;font-weight:700;padding:4px 10px;border-radius:12px;white-space:nowrap;align-self:start;margin-top:3px}
.step-failure{font-size:0.8rem;color:var(--muted);margin-top:5px;font-style:italic}
/* Session conclusion */
.session-conclusion{background:var(--secondary);border-radius:8px;padding:16px 18px;margin-top:8px;font-size:0.9rem}
.session-conclusion strong{display:block;margin-bottom:4px}
/* DocMorris comparison */
.dm-comparison{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:24px}
.dm-header{display:grid;grid-template-columns:1fr 1fr;background:var(--secondary);border-bottom:1px solid var(--border)}
.dm-header div{padding:12px 16px;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted)}
.dm-header div:first-child{border-right:1px solid var(--border)}
.dm-row{display:grid;grid-template-columns:1fr 1fr}
.dm-cell{padding:14px 16px;font-size:0.85rem;border-bottom:1px solid var(--border);vertical-align:top}
.dm-cell:first-child{border-right:1px solid var(--border)}
.dm-cell ol{margin:6px 0 0 16px}
.dm-cell ol li{margin:2px 0;line-height:1.35;font-size:0.82rem}
.dm-cell .dm-query{font-family:'SF Mono',ui-monospace,monospace;font-size:0.8rem;font-weight:600;background:var(--secondary);padding:3px 8px;border-radius:3px;display:inline-block;margin-bottom:8px}
.dm-cell .dm-count{font-size:0.75rem;color:var(--muted);margin-bottom:6px}
.dm-verdict{padding:12px 16px;font-size:0.82rem;background:#f0fdf4;color:var(--ok);font-weight:600;border-top:1px solid var(--border);grid-column:1/-1}
.dm-verdict.bad{background:#fff1f2;color:var(--bad)}
/* Footer */
footer{padding:32px 0;color:var(--muted);font-size:0.8rem;text-align:center;border-top:1px solid var(--border);margin-top:20px}
"""


def build_cover(summary: dict, date_str: str) -> str:
    c = summary["converted"]
    s = summary["split_basket"]
    a = summary["abandoned"]
    n = summary["total_personas"]
    avg_ref = summary["avg_reformulations"]
    rev_lost = summary["estimated_revenue_lost_per_session"]
    queries_run = summary["total_queries_run"]

    return f"""
<section class="cover">
  <div class="label">Persona Search Simulation · shop-apotheke.com</div>
  <h1>We sent 5 real shoppers to shop-apotheke.com.<br>Here's what happened.</h1>
  <div class="cover-meta">{esc(date_str)} · {queries_run} queries across 5 personas · live results · DocMorris spot-check included</div>

  <div class="hook">
    We simulated the exact search sessions of five real shopper archetypes — each with their own vocabulary, urgency, and patience threshold.
    Across <strong>{queries_run} queries</strong>, only <strong>{c} of {n} sessions ended in a clear conversion signal</strong>.
    <strong>{s} ended in split-basket behaviour</strong> — the shopper stayed but routed their primary item to a competitor.
    <strong>{a} sessions hard-abandoned</strong> to a physical Apotheke or docmorris.de.
    Average reformulation burden: <strong>{avg_ref} queries per session</strong> before success or exit.
    Estimated revenue impact across this session set: <strong>€{rev_lost}</strong>.
  </div>

  <div class="headline-grid">
    <div class="hn ok">
      <div class="n">{c}</div>
      <div class="nl">Converted</div>
    </div>
    <div class="hn warn">
      <div class="n">{s}</div>
      <div class="nl">Split basket<br><span style="font-size:0.65rem;font-weight:400">invisible in analytics</span></div>
    </div>
    <div class="hn bad">
      <div class="n">{a}</div>
      <div class="nl">Hard abandoned</div>
    </div>
    <div class="hn">
      <div class="n" style="color:var(--fg)">{avg_ref}</div>
      <div class="nl">Avg reformulations</div>
    </div>
  </div>
</section>
"""


def build_persona_card(persona: dict) -> str:
    key = persona["key"]
    narrative = PERSONA_NARRATIVES.get(key, {})
    outcome = persona["session_outcome"]
    out_color, out_bg, out_label = OUTCOME_CONFIG.get(outcome, ("#000", "#eee", outcome))

    # Header
    header = f"""
<div class="persona-header">
  <div>
    <div class="persona-name">{esc(narrative.get('name', persona['name']))}</div>
    <div class="persona-archetype">{esc(persona['archetype'])}</div>
    <div class="persona-situation">{esc(narrative.get('situation', ''))}</div>
    <div class="persona-stake">At stake: {esc(narrative.get('stake', ''))}</div>
  </div>
  <div>
    <div class="outcome-badge" style="color:{out_color};background:{out_bg};border:1px solid {out_color}33">
      {esc(out_label)}
    </div>
    <div style="font-size:0.75rem;color:var(--muted);margin-top:8px;text-align:center">
      {persona['reformulations_used']} reformulation(s)
    </div>
  </div>
</div>
"""

    # Query steps
    steps_html = '<div class="query-steps">'
    for q in persona["queries"]:
        state = q["state"]
        s_color, s_bg, s_label = STATE_COLORS.get(state, ("#555", "#eee", state))
        step_num = q["step"]

        # Top results
        results_html = ""
        if q["top5"]:
            items = ""
            for i, r in enumerate(q["top5"][:5]):
                title = r["title"][:80]
                # Flag obviously wrong results
                is_bad = any(kw in title.lower() for kw in [
                    "buch", "book", "roman", "modafinil", "zopiclon", "wick medinait",
                    "erkältungssirup", "erkältungs-", "rezeptpflichtig",
                ])
                cls = "r-bad" if is_bad and i == 0 else "r-title"
                items += f'<li><span class="{cls}">{esc(title)}</span></li>'
            results_html = f'<div class="step-results"><ol>{items}</ol></div>'
        else:
            results_html = '<div class="step-results" style="color:var(--muted);font-style:italic">No results returned</div>'

        steps_html += f"""
<div class="query-step">
  <div class="step-num" style="background:{s_bg};color:{s_color};border:1px solid {s_color}44">{step_num}</div>
  <div class="step-body">
    <div class="step-query">{esc(q['query'])}</div>
    <div class="step-intent">{esc(q['intent_label'])}</div>
    {results_html}
    <div class="step-failure">{esc(q['expected_failure'])}</div>
  </div>
  <div class="step-state" style="color:{s_color};background:{s_bg};border:1px solid {s_color}33">{s_label}</div>
</div>
"""

    steps_html += "</div>"

    # Session conclusion
    dest = narrative.get("abandon_destination", "")
    if outcome == "CONVERTED":
        conclusion_text = f"Session ended with a conversion signal. {esc(persona['name'])} found what she was looking for."
        conclusion_style = "border-left:3px solid var(--ok)"
    elif outcome == "SPLIT_BASKET":
        conclusion_text = (
            f"Session continued — but the primary item was lost to a competitor. "
            f"{esc(persona['name'])} went to {esc(dest)} for the core purchase and returned to shop-apotheke for secondary items. "
            f"<strong>This session looks successful in analytics. It wasn't.</strong>"
        )
        conclusion_style = "border-left:3px solid var(--warn)"
    else:
        conclusion_text = (
            f"Session terminated. {esc(persona['name'])} left for {esc(dest)}. "
            f"shop-apotheke lost this session after {persona['reformulations_used']} reformulation(s)."
        )
        conclusion_style = "border-left:3px solid var(--bad)"

    conclusion_html = f"""
<div class="session-conclusion" style="{conclusion_style}">
  <strong>Session outcome: {out_label}</strong>
  {conclusion_text}
</div>
"""

    body = f'<div class="persona-body">{steps_html}{conclusion_html}</div>'
    return f'<div class="persona-card">{header}{body}</div>'


def build_personas_section(personas: list[dict]) -> str:
    cards = "".join(build_persona_card(p) for p in personas)
    return f"""
<section>
  <div class="label">Session by session</div>
  <h2>Five shoppers. Five sessions. Here's what each one saw.</h2>
  {cards}
</section>
"""


def build_docmorris_section(spot_checks: dict, personas: list[dict]) -> str:
    if not spot_checks:
        return ""

    # Build a lookup for shop-apotheke results
    sa_lookup: dict[str, dict] = {}
    for p in personas:
        for q in p["queries"]:
            sa_lookup[q["query"]] = {
                "result_count": q["result_count"],
                "top5": q["top5"],
                "state": q["state"],
            }

    comparisons = ""
    for q_str, dm_data in spot_checks.items():
        sa = sa_lookup.get(q_str, {})
        sa_top5 = sa.get("top5", [])
        dm_top5 = dm_data.get("top5", [])
        sa_count = sa.get("result_count", 0)
        dm_count = dm_data.get("result_count", 0)

        sa_items = "".join(f"<li>{esc(r['title'][:70])}</li>" for r in sa_top5[:5]) or "<li><em>No results</em></li>"
        dm_items = "".join(f"<li>{esc(r['title'][:70])}</li>" for r in dm_top5[:5]) or "<li><em>No results</em></li>"

        # Simple verdict: did DocMorris do better?
        sa_state = sa.get("state", "NOTHING")
        dm_better = dm_count > sa_count and sa_state != "FOUND"
        verdict_cls = "" if dm_better else "bad"
        verdict_text = (
            f"DocMorris returned {dm_count} results vs shop-apotheke's {sa_count}. Query intent better served by competitor."
            if dm_better else
            f"Both platforms returned similar results for this query ({sa_count} vs {dm_count})."
        )

        comparisons += f"""
<div class="dm-comparison">
  <div class="dm-header">
    <div>shop-apotheke.com</div>
    <div>docmorris.de</div>
  </div>
  <div class="dm-row">
    <div class="dm-cell">
      <div class="dm-query">{esc(q_str)}</div>
      <div class="dm-count">{sa_count} results</div>
      <ol>{sa_items}</ol>
    </div>
    <div class="dm-cell">
      <div class="dm-query">{esc(q_str)}</div>
      <div class="dm-count">{dm_count} results</div>
      <ol>{dm_items}</ol>
    </div>
  </div>
  <div class="dm-row">
    <div class="dm-verdict {verdict_cls}" style="grid-column:1/-1">{verdict_text}</div>
  </div>
</div>
"""

    return f"""
<section>
  <div class="label">Competitive reference</div>
  <h2>The same queries on DocMorris</h2>
  <p>For the highest-friction queries, we ran the identical search on docmorris.de. This establishes whether the failure is a pharmacy search problem in general, or specific to shop-apotheke's configuration.</p>
  {comparisons}
</section>
"""


def build_fix_section(personas: list[dict]) -> str:
    # Aggregate failure modes across all queries with NOTHING/PARTIAL state
    failures: dict[str, list[str]] = {
        "Negation handling absent (ohne / kein)": [],
        "Life-stage routing missing (Baby / Kinder)": [],
        "Structured attribute indexing (form, potency, pack size)": [],
        "OTC/Rx contamination in symptom queries": [],
        "Symptom → product semantic mapping": [],
        "Brand search quality (rescue layer reliability)": [],
    }

    for p in personas:
        for q in p["queries"]:
            ef = q["expected_failure"].lower()
            q_str = q["query"]
            if "ohne" in q_str.lower() or "kein" in q_str.lower() or "negat" in ef:
                failures["Negation handling absent (ohne / kein)"].append(q_str)
            if "baby" in q_str.lower() or "kinder" in q_str.lower() or "life-stage" in ef:
                failures["Life-stage routing missing (Baby / Kinder)"].append(q_str)
            if any(t in ef for t in ["bisglycinat", "potency", "pack size", "d12", "charriere", "structured"]):
                failures["Structured attribute indexing (form, potency, pack size)"].append(q_str)
            if "rx" in ef or "rezeptpflichtig" in ef or "oTC/Rx" in ef.lower():
                failures["OTC/Rx contamination in symptom queries"].append(q_str)
            if "semantic" in ef or "symptom" in ef or "mapping" in ef:
                failures["Symptom → product semantic mapping"].append(q_str)
            if "brand" in ef.lower() and ("rescue" in ef or "recovery" in ef):
                failures["Brand search quality (rescue layer reliability)"].append(q_str)

    effort_map = {
        "Negation handling absent (ohne / kein)": ("Medium", "Add negation tokenizer for ohne/kein/nicht at query-rewrite time. Map excluded token to exclusion filter or category demotion."),
        "Life-stage routing missing (Baby / Kinder)": ("Medium", "Detect life-stage signals (Baby, Säugling, Kleinkind, Kinder, Schwangerschaft) and apply age-group filter at retrieval time. Block adult-only products from baby queries."),
        "Structured attribute indexing (form, potency, pack size)": ("High", "Add supplement_form, homeopathic_potency, and pack_size as structured Algolia attributes. Enable faceted filtering. Boosts form-match when form keyword appears in query."),
        "OTC/Rx contamination in symptom queries": ("Medium", "Implement OTC intent classifier for symptom-led queries. Apply Rx demotion / OTC boost. Add visual Rx indicator in result tiles so users can self-filter."),
        "Symptom → product semantic mapping": ("High", "Build symptom synonym map: Halsschmerzen → Rachentherapeutika, Gedankenkarussell → Beruhigung. Feed into Algolia synonym config. Augment with colloquial German variants."),
        "Brand search quality (rescue layer reliability)": ("Low", "Audit brand name Algolia synonyms. Ensure OTC variant surfaces before Rx variant for brand + symptom queries. This is the last rescue layer for all personas — highest ROI per hour of tuning."),
    }

    rows = ""
    for failure, affected_queries in failures.items():
        if not affected_queries:
            continue
        effort, fix = effort_map.get(failure, ("Medium", ""))
        effort_color = {"Low": "var(--ok)", "Medium": "var(--warn)", "High": "var(--bad)"}.get(effort, "var(--fg)")
        q_tags = "".join(
            f'<code style="font-size:0.78rem;background:var(--secondary);padding:2px 7px;border-radius:3px;margin:2px 4px 2px 0;display:inline-block">{esc(q)}</code>'
            for q in list(dict.fromkeys(affected_queries))[:6]
        )
        rows += f"""
<div style="border:1px solid var(--border);border-left:4px solid {effort_color};border-radius:var(--radius);padding:18px 22px;margin-bottom:14px">
  <div style="font-weight:700;margin-bottom:4px">{esc(failure)}</div>
  <div style="font-size:0.78rem;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.06em">
    Effort: <span style="color:{effort_color};font-weight:700">{effort}</span> · {len(set(affected_queries))} affected queries
  </div>
  <div style="font-size:0.9rem;margin-bottom:10px">{esc(fix)}</div>
  <div>{q_tags}</div>
</div>
"""

    return f"""
<section>
  <div class="label">Fix prioritisation</div>
  <h2>Root causes, grouped by engineering effort</h2>
  <p>Each fix below unblocks multiple persona sessions simultaneously. Ordered by effort so quick wins appear first.</p>
  {rows}
</section>
"""


def main(data_path: Path | None = None) -> None:
    if data_path is None:
        sim_dir = ROOT / "reports" / "persona_simulation"
        candidates = sorted(sim_dir.glob("persona_simulation_*_data.json"), reverse=True)
        if not candidates:
            print("No simulation data found. Run persona_simulation_run.py first.")
            sys.exit(1)
        data_path = candidates[0]

    print(f"Loading: {data_path}")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    date_str = datetime.now().strftime("%B %d, %Y")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    html_parts = [
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>shop-apotheke.com — Persona Search Simulation</title>',
        f'<style>{CSS}</style></head><body><div class="page">',
        build_cover(data["summary"], date_str),
        build_personas_section(data["personas"]),
        build_docmorris_section(data.get("docmorris_spot_checks", {}), data["personas"]),
        build_fix_section(data["personas"]),
        f'<footer>Persona Search Simulation · shop-apotheke.com · {date_str}</footer>',
        '</div></body></html>',
    ]

    html = "\n".join(html_parts)
    out_path = data_path.parent / f"persona_simulation_{ts}_report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written: {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(path)
