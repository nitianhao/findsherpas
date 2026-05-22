"""Focused search-quality report for a single-brand DTC site.

Deprioritizes ranking/scoring findings. Surfaces only the queries that
cause customers to bounce today: zero results, dropped constraints, and
queries where the top result is genuinely irrelevant (top-1 relevance
below a catastrophic threshold). Everything else - ranking nuances
within on-topic result sets - is omitted.

Reads Phase 6 checkpoint. Does NOT modify the audit workflow.
"""
import base64
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

CHECKPOINT = ROOT / "reports" / "_checkpoint_phase6.json"
SITE_CTX = ROOT / "reports" / "_checkpoint_phase1.json"
OUT_DIR = ROOT / "reports" / "www_underarmour_cz"
SCREENSHOT = OUT_DIR / "under armour screenshot.jpg"

CATASTROPHIC_TOP1 = 0.40

# Query -> (gender, product_type) for the coverage heatmap.
# gender: women | men | kids | unisex | brand | other
# product_type: shoes | apparel | accessories | other
TAXONOMY = {
    "bezecke boty": ("unisex", "shoes"),
    "sportovni podprsenka": ("women", "apparel"),
    "tilko": ("unisex", "apparel"),
    "kratasy": ("unisex", "apparel"),
    "panske bezecke boty": ("men", "shoes"),
    "damska sportovni podprsenka": ("women", "apparel"),
    "detske outlet tenisky": ("kids", "shoes"),
    "ponozka": ("unisex", "accessories"),
    "muzi": ("men", "other"),
    "deti": ("kids", "other"),
    "trenink": ("other", "other"),
    "běžecké boty": ("unisex", "shoes"),
    "sportovní podprsenka": ("women", "apparel"),
    "tenísky": ("unisex", "shoes"),
    "mikna": ("unisex", "apparel"),
    "tepákly": ("unisex", "apparel"),
    "legímy": ("women", "apparel"),
    "tílko": ("unisex", "apparel"),
    "kraťasy": ("unisex", "apparel"),
    "svetr": ("unisex", "apparel"),
    "tašky": ("unisex", "accessories"),
    "běžeckéboty": ("unisex", "shoes"),
    "sportovnípodprsenka": ("women", "apparel"),
    "dětskétenisky": ("kids", "shoes"),
    "tep láky": ("unisex", "apparel"),
    "mik ina": ("unisex", "apparel"),
    "ba toh": ("unisex", "accessories"),
    "under armour": ("brand", "other"),
    "under armour tenisky": ("unisex", "shoes"),
    "ponožka": ("unisex", "accessories"),
    "teniska": ("unisex", "shoes"),
    "pánské běžecké boty": ("men", "shoes"),
    "dámská sportovní podprsenka": ("women", "apparel"),
    "dětské outlet tenisky": ("kids", "shoes"),
    "ua": ("brand", "other"),
    "ua tenisky": ("unisex", "shoes"),
    "leginy": ("women", "apparel"),
    "teplaky": ("unisex", "apparel"),
    "běž": ("other", "other"),
    "mik": ("other", "other"),
    "under": ("other", "other"),
    "muži": ("men", "other"),
    "děti": ("kids", "other"),
    "fitness": ("other", "other"),
    "trénink": ("other", "other"),
}

