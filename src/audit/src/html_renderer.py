"""Render an AuditReport into a branded HTML file using the Jinja2 template."""

from __future__ import annotations

import base64
import re
from collections import Counter
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.models import (
    AuditReport,
    QueryJudgment,
    Severity,
)
from src.report_generator import (
    PIPELINE_NAME,
    _CAPABILITY_NAMES,
    _CATEGORY_DISPLAY,
    _CATEGORY_TO_CAPABILITY,
    _FAILURE_MODE_DISPLAY,
    _SEVERITY_RANK,
    _SEVERITY_SHORT,
    build_capability_scores,
    compute_aggregate_stats,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_DIR = _PROJECT_ROOT / "templates"
_ASSETS_DIR = _PROJECT_ROOT / "assets"


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

def _severity_class(severity_value: str) -> str:
    """Map a Severity enum .value to a CSS class name."""
    short = _SEVERITY_SHORT.get(severity_value, "")
    return short.lower()  # "critical", "moderate", "minor", "pass"


def _severity_short(severity_value: str) -> str:
    return _SEVERITY_SHORT.get(severity_value, severity_value)


# ---------------------------------------------------------------------------
# Data builders
# ---------------------------------------------------------------------------

def _build_stats(report: AuditReport, judgments: list[QueryJudgment]) -> dict:
    raw = compute_aggregate_stats(judgments)
    cap_scores = build_capability_scores(judgments)
    total_cap = len(cap_scores)
    pass_cap = sum(1 for cs in cap_scores if cs.severity == Severity.PASS.value)
    num_categories = len({j.test_query.category for j in judgments})

    poor_ranking_count = sum(1 for j in judgments if j.failure_mode == "POOR_RANKING")
    pct_retrieval = (poor_ranking_count / raw["total_queries"] * 100) if raw["total_queries"] else 0

    avg_pos = raw["avg_best_position"]
    pct_top3 = raw["pct_top3_irrelevant"]
    pct_top1 = raw["pct_top1_irrelevant"]

    return {
        "total_capabilities": total_cap,
        "pass_count": pass_cap,
        "total_queries": raw["total_queries"],
        "critical_count": raw["critical_count"],
        "moderate_count": raw["moderate_count"],
        "minor_count": raw["minor_count"],
        "pass_count_queries": raw["pass_count"],
        "avg_best_position": f"{avg_pos:.0f}",
        "avg_best_position_num": avg_pos,
        "pct_top3_irrelevant": f"{pct_top3:.0f}",
        "pct_top3_irrelevant_num": pct_top3,
        "pct_top1_irrelevant": f"{pct_top1:.0f}",
        "pct_top1_irrelevant_num": pct_top1,
        "worst_query": raw["worst_example_query"],
        "worst_displacement": raw["worst_example_displacement"] + 1,
        "pct_retrieval_ok": f"{pct_retrieval:.0f}",
        "retrieval_ok_count": poor_ranking_count,
        "num_categories": num_categories,
    }


def _build_capability_scores_ctx(judgments: list[QueryJudgment]) -> list[dict]:
    scores = build_capability_scores(judgments)
    return [
        {
            "capability_name": _CAPABILITY_NAMES.get(cs.capability, cs.capability),
            "severity_class": _severity_class(cs.severity),
            "severity_short": _severity_short(cs.severity),
            "summary": cs.summary,
        }
        for cs in scores
    ]


def _build_failure_modes(judgments: list[QueryJudgment]) -> list[dict]:
    counts = Counter(
        j.failure_mode for j in judgments if j.severity != Severity.PASS.value
    )
    return [
        {"name": _FAILURE_MODE_DISPLAY.get(mode, mode), "count": count}
        for mode, count in counts.most_common()
    ]


def _build_critical_failures(judgments: list[QueryJudgment]) -> list[dict]:
    """Extract the 3-5 most severe query failures for the Critical Failure Examples section."""
    critical = [
        j for j in judgments if j.severity == Severity.CRITICAL.value
    ]
    # Sort by displacement descending (worst buried results first)
    critical.sort(key=lambda j: -j.displacement)
    top = critical[:5] if len(critical) >= 3 else sorted(
        [j for j in judgments if j.severity != Severity.PASS.value],
        key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
    )[:5]

    results = []
    for j in top:
        by_original = sorted(j.results, key=lambda r: r.original_rank)
        actual_top_title = by_original[0].title if by_original else "N/A"
        cap_name = _CAPABILITY_NAMES.get(
            _CATEGORY_TO_CAPABILITY.get(j.test_query.category, ""),
            _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
        )
        results.append({
            "query": j.test_query.query,
            "expected_intent": cap_name,
            "actual_result": actual_top_title,
            "explanation": j.evidence,
            "severity_class": _severity_class(j.severity),
            "severity_short": _severity_short(j.severity),
            "best_position": j.displacement + 1,
        })
    return results


def _build_deep_dives(judgments: list[QueryJudgment]) -> list[dict]:
    """Build structured deep-dive data for each failing capability."""
    scores = build_capability_scores(judgments)
    failing = [cs for cs in scores if cs.severity != Severity.PASS.value]

    caps = []
    for cs in failing:
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)

        # Sort judgments: worst severity first, then highest displacement
        sorted_js = sorted(
            cs.judgments,
            key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
        )
        # Take up to 5 worst
        top_js = sorted_js[:5]

        queries = []
        for j in top_js:
            by_original = sorted(j.results, key=lambda r: r.original_rank)[:5]
            by_relevance = sorted(j.results, key=lambda r: r.relevance_score, reverse=True)[:3]

            queries.append({
                "query": j.test_query.query,
                "category": _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
                "severity_class": _severity_class(j.severity),
                "severity_short": _severity_short(j.severity),
                "best_position": j.displacement + 1,
                "displacement": j.displacement,
                "evidence": j.evidence,
                "actual_top": [
                    {"title": r.title, "price": r.price}
                    for r in by_original
                ],
                "ideal_top": [
                    {"title": r.title, "price": r.price}
                    for r in by_relevance
                ],
            })

        caps.append({
            "capability_name": cap_name,
            "severity_class": _severity_class(cs.severity),
            "queries": queries,
        })

    return caps


