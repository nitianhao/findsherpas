from __future__ import annotations

import re

from src.models import QueryJudgment, SiteContext, Severity


def _is_pass(j: QueryJudgment) -> bool:
    """A query whose calibrated verdict is PASS — search handled it acceptably. These
    diagnostics are built on the judge's verdicts/failure-modes (not raw reranker scores), so
    a PASS is always treated as 'search got this right' and never counted as a failure."""
    sev = j.severity.value if hasattr(j.severity, "value") else j.severity
    return sev == Severity.PASS.value


def _mode(j: QueryJudgment) -> str:
    return j.failure_mode.value if hasattr(j.failure_mode, "value") else j.failure_mode


_STOPWORDS = {
    "and", "or", "the", "with", "for", "not", "without", "under", "over",
    "from", "into", "best", "shop", "all", "new", "sale", "inch", "inches",
    "in", "on", "by", "to", "of", "a", "an",
}


def _by_original(judgment: QueryJudgment):
    return sorted(judgment.results, key=lambda r: r.original_rank)


def _pct(part: float, total: float) -> float:
    return (part / total * 100) if total else 0.0


def _query_terms(query: str) -> list[str]:
    terms = []
    # Unicode-aware tokenization: ``[^\W_]+`` matches letters/digits in any language
    # (incl. å, ä, ö, é, ü …). An ASCII-only regex shreds non-English words.
    for raw in re.findall(r"[^\W_]+", query.lower()):
        token = raw.rstrip("s") if len(raw) > 4 else raw
        if token in _STOPWORDS:
            continue
        if len(token) < 2:
            continue
        terms.append(token)
    return list(dict.fromkeys(terms))


def _trim(text: str | None, limit: int = 160) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _class_for_rate(rate: float, inverse: bool = False) -> str:
    value = 100 - rate if inverse else rate
    if value >= 80:
        return "good"
    if value >= 60:
        return "warn"
    return "bad"


# Human labels for failure modes, used in the substitution / wrong-product table.
_MODE_LABEL = {
    "NO_SEMANTIC_UNDERSTANDING": "wrong product type",
    "CATEGORY_MAPPING_FAILURE": "couldn’t map to your category",
    "PARTIAL_KEYWORD_MATCH": "matched only part of the query",
    "BRAND_BLEED": "wrong brand",
    "POOR_RANKING": "right type, mis-ordered",
    "DUPLICATE_FLOODING": "flooded with duplicates",
    "CONSTRAINT_DROPPED": "ignored a filter",
    "FACET_NOT_EXTRACTED": "missed a filter",
}

# Modes where the engine returned a product, but the wrong one, at the top.
_WRONG_PRODUCT_MODES = {
    "NO_SEMANTIC_UNDERSTANDING",
    "CATEGORY_MAPPING_FAILURE",
    "PARTIAL_KEYWORD_MATCH",
    "BRAND_BLEED",
    "POOR_RANKING",
    "DUPLICATE_FLOODING",
}
_WRONG_PRODUCT_ORDER = {
    m: i for i, m in enumerate([
        "NO_SEMANTIC_UNDERSTANDING",
        "CATEGORY_MAPPING_FAILURE",
        "PARTIAL_KEYWORD_MATCH",
        "BRAND_BLEED",
        "DUPLICATE_FLOODING",
        "POOR_RANKING",
    ])
}

# Categories that carry an explicit shopper-set constraint (price/colour/material/exclusion).
_CONSTRAINT_CATEGORIES = {
    "PRICE_ANCHORED",
    "NEGATIVE_INTENT",
    "MULTI_ATTRIBUTE",
    "FACET_EXTRACTION",
    "UNIT_VARIATION",
}
_CONSTRAINT_VIOLATION_MODES = {"CONSTRAINT_DROPPED", "FACET_NOT_EXTRACTED"}

ORDERING_MIN_RESULTS = 2
SPECIFICITY_MIN_PER_TIER = 3
_TIER_ORDER = ["1 word", "2 words", "3+ words"]


# ---------------------------------------------------------------------------
# 1. Did the best match come first?  (ordering quality — uses judge displacement)
# ---------------------------------------------------------------------------

def _build_ordering(judgments: list[QueryJudgment]) -> dict:
    rows = []
    evaluated = 0
    buried = 0
    for j in judgments:
        results = _by_original(j)
        if len(results) < ORDERING_MIN_RESULTS:
            continue  # ordering is only meaningful with ≥2 results
        evaluated += 1
        if _is_pass(j):
            continue  # search led with an acceptable result
        if j.displacement > 0:
            buried += 1
            first = results[0]
            # The buried better match is the highest-scored result (displacement>0 means
            # it is not at original rank 1). Score is used only to NAME it; the existence
            # of a stronger result is asserted by the judge's displacement field.
            best = max(results, key=lambda r: r.relevance_score)
            rows.append({
                "query": j.test_query.query,
                "first_title": first.title,
                "better_title": best.title,
                "buried_by": j.displacement,
            })
    rows.sort(key=lambda r: -r["buried_by"])
    return {
        "evaluated": evaluated,
        "buried": buried,
        "rate": _pct(buried, evaluated),
        "examples": rows[:4],
    }