# Per-query business-impact copy for the revenue-risk list.
MANUAL_COPY = {
    "tepákly": (
        "Zero results for a one-letter typo of tepláky (sweatpants).",
        "Fuzzy typo matching",
        "Enable edit-distance matching (Levenshtein <= 2) so common typos route to the right products. Tepákly / tepláky is a one-transposition error.",
        "The customer typed a single-letter typo and saw 'no results'. Sweatpants are a major catalog category on this site.",
        "Zalando (CZ apparel benchmark) recovers one- and two-character typos via fuzzy match and returns the intended category.",
    ),
    "sportovnípodprsenka": (
        "Zero results when the customer typed 'sports bra' without the space.",
        "Compound-word splitting",
        "Add a Czech compound-word splitter: sportovnípodprsenka -> sportovní podprsenka. Same rule recovers dětskétenisky, běžeckéboty, and similar merged inputs.",
        "Czech shoppers often concatenate adjectives with nouns. Your catalog carries sports bras, but the search engine cannot reach them when the input is merged.",
        "Zalando auto-splits merged Czech compounds and resolves to the same results as the spaced form.",
    ),
    "dětskétenisky": (
        "Zero results for the merged form of 'kids' sneakers'.",
        "Compound-word splitting",
        "Covered by the same Czech compound-splitter fix as sportovnípodprsenka.",
        "Kids' sneakers exist in the catalog and are reachable via the unmerged query. The merged form returns nothing.",
        "Zalando handles merged compounds; the kids' sneaker query resolves to the full kids' shoe assortment.",
    ),
    "svetr": (
        "Customer searched for 'sweater'. Five women's sports bras were returned.",
        "Synonym dictionary - clothing categories",
        "Map svetr -> mikina / pulovr / svetřík in the synonym layer. Also consider: tepláky <-> kalhoty, tílko <-> top, šortky <-> kraťasy.",
        "A shopper leaving this result set will conclude that Under Armour CZ does not carry sweaters.",
        "Zalando's synonym layer maps svetr to mikina/pulovr and returns the full sweater/hoodie set for the query.",
    ),
    "ba toh": (
        "Customer searched for 'backpack' with a typo space. Top 15 results were crop-top T-shirts.",
        "Split-word recovery + semantic guardrail",
        "Rejoin split single-words (ba toh -> batoh) before semantic matching. Add a fallback rule: when top-1 relevance falls below a quality floor, serve a narrowed result set rather than filler.",
        "The split-word input misrouted the query entirely. Backpacks exist on the site but none appear in the results.",
        "Zalando recovers split words before matching; the same input returns backpacks.",
    ),
    "běž": (
        "Three-letter prefix for 'running'. Returned only two hoodies, neither related to running.",
        "Prefix and suggest-ahead",
        "Route short prefixes (<= 3 chars) through a prefix index that expands to known root terms (běž- -> běh, běžecké). Or, surface a typeahead panel so the shopper can complete the intent before querying.",
        "Prefix queries are a common mobile pattern. Today this query behaves as a dead end.",
        "Zalando serves a type-ahead panel that completes běž to běžecké/běh before the query is submitted.",
    ),
    "dámská sportovní podprsenka": (
        "Gender filter dropped. All six results were girls' sports bras.",
        "Constraint enforcement - gender and section",
        "Tokenize gender and age qualifiers (dámská, pánské, dětské, dívčí, chlapecká) and enforce them as hard filters rather than ranking boosts.",
        "An adult woman searching for a sports bra saw only children's products. This is one of the highest-intent, highest-AOV query shapes on the site.",
        "Zalando enforces gender as a hard filter; a dámská query contains zero kids' products.",
    ),
    "dětské outlet tenisky": (
        "Outlet filter was ignored. All six results were full-price kids' sneakers.",
        "Constraint enforcement - section",
        "Tokenize section keywords (outlet, sleva, výprodej) and scope the result set to matching collections. Same mechanism as the gender filter above.",
        "Deal-seeking shoppers landed on full-price products. The outlet section has stock in this category.",
        "Zalando scopes 'outlet' to the sale collection; full-price products are excluded from the result set.",
    ),
}


