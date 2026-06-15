from __future__ import annotations

import re
from collections import Counter

from src.models import QueryJudgment, SiteContext


RELEVANT_THRESHOLD = 0.60
WEAK_THRESHOLD = 0.40

_ATTRIBUTE_CATEGORIES = {
    "MULTI_ATTRIBUTE",
    "PRICE_ANCHORED",
    "NEGATIVE_INTENT",
    "FACET_EXTRACTION",
    "UNIT_VARIATION",
}

_SPECIFICITY_CATEGORIES = {
    "BROAD_CATEGORY",
    "DIRECT_MATCH",
    "MULTI_ATTRIBUTE",
    "USE_CASE",
    "SYNONYM",
    "PLURAL_SINGULAR",
}

_STOPWORDS = {
    "and", "or", "the", "with", "for", "not", "without", "under", "over",
    "from", "into", "best", "shop", "all", "new", "sale", "inch", "inches",
    "in", "on", "by", "to", "of", "a", "an",
}

_VARIANT_WORDS = {
    "exclusive", "new", "fit", "hb", "lined", "lightweight", "classic",
}

_COLOR_WORDS = {
    "black", "white", "blue", "navy", "green", "red", "brown", "tan",
    "khaki", "grey", "gray", "olive", "natural", "stone", "cream",
}


def _by_original(judgment: QueryJudgment):
    return sorted(judgment.results, key=lambda r: r.original_rank)


def _relevant_count(results, limit: int) -> int:
    return sum(1 for r in results[:limit] if r.relevance_score >= RELEVANT_THRESHOLD)


def _pct(part: float, total: float) -> float:
    return (part / total * 100) if total else 0.0


def _query_terms(query: str) -> list[str]:
    terms = []
    # Unicode-aware tokenization: ``[^\W_]+`` matches letters/digits in any
    # language (incl. å, ä, ö, é, ü …) but excludes underscore. An ASCII-only
    # regex shreds non-English words (e.g. "kläder" -> "kl","der") so every
    # term then fails to match product titles and shows as falsely "dropped".
    for raw in re.findall(r"[^\W_]+", query.lower()):
        token = raw.rstrip("s") if len(raw) > 4 else raw
        if token in _STOPWORDS:
            continue
        if len(token) < 2:
            continue
        terms.append(token)
    return list(dict.fromkeys(terms))


def _title_text(result) -> str:
    return f"{result.title or ''} {result.snippet or ''}".lower()


def _family_key(title: str) -> str:
    key = title.lower()
    key = re.sub(r"\b\d+(?:\.\d+)?\b", " ", key)
    key = re.sub(r"\b\d+(?:\.\d+)?\s*(?:in|inch|\"|oz|ml|g|kg|pack)\b", " ", key)
    key = re.sub(r"[^\w\s-]", " ", key)  # keep Unicode letters/digits (non-ASCII safe)
    tokens = [
        t.rstrip("s") if len(t) > 4 else t
        for t in key.split()
        if t not in _COLOR_WORDS and t not in _VARIANT_WORDS
    ]
    return re.sub(r"\s+", " ", " ".join(tokens)).strip()


def _class_for_rate(rate: float, inverse: bool = False) -> str:
    value = 100 - rate if inverse else rate
    if value >= 80:
        return "good"
    if value >= 60:
        return "warn"
    return "bad"


def _build_result_set_purity(judgments: list[QueryJudgment]) -> dict:
    rows = []
    totals = {3: 0, 5: 0, 10: 0}
    denom = {3: 0, 5: 0, 10: 0}

    for j in judgments:
        results = _by_original(j)
        if not results:
            continue
        row = {"query": j.test_query.query}
        for limit in (3, 5, 10):
            scoped = results[:limit]
            relevant = _relevant_count(results, limit)
            totals[limit] += relevant
            denom[limit] += len(scoped)
            row[f"top{limit}_relevant"] = relevant
            row[f"top{limit}_total"] = len(scoped)
            row[f"top{limit}_purity"] = _pct(relevant, len(scoped))
        rows.append(row)

    polluted = sorted(rows, key=lambda r: (r["top5_purity"], r["top3_purity"]))[:5]
    return {
        "top3": _pct(totals[3], denom[3]),
        "top5": _pct(totals[5], denom[5]),
        "top10": _pct(totals[10], denom[10]),
        "polluted_queries": polluted,
    }


