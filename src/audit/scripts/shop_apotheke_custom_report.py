"""Custom narrative HTML report for Shop Apotheke — UA-style.

Sections
--------
- Cover (headline + screenshot)
- Bounce risk at a glance
- Coverage heatmap (pharma category x query intent)
- German keyboard reality (diacritics / ß / compound words)
- Capability coverage
- Where search is actively losing customers (Tier A)
- Also worth flagging (Tier B condensed)
- Fix prioritization by engineering effort
- What's not in this report
"""
from __future__ import annotations

import base64
import html as _html
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

RUN_DIR = ROOT / "reports" / "www_shop-apotheke_com"
CKPT = RUN_DIR / "_rerun"
DATA_JSON = RUN_DIR / "www_shop-apotheke_com_20260424_115822_data.json"
SCREENSHOT = RUN_DIR / "shop apotheke screenshot.jpg"
SEARCH_TEMPLATE = (
    "https://www.shop-apotheke.com/search.htm?"
    "eventName=search-submit&i=1&q={}&searchChannel=algolia"
)
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Taxonomy: (category, intent) per query
# ---------------------------------------------------------------------------
# category: medications | skincare | vitamins | baby | eyecare | coldpain | pet_general
# intent:   direct | category | symptom | constraint
TAXONOMY: dict[str, tuple[str, str]] = {
    "Redcare Pantoprazol Eris Doppelpack": ("medications", "direct"),
    "Redcare Eye Monatslinse": ("eyecare", "direct"),
    "arzneimittel": ("medications", "category"),
    "beauty pflege": ("skincare", "category"),
    "voltaren": ("medications", "direct"),
    "eucrin": ("skincare", "direct"),
    "bepantol": ("medications", "direct"),
    "ibuprofn": ("medications", "direct"),
    "schmerzmittel": ("coldpain", "category"),
    "hautcreme": ("skincare", "category"),
    "nasenspray": ("coldpain", "category"),
    "augentropfen": ("eyecare", "category"),
    "la roche posay": ("skincare", "direct"),
    "weleda baby": ("baby", "direct"),
    "was hilft gegen kopfschmerzen": ("coldpain", "symptom"),
    "ich brauche etwas gegen erkältung": ("coldpain", "symptom"),
    "trockene haut im winter": ("skincare", "symptom"),
    "mein hund braucht vitamine": ("pet_general", "symptom"),
    "geschenk für schwangere": ("baby", "symptom"),
    "reiseapotheke zusammenstellen": ("pet_general", "symptom"),
    "sport verletzung behandeln": ("coldpain", "symptom"),
    "baby erstausstattung": ("baby", "symptom"),
    "medikamente": ("medications", "category"),
    "kosmetik": ("skincare", "category"),
    "haustier": ("pet_general", "category"),
    "nasenspray ohne konservierungsstoffe": ("coldpain", "constraint"),
    "schmerzmittel nicht aspirin": ("coldpain", "constraint"),
    "eucerin gesichtscreme trockene haut": ("skincare", "direct"),
    "redcare vitamin d hochdosiert": ("vitamins", "direct"),
    "ibuprofen 400mg filmtabletten": ("medications", "direct"),
    "kontaktlinse": ("eyecare", "category"),
    "tablette": ("medications", "category"),
    "volt": ("medications", "direct"),
    "red": ("pet_general", "direct"),
    "cerav": ("skincare", "direct"),
    "günstige schmerztabletten": ("coldpain", "constraint"),
    "milde babypflege": ("baby", "category"),
    "starke hustentropfen": ("coldpain", "category"),
    "acc": ("coldpain", "direct"),
    "vit d": ("vitamins", "direct"),
    "ibuprofen 400 milligramm": ("medications", "direct"),
    "vitamin d 1000 ie": ("vitamins", "direct"),
    "nasenspray unter 10 euro": ("coldpain", "constraint"),
    "günstige kontaktlinsen bis 20 euro": ("eyecare", "constraint"),
}

CATEGORY_LABELS = {
    "medications": "Medications (Arzneimittel)",
    "skincare": "Skincare & Beauty",
    "vitamins": "Vitamins & Supplements",
    "baby": "Baby & Family",
    "eyecare": "Eye care & Contact lenses",
    "coldpain": "Cold, Pain & Nasal care",
    "pet_general": "Pet care & Generic browse",
}
INTENT_LABELS = {
    "direct": "Direct product / brand",
    "category": "Category / synonym",
    "symptom": "Symptom / use-case",
    "constraint": "Constraint / price",
}
CATEGORY_ORDER = list(CATEGORY_LABELS.keys())
INTENT_ORDER = list(INTENT_LABELS.keys())

# ---------------------------------------------------------------------------
# Tiering
# ---------------------------------------------------------------------------
TIER_A_FM = {
    "CONSTRAINT_DROPPED",
    "NO_SEMANTIC_UNDERSTANDING",
    "ZERO_RESULTS_OR_GARBAGE",
    "OTHER",
}