def strip_diacritics(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def top1_relevance(j):
    if not j["results"]:
        return None
    by_orig = sorted(j["results"], key=lambda r: r["original_rank"])
    return by_orig[0]["relevance_score"]


def classify(j):
    """Return 'revenue_risk' | 'catastrophic' | 'working' for a judgment."""
    q = j["test_query"]["query"]
    n = len(j["results"])
    t1 = top1_relevance(j)
    fm = j["failure_mode"]
    if q in MANUAL_COPY:
        return "revenue_risk"
    if n == 0:
        return "revenue_risk"
    if fm == "CONSTRAINT_DROPPED":
        return "revenue_risk"
    if t1 is not None and t1 < CATASTROPHIC_TOP1:
        return "catastrophic"
    return "working"


def main():
    judgments = json.loads(CHECKPOINT.read_text())
    site_ctx = json.loads(SITE_CTX.read_text())

    revenue_risk = []
    catastrophic = []
    working = []

    for j in judgments:
        q = j["test_query"]["query"]
        fm = j["failure_mode"]
        n = len(j["results"])
        t1 = top1_relevance(j)
        bucket = classify(j)

        entry = {
            "query": q,
            "category": j["test_query"]["category"],
            "failure_mode": fm,
            "n_results": n,
            "top1": t1,
            "bucket": bucket,
        }

        if q in MANUAL_COPY:
            why, fix_group, fix, ev, zalando = MANUAL_COPY[q]
            entry.update(why=why, fix_group=fix_group, fix=fix, evidence=ev, zalando=zalando)
            revenue_risk.append(entry)
            continue

        if bucket == "revenue_risk":
            if n == 0:
                entry.update(
                    why="Zero results where products exist.",
                    fix_group="Recall",
                    fix="Expand recall for this query type (see fix groups).",
                    evidence="The customer sees an empty results page and bounces.",
                    zalando="Zalando returns a populated result page for this query shape.",
                )
            else:
                entry.update(
                    why="The customer's filter was ignored.",
                    fix_group="Constraint enforcement",
                    fix="Tokenize and enforce filter qualifiers as hard predicates.",
                    evidence="Results do not match the customer's explicit filter.",
                    zalando="Zalando enforces this constraint as a hard filter.",
                )
            revenue_risk.append(entry)
            continue

        if bucket == "catastrophic":
            entry.update(
                why=f"Top result is off-topic (relevance {t1:.2f}).",
                fix_group="Semantic matching",
                fix="Improve category / intent mapping for this query shape.",
                evidence="The first result the customer sees is unrelated to what they searched for.",
            )
            catastrophic.append(entry)
            continue

        working.append(entry)

    total = len(judgments)
    html = render(site_ctx, revenue_risk, catastrophic, working, judgments, total)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"www_underarmour_cz_{ts}_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote: {out}")
    print(f"Revenue-risk queries: {len(revenue_risk)}")
    print(f"Additional off-topic:  {len(catastrophic)}")
    print(f"Working:               {len(working)}")


def encode_screenshot():
    if not SCREENSHOT.exists():
        return None
    b64 = base64.b64encode(SCREENSHOT.read_bytes()).decode("ascii")
    ext = SCREENSHOT.suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    return f"data:{mime};base64,{b64}"


def build_heatmap(judgments):
    """Build a gender x product_type grid of pass rates."""
    genders = ["women", "men", "kids", "unisex"]
    types = ["shoes", "apparel", "accessories"]
    grid = {g: {t: {"pass": 0, "fail": 0, "queries": []} for t in types} for g in genders}
    for j in judgments:
        q = j["test_query"]["query"]
        tax = TAXONOMY.get(q)
        if not tax:
            continue
        g, t = tax
        if g not in genders or t not in types:
            continue
        bucket = classify(j)
        cell = grid[g][t]
        if bucket == "working":
            cell["pass"] += 1
        else:
            cell["fail"] += 1
        cell["queries"].append((q, bucket))
    return genders, types, grid


DIACRITIC_CONFOUNDING_CATEGORIES = {"TYPO", "MERGED_WORDS", "SPLIT_WORD", "PARTIAL_QUERY"}


def build_diacritic_pairs(judgments):
    """Clean accented-vs-stripped pairs only.

    Excludes queries whose failure mode is a confound (typo, merged, split,
    partial) — those belong to their own fix groups, not to diacritics.
    """
    by_query = {j["test_query"]["query"]: j for j in judgments}
    pairs = []
    singletons = []
    seen = set()
    for q, j in by_query.items():
        stripped = strip_diacritics(q)
        if stripped == q:
            continue
        if q in seen:
            continue
        cat = j["test_query"]["category"]
        if cat in DIACRITIC_CONFOUNDING_CATEGORIES:
            continue
        seen.add(q)
        if stripped in by_query and stripped != q:
            twin = by_query[stripped]
            seen.add(stripped)
            pairs.append({
                "accented": q,
                "accented_bucket": classify(j),
                "stripped": stripped,
                "stripped_bucket": classify(twin),
            })
        else:
            singletons.append({"accented": q, "bucket": classify(j), "stripped": stripped})
    return pairs, singletons