def _build_top_result_trust(judgments: list[QueryJudgment]) -> dict:
    rows = []
    failed = 0
    evaluated = 0

    for j in judgments:
        results = _by_original(j)
        # Zero-result queries have no #1 result to assess for trustworthiness.
        # That is a separate dead-end failure (ZERO_RESULTS_OR_GARBAGE) captured
        # elsewhere; including them here both inflates the failure rate and
        # produces nonsensical "#1 was 'No results'" evidence. Exclude them from
        # this diagnostic entirely (matching Result Set Purity).
        if not results:
            continue

        evaluated += 1
        top = results[0]
        best_score = max(r.relevance_score for r in results)
        reason = ""
        if top.relevance_score < WEAK_THRESHOLD:
            reason = "The first result is weakly related to the query."
        elif top.relevance_score < RELEVANT_THRESHOLD:
            reason = "The first result is only a partial answer."
        elif best_score - top.relevance_score >= 0.20 and j.displacement > 2:
            reason = "A much stronger result appears lower in the list."

        if reason:
            failed += 1
            rows.append({
                "query": j.test_query.query,
                "top_result": top.title,
                "top_score": top.relevance_score,
                "best_score": best_score,
                "reason": reason,
            })

    rows.sort(key=lambda r: (r["top_score"], -r["best_score"]))
    return {
        "failure_rate": _pct(failed, evaluated),
        "failed": failed,
        "total": evaluated,
        "worst": rows[:5],
    }


def _build_attribute_drift(judgments: list[QueryJudgment]) -> dict:
    """Detect attribute drift using only *title-observable* terms.

    Title-substring matching cannot see attributes that live in facet metadata
    (colour, size, gender, generic category words) — those never appear in
    product titles, so naively treating them as "dropped" produces a false
    failure for almost every multi-attribute query. We therefore classify each
    query term by what the result set actually shows:

      * observable in the TOP results          -> preserved
      * observable elsewhere in the result set
        but absent from the top                 -> dropped (genuine ranking drift)
      * not present in ANY returned title       -> unverifiable (facet/metadata,
                                                    or the engine returned no
                                                    matching product — can't tell
                                                    from titles, so we don't guess)

    A query is reported as genuine drift only when it has BOTH a preserved
    (title-observable) anchor and a dropped title-observable attribute: the
    right product type is surfaced, but matching products for another attribute
    are buried. Total misses (no preserved anchor) and zero-result queries are
    handled by the failure-mode analysis, not here.
    """
    candidates = [
        j for j in judgments
        if j.test_query.category in _ATTRIBUTE_CATEGORIES
        and len(_query_terms(j.test_query.query)) >= 2
        and _by_original(j)
    ]
    rows = []
    dropped_counter: Counter[str] = Counter()
    unverifiable_queries = 0

    for j in candidates:
        terms = _query_terms(j.test_query.query)
        results = _by_original(j)
        top = results[:5]

        preserved, dropped, unverifiable = [], [], []
        for term in terms:
            all_hits = sum(1 for r in results if term in _title_text(r))
            top_hits = sum(1 for r in top if term in _title_text(r))
            if all_hits == 0:
                unverifiable.append(term)
            elif top_hits == 0:
                dropped.append(term)
            else:
                preserved.append(term)

        if preserved and dropped:
            dropped_counter.update(dropped)
            rows.append({
                "query": j.test_query.query,
                "preserved": preserved,
                "dropped": dropped,
                "unverifiable": unverifiable,
                # coverage over the title-observable terms only
                "coverage": _pct(len(preserved), len(preserved) + len(dropped)),
            })
        elif unverifiable and not dropped:
            # Attributes existed but none were title-observable, so drift could
            # not be assessed from result text. Count it for honest reporting.
            unverifiable_queries += 1

    rows.sort(key=lambda r: (r["coverage"], -len(r["dropped"])))
    return {
        "queries": rows,
        "worst": rows[:5],
        "common_dropped": dropped_counter.most_common(8),
        "unverifiable_queries": unverifiable_queries,
        "candidate_count": len(candidates),
    }