def _build_whats_working(judgments: list[QueryJudgment]) -> list[str]:
    """Return plain-text bullets for the What's Working section."""
    scores = build_capability_scores(judgments)
    bullets: list[str] = []

    # Minor capabilities
    for cs in scores:
        if cs.severity == Severity.MINOR.value:
            cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
            bullets.append(f"<strong>{cap_name} is mostly functional</strong> — minor issues only. {cs.summary}")

    # Retrieval worked
    poor_ranking = [j for j in judgments if j.failure_mode == "POOR_RANKING" and j.max_relevance_score >= 0.60]
    if poor_ranking:
        bullets.append(
            f"<strong>Retrieval is working</strong> — relevant results were found in {len(poor_ranking)} of "
            f"{len(judgments)} queries. The primary issue is ranking, not finding: the right results exist "
            f"in the result set but aren't being surfaced at the top."
        )

    # Near misses
    near_miss = [j for j in judgments if j.displacement <= 2 and j.severity != Severity.PASS.value]
    if near_miss:
        examples = [f'"{j.test_query.query}"' for j in near_miss[:3]]
        bullets.append(
            f"<strong>Close to correct</strong> on {len(near_miss)} queries ({', '.join(examples)}): "
            f"the best result was within the top 3, just not at #1."
        )

    # Typo recognition
    typo_caps = [cs for cs in scores if cs.capability == "TYPO_TOLERANCE"]
    for cs in typo_caps:
        retrieval_ok = [
            j for j in cs.judgments
            if j.failure_mode != "NO_FUZZY_MATCHING" and j.failure_mode != "ZERO_RESULTS_OR_GARBAGE"
        ]
        if retrieval_ok and len(retrieval_ok) == len(cs.judgments):
            bullets.append(
                "<strong>Your search correctly interprets typos and spelling variations</strong> — "
                "when we searched with misspellings, it recognized what customers meant. "
                "The issue is ranking the corrected results, not recognising the typo."
            )
            break

    if not bullets:
        bullets.append(
            "No capabilities passed all tests. However, the search engine does retrieve relevant "
            "results for most queries — the primary issue is ranking, not retrieval."
        )

    return bullets