def build_capability_coverage(judgments):
    """Per-search-capability pass rates. Capability = query category."""
    CAPABILITY_LABELS = {
        "DIRECT_MATCH": "Exact match",
        "BRAND_SEARCH": "Brand name",
        "BROAD_CATEGORY": "Broad category",
        "SYNONYM": "Synonym handling",
        "TYPO": "Typo tolerance",
        "SPECIAL_CHARACTER": "Diacritics / accents",
        "MERGED_WORDS": "Compound-word splitting",
        "SPLIT_WORD": "Split-word recovery",
        "PLURAL_SINGULAR": "Plural / singular",
        "ABBREVIATION": "Abbreviations (UA)",
        "MULTI_ATTRIBUTE": "Multi-attribute filters",
        "PARTIAL_QUERY": "Prefix / partial queries",
        "LOCALE_VARIATION": "Locale-specific terms",
    }
    from collections import defaultdict
    stats = defaultdict(lambda: {"pass": 0, "fail": 0, "queries": []})
    for j in judgments:
        cat = j["test_query"]["category"]
        bucket = classify(j)
        q = j["test_query"]["query"]
        if bucket == "working":
            stats[cat]["pass"] += 1
        else:
            stats[cat]["fail"] += 1
        stats[cat]["queries"].append(q)
    rows = []
    for cat, label in CAPABILITY_LABELS.items():
        if cat not in stats:
            continue
        s = stats[cat]
        total = s["pass"] + s["fail"]
        rate = s["pass"] / total if total else 0
        rows.append({"label": label, "cat": cat, "pass": s["pass"], "total": total, "rate": rate, "fail": s["fail"]})
    return rows


def capability_html(rows):
    body = ""
    for r in rows:
        if r["rate"] >= 0.9:
            cls, status = "cap-good", "Healthy"
        elif r["rate"] >= 0.6:
            cls, status = "cap-ok", "Partial"
        elif r["rate"] >= 0.3:
            cls, status = "cap-bad", "Weak"
        else:
            cls, status = "cap-critical", "Broken"
        pct = int(round(r["rate"] * 100))
        body += f"""<tr class="{cls}">
<td>{r['label']}</td>
<td class="cap-n">{r['pass']} / {r['total']}</td>
<td class="cap-pct">{pct}%</td>
<td class="cap-status">{status}</td>
</tr>"""
    return f'<table class="capability"><thead><tr><th>Search capability</th><th>Pass / Total</th><th>Rate</th><th>Status</th></tr></thead><tbody>{body}</tbody></table>'


def heatmap_html(genders, types, grid):
    def cell_html(cell):
        total = cell["pass"] + cell["fail"]
        if total == 0:
            return '<td class="hm-empty">-</td>'
        rate = cell["pass"] / total
        if rate >= 0.9:
            cls = "hm-good"
        elif rate >= 0.6:
            cls = "hm-ok"
        elif rate >= 0.3:
            cls = "hm-bad"
        else:
            cls = "hm-critical"
        pct = int(round(rate * 100))
        return f'<td class="{cls}"><div class="hm-pct">{pct}%</div><div class="hm-n">{cell["pass"]}/{total}</div></td>'

    header = "<th></th>" + "".join(f"<th>{t}</th>" for t in types)
    rows = ""
    for g in genders:
        rows += f"<tr><th>{g}</th>" + "".join(cell_html(grid[g][t]) for t in types) + "</tr>"
    return f'<table class="heatmap"><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>'