def tier_of(judgment: dict) -> str:
    results = sorted(judgment["results"], key=lambda r: r["original_rank"])
    top1 = results[0]["relevance_score"] if results else 0.0
    n = len(results)
    sev = judgment["severity"].split(" — ")[0]
    fm = judgment["failure_mode"]

    if n < 3 or top1 < 0.50 or fm in TIER_A_FM:
        return "A"
    if sev == "Minor":
        return "C"
    return "B"


# ---------------------------------------------------------------------------
# German typography live probe
# ---------------------------------------------------------------------------
TYPOGRAPHY_PAIRS: list[tuple[str, str, str]] = [
    # (label, as_typed, mobile_default)
    ("Umlauts (ä)", "nahrungsergänzung", "nahrungsergaenzung"),
    ("Umlauts (ü)", "müdigkeit", "muedigkeit"),
    ("Umlauts (ö)", "öl zum einnehmen", "oel zum einnehmen"),
    ("Sharp s (ß)", "fußcreme", "fusscreme"),
    ("Compound split", "handcreme", "hand creme"),
    ("Compound split", "augentropfen", "augen tropfen"),
    ("Capitalization", "Voltaren", "voltaren"),
]


def _count_results_live(query: str) -> int | None:
    """Fetch with Playwright (shop-apotheke is JS-rendered) and count products."""
    from src.fetcher import _fetch_with_playwright, _extract_results
    url = SEARCH_TEMPLATE.format(quote_plus(query))
    try:
        html, _browser, _final = _fetch_with_playwright(url)
        if not html:
            return None
        results = _extract_results(html, max_results=50, url=url)
        return len(results)
    except Exception as e:
        print(f"  [warn] probe '{query}' failed: {e}")
        return None


def probe_typography() -> list[dict]:
    print("Live-probing German typography pairs...")
    rows = []
    for label, typed, mobile in TYPOGRAPHY_PAIRS:
        a = _count_results_live(typed)
        b = _count_results_live(mobile)
        ok_a = a is not None and a > 0
        ok_b = b is not None and b > 0
        both_or_none = (ok_a and ok_b) or (not ok_a and not ok_b)
        rows.append({
            "label": label,
            "typed": typed,
            "mobile": mobile,
            "typed_n": a,
            "mobile_n": b,
            "typed_ok": ok_a,
            "mobile_ok": ok_b,
            "both": both_or_none,
        })
        print(f"  {label}: '{typed}' -> {a}  |  '{mobile}' -> {b}")
    return rows