def _parse_roadmap(roadmap_markdown: str) -> list[dict]:
    """Parse the LLM-generated roadmap markdown into structured items."""
    items = []
    # Match numbered items: "1. **Title**\n   Description\n   Impact: X | Effort: Y"
    pattern = re.compile(
        r"^\d+\.\s+\*\*(.+?)\*\*\s*\n\s+(.+?)(?:\n\s+Impact:\s*(\w+).*?\|\s*Effort:\s*(.+?))?$",
        re.MULTILINE,
    )

    # Simpler approach: split on numbered items
    chunks = re.split(r"\n(?=\d+\.\s+\*\*)", roadmap_markdown.strip())
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        # Extract title
        title_match = re.search(r"\*\*(.+?)\*\*", chunk)
        title = title_match.group(1) if title_match else chunk[:80]

        # Extract impact/effort from the last line
        impact = effort = ""
        impact_match = re.search(r"Impact:\s*(\w+)", chunk)
        effort_match = re.search(r"Effort:\s*(.+?)(?:\n|$)", chunk)
        if impact_match:
            impact = impact_match.group(1)
        if effort_match:
            effort = effort_match.group(1).strip()

        # Description: everything between title and impact line
        desc_text = chunk
        desc_text = re.sub(r"^\d+\.\s+\*\*.+?\*\*\s*", "", desc_text).strip()
        desc_text = re.sub(r"\s*Impact:.*$", "", desc_text, flags=re.MULTILINE).strip()

        impact_class = {
            "Critical": "critical",
            "High": "high",
            "Moderate": "moderate",
        }.get(impact, "moderate")

        effort_class = "quick"
        if "Medium" in effort:
            effort_class = "medium"
        elif "Major" in effort:
            effort_class = "major"

        items.append({
            "title": title,
            "description": desc_text,
            "impact": impact,
            "effort": effort,
            "impact_class": impact_class,
            "effort_class": effort_class,
        })

    return items


def _build_benchmarks(stats: dict) -> list[dict]:
    pct_top3_relevant = 100 - float(stats["pct_top3_irrelevant"])
    return [
        {
            "metric": "Relevant result in top 3",
            "your_score": f"{pct_top3_relevant:.0f}%",
            "target": "80%+",
            "source": "Baymard Institute",
            "score_class": "below" if pct_top3_relevant < 80 else "meets",
        },
        {
            "metric": "Average best result position",
            "your_score": f"#{stats['avg_best_position']}",
            "target": "#1\u20132",
            "source": "Industry best practice",
            "score_class": "below" if float(stats["avg_best_position"]) > 2 else "meets",
        },
        {
            "metric": "Irrelevant #1 result",
            "your_score": f"{stats['pct_top1_irrelevant']}%",
            "target": "<10%",
            "source": "Industry best practice",
            "score_class": "below" if float(stats["pct_top1_irrelevant"]) > 10 else "meets",
        },
    ]