def _build_diversity(site_context: SiteContext, judgments: list[QueryJudgment]) -> dict:
    applicable = site_context.site_type != "SERVICES_EXPERIENCES" and len(site_context.brands) > 1
    if not applicable:
        return {
            "applicable": False,
            "reason": "Skipped because this diagnostic is mainly useful for multi-brand or broad-catalog ecommerce.",
            "queries": [],
            "worst": [],
        }

    candidates = [
        j for j in judgments
        if j.test_query.category in {"BROAD_CATEGORY", "SYNONYM", "USE_CASE", "PLURAL_SINGULAR"}
    ]
    rows = []
    for j in candidates:
        results = _by_original(j)[:10]
        if len(results) < 5:
            continue
        keys = [_family_key(r.title) for r in results if _family_key(r.title)]
        unique_count = len(set(keys))
        duplicate_count = max(0, len(keys) - unique_count)
        diversity_rate = _pct(unique_count, len(keys))
        rows.append({
            "query": j.test_query.query,
            "unique_families": unique_count,
            "result_count": len(keys),
            "duplicate_count": duplicate_count,
            "diversity_rate": diversity_rate,
        })

    rows.sort(key=lambda r: (r["diversity_rate"], -r["duplicate_count"]))
    return {
        "applicable": True,
        "queries": rows,
        "worst": rows[:5],
    }


def _build_specificity_scaling(judgments: list[QueryJudgment]) -> dict:
    candidates = [
        j for j in judgments
        if j.test_query.category in _SPECIFICITY_CATEGORIES
    ]
    sets = [(j, set(_query_terms(j.test_query.query))) for j in candidates]
    ladders = []

    for base, base_terms in sets:
        if not base_terms:
            continue
        chain = [(base, base_terms)]
        current_terms = base_terms
        for other, other_terms in sorted(sets, key=lambda item: len(item[1])):
            if other is base or len(other_terms) <= len(current_terms):
                continue
            if current_terms < other_terms:
                chain.append((other, other_terms))
                current_terms = other_terms
        if len(chain) >= 3:
            signature = tuple(j.test_query.query for j, _terms in chain)
            if signature not in [tuple(item["queries"]) for item in ladders]:
                scores = []
                for j, _terms in chain:
                    top = _by_original(j)[:3]
                    top3_avg = sum(r.relevance_score for r in top) / len(top) if top else 0.0
                    scores.append(top3_avg)
                drop_index = None
                for idx in range(1, len(scores)):
                    if scores[idx] + 0.15 < scores[idx - 1]:
                        drop_index = idx
                        break
                ladders.append({
                    "queries": list(signature),
                    "top3_scores": scores,
                    "break_query": signature[drop_index] if drop_index is not None else "",
                })

    return {
        "ladders": ladders[:3],
        "detected": bool(ladders),
    }


def build_advanced_diagnostics(site_context: SiteContext, judgments: list[QueryJudgment]) -> dict:
    purity = _build_result_set_purity(judgments)
    trust = _build_top_result_trust(judgments)
    drift = _build_attribute_drift(judgments)
    diversity = _build_diversity(site_context, judgments)
    specificity = _build_specificity_scaling(judgments)

    return {
        "purity": {
            **purity,
            "top3_class": _class_for_rate(purity["top3"]),
            "top5_class": _class_for_rate(purity["top5"]),
            "top10_class": _class_for_rate(purity["top10"]),
        },
        "top_result_trust": {
            **trust,
            "failure_class": _class_for_rate(trust["failure_rate"], inverse=True),
        },
        "attribute_drift": drift,
        "diversity": diversity,
        "specificity": specificity,
    }