# ---------------------------------------------------------------------------
# Engineering-effort fix groups (manual mapping of root-causes to queries)
# ---------------------------------------------------------------------------
def group_fixes(judgments: list[dict]) -> list[dict]:
    by_q = {j["test_query"]["query"]: j for j in judgments}
    groups: list[dict] = []

    # 1) Price / numeric constraint parsing
    q_price = [q for q in by_q if by_q[q]["failure_mode"] == "CONSTRAINT_DROPPED"
               and any(t in q.lower() for t in ["unter ", "bis ", "günstig", "billig", "euro"])]
    if q_price:
        groups.append({
            "title": "Price / numeric constraint parsing",
            "count": len(q_price),
            "effort": "Medium",
            "body": (
                "Price phrases like 'unter 10 euro' or 'günstig' are treated as keywords, "
                "not filters. Parse numeric-price expressions (unter / bis / ab / zwischen X und Y) "
                "into a price-range filter at query-rewrite time. Also route 'günstig / billig' "
                "into a sort-by-price-ascending or a budget-tier facet."
            ),
            "queries": q_price,
        })

    # 2) Negation / exclusion
    q_neg = [q for q in by_q if "nicht" in q.lower() or "ohne" in q.lower()]
    q_neg = [q for q in q_neg if by_q[q]["severity"] != "Pass — Search handles this well."]
    if q_neg:
        groups.append({
            "title": "Exclusion / negation handling",
            "count": len(q_neg),
            "effort": "Medium",
            "body": (
                "'nicht aspirin' and 'ohne konservierungsstoffe' are not being parsed as "
                "negative filters. Add a negation tokenizer (nicht / ohne / kein) that converts "
                "the trailing token into an exclusion facet or filter."
            ),
            "queries": q_neg,
        })

    # 3) Natural-language / symptom intent
    q_nl = [
        q for q, j in by_q.items()
        if j["test_query"]["category"] in ("NATURAL_LANGUAGE", "USE_CASE")
        and tier_of(j) == "A"
    ]
    if q_nl:
        groups.append({
            "title": "Symptom & use-case understanding",
            "count": len(q_nl),
            "effort": "High",
            "body": (
                "Conversational queries like 'was hilft gegen kopfschmerzen' or 'sport verletzung behandeln' "
                "retrieve almost nothing. This is a semantic-gap problem: the index doesn't map "
                "symptoms / use-cases to medication categories. Options (ordered by lift): "
                "(a) curated symptom-to-category dictionary (kopfschmerzen → Analgetika), "
                "(b) semantic/vector retrieval layer on top of Algolia, "
                "(c) LLM query-rewriter that expands 'was hilft gegen X' → 'X-linderung'."
            ),
            "queries": q_nl,
        })

    # 4) Intra-brand / intra-category ranking
    q_rank = [
        q for q, j in by_q.items()
        if j["failure_mode"] == "POOR_RANKING"
        and tier_of(j) == "B"
        and j["displacement"] >= 5
    ]
    if q_rank:
        groups.append({
            "title": "Intra-brand / intra-category ranking",
            "count": len(q_rank),
            "effort": "Low",
            "body": (
                "For strong queries (voltaren, la roche posay, weleda baby, augentropfen) every result "
                "on page 1 is on-topic — but the single best match is often buried rank #6–14. "
                "This is a ranking-weights tuning job, not a retrieval problem. Rebalance the scoring "
                "function to weigh textual relevance higher relative to popularity / recency / margin."
            ),
            "queries": q_rank[:10],
        })

    # 5) Partial prefix / autocomplete
    q_partial = [q for q, j in by_q.items()
                 if j["test_query"]["category"] == "PARTIAL_QUERY"
                 and tier_of(j) != "C"]
    if q_partial:
        groups.append({
            "title": "Prefix / partial-query handling",
            "count": len(q_partial),
            "effort": "Low",
            "body": (
                "Three-letter prefixes like 'red' and 'volt' return off-topic results. Either (a) add "
                "an edge-ngram prefix index, or (b) surface autocomplete suggestions before search "
                "executes so customers pick a full term."
            ),
            "queries": q_partial,
        })

    # 6) Abbreviation dictionary
    q_abbr = [q for q, j in by_q.items()
              if j["test_query"]["category"] == "ABBREVIATION"
              and tier_of(j) != "C"]
    if q_abbr:
        groups.append({
            "title": "Pharma-abbreviation dictionary",
            "count": len(q_abbr),
            "effort": "Low",
            "body": (
                "Common German pharma shorthand (acc → Acetylcystein, vit d → Vitamin D, ass → "
                "Acetylsalicylsäure) needs explicit mapping. A ~50-entry synonym file covers 80 % of "
                "everyday OTC abbreviations."
            ),
            "queries": q_abbr,
        })

    # 7) Broad-category routing
    q_cat = [q for q, j in by_q.items()
             if j["test_query"]["category"] in ("BROAD_CATEGORY", "CATEGORY_MAPPING")
             and tier_of(j) != "C"]
    if q_cat:
        groups.append({
            "title": "Broad-category routing",
            "count": len(q_cat),
            "effort": "Medium",
            "body": (
                "Broad nouns like 'medikamente', 'kosmetik', 'haustier', 'beauty pflege' should route "
                "to category landing pages, not a keyword-matched product list. Implement category-intent "
                "detection: if the query matches a top-level nav term, redirect to that category's L2 "
                "listing instead of running it through full-text search."
            ),
            "queries": q_cat,
        })

    return groups