_METHODOLOGY_STEPS = [
    {
        "title": "Site Discovery",
        "description": "Automated analysis of your site\u2019s structure, navigation categories, brands, and featured products to understand what your search engine should be able to find.",
    },
    {
        "title": "Test Design",
        "description": "Site-type-aware selection from a library of 26 test categories. Categories are chosen based on your site\u2019s commerce model to ensure the audit tests what matters most for your customers.",
    },
    {
        "title": "Query Generation",
        "description": "AI-generated realistic customer queries grounded in the actual products, brands, and categories found on your site \u2014 not generic templates.",
    },
    {
        "title": "Result Collection",
        "description": "Automated search execution collecting the top results for each test query exactly as your customers would see them.",
    },
    {
        "title": "Relevance Scoring",
        "description": "Each result scored on a 0.0\u20131.0 scale by a specialized relevance model, producing an objective measure of how well each result matches the query intent.",
    },
    {
        "title": "Failure Analysis",
        "description": "Each query classified by failure mode (e.g., poor ranking, constraint dropped, no fuzzy matching) and severity based on how far the best result was buried below irrelevant ones.",
    },
    {
        "title": "Report Assembly",
        "description": "Findings synthesized into this actionable narrative with prioritized recommendations ordered by business impact.",
    },
]


def _build_appendix(judgments: list[QueryJudgment]) -> list[dict]:
    sorted_js = sorted(
        judgments,
        key=lambda j: (-_SEVERITY_RANK.get(j.severity, 0), -j.displacement),
    )
    rows = []
    for j in sorted_js:
        sev_class = _severity_class(j.severity)
        sev_short = _severity_short(j.severity)
        fm = _FAILURE_MODE_DISPLAY.get(j.failure_mode, j.failure_mode)

        if j.severity == Severity.PASS.value:
            fm = "\u2014"
            best_pos = 1
        else:
            best_pos = j.displacement + 1

        rows.append({
            "query": j.test_query.query,
            "category": _CATEGORY_DISPLAY.get(j.test_query.category, j.test_query.category),
            "severity_class": sev_class,
            "severity_short": sev_short,
            "best_position": best_pos,
            "failure_mode": fm,
        })
    return rows


# ---------------------------------------------------------------------------
# Main rendering functions
# ---------------------------------------------------------------------------

def _load_logo_svg() -> str:
    logo_path = _ASSETS_DIR / "logo.svg"
    if logo_path.exists():
        return logo_path.read_text(encoding="utf-8")
    return ""


def render_html_report(report: AuditReport, screenshot_path: str | Path | None = None) -> str:
    """Render an AuditReport into a self-contained HTML string."""
    # Reconstruct judgments from capability_scores
    judgments: list[QueryJudgment] = []
    for cs in report.capability_scores:
        judgments.extend(cs.judgments)

    # If no judgments in capability_scores, the report has no data
    if not judgments:
        return "<html><body><p>No audit data available.</p></body></html>"

    site_name = report.site_context.site_name or report.site_context.url
    stats = _build_stats(report, judgments)

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,  # we control the HTML
    )
    template = env.get_template("master_report.html")

    screenshot_b64 = None
    if screenshot_path:
        sp = Path(screenshot_path)
        if sp.exists():
            screenshot_b64 = base64.b64encode(sp.read_bytes()).decode("ascii")

    context = {
        "site_name": site_name,
        "date": date.today().strftime("%B %d, %Y"),
        "pipeline_name": PIPELINE_NAME,
        "logo_svg": _load_logo_svg(),
        "screenshot_b64": screenshot_b64,
        "stats": stats,
        "capability_scores": _build_capability_scores_ctx(judgments),
        "failure_modes": _build_failure_modes(judgments),
        "deep_dives": _build_deep_dives(judgments),
        "critical_failures": _build_critical_failures(judgments),
        "whats_working": _build_whats_working(judgments),
        "roadmap_items": _parse_roadmap(report.roadmap_narrative),
        "benchmarks": _build_benchmarks(stats),
        "methodology_steps": _METHODOLOGY_STEPS,
        "appendix": _build_appendix(judgments),
    }

    return template.render(**context)


def save_html_report(report: AuditReport, output_path: str | Path, screenshot_path: str | Path | None = None) -> Path:
    """Render and save the HTML report to a file. Returns the output path."""
    html = render_html_report(report, screenshot_path=screenshot_path)
    path = Path(output_path)
    path.write_text(html, encoding="utf-8")
    return path