def build_advanced_diagnostics_markdown(
    site_context: SiteContext,
    judgments: list[QueryJudgment],
) -> str:
    lines = [
        "## Advanced Query Diagnostics\n",
        "These diagnostics look beyond the single best result and evaluate the quality of the visible result set.",
    ]

    for section in build_advanced_diagnostics_sections(site_context, judgments):
        lines.extend([
            "",
            f"### {section['title']}\n",
            f"**What it means:** {section['meaning']}",
            "",
            f"**Result:** {section['result']}",
        ])
        if section["evidence"]:
            lines.append("")
            lines.append("Evidence:")
            for item in section["evidence"]:
                lines.append(f"- {item}")
        lines.extend([
            "",
            f"**How to remedy it:** {section['remedy']}",
        ])

    return "\n".join(lines)


def _purity_result_text(purity: dict) -> str:
    if purity["top5"] >= 70:
        return (
            f"The visible result set is fairly clean: {purity['top5']:.0f}% of top 5 "
            "results were relevant on average."
        )
    return (
        f"The visible result set is noisy: only {purity['top5']:.0f}% of top 5 "
        f"results were relevant on average, and top 10 purity was {purity['top10']:.0f}%."
    )


def _trust_result_text(trust: dict) -> str:
    if trust["failure_rate"] <= 20:
        return (
            f"The first result is generally defensible: {trust['failed']} of "
            f"{trust['total']} queries had a weak or questionable #1 result."
        )
    return (
        f"The first result is not reliable enough: {trust['failed']} of "
        f"{trust['total']} queries ({trust['failure_rate']:.0f}%) had a weak, partial, "
        "or clearly beaten #1 result."
    )


def _drift_result_text(drift: dict) -> str:
    if not drift["queries"]:
        unverifiable = drift.get("unverifiable_queries", 0)
        if unverifiable:
            return (
                f"No title-observable attribute drift detected. In this catalog the constraint "
                f"attributes (colour, size, gender, category) for {unverifiable} multi-attribute "
                "quer" + ("y" if unverifiable == 1 else "ies") + " appear only in facet metadata, "
                "not in product titles, so drift cannot be confirmed from result text — attribute "
                "handling for these is assessed in the failure-mode analysis (e.g. FACET_NOT_EXTRACTED, "
                "CONSTRAINT_DROPPED)."
            )
        return "No multi-attribute constraint queries were available for this diagnostic."
    affected = len(drift["queries"])
    return (
        f"{affected} multi-attribute quer" + ("y" if affected == 1 else "ies") + " showed genuine "
        "attribute drift: the product type was surfaced in the top results, but matching products "
        "for another title-observable attribute were ranked below it. Only attributes that actually "
        "appear in product titles are assessed; facet-only attributes are not guessed at."
    )


def _diversity_result_text(diversity: dict) -> str:
    if not diversity["applicable"]:
        return diversity["reason"]
    if not diversity["worst"]:
        return "No broad or exploratory result sets had enough results for this diagnostic."
    worst = diversity["worst"][0]
    return (
        f"The most redundant broad result set was \"{worst['query']}\": "
        f"{worst['unique_families']} unique product families across {worst['result_count']} top results."
    )


def _specificity_result_text(specificity: dict) -> str:
    if not specificity["detected"]:
        return (
            "No three-step specificity ladder was detected in this query set. This diagnostic activates when generated queries include broad -> specific query chains."
        )
    broken = [ladder for ladder in specificity["ladders"] if ladder["break_query"]]
    if broken:
        return f"Specificity break points were detected, starting with \"{broken[0]['break_query']}\"."
    return "Specificity ladders were detected, with no clear relevance drop across the tested chain."