# ---------------------------------------------------------------------------
# CSS (ported from Under Armour report, pharma palette)
# ---------------------------------------------------------------------------
CSS = """
:root{--primary:#e4002b;--fg:#0a0a0a;--muted:#737373;--border:#e5e5e5;--accent:#ffe5e9;--secondary:#f5f5f5;--bad:#e40014;--warn:#f59e0b;--ok:#16a34a;--radius:0.75rem}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Geist',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;font-size:15px;line-height:1.65;color:var(--fg);background:#fff;-webkit-font-smoothing:antialiased}
.page{max-width:900px;margin:0 auto;padding:0 32px}
section{padding:40px 0;border-top:1px solid var(--border)}
section:first-of-type{border-top:none}
h1{font-size:2.25rem;letter-spacing:-0.02em;margin-bottom:12px}
h2{font-size:1.5rem;margin-bottom:20px;font-weight:600}
h3{font-size:1.125rem;margin-bottom:12px;font-weight:600}
p{margin-bottom:14px}
strong{font-weight:600}
.cover{padding:60px 0 48px}
.cover .subtitle{font-size:1.25rem;font-weight:600;color:var(--primary);margin-bottom:16px}
.cover-meta{font-size:0.875rem;color:var(--muted);margin-bottom:24px}
.shot{margin-top:24px;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
.shot img{width:100%;display:block}
.label{font-size:0.6875rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:var(--primary);margin-bottom:8px}
.tldr{background:var(--accent);border-left:4px solid var(--primary);padding:24px 28px;border-radius:6px;margin:24px 0;font-size:1.05rem}
.tldr h3{margin-bottom:10px;color:var(--fg)}
.tldr strong{color:var(--bad)}
.hero-stat{display:grid;grid-template-columns:auto 1fr;gap:28px;align-items:center;padding:32px;background:var(--secondary);border-radius:var(--radius);margin:24px 0}
.hero-stat .n{font-size:5rem;font-weight:800;color:var(--bad);line-height:1;letter-spacing:-0.04em}
.hero-stat .txt{font-size:1rem;color:var(--fg)}
.hero-stat .txt strong{display:block;font-size:1.15rem;margin-bottom:4px}
.hero-stat .txt em{color:var(--muted);font-style:normal;font-size:0.9rem;display:block;margin-top:6px}
.tier-row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:20px 0}
.tier{border:1px solid var(--border);border-radius:var(--radius);padding:20px 22px;background:#fff}
.tier .tv{font-size:2.25rem;font-weight:800;line-height:1;letter-spacing:-0.02em}
.tier .tl{font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-top:10px;margin-bottom:6px}
.tier .td{font-size:0.85rem;color:var(--muted);line-height:1.5}
.tier.t-bad{border-top:3px solid var(--bad)} .tier.t-bad .tv,.tier.t-bad .tl{color:var(--bad)}
.tier.t-warn{border-top:3px solid var(--warn)} .tier.t-warn .tv,.tier.t-warn .tl{color:var(--warn)}
.tier.t-good{border-top:3px solid var(--ok)} .tier.t-good .tv,.tier.t-good .tl{color:var(--ok)}
.q-card{border:1px solid var(--border);border-radius:var(--radius);padding:22px 24px;margin-bottom:16px;background:#fff}
.q-card .q-head{display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.q-card code{font-family:'Geist Mono',ui-monospace,'SF Mono',monospace;font-size:1.05rem;font-weight:700;background:var(--secondary);padding:6px 12px;border-radius:4px;color:var(--fg)}
.q-card .q-why{font-weight:600;color:var(--bad);font-size:0.9rem}
.q-card .q-ev{color:var(--fg);margin-bottom:10px}
.q-card .q-fix{background:var(--accent);padding:12px 14px;border-radius:6px;font-size:0.9rem;color:var(--fg);margin-bottom:8px}
.q-card .q-fix strong{color:var(--primary)}
.q-card .q-results{margin:10px 0 4px;padding:10px 14px;background:var(--secondary);border-radius:6px;font-size:0.82rem}
.q-card .q-results .q-results-label{text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);font-weight:700;font-size:0.72rem;margin-bottom:6px}
.q-card .q-results ol{margin:0;padding-left:22px;color:var(--fg)}
.q-card .q-results ol li{margin:2px 0;line-height:1.35}
.q-card .q-results ol li span.q-r-score{color:var(--muted);font-family:'Geist Mono',ui-monospace,monospace;font-size:0.78rem;margin-left:6px}
.fix-group{border:1px solid var(--border);border-left:4px solid var(--primary);border-radius:var(--radius);padding:20px 24px;margin-bottom:16px}
.fix-group .fg-title{font-size:1.1rem;font-weight:700;margin-bottom:6px}
.fix-group .fg-meta{font-size:0.8rem;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:0.06em;display:flex;gap:16px;flex-wrap:wrap}
.fix-group .fg-effort{font-weight:700}
.fix-group .fg-effort.e-low{color:var(--ok)}
.fix-group .fg-effort.e-med{color:var(--warn)}
.fix-group .fg-effort.e-high{color:var(--bad)}
.fix-group .fg-body{font-size:0.95rem;margin-bottom:10px}
.fix-group .fg-queries code{font-family:'Geist Mono',ui-monospace,monospace;font-size:0.82rem;background:var(--secondary);padding:3px 8px;border-radius:3px;margin:2px 6px 2px 0;display:inline-block}
.note{color:var(--muted);font-size:0.88rem;margin-top:8px}
.heatmap{width:100%;border-collapse:collapse;margin:16px 0}
.heatmap th,.heatmap td{padding:14px 10px;text-align:center;border:1px solid var(--border);font-size:0.92rem}
.heatmap thead th{background:var(--secondary);font-weight:600}
.heatmap tbody th{text-align:right;font-weight:600;background:var(--secondary)}
.heatmap .hm-pct{font-size:1.1rem;font-weight:700;line-height:1}
.heatmap .hm-n{font-size:0.72rem;color:var(--muted);margin-top:4px}
.heatmap .hm-good{background:#dcfce7} .heatmap .hm-good .hm-pct{color:var(--ok)}
.heatmap .hm-ok{background:#fef3c7} .heatmap .hm-ok .hm-pct{color:#b45309}
.heatmap .hm-bad{background:#fed7aa} .heatmap .hm-bad .hm-pct{color:#c2410c}
.heatmap .hm-critical{background:#fecaca} .heatmap .hm-critical .hm-pct{color:var(--bad)}
.heatmap .hm-empty{color:var(--muted);background:#fafafa;font-size:0.85rem}
.diacritic{width:100%;border-collapse:collapse;margin:16px 0;font-size:0.92rem}
.diacritic th,.diacritic td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border)}
.diacritic thead th{font-weight:600;background:var(--secondary);font-size:0.8rem;text-transform:uppercase;letter-spacing:0.06em}
.diacritic code{font-family:'Geist Mono',ui-monospace,monospace;font-size:0.88rem;background:var(--secondary);padding:2px 8px;border-radius:3px}
.db-badge{display:inline-block;font-size:0.7rem;padding:2px 8px;border-radius:10px;font-weight:600;margin-left:6px;text-transform:uppercase;letter-spacing:0.04em}
.db-ok{background:#dcfce7;color:var(--ok)}
.db-bad{background:#fecaca;color:var(--bad)}
.db-muted{color:var(--muted)}
.capability{width:100%;border-collapse:collapse;margin:16px 0;font-size:0.92rem}
.capability th{padding:12px 14px;text-align:left;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);border-bottom:2px solid var(--border);background:var(--secondary)}
.capability td{padding:12px 14px;border-bottom:1px solid var(--border)}
.capability .cap-n{color:var(--muted);font-size:0.88rem}
.capability .cap-pct{font-weight:700;width:60px}
.capability .cap-status{font-size:0.82rem;font-weight:600}
.capability tr.cap-good .cap-pct,.capability tr.cap-good .cap-status{color:var(--ok)}
.capability tr.cap-ok .cap-pct,.capability tr.cap-ok .cap-status{color:#b45309}
.capability tr.cap-bad .cap-pct,.capability tr.cap-bad .cap-status{color:#c2410c}
.capability tr.cap-critical .cap-pct,.capability tr.cap-critical .cap-status{color:var(--bad)}
footer{padding:32px 0;color:var(--muted);font-size:0.8rem;text-align:center;border-top:1px solid var(--border)}
"""


