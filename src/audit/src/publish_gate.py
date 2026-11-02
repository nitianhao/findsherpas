"""Pre-publish gate: refuse to put a report in front of a prospect when it is not trustworthy.

Every check here corresponds to something that already reached (or nearly reached) a client
deliverable:

- a fetch that never observed the page (bot wall, timeout) scored as "search returns nothing";
- a no-results recommendation widget scraped as results for several queries (Cotswold: six
  different queries "returned" the same socks and smartwatches);
- judge fallbacks and unresolved ``[MANUAL VERIFICATION REQUIRED]`` flags shipped as verdicts;
- internal workflow notes ("User override:", "per calibration") and raw reranker numbers
  ("Max relevance score is 0.000") in client-facing evidence;
- placeholder text ("Roadmap section was not generated") rendered as the headline fix.

Errors block publishing. Warnings are printed for the operator and do not block.

CLI (for the gated manual flow, before Phase 8)::

    python -m src.publish_gate reports/<site>/<slug>_data.json --html reports/<site>/<slug>_report.html
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.models import TRUSTED_FETCH_STATUSES, AuditReport

# Share of queries whose page the fetcher could not observe before the audit is unusable.
MAX_UNVERIFIED_FETCH_SHARE = 0.20
# Above this share of zero-result pages, the fetcher is more likely broken than the search.
WARN_ZERO_RESULT_SHARE = 0.50
# This many queries with an identical top-5 means a fallback widget was scraped.
IDENTICAL_TOP5_LIMIT = 3
# Page weight a prospect has to download; the renderer re-encodes the cover screenshot to stay
# under this budget.
try:
    from src.html_renderer import HTML_SIZE_BUDGET as WARN_HTML_BYTES
except ImportError:
    WARN_HTML_BYTES = 900_000

# Text that must never appear in anything a client reads.
_FORBIDDEN_CLIENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("raw relevance score", re.compile(r"\brelevance(?: score)?\s*(?:of|is|=|:)?\s*[01]\.\d{2,}", re.I)),
    # A bare 0.xxx is a reranker score unless a unit or currency follows ("Thermosflasche 0.750 L").
    ("raw score figure", re.compile(r"(?<![\d.,€£$])\b0\.\d{3}\b(?!\s*(?:l|ml|cl|dl|kg|g|mm|cm|m|oz|€|eur|£|\$|kr|sek|dkk|nok|chf)\b)", re.I)),
    # "voyage" alone is French for travel ("sac de voyage"); only the vendor spellings count.
    ("scoring internals", re.compile(r"\b(?:rerank(?:er|ed|ing)?|voyage[ -]?ai|voyage-\d|rerank-2|cross-encoder|max_relevance|relevance_score)\b", re.I)),
    ("model / tooling name", re.compile(r"\b(?:LLM|claude|sonnet|haiku|anthropic|openai|gpt-\d)\b", re.I)),
    ("override marker", re.compile(r"(?:user override|\[override|severity escalated|per calibration|calibration rule)", re.I)),
    ("unresolved manual check", re.compile(r"MANUAL VERIFICATION REQUIRED", re.I)),
    ("judge fallback text", re.compile(r"LLM analysis failed|failed to parse after", re.I)),
    # TODO is case-sensitive: "todo" is Spanish/Portuguese ("Zapatillas todo terreno").
    ("placeholder text", re.compile(r"(?:(?i:section was not generated|lorem ipsum)|\bTODO\b|\{\{\s*\w+\s*\}\})")),
]


@dataclass
class GateResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def format(self) -> str:
        lines = [f"Publish gate: {'PASS' if self.ok else 'BLOCKED'} "
                 f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))"]
        lines += [f"  ERROR   {e}" for e in self.errors]
        lines += [f"  warning {w}" for w in self.warnings]
        return "\n".join(lines)


def _client_text_fields(report: AuditReport):
    """(label, text) for every judgment field and narrative a client can read."""
    for cs in report.capability_scores:
        for j in cs.judgments:
            q = j.test_query.query
            yield f"evidence[{q!r}]", j.evidence or ""
            yield f"recommended_fix[{q!r}]", j.recommended_fix or ""
            if j.failure_mode_explanation:
                yield f"failure_mode_explanation[{q!r}]", j.failure_mode_explanation
    yield "deep_dive_narrative", report.deep_dive_narrative or ""
    yield "roadmap_narrative", report.roadmap_narrative or ""


def _visible_html_text(html: str) -> str:
    """Rough visible text: drop script/style/svg blocks and tags, keep attribute-free text."""
    html = re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def _stems(query: str) -> set[str]:
    return {t[:4] for t in re.findall(r"[^\W_]+", query.casefold()) if len(t) >= 3}


def _unrelated_query_count(queries: list[str]) -> int:
    """Number of groups of mutually unrelated queries (connected components on shared stems).

    "Hängematte Garten" / "Hängematten" / "Hängematte CHICO" legitimately return the same
    hammocks — one component. "walkinboots" / "waterprooftrousers" / "softshelljakket" sharing
    one top 5 are three components: the page is a fallback widget, not search results.
    """
    stems = [_stems(q) for q in queries]
    parent = list(range(len(queries)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(queries)):
        for k in range(i + 1, len(queries)):
            if stems[i] & stems[k]:
                parent[find(i)] = find(k)
    return len({find(i) for i in range(len(queries))})


def _scan(label: str, text: str, out: list[str]) -> None:
    for name, pattern in _FORBIDDEN_CLIENT_PATTERNS:
        m = pattern.search(text)
        if m:
            start = max(0, m.start() - 40)
            snippet = text[start:m.end() + 40].replace("\n", " ")
            out.append(f"{name} in {label}: …{snippet}…")


def check_report(report: AuditReport, html: str | None = None) -> GateResult:
    res = GateResult()
    judgments = [j for cs in report.capability_scores for j in cs.judgments]

    if not judgments:
        res.errors.append("report has no judgments")
        return res

    # ── Completeness ────────────────────────────────────────────────────
    judged = Counter(j.test_query.query for j in judgments)
    missing = [q.query for q in report.queries if q.query not in judged]
    if missing:
        res.errors.append(f"{len(missing)} generated queries have no judgment (e.g. {missing[:3]})")
    dupes = [q for q, n in judged.items() if n > 1]
    if dupes:
        res.warnings.append(f"queries judged more than once: {dupes[:5]}")

    # ── Fetch trust ─────────────────────────────────────────────────────
    unverified = [j for j in judgments if j.fetch_status and j.fetch_status not in TRUSTED_FETCH_STATUSES]
    if len(unverified) / len(judgments) > MAX_UNVERIFIED_FETCH_SHARE:
        statuses = Counter(j.fetch_status for j in unverified)
        res.errors.append(
            f"{len(unverified)}/{len(judgments)} queries were never observed reliably "
            f"({dict(statuses)}) — re-fetch before publishing"
        )
    if any(j.fetch_status and j.fetch_status not in TRUSTED_FETCH_STATUSES and j.excluded_reason is None
           for j in judgments):
        res.errors.append("an unverified fetch is being scored as a search result (excluded_reason missing)")

    scored = [j for j in judgments if j.excluded_reason is None]
    if not scored:
        res.errors.append("every judgment is excluded from scoring")
        return res

    zero = [j for j in scored if not j.results]
    if len(zero) / len(scored) > WARN_ZERO_RESULT_SHARE:
        res.warnings.append(
            f"{len(zero)}/{len(scored)} scored queries show zero results — confirm on the live site "
            "that this is the engine, not the fetcher"
        )

    top5_groups: dict[tuple, list[str]] = {}
    for j in scored:
        # Gibberish queries are *supposed* to land on the same fallback grid — that grid is the finding.
        if len(j.results) >= 3 and j.test_query.category != "GIBBERISH":
            key = tuple(r.title.strip().casefold() for r in sorted(j.results, key=lambda r: r.original_rank)[:5])
            top5_groups.setdefault(key, []).append(j.test_query.query)
    for qs in top5_groups.values():
        if _unrelated_query_count(qs) >= IDENTICAL_TOP5_LIMIT:
            res.errors.append(
                f"{len(qs)} different queries returned an identical top 5 ({qs[:4]}) — almost certainly "
                "a no-results recommendation widget scraped as results"
            )

    # ── Verdict provenance ──────────────────────────────────────────────
    fallbacks = [j.test_query.query for j in scored if j.judge_status == "fallback"]
    if fallbacks:
        res.errors.append(f"{len(fallbacks)} verdicts are judge fallbacks, not reviewed verdicts: {fallbacks[:5]}")
    # A verdict the judge could not settle from titles alone (e.g. colour not in any title) carries
    # a MANUAL CHECK note. The operator resolves it by confirming or overriding the verdict and
    # setting judge_status="manual"; until then it must not ship (six such flags once shipped as PASS).
    unresolved = [j.test_query.query for j in scored
                  if j.judge_status != "manual" and "MANUAL CHECK" in (j.internal_notes or "")]
    if unresolved:
        res.errors.append(
            f"{len(unresolved)} verdicts await a manual check (set judge_status='manual' once confirmed): {unresolved[:5]}"
        )

    rules_version = (report.run_metadata or {}).get("judge_rules_version")
    try:
        from src.judge import JUDGE_RULES_VERSION
    except ImportError:  # judge not importable in a stripped environment
        JUDGE_RULES_VERSION = None
    if JUDGE_RULES_VERSION and rules_version and rules_version != JUDGE_RULES_VERSION:
        res.errors.append(
            f"judged under rules {rules_version}, current rules are {JUDGE_RULES_VERSION} — re-judge first"
        )
    elif JUDGE_RULES_VERSION and not rules_version:
        res.warnings.append("report has no judge_rules_version (judged before versioning) — consider re-judging")

    # ── Client-facing text ──────────────────────────────────────────────
    if not (report.deep_dive_narrative or "").strip():
        res.errors.append("deep-dive narrative is empty")
    # Data fields: warnings. Legacy judgments carry scores in `evidence` by design (the renderer
    # sanitises them); what a client actually reads is checked on the rendered HTML below.
    field_hits: list[str] = []
    for label, text in _client_text_fields(report):
        _scan(label, text, field_hits)
    if field_hits:
        res.warnings.append(f"{len(field_hits)} internal-detail hits in client text fields of the data, e.g. {field_hits[0]}")
    if html is None:
        res.warnings.append("no rendered HTML supplied — client-visible text was not checked")

    # ── Rendered HTML ───────────────────────────────────────────────────
    if html is not None:
        size = len(html.encode("utf-8"))
        if size > WARN_HTML_BYTES:
            res.warnings.append(f"HTML is {size / 1e6:.2f} MB — compress the embedded screenshot")
        if "findsherpas.com/book-a-call" not in html:
            res.errors.append("final CTA link to findsherpas.com/book-a-call is missing")
        if "<svg" not in html:
            res.errors.append("cover logo (inline SVG) is missing")
        _scan("rendered HTML", _visible_html_text(html), res.errors)

    return res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check an audit report before publishing it.")
    parser.add_argument("data_json", help="Path to <slug>_data.json")
    parser.add_argument("--html", help="Path to the rendered <slug>_report.html")
    args = parser.parse_args(argv)

    try:
        report = AuditReport.model_validate(json.loads(Path(args.data_json).read_text(encoding="utf-8")))
    except Exception as e:  # pydantic.ValidationError, JSONDecodeError
        print(f"Publish gate: BLOCKED — {args.data_json} does not validate against the current models:\n{str(e)[:800]}")
        return 1
    html = Path(args.html).read_text(encoding="utf-8") if args.html else None
    result = check_report(report, html)
    print(result.format())
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