def build_advanced_diagnostics_sections(
    site_context: SiteContext,
    judgments: list[QueryJudgment],
) -> list[dict]:
    diagnostics = build_advanced_diagnostics(site_context, judgments)
    purity = diagnostics["purity"]
    trust = diagnostics["top_result_trust"]
    drift = diagnostics["attribute_drift"]
    diversity = diagnostics["diversity"]

    sections = [
        {
            "key": "purity",
            "title": "Result Set Purity",
            "metric": f"{purity['top5']:.0f}%",
            "metric_label": "top 5 relevant",
            "metric_class": purity["top5_class"],
            "meaning": (
                "This checks how much of the visible result set is actually relevant, not just whether one good result exists somewhere. "
                "A noisy top 5 means customers must visually filter around weak results even when search technically found a match."
            ),
            "result": _purity_result_text(purity),
            "evidence": [
                f"\"{row['query']}\": {row['top5_relevant']}/{row['top5_total']} relevant in top 5"
                for row in purity["polluted_queries"][:4]
            ],
            "remedy": (
                "Tune ranking to demote low-relevance partial matches once a strong intent match exists. Add a top-N quality guardrail: "
                "for each important query class, require a minimum share of relevant results in the top 5, not only a good best-result position."
            ),
        },
        {
            "key": "top_result_trust",
            "title": "Top Result Trust",
            "metric": f"{trust['failure_rate']:.0f}%",
            "metric_label": "questionable #1 results",
            "metric_class": trust["failure_class"],
            "meaning": (
                "This asks whether the first result is defensible as the best thing to show a customer. "
                "A bad #1 is the clearest search failure because it shapes the shopper's first impression."
            ),
            "result": _trust_result_text(trust),
            "evidence": [
                f"\"{row['query']}\": #1 was \"{row['top_result']}\" (score {row['top_score']:.2f}). {row['reason']}"
                for row in trust["worst"][:4]
            ],
            "remedy": (
                "Add a stricter first-result threshold for high-intent queries. If the top result is weak and a stronger result exists lower, "
                "boost the stronger exact/category/brand match or suppress the weak partial match from rank #1."
            ),
        },
        {
            "key": "attribute_drift",
            "title": "Attribute Drift",
            "metric": str(len(drift["queries"])),
            "metric_label": "queries with attribute drift",
            "metric_class": "warn" if drift["queries"] else "good",
            "meaning": (
                "This decomposes multi-attribute queries to see which terms survive into the top results. "
                "It distinguishes right-category-but-wrong-attribute failures from total search failures. "
                "Only attributes that appear in product titles can be checked here; attributes carried in facet "
                "metadata (colour, size, gender) are assessed in the failure-mode analysis instead."
            ),
            "result": _drift_result_text(drift),
            "evidence": [
                f"\"{row['query']}\": kept {', '.join(row['preserved'])}; "
                f"buried below the top results: {', '.join(row['dropped'])}"
                + (f"; not verifiable from titles: {', '.join(row['unverifiable'])}" if row['unverifiable'] else "")
                for row in drift["worst"][:4]
            ],
            "remedy": (
                "Extract query attributes before ranking and give required attributes explicit weight. For brand, size, material, activity, and style terms, "
                "penalize results that match the product type but omit or contradict the attribute."
            ),
        },
        {
            "key": "diversity",
            "title": "Diversity vs Redundancy",
            "metric": (
                str(diversity["worst"][0]["unique_families"])
                if diversity.get("applicable") and diversity["worst"]
                else "N/A"
            ),
            "metric_label": "unique families in worst broad top 10",
            "metric_class": "bad" if diversity.get("applicable") and diversity["worst"] and diversity["worst"][0]["unique_families"] <= 3 else "warn",
            "meaning": (
                "This checks whether broad or exploratory queries show useful choice, or whether the top results are flooded by repeated variants. "
                "It is most useful for multi-brand or broad-catalog ecommerce, and less useful for true single-brand stores."
            ),
            "result": _diversity_result_text(diversity),
            "evidence": [
                f"\"{row['query']}\": {row['unique_families']} unique product families across {row['result_count']} top results"
                for row in diversity.get("worst", [])[:4]
            ],
            "remedy": (
                "Group color/size/variant duplicates under a product-family cap for broad queries. Keep exact product searches variant-rich, "
                "but diversify broad discovery queries across families, brands, styles, and use cases."
            ),
        },
    ]

    return sections