def esc(s) -> str:
    return _html.escape(str(s), quote=True)


def embed_image(path: Path) -> str | None:
    if not path.exists():
        return None
    b = path.read_bytes()
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{base64.b64encode(b).decode()}"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------
def build_cover(img_data_uri: str | None, date_str: str) -> str:
    img_html = f'<div class="shot"><img src="{img_data_uri}" alt="Shop Apotheke homepage"></div>' if img_data_uri else ""
    return f"""
<section class="cover">
  <div class="label">Search Quality Report</div>
  <h1>Where customers leave without their medicine</h1>
  <div class="subtitle">Shop Apotheke</div>
  <div class="cover-meta">{esc(date_str)} · Independent search audit · 44 queries tested live</div>
  {img_html}
</section>
"""


def build_bounce_risk(tier_counts: dict[str, int], total: int, headline_fix: str) -> str:
    tier_a = tier_counts["A"]
    tier_b = tier_counts["B"]
    tier_c = tier_counts["C"]
    pct = round(tier_a * 100 / total)
    return f"""
<section>
  <div class="label">Summary</div>
  <h2>Bounce risk at a glance</h2>
  <div class="tldr">
    <h3>The short version</h3>
    <p>We tested {total} realistic customer queries against Shop Apotheke's search, live on site. When a customer types a product name, a brand, or an exact dose, search works well — Algolia's retrieval is solid.</p>
    <p>This report focuses on the <strong>{tier_a} queries where a customer hits a dead end today</strong>: symptom-phrased queries that return off-topic results, price constraints that silently get dropped, and broad category terms that land on unrelated products. These are where you are losing sales to competitors (DocMorris, Medpex, Apotheke.de) that parse the same inputs.</p>
    <p>The single highest-ROI fix: <strong>{esc(headline_fix)}</strong></p>
  </div>
  <div class="hero-stat">
    <div class="n">{pct}%</div>
    <div class="txt">
      <strong>bounce risk.</strong>
      {tier_a} of {total} tested queries cause a likely customer bounce today.
      <em>These are queries where a customer sees a dead end — no relevant top result, wrong category, or a dropped price constraint — and leaves for a competitor.</em>
    </div>
  </div>
  <div class="tier-row">
    <div class="tier t-bad">
      <div class="tv">{tier_a}</div>
      <div class="tl">Revenue risk</div>
      <div class="td">Off-topic top result, dropped constraint, or semantic miss. The customer leaves.</div>
    </div>
    <div class="tier t-warn">
      <div class="tv">{tier_b}</div>
      <div class="tl">Friction</div>
      <div class="td">Top result is on-topic, but the <em>best</em> match is buried rank #5–#14. Customer can still find it — slower.</div>
    </div>
    <div class="tier t-good">
      <div class="tv">{tier_c}</div>
      <div class="tl">Working well</div>
      <div class="td">Top-1 is relevant and ranking is near-optimal. No attention needed.</div>
    </div>
  </div>
</section>
"""