# ---------------------------------------------------------------------------
# 2. The specificity cliff  (pass rate by query word count — uses judge verdicts)
# ---------------------------------------------------------------------------

def _specificity_tier(query: str) -> str:
    n = len(_query_terms(query))
    if n <= 1:
        return "1 word"
    if n == 2:
        return "2 words"
    return "3+ words"


def _build_specificity_cliff(judgments: list[QueryJudgment]) -> dict:
    buckets = {t: {"total": 0, "passed": 0} for t in _TIER_ORDER}
    for j in judgments:
        tier = _specificity_tier(j.test_query.query)
        buckets[tier]["total"] += 1
        if _is_pass(j):
            buckets[tier]["passed"] += 1

    tiers = []
    for t in _TIER_ORDER:
        b = buckets[t]
        if b["total"] == 0:
            continue
        tiers.append({
            "tier": t,
            "total": b["total"],
            "passed": b["passed"],
            "pass_rate": _pct(b["passed"], b["total"]),
        })

    # Only meaningful when at least two tiers each carry enough queries to compare.
    populated = [t for t in tiers if t["total"] >= SPECIFICITY_MIN_PER_TIER]
    applicable = len(populated) >= 2
    broad = populated[0]["pass_rate"] if populated else 0.0
    specific = populated[-1]["pass_rate"] if populated else 0.0
    return {
        "applicable": applicable,
        "tiers": tiers,
        "broad_rate": broad,
        "specific_rate": specific,
        "drop": broad - specific,
    }


# ---------------------------------------------------------------------------
# 3. When it misses, what shows up instead?  (wrong-product table — titles + mode)
# ---------------------------------------------------------------------------

def _build_substitutions(judgments: list[QueryJudgment]) -> dict:
    rows = []
    for j in judgments:
        results = _by_original(j)
        if not results:
            continue  # zero-result dead ends are reported in the retrieval/exec sections
        if _is_pass(j):
            continue
        mode = _mode(j)
        if mode not in _WRONG_PRODUCT_MODES:
            continue
        rows.append({
            "query": j.test_query.query,
            "got": results[0].title,
            "why": _MODE_LABEL.get(mode, "wrong result"),
            "mode": mode,
        })
    rows.sort(key=lambda r: _WRONG_PRODUCT_ORDER.get(r["mode"], 9))
    return {"examples": rows[:6], "count": len(rows)}


# ---------------------------------------------------------------------------
# 4. Did it respect the filters?  (constraint obedience — category + judge mode)
# ---------------------------------------------------------------------------

def _build_constraint_obedience(judgments: list[QueryJudgment]) -> dict:
    candidates = [j for j in judgments if j.test_query.category in _CONSTRAINT_CATEGORIES]
    total = len(candidates)
    honored = 0
    violations = []
    empty = 0
    for j in candidates:
        if _is_pass(j):
            honored += 1
            continue
        mode = _mode(j)
        if not _by_original(j):
            empty += 1
            continue
        if mode in _CONSTRAINT_VIOLATION_MODES:
            violations.append({
                "query": j.test_query.query,
                "detail": _trim(j.evidence),
            })
    return {
        "applicable": total > 0,
        "total": total,
        "honored": honored,
        "violated": len(violations),
        "empty": empty,
        "examples": violations[:4],
    }


# ---------------------------------------------------------------------------
# Result text
# ---------------------------------------------------------------------------

_STATUS_LABEL = {"good": "Healthy", "warn": "Worth a look", "bad": "Needs attention"}


def _short(text: str, limit: int = 40) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _ordering_text(o: dict) -> str:
    if o["buried"] == 0:
        return "Every search that returned results led with its strongest match."
    return (
        f"A stronger product sat below the first result on {o['buried']} of "
        f"{o['evaluated']} searches."
    )


def _specificity_text(s: dict) -> str:
    return (
        f"Pass rate slides from {s['broad_rate']:.0f}% on broad searches to "
        f"{s['specific_rate']:.0f}% on the most specific — the shoppers closest to buying."
    )


def _substitutions_text(sub: dict) -> str:
    return f"{sub['count']} searches led with the wrong type of product. What shoppers saw instead:"


def _constraint_text(c: dict) -> str:
    base = f"{c['honored']} of {c['total']} filtered searches kept the shopper's limit."
    if c["violated"]:
        base += f" {c['violated']} returned items that broke it."
    return base


# ---------------------------------------------------------------------------
# Section assembly (shared by HTML + markdown renderers)
# ---------------------------------------------------------------------------

def build_advanced_diagnostics(site_context: SiteContext, judgments: list[QueryJudgment]) -> dict:
    return {
        "ordering": _build_ordering(judgments),
        "specificity": _build_specificity_cliff(judgments),
        "substitutions": _build_substitutions(judgments),
        "constraints": _build_constraint_obedience(judgments),
    }