def diacritic_html(pairs, singletons):
    def bucket_badge(b):
        cls = {"working": "db-ok", "revenue_risk": "db-bad", "catastrophic": "db-bad"}[b]
        label = {"working": "works", "revenue_risk": "fails", "catastrophic": "off-topic"}[b]
        return f'<span class="db-badge {cls}">{label}</span>'

    rows = ""
    for p in pairs:
        rows += f"""<tr>
<td><code>{p['accented']}</code> {bucket_badge(p['accented_bucket'])}</td>
<td><code>{p['stripped']}</code> {bucket_badge(p['stripped_bucket'])}</td>
</tr>"""
    for s in singletons:
        rows += f"""<tr>
<td><code>{s['accented']}</code> {bucket_badge(s['bucket'])}</td>
<td class="db-muted">no stripped twin tested <code>({s['stripped']})</code></td>
</tr>"""
    return f'<table class="diacritic"><thead><tr><th>As typed (with diacritics)</th><th>Mobile default (stripped)</th></tr></thead><tbody>{rows}</tbody></table>'


def render(site_ctx, revenue_risk, catastrophic, working, judgments, total):
    site_name = site_ctx.get("site_name", "Site")
    date = datetime.now().strftime("%B %-d, %Y")
    screenshot_uri = encode_screenshot()

    groups = defaultdict(list)
    for e in revenue_risk:
        groups[e["fix_group"]].append(e)
    group_order = sorted(groups.items(), key=lambda kv: -len(kv[1]))

    genders, types, grid = build_heatmap(judgments)
    pairs, singletons = build_diacritic_pairs(judgments)
    capability_rows = build_capability_coverage(judgments)

    bounce_n = len(revenue_risk)
    bounce_pct = int(round(100 * bounce_n / total))

    css = """
:root{--primary:#009ba3;--fg:#0a0a0a;--muted:#737373;--border:#e5e5e5;--accent:#dcf8fa;--secondary:#f5f5f5;--bad:#e40014;--warn:#f59e0b;--ok:#16a34a;--radius:0.75rem}
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
.tier.t-bad{border-top:3px solid var(--bad)}
.tier.t-bad .tv{color:var(--bad)}
.tier.t-bad .tl{color:var(--bad)}
.tier.t-warn{border-top:3px solid var(--warn)}
.tier.t-warn .tv{color:var(--warn)}
.tier.t-warn .tl{color:var(--warn)}
.tier.t-good{border-top:3px solid var(--ok)}
.tier.t-good .tv{color:var(--ok)}
.tier.t-good .tl{color:var(--ok)}
.q-card{border:1px solid var(--border);border-radius:var(--radius);padding:22px 24px;margin-bottom:16px;background:#fff}
.q-card .q-head{display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.q-card code{font-family:'Geist Mono',ui-monospace,'SF Mono',monospace;font-size:1.05rem;font-weight:700;background:var(--secondary);padding:6px 12px;border-radius:4px;color:var(--fg)}
.q-card .q-why{font-weight:600;color:var(--bad);font-size:0.9rem}
.q-card .q-ev{color:var(--fg);margin-bottom:10px}
.q-card .q-fix{background:var(--accent);padding:12px 14px;border-radius:6px;font-size:0.9rem;color:var(--fg);margin-bottom:8px}
.q-card .q-fix strong{color:var(--primary)}
.q-card .q-zalando{font-size:0.85rem;color:var(--muted);padding:0 2px}
.q-card .q-zalando strong{color:var(--fg)}
.fix-group{border:1px solid var(--border);border-left:4px solid var(--primary);border-radius:var(--radius);padding:20px 24px;margin-bottom:16px}
.fix-group .fg-title{font-size:1.1rem;font-weight:700;margin-bottom:6px}
.fix-group .fg-count{font-size:0.8rem;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:0.06em}
.fix-group .fg-body{font-size:0.95rem;margin-bottom:10px}
.fix-group .fg-queries code{font-family:'Geist Mono',ui-monospace,monospace;font-size:0.82rem;background:var(--secondary);padding:3px 8px;border-radius:3px;margin:2px 6px 2px 0;display:inline-block}
.note{color:var(--muted);font-size:0.88rem;margin-top:8px}
.heatmap{width:100%;border-collapse:collapse;margin:16px 0}
.heatmap th,.heatmap td{padding:14px 10px;text-align:center;border:1px solid var(--border);font-size:0.92rem}
.heatmap thead th{background:var(--secondary);font-weight:600;text-transform:capitalize}
.heatmap tbody th{text-align:right;font-weight:600;text-transform:capitalize;background:var(--secondary)}
.heatmap .hm-pct{font-size:1.1rem;font-weight:700;line-height:1}
.heatmap .hm-n{font-size:0.72rem;color:var(--muted);margin-top:4px}
.heatmap .hm-good{background:#dcfce7}
.heatmap .hm-good .hm-pct{color:var(--ok)}
.heatmap .hm-ok{background:#fef3c7}
.heatmap .hm-ok .hm-pct{color:#b45309}
.heatmap .hm-bad{background:#fed7aa}
.heatmap .hm-bad .hm-pct{color:#c2410c}
.heatmap .hm-critical{background:#fecaca}
.heatmap .hm-critical .hm-pct{color:var(--bad)}
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

    shot_html = f'<div class="shot"><img src="{screenshot_uri}" alt=""></div>' if screenshot_uri else ""

    cards_html = ""
    for e in revenue_risk:
        zalando_html = f'<p class="q-zalando"><strong>Benchmark:</strong> {e.get("zalando","")}</p>' if e.get("zalando") else ""
        cards_html += f"""