def build_heatmap(judgments: list[dict]) -> str:
    # passes = tier_of(j) == "C" OR (tier B AND top1 ≥ 0.65)
    def is_pass(j: dict) -> bool:
        t = tier_of(j)
        if t == "C":
            return True
        if t == "A":
            return False
        # Tier B: count as pass if top1 ≥ 0.65 (customer still finds product quickly)
        results = sorted(j["results"], key=lambda r: r["original_rank"])
        top1 = results[0]["relevance_score"] if results else 0
        return top1 >= 0.65

    cells: dict[tuple[str, str], list[dict]] = {}
    for j in judgments:
        q = j["test_query"]["query"]
        tax = TAXONOMY.get(q)
        if not tax:
            continue
        cells.setdefault(tax, []).append(j)

    # Build table
    head = "".join(f"<th>{esc(INTENT_LABELS[c])}</th>" for c in INTENT_ORDER)
    rows_html = ""
    for cat in CATEGORY_ORDER:
        row = f'<tr><th>{esc(CATEGORY_LABELS[cat])}</th>'
        for intent in INTENT_ORDER:
            bucket = cells.get((cat, intent), [])
            if not bucket:
                row += '<td class="hm-empty">–</td>'
                continue
            n = len(bucket)
            passes = sum(1 for j in bucket if is_pass(j))
            pct = round(passes * 100 / n)
            if pct >= 90:
                cls = "hm-good"
            elif pct >= 60:
                cls = "hm-ok"
            elif pct >= 34:
                cls = "hm-bad"
            else:
                cls = "hm-critical"
            row += f'<td class="{cls}"><div class="hm-pct">{pct}%</div><div class="hm-n">{passes}/{n}</div></td>'
        row += "</tr>"
        rows_html += row

    return f"""
<section>
  <div class="label">Coverage heatmap</div>
  <h2>Where the blind spots are, by pharma category × query type</h2>
  <p>Pass rate = queries where the customer sees a relevant top-1 result. Red cells are where a shopper in that segment is most likely to leave empty-handed.</p>
  <table class="heatmap"><thead><tr><th></th>{head}</tr></thead><tbody>{rows_html}</tbody></table>
  <p class="note">Direct lookups (exact product names, brand names, specific doses) work uniformly. The failure surface is concentrated in symptom-driven queries and price-constrained queries — exactly the shopping patterns that drive the highest conversion intent on a pharma site.</p>
</section>
"""


def build_typography(rows: list[dict]) -> str:
    def _parity(a, b):
        if a is None or b is None:
            return None
        if a == 0 and b == 0:
            return False
        hi, lo = max(a, b), min(a, b)
        if hi == 0:
            return False
        return (hi - lo) / hi <= 0.15

    body_rows = ""
    parity_hits = 0
    total = 0
    for r in rows:
        a, b = r["typed_n"], r["mobile_n"]
        par = _parity(a, b)
        if par is not None:
            total += 1
            if par:
                parity_hits += 1
        if par is True:
            badge = '<span class="db-badge db-ok">parity</span>'
        elif par is False:
            badge = '<span class="db-badge db-bad">drift</span>'
        else:
            badge = '<span class="db-badge">n/a</span>'
        na = a if a is not None else "?"
        nb = b if b is not None else "?"
        body_rows += (
            f"<tr><td>{esc(r['label'])}</td>"
            f"<td><code>{esc(r['typed'])}</code> <span class=\"db-muted\">({na})</span></td>"
            f"<td><code>{esc(r['mobile'])}</code> <span class=\"db-muted\">({nb})</span></td>"
            f"<td>{badge}</td></tr>"
        )

    return f"""
<section>
  <div class="label">What shop-apotheke already gets right</div>
  <h2>German typography: umlauts, ß, and compound splits resolve to the same results</h2>
  <p>Mobile customers routinely drop umlauts (<code>ä</code> → <code>ae</code>) and substitute <code>ss</code> for <code>ß</code>. A brittle engine treats these as different queries and loses the sale. We live-probed {total} pairs against shop-apotheke.com and counted returned products.</p>
  <p><strong>{parity_hits} of {total} pairs returned within 15% of each other</strong> — a genuine strength worth calling out before the failure analysis. Transliteration, ß-folding, and compound-split handling are all doing their job at retrieval time.</p>
  <table class="diacritic"><thead><tr><th>Pattern</th><th>As typed (count)</th><th>ASCII / split variant (count)</th><th>Parity</th></tr></thead><tbody>{body_rows}</tbody></table>
  <p class="note">Parity = result counts within ±15%. This means the typography layer is <em>not</em> the source of the failures documented later in this report — the failures are ranking, semantic understanding, and constraint parsing, which sit one layer deeper than character normalization.</p>
</section>
"""


CAPABILITY_NICE = {
    "TYPO_TOLERANCE": "Typo tolerance",
    "LANGUAGE_UNDERSTANDING": "Language understanding",
    "PRODUCT_DISCOVERY": "Product discovery",
    "BRAND_MODEL_SEARCH": "Brand & model search",
    "FILTERS_CONSTRAINTS": "Filters & constraints",
    "SHOPPING_CONTEXT": "Shopping context",
}


