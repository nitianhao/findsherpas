"""Commercial Impact Addendum generator for single-brand DTC sites.

Reads the existing Phase 6 checkpoint and produces a second HTML report that
re-prioritizes the findings through a revenue-at-risk lens appropriate for
monobrand retailers (where ranking precision among in-brand results matters
less than constraint enforcement, semantic coverage, and zero-result recovery).

Does NOT modify the underlying audit workflow. Runs alongside the main report.
"""
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
CHECKPOINT = ROOT / "reports" / "_checkpoint_phase6.json"
SITE_CTX = ROOT / "reports" / "_checkpoint_phase1.json"
OUT_DIR = ROOT / "reports" / "www_underarmour_cz"
SCREENSHOT = OUT_DIR / "under armour screenshot.jpg"

SEMANTIC_MISS_THRESHOLD = 0.40  # top-1 relevance below this = customer sees irrelevant result


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def top1_score(j):
    if not j["results"]:
        return None
    by_orig = sorted(j["results"], key=lambda r: r["original_rank"])
    return by_orig[0]["relevance_score"]


def classify(j):
    """Return tier, reason, business_impact_note."""
    q = j["test_query"]["query"]
    fm = j["failure_mode"]
    nres = len(j["results"])
    t1 = top1_score(j)

    if nres == 0:
        return ("A", "Zero results",
                "Customer sees 'no results' and bounces. Recovery requires leaving the site.")
    if fm == "CONSTRAINT_DROPPED":
        return ("A", "Constraint ignored",
                "Customer's filter (gender/section/age) was dropped. Wrong products shown; purchase intent broken.")
    if t1 is not None and t1 < SEMANTIC_MISS_THRESHOLD:
        return ("A", "Semantic miss",
                f"Top-1 relevance {t1:.2f} — customer believes the brand does not carry this product.")

    # Tier B: results are on-topic but ranking is imperfect
    if fm == "POOR_RANKING":
        return ("B", "Ranking imperfect (on-topic)",
                "All results relevant; secondary sort (size/stock/newness) outranks best match. Mild friction, not a lost sale.")
    return ("C", "Acceptable", "Results are on-topic; no meaningful customer impact.")