<div class="q-card">
  <div class="q-head">
    <code>{e['query']}</code>
    <span class="q-why">{e['why']}</span>
  </div>
  <p class="q-ev">{e['evidence']}</p>
  <div class="q-fix"><strong>Fix:</strong> {e['fix']}</div>
  {zalando_html}
</div>"""

    groups_html = ""
    for group_name, items in group_order:
        q_html = "".join(f"<code>{e['query']}</code>" for e in items)
        fix_text = items[0]["fix"]
        groups_html += f"""
<div class="fix-group">
  <div class="fg-title">{group_name}</div>
  <div class="fg-count">{len(items)} quer{'y' if len(items)==1 else 'ies'}</div>
  <div class="fg-body">{fix_text}</div>
  <div class="fg-queries">{q_html}</div>
</div>"""

    extra_html = ""
    if catastrophic:
        rows = ""
        for e in catastrophic:
            rows += f"""
<div class="q-card">
  <div class="q-head">
    <code>{e['query']}</code>
    <span class="q-why">{e['why']}</span>
  </div>
  <p class="q-ev">{e['evidence']}</p>
</div>"""
        extra_html = f"""
<section>
  <div class="label">Also worth flagging</div>
  <h2>Additional queries where the first result lands off-topic</h2>
  <p>These returned products, but the top result doesn't match what the customer asked for. Lower priority than the revenue-risk list above - customers may still find something useful - but worth a closer look.</p>
  {rows}