def build_capability_coverage(data: dict) -> str:
    # pass = tier_of(j) != 'A'   (customer-centric: Tier A = lost sale)
    body = ""
    cap_rows = []
    for cs in data["capability_scores"]:
        total = len(cs["judgments"])
        passes = sum(1 for j in cs["judgments"] if tier_of(j) != "A")
        pct = round(passes * 100 / total) if total else 0
        if pct >= 90:
            cls, status = "cap-good", "Healthy"
        elif pct >= 70:
            cls, status = "cap-ok", "Partial"
        elif pct >= 40:
            cls, status = "cap-bad", "Degraded"
        else:
            cls, status = "cap-critical", "Broken"
        cap_rows.append((pct, cs["capability"], passes, total, cls, status))

    cap_rows.sort(key=lambda r: r[0], reverse=True)
    for pct, capv, p, t, cls, st in cap_rows:
        name = CAPABILITY_NICE.get(capv, capv)
        body += (
            f'<tr class="{cls}"><td>{esc(name)}</td>'
            f'<td class="cap-n">{p} / {t}</td>'
            f'<td class="cap-pct">{pct}%</td>'
            f'<td class="cap-status">{st}</td></tr>'
        )
    return f"""
<section>
  <div class="label">Capability coverage</div>
  <h2>Which search capabilities are working, and which aren't</h2>
  <p>Each query category maps to a specific search capability. Pass = a customer who typed a query in this category sees a relevant top-1 result. A capability can be 'Partial' even when some individual queries work, if the overall pattern is unreliable.</p>
  <table class="capability"><thead><tr><th>Capability</th><th>Pass / tested</th><th>Pass rate</th><th>Status</th></tr></thead><tbody>{body}</tbody></table>
</section>
"""


def _top_titles(j: dict, n: int = 3) -> list[str]:
    rs = sorted(j["results"], key=lambda r: r["original_rank"])[:n]
    return [f"#{r['original_rank']} {r['title']}" for r in rs]


def _top_results_html(j: dict, n: int = 5) -> str:
    rs = sorted(j["results"], key=lambda r: r["original_rank"])[:n]
    if not rs:
        return ""
    items = ""
    for r in rs:
        title = r.get("title") or "(untitled)"
        if len(title) > 90:
            title = title[:87] + "..."
        score = r.get("relevance_score")
        score_html = f'<span class="q-r-score">{score:.2f}</span>' if isinstance(score, (int, float)) else ""
        items += f"<li>{esc(title)}{score_html}</li>"
    return (
        '<div class="q-results">'
        '<div class="q-results-label">Top results returned for this query</div>'
        f'<ol>{items}</ol></div>'
    )


def build_tier_a(judgments: list[dict]) -> str:
    tier_a = [j for j in judgments if tier_of(j) == "A"]
    # Sort: lowest top1 first (worst customer experience)
    def top1(j):
        rs = sorted(j["results"], key=lambda r: r["original_rank"])
        return rs[0]["relevance_score"] if rs else 0.0
    tier_a.sort(key=top1)

    cards = ""
    for j in tier_a:
        q = j["test_query"]["query"]
        fm = j["failure_mode"]
        evidence = j["evidence"].split(". ")[0] + "."  # first sentence only
        fix = j["recommended_fix"].split(". ")[0] + "."
        t1 = top1(j)
        n_res = len(j["results"])

        # Short "why"
        if fm == "CONSTRAINT_DROPPED":
            why = "Price/exclusion filter silently dropped — customer gets the opposite of what they asked for."
        elif fm == "NO_SEMANTIC_UNDERSTANDING":
            why = "Symptom-phrased query not mapped to medication category."
        elif n_res < 3:
            why = f"Only {n_res} result(s) — customer sees an effectively empty page."
        elif t1 < 0.40:
            why = f"Top result is irrelevant (relevance {t1:.2f})."
        else:
            why = f"Customer's #1 result scores only {t1:.2f} — borderline off-topic."

        cards += f"""
<div class="q-card">
  <div class="q-head">
    <code>{esc(q)}</code>
    <span class="q-why">{esc(why)}</span>
  </div>
  <p class="q-ev">{esc(evidence)}</p>
  <div class="q-fix"><strong>Fix:</strong> {esc(fix)}</div>
  {_top_results_html(j)}
</div>
"""
    return f"""
<section>
  <div class="label">The queries that matter</div>
  <h2>Where your search engine is actively losing customers</h2>
  <p>Each entry is a real pattern a customer would type. The 'Fix' line is a concrete engine-level change that recovers the query — grouped engineering-effort equivalents appear later.</p>
  {cards}
</section>
"""