def build_advanced_diagnostics_sections(
    site_context: SiteContext,
    judgments: list[QueryJudgment],
) -> list[dict]:
    d = build_advanced_diagnostics(site_context, judgments)
    ordering = d["ordering"]
    spec = d["specificity"]
    sub = d["substitutions"]
    con = d["constraints"]

    sections: list[dict] = []

    # 1. Ordering — render whenever any search returned results.
    if ordering["evaluated"]:
        cls = _class_for_rate(ordering["rate"], inverse=True)
        sections.append({
            "key": "ordering",
            "type": "rate_list",
            "title": "Did the best match come first?",
            "question": "Whether a stronger product was buried below the first result.",
            "headline": f"{ordering['rate']:.0f}%",
            "headline_label": "led with a weaker result",
            "headline_class": cls,
            "status_label": _STATUS_LABEL[cls],
            "narrative": _ordering_text(ordering),
            "examples": [
                {
                    "code": row["query"],
                    "detail": (
                        f"“{_short(row['first_title'])}” ranked first — the better "
                        f"“{_short(row['better_title'])}” was {row['buried_by']} "
                        f"spot{'s' if row['buried_by'] != 1 else ''} lower."
                    ),
                }
                for row in ordering["examples"][:3]
            ],
        })

    # 2. Specificity cliff — only when tiers are comparable.
    if spec["applicable"]:
        cls = _class_for_rate(spec["specific_rate"])
        sections.append({
            "key": "specificity",
            "type": "bars",
            "title": "The specificity cliff",
            "question": "How search holds up as shoppers describe what they want more precisely.",
            "headline": f"{spec['broad_rate']:.0f}% → {spec['specific_rate']:.0f}%",
            "headline_label": "broad → most specific",
            "headline_class": cls,
            "status_label": _STATUS_LABEL[cls],
            "narrative": _specificity_text(spec),
            "bars": [
                {
                    "label": t["tier"],
                    "pct": round(t["pass_rate"]),
                    "pct_label": f"{t['pass_rate']:.0f}%",
                    "detail": f"{t['passed']}/{t['total']}",
                    "cls": _class_for_rate(t["pass_rate"]),
                }
                for t in spec["tiers"]
            ],
        })

    # 3. Wrong-product substitutions — only when there are wrong-#1 results.
    if sub["examples"]:
        cls = "bad" if sub["count"] >= 5 else "warn"
        sections.append({
            "key": "substitutions",
            "type": "table",
            "title": "When it misses, what shows up instead",
            "question": "The wrong-product pattern behind the failures.",
            "headline": str(sub["count"]),
            "headline_label": "wrong-product results",
            "headline_class": cls,
            "status_label": _STATUS_LABEL[cls],
            "narrative": _substitutions_text(sub),
            "rows": [
                {"searched": r["query"], "got": _short(r["got"], 46), "why": r["why"]}
                for r in sub["examples"][:5]
            ],
        })

    # 4. Constraint obedience — only when constraint queries exist.
    if con["applicable"]:
        cls = _class_for_rate(_pct(con["honored"], con["total"]))
        sections.append({
            "key": "constraints",
            "type": "rate_list",
            "title": "Did it respect the filters?",
            "question": "Whether hard limits (price, colour, material, “not X”) were honoured.",
            "headline": f"{con['honored']}/{con['total']}",
            "headline_label": "filters honoured",
            "headline_class": cls,
            "status_label": _STATUS_LABEL[cls],
            "narrative": _constraint_text(con),
            "examples": [
                {"code": ex["query"], "detail": _short(ex["detail"], 96)}
                for ex in con["examples"][:3]
            ],
        })

    return sections


def build_advanced_diagnostics_markdown(
    site_context: SiteContext,
    judgments: list[QueryJudgment],
) -> str:
    lines = [
        "## Advanced Query Diagnostics\n",
        "Beyond pass/fail, these checks read the whole result page the way a shopper does — "
        "and are built on the audited verdicts, not internal relevance scores.",
    ]

    for section in build_advanced_diagnostics_sections(site_context, judgments):
        lines.extend([
            "",
            f"### {section['title']}\n",
            f"_{section['question']}_",
            "",
            f"**{section['headline']}** — {section['headline_label']}",
            "",
            section["narrative"],
        ])

        if section["type"] == "bars":
            lines.append("")
            for bar in section["bars"]:
                lines.append(f"- **{bar['label']}** — {bar['pct_label']} ({bar['detail']})")
        elif section["type"] == "table":
            lines.append("")
            lines.append("| Shopper searched | Top result was | Why |")
            lines.append("| --- | --- | --- |")
            for row in section["rows"]:
                lines.append(f"| `{row['searched']}` | {row['got']} | {row['why']} |")
        else:  # rate_list
            if section["examples"]:
                lines.append("")
                for ex in section["examples"]:
                    lines.append(f"- `{ex['code']}` — {ex['detail']}")

    return "\n".join(lines)