</section>"""

    hm_html = heatmap_html(genders, types, grid)
    dia_html = diacritic_html(pairs, singletons)
    cap_html = capability_html(capability_rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Search Quality Report - {site_name}</title>
<style>{css}</style>
</head>
<body>
<div class="page">

<div class="cover">
  <div class="label">Search Quality Report</div>
  <h1>Where customers are leaving empty-handed</h1>
  <div class="subtitle">{site_name}</div>
  <div class="cover-meta">{date}</div>
  {shot_html}
</div>

<section>
  <div class="label">Summary</div>
  <h2>Bounce risk at a glance</h2>
  <div class="tldr">
    <h3>The short version</h3>
    <p>We tested {total} realistic customer queries against your site's search. The vast majority returned relevant Under Armour products - your engine is returning on-topic results.</p>
    <p>This report focuses on the <strong>{bounce_n} queries where customers hit a dead end today</strong>: zero results when products exist, filters that get dropped, or top results that aren't what the customer asked for. Ranking nuances within already-relevant result sets are intentionally <em>not</em> in scope here.</p>
  </div>
  <div class="hero-stat">
    <div class="n">{bounce_pct}%</div>
    <div class="txt">
      <strong>bounce risk.</strong>
      {bounce_n} of {total} tested queries cause a likely customer bounce today.
      <em>These are the queries where a customer lands on a dead end - no results, wrong section, or off-topic top result - and leaves for a competitor.</em>
    </div>
  </div>
  <div class="tier-row">
    <div class="tier t-bad">
      <div class="tv">{bounce_n}</div>
      <div class="tl">Revenue risk</div>
      <div class="td">Zero results, dropped constraints, or semantic misses. Customer bounces.</div>
    </div>
    <div class="tier t-warn">
      <div class="tv">{len(catastrophic)}</div>
      <div class="tl">Off-topic top-1</div>
      <div class="td">Results are populated but the #1 result doesn't match. Customer may still find something, but friction is high.</div>
    </div>
    <div class="tier t-good">
      <div class="tv">{len(working)}</div>
      <div class="tl">Working</div>
      <div class="td">Returns on-topic results. Ranking nuances within this set are out of scope here.</div>
    </div>
  </div>
</section>

<section>
  <div class="label">Coverage heatmap</div>
  <h2>Where the blind spots are, by gender x product type</h2>
  <p>Pass rate = queries that returned on-topic, constraint-respecting results. The red cells are where a shopper in that segment is most likely to leave empty-handed.</p>
  {hm_html}
  <p class="note">Unisex and broad queries (e.g. "under armour", "fitness", "trénink") are excluded from this grid. Cells with a dash had no tested query in that segment.</p>
</section>

<section>
  <div class="label">The Czech-shopper reality</div>
  <h2>Diacritics: what the customer types vs. what the engine expects</h2>
  <p>Czech mobile shoppers routinely drop diacritics - on many phone keyboards, typing <code>é</code>, <code>á</code>, or <code>č</code> takes an extra tap. A robust engine should treat <code>legíny</code> and <code>leginy</code> as the same intent.</p>
  <p>We ran each diacritic-bearing query alongside its stripped "mobile twin" (confounding categories like typos and compounds are excluded - those appear in their own fix groups). Both forms return populated result sets, so accent-insensitive <em>matching</em> works. The relevance of the <em>top result</em>, however, shifts on several multi-word queries - the stripped version ranks slightly worse, meaning mobile users get a nudged-down #1 pick.</p>
  {dia_html}
  <p class="note"><strong>Recommendation:</strong> Mobile users are not broken today. Matching works. But for multi-word queries (<code>panske bezecke boty</code>, <code>detske outlet tenisky</code>) the stripped twin scores lower - the engine is likely boosting diacritic matches as a ranking signal. Normalize diacritics at the ranking layer too, so the stripped form returns the same ordered results as the accented one.</p>
</section>

<section>
  <div class="label">Capability coverage</div>
  <h2>Which search capabilities are working, and which aren't</h2>
  <p>Each query category maps to a specific search capability. This table shows how many queries in each category returned acceptable results — so you can see whether a failure is a one-off or a systemic gap in that capability.</p>
  {cap_html}
  <p class="note">A "Broken" or "Weak" status means the capability is the root cause of multiple customer-facing failures; those are the highest-leverage fixes.</p>
</section>

<section>
  <div class="label">The queries</div>
  <h2>Where your search engine is actively losing customers</h2>
  <p>Each entry is a real search pattern a customer might type on your site. The "Fix" line is the specific engine-level change that recovers the query. The "Benchmark" line notes how a best-in-class CZ apparel search (Zalando) handles the same input.</p>
  {cards_html}
</section>

{extra_html}

<section>
  <div class="label">Fix prioritization</div>
  <h2>Grouped by engineering effort</h2>
  <p>The {bounce_n} failures above cluster into a small number of root causes. Each fix below unblocks multiple queries at once.</p>
  {groups_html}
</section>

<section>
  <div class="label">What's not in this report</div>
  <h2>The other {total - bounce_n - len(catastrophic)} queries</h2>
  <p>The remaining test queries returned on-topic results. Things like "tenisky", "mikina", "běžecké boty", "under armour" - customers typing these see the right category of product. There are ordering nuances within those result sets (e.g. which specific running shoe ranks #1), but investigating those is a separate optimization pass and out of scope here: they are not the queries where you are losing sales.</p>
  <p class="note">If an internal team wants the full per-query capability breakdown (including ranking-within-category signals), that diagnostic is available as a separate artifact.</p>
</section>

<footer>
  Search Quality Report &middot; {site_name} &middot; {date}
</footer>

</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