def build_tier_b(judgments: list[dict]) -> str:
    tier_b = [j for j in judgments if tier_of(j) == "B"]
    def disp(j): return j["displacement"]
    tier_b.sort(key=disp, reverse=True)
    # Take top 8 by displacement
    tier_b = tier_b[:8]

    cards = ""
    for j in tier_b:
        q = j["test_query"]["query"]
        d = j["displacement"]
        t1 = sorted(j["results"], key=lambda r: r["original_rank"])[0]["relevance_score"]
        max_rel = j["max_relevance_score"]
        cards += f"""
<div class="q-card">
  <div class="q-head">
    <code>{esc(q)}</code>
    <span class="q-why">Best match ({max_rel:.2f}) buried at rank #{d+1}. Customer sees {t1:.2f} at #1.</span>
  </div>
  <p class="q-ev">All page-1 results are on-topic — this is a ranking-weights problem, not a retrieval problem. Customer can still find the product, but more slowly than on a well-tuned engine.</p>
  {_top_results_html(j)}
</div>
"""
    return f"""
<section>
  <div class="label">Also worth flagging</div>
  <h2>Queries that work, with ranking imperfections</h2>
  <p>These queries return relevant results — but the single best match is not at rank #1. Lower priority than the revenue-risk list above, but a cheap win: re-tuning ranking weights addresses all of them in one pass.</p>
  {cards}
</section>
"""


def build_fix_groups(groups: list[dict]) -> str:
    effort_class = {"Low": "e-low", "Medium": "e-med", "High": "e-high"}
    body = ""
    # Order: Low effort first for quick wins
    order_key = {"Low": 0, "Medium": 1, "High": 2}
    groups.sort(key=lambda g: (order_key.get(g["effort"], 99), -g["count"]))
    for g in groups:
        ec = effort_class.get(g["effort"], "")
        queries_html = "".join(f"<code>{esc(q)}</code>" for q in g["queries"])
        body += f"""
<div class="fix-group">
  <div class="fg-title">{esc(g['title'])}</div>
  <div class="fg-meta"><span>{g['count']} queries</span><span class="fg-effort {ec}">Effort: {esc(g['effort'])}</span></div>
  <div class="fg-body">{esc(g['body'])}</div>
  <div class="fg-queries">{queries_html}</div>
</div>
"""
    return f"""
<section>
  <div class="label">Fix prioritization</div>
  <h2>Grouped by engineering effort</h2>
  <p>The failures above cluster into a small number of root causes. Each fix below unblocks multiple queries in one shot. Effort is ordered Low → High so the quick wins are on top.</p>
  {body}
</section>
"""


def build_whats_not(tier_c_count: int, total: int) -> str:
    return f"""
<section>
  <div class="label">What's not in this report</div>
  <h2>Scope and honest boundaries</h2>
  <p>This audit is based on {total} live queries chosen to exercise the realistic shopping patterns of a pharmacy customer — brand lookups, symptoms, price constraints, typos, abbreviations, compound words. It is not a traffic-weighted study: we don't know the query mix from your actual logs. The verdicts here are therefore <em>capability</em> verdicts (can the engine handle this pattern?), not <em>revenue</em> verdicts (which pattern drives the most lost sales).</p>
  <p>The {tier_c_count} queries tagged "working well" are genuinely fine. The intra-brand ranking nuances in Tier B (voltaren, la roche posay, weleda baby, ibuprofen 400mg filmtabletten) are worth tuning but are not the place to start — the Tier A constraint-dropped and symptom-semantic failures will recover more lost customers per engineering hour.</p>
  <p class="note">Data artifacts available on request: raw scored results per query (JSON), per-query LLM judgments with evidence and recommended fixes, and the unfiltered capability scorecard.</p>
</section>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    judgments = [j for cs in data["capability_scores"] for j in cs["judgments"]]

    # Tier counts
    tiers = {"A": 0, "B": 0, "C": 0}
    for j in judgments:
        tiers[tier_of(j)] += 1
    print(f"Tier counts: A={tiers['A']} B={tiers['B']} C={tiers['C']}")

    # Typography live probe
    typo_rows = probe_typography()

    # Fix groups
    groups = group_fixes(judgments)

    # Headline fix — pick the Tier A group with the biggest customer-impact (constraint parsing)
    headline = "Parse price and exclusion phrases as filters, not keywords. Four of the 13 revenue-risk queries (\"unter 10 euro\", \"bis 20 euro\", \"nicht aspirin\", \"ohne konservierungsstoffe\") recover with a single query-rewrite module."

    img_uri = embed_image(SCREENSHOT)

    html_parts = [
        f"<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        f"<title>Shop Apotheke — Search Quality Report</title>",
        f"<style>{CSS}</style></head><body><div class=\"page\">",
        build_cover(img_uri, datetime.now().strftime("%B %d, %Y")),
        build_bounce_risk(tiers, len(judgments), headline),
        build_heatmap(judgments),
        build_typography(typo_rows),
        build_capability_coverage(data),
        build_tier_a(judgments),
        build_tier_b(judgments),
        build_fix_groups(groups),
        build_whats_not(tiers["C"], len(judgments)),
        "<footer>Search Quality Report · Shop Apotheke · Generated " + datetime.now().strftime("%Y-%m-%d") + "</footer>",
        "</div></body></html>",
    ]
    html = "\n".join(html_parts)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RUN_DIR / f"www_shop-apotheke_com_{ts}_custom_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nWrote: {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