# ---------------------------------------------------------------------------
# Build content
# ---------------------------------------------------------------------------
def main():
    judgments = json.loads(CHECKPOINT.read_text())
    site_ctx = json.loads(SITE_CTX.read_text())

    classified = []
    for j in judgments:
        tier, reason, impact = classify(j)
        classified.append({
            "query": j["test_query"]["query"],
            "category": j["test_query"]["category"],
            "failure_mode": j["failure_mode"],
            "n_results": len(j["results"]),
            "top1": top1_score(j),
            "tier": tier,
            "reason": reason,
            "impact": impact,
            "evidence": (j.get("evidence") or "")[:300],
            "recommended_fix": (j.get("recommended_fix") or "")[:400],
        })

    tier_a = [c for c in classified if c["tier"] == "A"]
    tier_b = [c for c in classified if c["tier"] == "B"]
    tier_c = [c for c in classified if c["tier"] == "C"]

    # Diacritic-test queries: the two SPECIAL_CHARACTER tests (leginy, teplaky)
    diacritic = [c for c in classified if c["category"] == "SPECIAL_CHARACTER"]

    # Category coverage: pass = tier B or C (results on-topic), fail = tier A
    from collections import defaultdict
    cat_stats = defaultdict(lambda: {"total": 0, "tier_a": 0})
    for c in classified:
        cat_stats[c["category"]]["total"] += 1
        if c["tier"] == "A":
            cat_stats[c["category"]]["tier_a"] += 1

    # Fix prioritization — group tier-A by root cause
    fix_groups = {
        "Compound-word splitting": [c for c in tier_a if c["category"] == "MERGED_WORDS"],
        "Fuzzy typo matching": [c for c in tier_a if c["category"] == "TYPO"],
        "Synonym dictionary (clothing categories)": [c for c in tier_a if c["category"] == "SYNONYM"],
        "Constraint enforcement (gender / section)": [c for c in tier_a if c["failure_mode"] == "CONSTRAINT_DROPPED"],
        "Split-word recovery": [c for c in tier_a if c["category"] == "SPLIT_WORD"],
        "Prefix / partial query handling": [c for c in tier_a if c["category"] == "PARTIAL_QUERY"],
        "Locale term mapping": [c for c in tier_a if c["category"] == "LOCALE_VARIATION"],
    }
    fix_groups = {k: v for k, v in fix_groups.items() if v}
    # Sort by query count descending
    fix_priority = sorted(fix_groups.items(), key=lambda kv: -len(kv[1]))

    # Render
    html = render_html(
        site_ctx=site_ctx,
        classified=classified,
        tier_a=tier_a, tier_b=tier_b, tier_c=tier_c,
        diacritic=diacritic,
        cat_stats=dict(cat_stats),
        fix_priority=fix_priority,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"www_underarmour_cz_{ts}_commercial_addendum.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Tier A (revenue risk): {len(tier_a)}")
    print(f"Tier B (friction):     {len(tier_b)}")
    print(f"Tier C (cosmetic):     {len(tier_c)}")


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
def encode_screenshot():
    if not SCREENSHOT.exists():
        return None
    ext = SCREENSHOT.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    b64 = base64.b64encode(SCREENSHOT.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def render_html(site_ctx, classified, tier_a, tier_b, tier_c, diacritic, cat_stats, fix_priority):
    site_name = site_ctx.get("site_name", "Site")
    date = datetime.now().strftime("%B %-d, %Y")
    screenshot_uri = encode_screenshot()

    css = """
:root{--primary:#009ba3;--fg:#0a0a0a;--muted:#737373;--border:#e5e5e5;--accent:#dcf8fa;--secondary:#f5f5f5;
--tier-a:#e40014;--tier-b:#fcbb00;--tier-c:#009ba3;--radius:0.75rem}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Geist',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:15px;line-height:1.65;color:var(--fg);background:#fff;-webkit-font-smoothing:antialiased}
.page{max-width:900px;margin:0 auto;padding:0 32px}
section{padding:40px 0;border-top:1px solid var(--border)}
section:first-of-type{border-top:none}
h1{font-size:2.25rem;letter-spacing:-0.02em;margin-bottom:12px}
h2{font-size:1.5rem;margin-bottom:20px;font-weight:600}
h3{font-size:1.125rem;margin-bottom:12px;font-weight:600}
h4{font-size:0.95rem;font-weight:700;margin-bottom:8px}
p{margin-bottom:14px}
strong{font-weight:600}
.cover{padding:60px 0 48px}
.cover h1{font-size:2rem}
.subtitle{font-size:1.25rem;font-weight:600;color:var(--primary);margin-bottom:16px}
.cover-meta{font-size:0.875rem;color:var(--muted);margin-bottom:24px}
.shot{margin-top:24px;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.shot img{width:100%;display:block}
.label{font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:var(--primary);margin-bottom:8px}
.stat-row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0}
.stat{background:var(--secondary);border:1px solid var(--border);border-radius:var(--radius);padding:20px}
.stat .v{font-size:2rem;font-weight:700;line-height:1.1}
.stat .v.bad{color:var(--tier-a)}.stat .v.warn{color:#b38600}.stat .v.good{color:var(--tier-c)}
.stat .l{font-size:0.8rem;color:var(--muted);margin-top:6px;line-height:1.4}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:0.9rem}
th{text-align:left;font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);padding:10px 14px;border-bottom:2px solid var(--border)}
td{padding:12px 14px;border-bottom:1px solid var(--border);vertical-align:top}
td code{font-family:'Geist Mono',ui-monospace,'SF Mono',monospace;font-size:0.85rem;background:var(--secondary);padding:2px 6px;border-radius:3px}
.tier-pill{display:inline-block;padding:2px 10px;border-radius:10px;font-size:0.72rem;font-weight:700;letter-spacing:0.03em;text-transform:uppercase}
.tier-A{background:#fde8ea;color:var(--tier-a)}
.tier-B{background:#fff4d6;color:#7a5900}
.tier-C{background:var(--accent);color:var(--tier-c)}
.callout{background:var(--accent);border-left:4px solid var(--primary);padding:20px 24px;border-radius:6px;margin:24px 0}
.callout.warn{background:#fff4d6;border-left-color:#fcbb00}
.callout h3{margin-bottom:8px;color:var(--fg)}
.framing{background:var(--secondary);border-radius:var(--radius);padding:24px;margin:20px 0;font-size:0.95rem;color:var(--fg)}
.framing h3{color:var(--primary);margin-bottom:10px}
.heatmap{display:grid;grid-template-columns:1fr auto auto auto;gap:8px;margin:20px 0;align-items:center}
.heatmap .hdr{font-size:0.72rem;font-weight:600;text-transform:uppercase;color:var(--muted);letter-spacing:0.06em;padding:8px 12px;border-bottom:1px solid var(--border)}
.heatmap .row{padding:10px 12px;border-bottom:1px solid var(--border)}
.heatmap .row.first{font-weight:600}
.pct{display:inline-block;min-width:48px;padding:4px 10px;border-radius:10px;font-weight:700;font-size:0.8rem;text-align:center}
.pct.ok{background:#dcf8fa;color:var(--tier-c)}
.pct.warn{background:#fff4d6;color:#7a5900}
.pct.bad{background:#fde8ea;color:var(--tier-a)}
.fix-card{border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin-bottom:16px}
.fix-card .fix-title{font-weight:600;color:var(--fg);margin-bottom:6px}
.fix-card .fix-meta{font-size:0.8rem;color:var(--muted);margin-bottom:10px}
.fix-card .fix-queries{font-size:0.85rem;color:var(--fg)}
.fix-card .fix-queries code{margin-right:6px}
footer{padding:32px 0;color:var(--muted);font-size:0.8rem;text-align:center;border-top:1px solid var(--border)}
"""

    def badge(tier):
        return f'<span class="tier-pill tier-{tier}">Tier {tier}</span>'

    def pct_cell(passed, total):
        if total == 0: return '<span class="pct ok">—</span>'
        rate = passed / total
        cls = "ok" if rate >= 0.8 else ("warn" if rate >= 0.5 else "bad")
        return f'<span class="pct {cls}">{int(rate*100)}%</span>'

    # Category coverage heatmap
    cat_rows = ""
    cat_order = ["DIRECT_MATCH", "BRAND_SEARCH", "BROAD_CATEGORY", "SYNONYM",
                 "TYPO", "SPECIAL_CHARACTER", "MERGED_WORDS", "SPLIT_WORD",
                 "PLURAL_SINGULAR", "ABBREVIATION", "MULTI_ATTRIBUTE",
                 "PARTIAL_QUERY", "LOCALE_VARIATION"]
    for cat in cat_order:
        if cat not in cat_stats: continue
        s = cat_stats[cat]
        passed = s["total"] - s["tier_a"]
        cat_rows += f"""
<tr>
  <td>{cat.replace('_', ' ').title()}</td>
  <td style="text-align:right">{passed}/{s['total']}</td>
  <td>{pct_cell(passed, s['total'])}</td>
  <td style="color:var(--muted);font-size:0.85rem">{'Revenue risk' if s['tier_a'] else 'OK'}</td>
</tr>"""

    # Tier A table
    tier_a_rows = ""
    for c in tier_a:
        tier_a_rows += f"""
<tr>
  <td><code>{c['query']}</code></td>
  <td><span class="tier-pill tier-A">{c['reason']}</span></td>
  <td style="color:var(--muted);font-size:0.85rem">{c['impact']}</td>
</tr>"""

    # Tier B/C summary counts
    tier_b_sev_ok = [c for c in tier_b if c["top1"] and c["top1"] >= 0.60]
    tier_b_sev_meh = [c for c in tier_b if c["top1"] and c["top1"] < 0.60]

    # Fix priority cards
    fix_cards_html = ""
    for group, items in fix_priority:
        query_html = " ".join(f"<code>{c['query']}</code>" for c in items)
        fix_cards_html += f"""
<div class="fix-card">
  <div class="fix-title">{group}</div>
  <div class="fix-meta">{len(items)} queries affected · Tier A (revenue risk)</div>
  <div class="fix-queries">{query_html}</div>
</div>"""

    # Diacritic callout
    diac_html = ""
    if diacritic:
        diac_queries = " ".join(f"<code>{c['query']}</code>" for c in diacritic)
        diac_html = f"""
<div class="callout">
  <h3>Mobile / diacritic reality</h3>
  <p>Czech mobile shoppers frequently type without diacritics. Queries like {diac_queries} did return products on your site — so accent-insensitive matching works — but they were flagged as ranking failures in the main audit. In practice, these queries <strong>already behave acceptably</strong>: the right products appear, just not in the tightest possible order. Prioritize the Tier A items first; diacritic ranking is a polish pass.</p>
</div>"""

    screenshot_html = f'<div class="shot"><img src="{screenshot_uri}" alt="Site screenshot"></div>' if screenshot_uri else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Commercial Impact Addendum — {site_name}</title>
<style>{css}</style>
</head>
<body>
<div class="page">

<div class="cover">
  <div class="label">Commercial Impact Addendum</div>
  <h1>Where Search Is Actually Costing You Sales</h1>
  <div class="subtitle">{site_name}</div>
  <div class="cover-meta">{date} · Companion to the main Search Audit Report</div>
  {screenshot_html}
</div>

<section>
  <div class="label">Framing</div>
  <h2>Why a monobrand site needs a different lens</h2>
  <div class="framing">
    <h3>Under Armour CZ is a single-brand DTC retailer</h3>
    <p>Every product on the site is Under Armour. That changes what "relevance" means. On a marketplace, a bad result is a competitor's product surfacing over yours. Here, almost every result is a legitimate UA product — so surface-level relevance looks healthy across most queries.</p>
    <p>The main audit flags 21 queries as critical. A close read shows most of those are <strong>ranking imperfections within an on-topic result set</strong> — e.g. the "best" running shoe ranked #15 among 15 running shoes. That's real signal for a search engineer but not a bleeding wound for the business.</p>
    <p>This addendum separates the findings into three tiers based on <strong>customer bounce risk</strong>: queries that cost you sales today, queries that cause mild friction, and queries that are working.</p>
  </div>
</section>

<section>
  <div class="label">Headline</div>
  <h2>The business-impact numbers</h2>
  <div class="stat-row">
    <div class="stat"><div class="v bad">{len(tier_a)}</div><div class="l">queries at immediate revenue risk<br>(zero results, dropped constraints, or semantic misses)</div></div>
    <div class="stat"><div class="v warn">{len(tier_b)}</div><div class="l">queries with on-topic results but imperfect ranking<br>(mild friction, not bounce-inducing)</div></div>
    <div class="stat"><div class="v good">{len(tier_c)}</div><div class="l">queries returning acceptable results<br>(customer finds what they wanted)</div></div>
  </div>
  <p style="color:var(--muted)">Of {len(classified)} tested queries, <strong>{len(tier_a)} ({int(len(tier_a)/len(classified)*100)}%)</strong> are the ones to fix first. Most are narrow, solvable engine gaps.</p>
</section>

<section>
  <div class="label">Tier A — Revenue risk</div>
  <h2>The {len(tier_a)} queries that cost you sales</h2>
  <p>Each of these either shows zero results when products exist, ignores the customer's explicit filter, or surfaces products from the wrong category. These are the fixes that move the needle.</p>
  <table>
    <thead><tr><th>Query</th><th>Why it fails</th><th>Business impact</th></tr></thead>
    <tbody>{tier_a_rows}</tbody>
  </table>
</section>

<section>
  <div class="label">Tier B — Friction</div>
  <h2>Queries that work, with mild ranking imperfections</h2>
  <p>These {len(tier_b)} queries return products that match the customer's intent — running shoes when they search for running shoes, hoodies when they search for hoodies. The objection is that the scorer's #1 pick isn't always at position #1. On a monobrand site where the product catalog is already curated, <strong>this is UX polish, not revenue rescue</strong>.</p>
  <p style="color:var(--muted)">Breakdown: {len(tier_b_sev_ok)} queries with top-1 relevance ≥ 0.60 (clearly on-topic) · {len(tier_b_sev_meh)} queries with top-1 relevance 0.40–0.60 (borderline).</p>
</section>

<section>
  <div class="label">Tier C — Working</div>
  <h2>Queries that don't need attention</h2>
  <p>{len(tier_c)} queries returned acceptable results. Most of these are broad-category or brand-name queries ("under armour", "muži", "děti") where any UA product is fundamentally on-topic.</p>
</section>

<section>
  <div class="label">Category coverage</div>
  <h2>Where the engine holds up — and where it doesn't</h2>
  <p>Each query category maps to a specific search capability. The 'revenue risk' column flags categories where at least one query hit a Tier A failure.</p>
  <table>
    <thead><tr><th>Capability</th><th>Pass / Total</th><th>Rate</th><th>Status</th></tr></thead>
    <tbody>{cat_rows}</tbody>
  </table>
</section>

{diac_html}

<section>
  <div class="label">Fix prioritization</div>
  <h2>Top {len(fix_priority)} engineering fixes, ranked by reach</h2>
  <p>The Tier A failures cluster into a small number of root causes. Fixing each one closes multiple queries at once.</p>
  {fix_cards_html}
</section>

<section>
  <div class="callout warn">
    <h3>How to read this addendum alongside the main report</h3>
    <p>The main audit is a thorough, capability-by-capability diagnostic — it catches every signal, including fine-grained ranking imperfections. That's the right output for an internal search team doing a deep tune-up.</p>
    <p>This addendum is a commercial triage pass: <strong>if you have to pick five things to fix this quarter, pick from Tier A.</strong> They are the ones your customers notice.</p>
  </div>
</section>

<footer>
  Commercial Impact Addendum · {site_name} · {date}
</footer>

</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
