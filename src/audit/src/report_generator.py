"""Phase 7 — assemble the audit report: deterministic scoring + two grounded LLM narratives.

Numbers come from :mod:`src.report_stats` (shared with the HTML renderer). The two narratives —
per-capability deep dives and the prioritised roadmap — are separate structured calls
(:func:`generate_deep_dives`, :func:`generate_roadmap`). Both are checked by
:func:`grounding_violations` before they are accepted: every quoted search must be a tested
query, every quoted product title must appear in that search's results, every "#N" must be a
real result position, and "the store carries X" needs proof. A failed check regenerates once,
then raises — no placeholder text can ever reach a rendered report.

The accepted narratives are stored, query-keyed, in
``report.run_metadata["report_content"]`` so the HTML renders the same reviewed text as the .md.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.advanced_diagnostics import build_advanced_diagnostics_markdown
from src.llm_compat import LLMResponseError, structured_call
from src.models import (
    AuditReport,
    CapabilityScore,
    QueryCategory,
    QueryJudgment,
    Severity,
    SiteContext,
)
from src.report_stats import (
    CAPABILITY_NAMES,
    CATEGORY_DISPLAY,
    CATEGORY_TO_CAPABILITY,
    EXCLUDED_REASON_TEXT,
    FAILURE_MODE_DISPLAY,
    FOUND_BUT_WRONG_LABEL,
    SAMPLE_NOTE,
    SEVERITY_RANK,
    SEVERITY_SHORT,
    ZERO_RESULT_FOOTNOTE,
    ZERO_RESULT_LABEL,
    BENCHMARK_NOTE,
    benchmark_rows,
    better_matches,
    build_capability_scores,
    by_original,
    capability_rows,
    category,
    client_observation,
    compute_stats,
    excluded,
    formatted_stats,
    is_pass,
    md_cell,
    mode,
    peer_label,
    pick_worst_example,  # noqa: F401 — re-exported for callers of the old location
    position_context,
    proof_of_stock,
    root_causes,
    scope_line,
    scored,
    search_url,
    sev,
    whats_working_items,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Overridable per-run; unset env = unchanged default. See docs/CASE_STUDY_PLAYBOOK.md.
_MODEL = os.environ.get("AUDIT_MODEL_REPORT", "claude-sonnet-4-6")

# Back-compat names (orchestrator / runner scripts import these from here).
_SEVERITY_RANK = SEVERITY_RANK
_SEVERITY_SHORT = SEVERITY_SHORT
_CAPABILITY_NAMES = CAPABILITY_NAMES
_FAILURE_MODE_DISPLAY = FAILURE_MODE_DISPLAY
_CATEGORY_DISPLAY = CATEGORY_DISPLAY
_CATEGORY_TO_CAPABILITY = CATEGORY_TO_CAPABILITY
compute_aggregate_stats = compute_stats

# Report is unbranded; kept for backward-compat references.
PIPELINE_NAME = ""

_SEVERITY_EMOJI: dict[str, str] = {
    Severity.CRITICAL.value: "\U0001f534",
    Severity.MODERATE.value: "\U0001f7e1",
    Severity.MINOR.value: "\U0001f7e2",
    Severity.PASS.value: "✅",
}

_OWNER_LABELS = {"merch": "Merchandising team", "dev": "Development team"}


class GroundingError(LLMResponseError):
    """A narrative quoted a search, product title or position that isn't in the audit data."""


# ---------------------------------------------------------------------------
# PART 1 — Deterministic markdown sections
# ---------------------------------------------------------------------------


def build_scorecard_markdown(judgments_or_scores) -> str:
    """Capability priority table. Same order and labels as the HTML improvement map."""
    rows = capability_rows(_as_judgments(judgments_or_scores))
    lines = [
        "## Search Improvement Focus Map\n",
        f"We tested your site's search across {len(rows)} core capabilities and grouped the results "
        "by where improvements are likely to help most.\n",
        "",
        "| Priority | Capability | What it means |",
        "|----------|-----------|---------------|",
    ]
    for r in rows:
        lines.append(f"| {md_cell(r['priority'])} | {md_cell(r['capability'])} | {md_cell(r['summary'])} |")
    lines.append("")
    lines.append("**Use this as an improvement map: the focus areas are where changes are likely to help "
                 "the most customer journeys.**")
    return "\n".join(lines)


def build_whats_working_markdown(judgments_or_scores) -> str:
    """Strengths at the query-category grain, every statement checked against data ("" if none)."""
    items = whats_working_items(_as_judgments(judgments_or_scores))
    if not items:
        return ""
    lines = ["## What's Working\n"]
    lines.extend(f"- **{it['label']}** {it['text']}" for it in items)
    return "\n".join(lines)


def _as_judgments(value) -> list[QueryJudgment]:
    """Accept judgments or CapabilityScores (legacy call shape)."""
    value = list(value or [])
    if value and isinstance(value[0], CapabilityScore):
        return [j for cs in value for j in cs.judgments]
    return value


# ---------------------------------------------------------------------------
# PART 2 — Grounded LLM narratives (deep dives + roadmap, separate calls)
# ---------------------------------------------------------------------------


class Impact(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"


class Effort(str, Enum):
    QUICK_WIN = "Quick Win"
    MEDIUM = "Medium Effort"
    MAJOR = "Major Project"


class Owner(str, Enum):
    MERCH = "merch"
    DEV = "dev"


class RoadmapItemOut(BaseModel):
    query_ids: list[int] = Field(description="Ids of the failing searches this fix resolves.")
    title: str = Field(description="One clear action, plain text.")
    description: str = Field(description="One or two sentences: what changes and what it fixes.")
    impact: Impact
    effort: Effort
    owner: Owner


class RoadmapOut(BaseModel):
    items: list[RoadmapItemOut]


class DeepDiveExampleOut(BaseModel):
    query_id: int
    narrative: str = Field(description="1-2 plain-language sentences about what the shopper saw.")


class DeepDiveSectionOut(BaseModel):
    capability_id: int
    intro: str = Field(description="2-3 sentences: what this capability means for shoppers.")
    examples: list[DeepDiveExampleOut]


class DeepDivesOut(BaseModel):
    sections: list[DeepDiveSectionOut]


_SHARED_RULES = """Audience: a business stakeholder at the store (e-commerce, merchandising or product lead). Plain language, short sentences. No technical jargon ("fuzzy matching", "tokenization", "relevance score", "reranker", "embedding"). Never use the words leverage, robust, optimize, deep dive, powerful or unique. Say "results", "products" or "items" — not "deals", "listings" or "offers" unless quoting a title.

GROUNDING RULES — your answer is checked automatically and rejected if it breaks any of them:
1. Put searches and product titles in straight double quotes, copied exactly from the data. Quote only searches and titles that appear in the data you were given for that example or item. Never invent a search or a product.
2. Cite a result position "#N" only when that position appears under "Customer saw" for the same example. Searches with no results have no positions.
3. Say or imply that the store carries, stocks or sells a product ONLY when the data has a "Proof the store carries it" line for that search — and then cite that proof. Without it, describe only what the shopper saw.
4. No scores, percentages or prices that are not in the data. Prices keep the currency exactly as shown; never introduce a budget or currency of your own.
5. Do not name or qualify the site's own language ("Swedish category terms", "German synonyms"); the quoted searches already show it.
6. Plain text only: no markdown, no headings, no bullet characters, no bold."""

_DEEP_DIVE_SYSTEM = """You write the per-capability analysis section of a site-search audit report.

""" + _SHARED_RULES + """

TASK: For each capability in the data, return one section:
- capability_id: the capability number given in the data.
- intro: 2-3 sentences on what this capability means for shoppers and why it matters for the business.
- examples: up to 5 of that capability's searches, worst first. Use only the ids listed under that capability. If it has fewer than 5, show only those.
  narrative: 1-2 sentences in plain language about what the shopper experienced, referencing specific product titles from that search's data.
Match the narrative to the failure:
- No results: say plainly the search returned nothing. Name the kind of product that should have appeared; do not list specific titles it "should have shown"; no position numbers.
- Constraint dropped: lead with the violation across the set ("every result contained leather") and quote one or two offending titles. No position number.
- Ranking (results exist and a better match sat lower): say where the better match was ("#N").
Do not add warnings like "most customers never scroll past position 3". Vary how examples and sections open; never use the same opening structure twice in a row."""

_ROADMAP_SYSTEM = """You write the prioritised roadmap of a site-search audit report.

""" + _SHARED_RULES + """

TASK: Return 3 to 8 fixes (fewer if there are fewer distinct problems), ordered by business impact, most impactful first. For each item:
- query_ids: the ids of the failing searches this fix resolves (at least one; only ids from the data).
- title: one clear action, at most about 12 words.
- description: one or two sentences on what changes and what it fixes for shoppers. You may quote one or two of the item's own searches.
- impact: Critical when it fixes critical searches, else High or Moderate.
- effort: Quick Win (configuration or rules, days), Medium Effort (development, 2-4 weeks), Major Project (1-3 months).
- owner: merch for synonyms, redirects, merchandising rules, category mapping and product data; dev for query parsing, ranking logic and index changes.

CONSOLIDATION — one mechanism, one item:
- Searches that fail for the same underlying reason are ONE fix. The "Root causes" list in the data groups them for you.
- "The product type in the query is under-weighted against a colour, material or season word" is ONE item: it covers both requiring the product-type noun and boosting it above modifier-only matches, and it absorbs every ordering problem within a correctly retrieved set. Never add a separate generic item about ranking or relevance order.
- All category-mapping failures (occasion, colloquial or category terms that should map to the store's categories) are ONE item.

TITLES: no title may be about "relevance", "relevance score", "the ranking algorithm", "sort order" or "re-ranking" in the abstract. Name the concrete behaviour (treat price phrases as a filter; boost the product type; map gift and occasion terms to categories). Item 1 in particular must name the concrete intent signals (brand, product type, price, sale, bestseller, exclusion) to act on before generic keyword matching."""


def failing_judgments(judgments: list[QueryJudgment]) -> list[QueryJudgment]:
    """Scored, non-PASS judgments in a stable order — the id space both prompts share."""
    fails = [j for j in scored(judgments) if not is_pass(j)]
    fails.sort(key=lambda j: (-SEVERITY_RANK.get(sev(j), 0), CATEGORY_TO_CAPABILITY.get(category(j), ""),
                              j.test_query.query))
    return fails


def _price(r) -> str:
    return f" ({r.price})" if r.price else ""


def _judgment_block(idx: int, j: QueryJudgment, all_scored: list[QueryJudgment]) -> str:
    lines = [
        f'[{idx}] "{j.test_query.query}" — category: {CATEGORY_DISPLAY.get(category(j), category(j))}; '
        f"failure: {FAILURE_MODE_DISPLAY.get(mode(j), mode(j))}; severity: {SEVERITY_SHORT.get(sev(j), sev(j))}",
        f"    What we observed: {client_observation(j)}",
    ]
    results = by_original(j)[:5]
    if results:
        lines.append("    Customer saw: " + "; ".join(f'#{r.original_rank} "{r.title}"{_price(r)}' for r in results))
        better = [r for r in better_matches(j) if r.original_rank != 1]
        if better:
            lines.append("    Better matches further down: " +
                         "; ".join(f'#{r.original_rank} "{r.title}"' for r in better))
    else:
        lines.append("    Customer saw: nothing (no results)")
    proof = proof_of_stock(j, all_scored)
    if proof:
        lines.append(f'    Proof the store carries it: searching "{proof["working_variant"]}" returns '
                     f'"{proof["example_title"]}"')
    return "\n".join(lines)


def _site_header(site_context: SiteContext) -> str:
    currency = getattr(site_context, "currency", "") or "as shown in the prices"
    return (f"Site: {site_context.site_name or '(unknown)'} ({site_context.url})\n"
            f"Currency of prices on the site: {currency}")


def _capability_groups(fails: list[QueryJudgment], all_scored: list[QueryJudgment]) -> list[tuple[str, list[int]]]:
    """[(capability key, [ids])] in the scorecard's priority order."""
    order = [r["capability_key"] for r in capability_rows(all_scored)]
    groups: dict[str, list[int]] = {}
    for i, j in enumerate(fails):
        groups.setdefault(CATEGORY_TO_CAPABILITY.get(category(j), ""), []).append(i)
    return [(cap, groups[cap]) for cap in order if cap in groups]


def _deep_dive_user(site_context, fails, all_scored) -> str:
    blocks = [_site_header(site_context), ""]
    for cid, (cap, ids) in enumerate(_capability_groups(fails, all_scored)):
        blocks.append(f"## Capability {cid}: {CAPABILITY_NAMES.get(cap, cap)}")
        blocks.extend(_judgment_block(i, fails[i], all_scored) for i in ids)
        blocks.append("")
    return "\n".join(blocks)


def _roadmap_user(site_context, fails, all_scored) -> str:
    blocks = [_site_header(site_context), "", "## Failing searches"]
    blocks.extend(_judgment_block(i, j, all_scored) for i, j in enumerate(fails))
    index = {j.test_query.query: i for i, j in enumerate(fails)}
    blocks.append("\n## Root causes (searches failing for the same reason)")
    for rc in root_causes(fails):
        ids = ", ".join(str(index[q]) for q in rc["queries"] if q in index)
        blocks.append(f"- {rc['mechanism']}: ids {ids} ({rc['critical']} critical)")
    return "\n".join(blocks)


# ── Grounding validator ─────────────────────────────────────────────────

_QUOTE_RE = re.compile(r'"([^"\n]{2,200})"|“([^”\n]{2,200})”|‘([^’\n]{2,200})’')
_RANK_RE = re.compile(r"#\s?(\d{1,3})\b")
_CARRY_RE = re.compile(r"\b(?:carr(?:y|ies|ied)|stock(?:s|ed)?|in stock|sells?|sold)\b", re.I)


def _gnorm(s: str) -> str:
    """Comparison key: casefolded word tokens only.

    Punctuation-insensitive, so a narrative quoting "Gozney Tread Portable Pizza Oven" matches the
    scraped title "Gozney Tread - Portable Pizza Oven".
    """
    return " ".join(re.findall(r"[^\W_]+", (s or "").casefold()))


def _catalog_titles(all_scored: list[QueryJudgment], site_context: SiteContext | None) -> set[str]:
    """Every real product title the audit observed: any tested search's results + the catalog sample."""
    titles = {_gnorm(r.title) for j in all_scored for r in j.results}
    if site_context is not None:
        titles.update(_gnorm(t) for t in (site_context.catalog_sample or []) + (site_context.featured_items or []))
    titles.discard("")
    return titles


def _allowed_strings(scope: list[QueryJudgment], all_scored: list[QueryJudgment],
                     site_context: SiteContext | None) -> tuple[set[str], set[int], bool]:
    """(allowed quote strings, allowed #ranks, whether a carry claim is provable)."""
    allowed: set[str] = {_gnorm(j.test_query.query) for j in all_scored}
    ranks: set[int] = set()
    provable = False
    for j in scope:
        if j.test_query.target_term:
            allowed.add(_gnorm(j.test_query.target_term))
        for r in j.results:
            allowed.add(_gnorm(r.title))
            ranks.add(r.original_rank)
        proof = proof_of_stock(j, all_scored)
        if proof:
            provable = True
            allowed.add(_gnorm(proof["working_variant"]))
            allowed.add(_gnorm(proof["example_title"]))
    if site_context is not None:
        allowed.update(_gnorm(x) for x in (site_context.nav_categories or []) + (site_context.brands or []))
    # A real product observed anywhere in the audit may be named (e.g. as proof the store
    # stocks what a zero-result search was looking for).
    allowed |= _catalog_titles(all_scored, site_context)
    allowed.discard("")
    return allowed, ranks, provable


def grounding_violations(
    text: str,
    scope: list[QueryJudgment],
    all_scored: list[QueryJudgment],
    site_context: SiteContext | None = None,
    label: str = "text",
) -> list[str]:
    """Everything in ``text`` that is not backed by the audit data, as readable messages.

    ``scope`` is the set of judgments the text is about (one example, a capability, a roadmap
    item). Quotes must be tested searches (any) or titles/terms from the scope's results or
    proof; "#N" must be a position in the scope's results; carry/stock claims need proof.
    """
    problems: list[str] = []
    allowed, ranks, provable = _allowed_strings(scope, all_scored, site_context)
    catalog = _catalog_titles(all_scored, site_context)
    for m in _QUOTE_RE.finditer(text or ""):
        quote = _gnorm(next(g for g in m.groups() if g is not None))
        if len(quote) < 2 or quote in allowed:
            continue
        if re.fullmatch(r"[^\W\d_]{1,10}", quote):
            continue  # a single plain word ("not", "wool") is a quoted query term, not a claim
        if len(quote) >= 3 and any(quote in a for a in allowed):
            continue  # partial quote of a real title or query
        if quote in catalog or (len(quote) >= 8 and any(quote in t for t in catalog)):
            provable = True  # naming a real, observed product backs a "the store carries it" claim
            continue
        problems.append(f"{label}: quoted \"{quote}\" is not a tested search or a product title in its results")
    if not provable:
        # Quoted real products (from any search or the catalog sample) prove stock.
        quoted = [_gnorm(next(g for g in m.groups() if g is not None)) for m in _QUOTE_RE.finditer(text or "")]
        provable = any(len(q) >= 8 and (q in catalog or any(q in t for t in catalog)) for q in quoted)
    prose = _QUOTE_RE.sub(" ", text or "")  # positions/claims are checked outside quoted titles
    for m in _RANK_RE.finditer(prose):
        n = int(m.group(1))
        if n not in ranks:
            problems.append(f"{label}: cites #{n}, which is not a result position for these searches")
    zero_scope = [j for j in failing_judgments(scope) if not j.results]
    if zero_scope and not provable and _CARRY_RE.search(prose):
        problems.append(f"{label}: claims the store carries/stocks the product without proof")
    return problems


def _scope_for(queries: list[str], all_scored: list[QueryJudgment]) -> list[QueryJudgment]:
    by_q = {j.test_query.query: j for j in all_scored}
    return [by_q[q] for q in queries if q in by_q]


def deep_dive_violations(sections: list[dict], judgments: list[QueryJudgment],
                         site_context: SiteContext | None = None) -> list[str]:
    """Validate stored-format deep dives against the audit data."""
    sc = scored(judgments)
    fails = {j.test_query.query for j in failing_judgments(sc)}
    problems: list[str] = []
    for s in sections:
        cap = s.get("capability")
        queries = [e.get("query") for e in s.get("examples", [])]
        for q in queries:
            if q not in fails:
                problems.append(f"deep dive {cap}: example \"{q}\" is not a failing tested search")
        cap_scope = [j for j in sc if CATEGORY_TO_CAPABILITY.get(category(j)) == cap]
        problems += grounding_violations(s.get("intro", ""), cap_scope, sc, site_context, f"deep dive {cap} intro")
        for e in s.get("examples", []):
            problems += grounding_violations(e.get("narrative", ""), _scope_for([e.get("query")], sc), sc,
                                             site_context, f"deep dive \"{e.get('query')}\"")
    return problems


def roadmap_violations(items: list[dict], judgments: list[QueryJudgment],
                       site_context: SiteContext | None = None) -> list[str]:
    """Validate stored-format roadmap items against the audit data."""
    sc = scored(judgments)
    fails = {j.test_query.query for j in failing_judgments(sc)}
    problems: list[str] = []
    for n, it in enumerate(items, 1):
        qs = it.get("queries") or []
        if not qs:
            problems.append(f"roadmap item {n}: has no tested searches")
        bad = [q for q in qs if q not in fails]
        if bad:
            problems.append(f"roadmap item {n}: {bad[:3]} are not failing tested searches")
        if not (it.get("title") or "").strip():
            problems.append(f"roadmap item {n}: empty title")
        scope = _scope_for(qs, sc)
        text = f"{it.get('title', '')}. {it.get('description', '')}"
        problems += grounding_violations(text, scope, sc, site_context, f"roadmap item {n}")
    return problems


# Concrete intent terms that make a "ranking" title acceptable (not vague).
_INTENT_TERMS = (
    "intent", "boost", "price", "brand", "bestseller", "best seller", "sale",
    "product-type", "product type", "filter", "negative", "facet", "constraint",
    "synonym", "typo", "fuzzy", "exclu",
)


def _is_relevance_vague_title(title: str) -> bool:
    """True when a roadmap title leads with abstract 'relevance/ranking' framing."""
    t = title.lower()
    if "relevance" in t:
        return True
    if "ranking algorithm" in t or "sort order" in t or "re-rank" in t or "rerank" in t:
        return True
    return "ranking" in t and not any(term in t for term in _INTENT_TERMS)


def _with_feedback(user: str, problems: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in problems[:25])
    return (f"{user}\n\nYOUR PREVIOUS ANSWER WAS REJECTED for these reasons:\n{listed}\n"
            "Return a corrected answer that follows every rule.")


def _grounded_call(*, system: str, user: str, schema, convert, validate, phase: str,
                   max_tokens: int, client=None, soft_validate=None):
    """structured_call → convert → validate; on violations regenerate once, then raise.

    ``soft_validate`` problems (style rules) trigger the retry but never raise.
    """
    problems: list[str] = []
    for attempt in range(2):
        prompt = user if attempt == 0 else _with_feedback(user, problems)
        out = structured_call(model=_MODEL, system=system, user=prompt, schema=schema,
                              max_tokens=max_tokens, phase=phase, temperature=0.3, client=client)
        content, problems = convert(out)
        if not problems:
            problems = validate(content)
        soft = soft_validate(content) if (soft_validate and not problems) else []
        if not problems and not soft:
            return content
        if not problems and attempt == 1:
            logger.warning("%s: style rule still broken after retry: %s", phase, soft)
            return content
        problems = problems or soft
        logger.warning("%s attempt %d rejected: %s", phase, attempt + 1, problems[:5])
    raise GroundingError(f"{phase}: narrative failed grounding twice: {problems[:10]}")


def generate_deep_dives(site_context: SiteContext, judgments: list[QueryJudgment], client=None) -> list[dict]:
    """Per-capability deep dives (stored format), grounded. [] when nothing failed."""
    sc = scored(judgments)
    fails = failing_judgments(sc)
    if not fails:
        return []
    groups = _capability_groups(fails, sc)

    def convert(out: DeepDivesOut):
        problems, sections, seen = [], [], set()
        for s in out.sections:
            if not 0 <= s.capability_id < len(groups) or s.capability_id in seen:
                problems.append(f"unknown or repeated capability_id {s.capability_id}")
                continue
            seen.add(s.capability_id)
            cap, ids = groups[s.capability_id]
            examples = []
            for e in s.examples[:5]:
                if e.query_id not in ids:
                    problems.append(f"query_id {e.query_id} does not belong to capability {s.capability_id}")
                    continue
                examples.append({"query": fails[e.query_id].test_query.query, "narrative": e.narrative.strip()})
            sections.append({"capability": cap, "capability_name": CAPABILITY_NAMES.get(cap, cap),
                             "intro": s.intro.strip(), "examples": examples})
        missing = [CAPABILITY_NAMES.get(groups[i][0]) for i in range(len(groups)) if i not in seen]
        if missing:
            problems.append(f"no section for capabilities: {missing}")
        return sections, problems

    sections = _grounded_call(
        system=_DEEP_DIVE_SYSTEM, user=_deep_dive_user(site_context, fails, sc), schema=DeepDivesOut,
        convert=convert, validate=lambda c: deep_dive_violations(c, sc, site_context),
        phase="report_deep_dives", max_tokens=8000, client=client,
    )
    order = {cap: i for i, (cap, _) in enumerate(groups)}
    sections.sort(key=lambda s: order.get(s["capability"], 99))
    return sections


def generate_roadmap(site_context: SiteContext, judgments: list[QueryJudgment], client=None) -> list[dict]:
    """Prioritised roadmap (stored format), grounded. [] when nothing failed."""
    sc = scored(judgments)
    fails = failing_judgments(sc)
    if not fails:
        return []

    def convert(out: RoadmapOut):
        problems, items = [], []
        if not out.items:
            problems.append("roadmap has no items")
        for n, it in enumerate(out.items[:8], 1):
            ids = [i for i in dict.fromkeys(it.query_ids) if 0 <= i < len(fails)]
            if len(ids) != len(set(it.query_ids)):
                problems.append(f"item {n}: query_ids out of range {it.query_ids}")
            items.append({
                "title": " ".join(it.title.split()).rstrip("."),
                "description": " ".join(it.description.split()),
                "impact": it.impact.value, "effort": it.effort.value, "owner": it.owner.value,
                "queries": [fails[i].test_query.query for i in ids],
            })
        return items, problems

    def soft(items):
        return ([f"item 1 title is abstract ranking/relevance framing: {items[0]['title']!r} — name "
                 "concrete intent signals"] if items and _is_relevance_vague_title(items[0]["title"]) else [])

    return _grounded_call(
        system=_ROADMAP_SYSTEM, user=_roadmap_user(site_context, fails, sc), schema=RoadmapOut,
        convert=convert, validate=lambda c: roadmap_violations(c, sc, site_context),
        soft_validate=soft, phase="report_roadmap", max_tokens=3000, client=client,
    )


# ── Language-mention cap (deterministic backstop to prompt rule 5) ──────────

_PROTECTED_SPAN = re.compile(r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|`[^`\n]*`')


def _limit_language_mentions(text: str, language: str, already_kept: int, cap: int = 1) -> tuple[str, int]:
    """Drop adjectival mentions of the site's own language beyond ``cap`` ("German synonym
    mapping" -> "synonym mapping"). Never edits inside quotes or backticks (queries/titles stay
    verbatim), never touches noun uses ("in German"), and re-capitalises only a sentence it
    edited. Returns (text, running mention count)."""
    if not language or not text:
        return text, already_kept
    word_re = re.compile(rf"\b{re.escape(language)}\b(\s+(?=[^\W\d_]))?", re.I)
    count = already_kept
    out: list[str] = []
    pos = 0

    def process(segment: str) -> None:
        nonlocal count
        p = 0
        for m in word_re.finditer(segment):
            count += 1
            out.append(segment[p:m.start()])
            p = m.end()
            if count <= cap or m.group(1) is None:
                out.append(m.group(0))
                continue
            before = "".join(out).rstrip(" *")
            at_start = not before or before.endswith((".", "!", "?", ":", "\n"))
            rest = segment[p:]
            if at_start and rest[:1].islower():
                out.append(rest[:1].upper())
                p += 1
        out.append(segment[p:])

    for m in _PROTECTED_SPAN.finditer(text):
        process(text[pos:m.start()])
        out.append(m.group(0))
        pos = m.end()
    process(text[pos:])
    return "".join(out), count


def _apply_language_cap(site_context: SiteContext, deep_dives: list[dict], roadmap: list[dict]) -> None:
    language = getattr(site_context, "primary_language", None)
    if not language or language.lower() == "english":
        return
    kept = 0
    for s in deep_dives:
        s["intro"], kept = _limit_language_mentions(s["intro"], language, kept)
        for e in s["examples"]:
            e["narrative"], kept = _limit_language_mentions(e["narrative"], language, kept)
    for it in roadmap:
        it["title"], kept = _limit_language_mentions(it["title"], language, kept)
        it["description"], kept = _limit_language_mentions(it["description"], language, kept)


# ── Markdown rendering of the narratives ────────────────────────────────


def render_deep_dives_markdown(sections: list[dict], judgments: list[QueryJudgment]) -> str:
    if not sections:
        return "## Detailed Analysis\n\nEvery scored search passed — no failing capability to analyse."
    by_q = {j.test_query.query: j for j in scored(judgments)}
    out: list[str] = []
    for s in sections:
        out.append(f"## {s['capability_name']}\n")
        out.append(f"{s['intro']}\n")
        for e in s["examples"]:
            j = by_q.get(e["query"])
            if j is None:
                continue
            meta = f"{CATEGORY_DISPLAY.get(category(j), category(j))} · {SEVERITY_SHORT.get(sev(j), sev(j))}"
            out.append(f"### \"{e['query']}\"\n")
            out.append(f"*{meta}{' · No results returned' if not j.results else ''}*\n")
            out.append(f"{e['narrative']}\n")
            shown = by_original(j)[:5]
            if shown:
                out.append("**Customer saw:**")
                out.extend(f"{r.original_rank}. {r.title}{_price(r)}" for r in shown)
                out.append("")
                better = better_matches(j)
                if better:
                    out.append("**Should have seen:**")
                    out.extend(f"- {r.title}{_price(r)} (shown at #{r.original_rank})" for r in better)
                    out.append("")
    return "\n".join(out).strip()


def _roadmap_reach(item: dict, judgments: list[QueryJudgment]) -> tuple[int, int]:
    scope = _scope_for(item.get("queries") or [], scored(judgments))
    return len(scope), sum(1 for j in scope if sev(j) == Severity.CRITICAL.value)


def roadmap_reach_text(item: dict, judgments: list[QueryJudgment]) -> str:
    n, k = _roadmap_reach(item, judgments)
    word = "search" if n == 1 else "searches"
    return f"Fixes {n} tested {word}" + (f" ({k} critical)" if k else "")


def render_roadmap_markdown(items: list[dict], judgments: list[QueryJudgment]) -> str:
    if not items:
        return "Every scored search passed — no fixes needed."
    lines = []
    for n, it in enumerate(items, 1):
        owner = _OWNER_LABELS.get(it.get("owner"), "")
        lines.append(f"{n}. **{it['title']}**")
        lines.append(f"   {it['description']}")
        lines.append(f"   Impact: {it['impact']} | Effort: {it['effort']}" + (f" | Owner: {owner}" if owner else ""))
        lines.append(f"   {roadmap_reach_text(it, judgments)}: " +
                     ", ".join(f"\"{q}\"" for q in it.get("queries", [])[:5]))
        lines.append("")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# PART 3 — Deterministic stats + framing sections
# ---------------------------------------------------------------------------


def build_summary_statistics_markdown(stats: dict, judgments: list[QueryJudgment]) -> str:
    """Severity distribution, failure modes and key metrics (scored searches only)."""
    f = formatted_stats(stats)
    total = stats["total_queries"]
    lines = [
        "## Test Results Summary\n",
        f"We scored **{total} test searches** across multiple search capability categories."
        + (f" {stats['excluded_count']} more are listed under “Not scored”." if stats["excluded_count"] else "")
        + " Here is the breakdown.\n",
        "### Severity Distribution\n",
        "| Severity | Searches |",
        "|----------|---------|",
    ]
    for sev_value, label in [(Severity.CRITICAL.value, "Critical"), (Severity.MODERATE.value, "Moderate"),
                             (Severity.MINOR.value, "Minor"), (Severity.PASS.value, "Pass")]:
        lines.append(f"| {_SEVERITY_EMOJI.get(sev_value, '')} {label} | {stats[f'{label.lower()}_count']} |")

    if stats["failure_mode_counts"]:
        lines += ["", "### Failure Mode Breakdown\n", "| Failure Mode | Searches |", "|-------------|---------|"]
        lines += [f"| {md_cell(fm['label'])} | {fm['count']} |" for fm in stats["failure_mode_counts"]]

    lines += ["", "### Key Metrics\n"]
    if total:
        lines.append(f"- **{ZERO_RESULT_LABEL}:** {f['pct_zero_result']} of searches ({f['zero_of_total']})¹")
        lines.append(f"- **{FOUND_BUT_WRONG_LABEL}:** {f['pct_found_but_wrong']} of searches "
                     f"({f['found_wrong_of_total']}) — products came back, but ordered poorly, ignoring a "
                     "stated limit, or matching only part of the query")
    lines.append(f"- **Average best result position (searches that returned products):** {f['avg_best_position']}")
    lines.append(f"- **Best match outside the top 3 (searches that returned products):** {f['pct_top3_irrelevant']}")
    lines.append(f"- **Irrelevant #1 result (searches that returned products):** {f['pct_top1_irrelevant']}")
    lines += ["", f"¹ {ZERO_RESULT_FOOTNOTE}"]
    return "\n".join(lines)


def build_root_causes_markdown(judgments: list[QueryJudgment]) -> str:
    rows = root_causes(judgments)
    if not rows:
        return ""
    lines = [
        "## Root Causes\n",
        "Many failures share one mechanism. Fix the mechanism once and every search below it improves.\n",
        "| Cause | Searches | Critical | Examples |",
        "|-------|----------|----------|----------|",
    ]
    for r in rows:
        ex = ", ".join(f"`{md_cell(q)}`" for q in r["queries"][:3])
        lines.append(f"| {md_cell(r['mechanism'])} | {r['count']} | {r['critical']} | {ex} |")
    return "\n".join(lines)


def build_full_query_appendix_markdown(judgments: list[QueryJudgment], search_url_template: str = "") -> str:
    """Every SCORED search, worst first, with a reproduction link when the template allows."""
    sc = scored(judgments)
    lines = [
        "## Appendix: Complete Test Results\n",
        f"All {len(sc)} scored searches in this audit.\n",
        "| # | Search | Category | Severity | Best Position | Failure Mode |",
        "|---|-------|----------|----------|--------------|-------------|",
    ]
    for idx, j in enumerate(sorted(sc, key=lambda j: (-SEVERITY_RANK.get(sev(j), 0), -j.displacement)), 1):
        q = md_cell(j.test_query.query)
        url = search_url(search_url_template, j.test_query.query)
        query_cell = f"[{q.replace('[', '(').replace(']', ')')}]({url})" if url else q
        if is_pass(j):
            failure, best_pos = "—", "#1"
        else:
            failure = FAILURE_MODE_DISPLAY.get(mode(j), mode(j))
            best_pos = f"#{j.displacement + 1}" if j.results else "—"
        lines.append(
            f"| {idx} | {query_cell} | {md_cell(CATEGORY_DISPLAY.get(category(j), category(j)))} | "
            f"{_SEVERITY_EMOJI.get(sev(j), '')} {SEVERITY_SHORT.get(sev(j), sev(j))} | {best_pos} | {md_cell(failure)} |"
        )
    return "\n".join(lines)


def build_not_scored_markdown(judgments: list[QueryJudgment]) -> str:
    ex = excluded(judgments)
    if not ex:
        return ""
    lines = [
        "## Not Scored\n",
        "These searches were tested but left out of every figure in this report.\n",
        "| Search | Why it isn't scored |",
        "|--------|---------------------|",
    ]
    for j in ex:
        reason = EXCLUDED_REASON_TEXT.get(j.excluded_reason, "Left out of scoring.")
        lines.append(f"| {md_cell(j.test_query.query)} | {md_cell(reason)} |")
    return "\n".join(lines)


def build_executive_summary(site_context: SiteContext, capability_scores, stats: dict) -> str:
    """Deterministic executive summary (no LLM). Every claim comes from ``stats``."""
    f = formatted_stats(stats)
    site_name = site_context.site_name or site_context.url
    n_caps = len(capability_rows(_as_judgments(capability_scores)))
    n = stats["total_queries"]

    summary = (
        "## Executive Summary\n\n"
        f"This audit tested {site_name}'s site search across {n_caps} core capabilities using {n} "
        "realistic customer searches. **The results are grouped by where improvements are likely to "
        "help customer journeys most.**\n\n"
        f"In **{f['pct_no_relevant_first']} of tested searches**, the shopper was not shown a relevant "
        "result first — either nothing usable at all or an off-topic top result."
    )
    if stats["zero_result_count"]:
        causes = stats["zero_result_causes"]
        cause_txt = ""
        if causes:
            parts = [f"{c} ({k})" for c, k in causes]
            joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " or " + parts[-1]
            cause_txt = f", most often because {joined}"
        summary += (f" **{f['zero_of_total']} searches returned nothing usable**{cause_txt}.")
    if stats["with_results_count"]:
        summary += (
            "\n\nAmong the searches that did return products, the best match sat at "
            f"**position {f['avg_best_position']}** on average — {position_context(stats['avg_best_position'])}"
            f" — and in **{f['pct_top3_irrelevant']}** of them the best match wasn't in the top 3."
        )
    if stats["worst_example"]:
        ex = stats["worst_example"]
        summary += f"\n\nThe most telling example: {ex[:1].lower() + ex[1:] if ex.startswith('A ') else ex}"
    summary += f"\n\n_{SAMPLE_NOTE}_"
    return summary


def build_methodology(total_queries: int, num_capabilities: int, num_categories: int) -> str:
    """Methodology — describes the pipeline without naming tools or internal scores."""
    return (
        "## Methodology: How We Tested\n\n"
        f"{total_queries} scored test searches were generated across {num_categories} query categories, "
        f"grouped into {num_capabilities} core capabilities.\n\n"
        "**1. Site Discovery**\n"
        "Analysis of your site's navigation categories, brands and featured products, to understand "
        "what your search should be able to find.\n\n"
        "**2. Test Design**\n"
        "Site-type-aware selection from a library of test categories, chosen for how your customers shop.\n\n"
        "**3. Query Generation**\n"
        "Realistic customer searches grounded in the actual products, brands and categories on your site — "
        "not generic templates. Where a search has a plain underlying term (the correct spelling behind a "
        "typo, the product type behind a long phrase), that term is searched too, as a control.\n\n"
        "**4. Result Collection**\n"
        "Each search run live on the site (desktop), collecting the top results exactly as a shopper sees them.\n\n"
        "**5. Result Rating**\n"
        "Every returned product rated for how well it matches what the shopper asked for.\n\n"
        "**6. Failure Analysis**\n"
        "Each search classified by failure mode (no results, category not understood, constraint ignored, "
        "typo not handled, relevant results buried) and given a severity based on shopper impact. Searches "
        "whose control also found nothing (the store doesn't stock it) or whose page couldn't be loaded "
        "reliably are listed as not scored and left out of every figure.\n\n"
        "**7. Report Assembly**\n"
        "Findings written up with prioritised fixes, ordered by impact. Every quoted search, product and "
        "position is checked against the collected results."
    )


def build_industry_benchmarks_markdown(stats: dict, peer_benchmark: dict | None = None) -> str:
    rows = benchmark_rows(stats, peer_benchmark)
    peer = peer_label(peer_benchmark)
    head = "| Metric | Your Result | Target |" + (f" {md_cell(peer)} |" if peer else "")
    sep = "|--------|-------------|--------|" + ("--------|" if peer else "")
    lines = ["## How to Read These Numbers\n", BENCHMARK_NOTE + "\n", head, sep]
    for r in rows:
        line = f"| {md_cell(r['metric'])} | {r['your_score']} | {r['target']} |"
        if peer:
            line += f" {r['peer'] or '—'} |"
        lines.append(line)
    lines += ["", f"_{SAMPLE_NOTE}_"]
    return "\n".join(lines)


def build_call_to_action() -> str:
    return (
        "## Next Steps\n\n"
        "We'd welcome the opportunity to walk you through these findings in detail and discuss "
        "a remediation plan tailored to your team's priorities and timeline. The issues "
        "identified in this audit are fixable — most ecommerce search platforms support the "
        "capabilities tested here, and the roadmap above is ordered by impact to help you "
        "prioritize.\n\n"
        "**Contact us to schedule a 30-minute walkthrough of this report.**"
    )


def audit_date_text(run_metadata: dict | None) -> str:
    """Human date of the audit run (falls back to today for legacy reports)."""
    md = run_metadata or {}
    for key in ("audit_date", "run_date", "started_at", "run_started_at", "generated_at"):
        raw = md.get(key)
        if raw:
            try:
                return date.fromisoformat(str(raw)[:10]).strftime("%B %d, %Y")
            except ValueError:
                continue
    return date.today().strftime("%B %d, %Y")


# ---------------------------------------------------------------------------
# Main report assembly
# ---------------------------------------------------------------------------


def report_content(report: AuditReport) -> dict:
    """The accepted narratives stored on a report: {"deep_dives": [...], "roadmap": [...]}."""
    return (report.run_metadata or {}).get("report_content") or {}


def generate_report(
    site_context: SiteContext,
    judgments: list[QueryJudgment],
    deep_dives: list[dict] | None = None,
    roadmap: list[dict] | None = None,
    client=None,
    peer_benchmark: dict | None = None,
) -> AuditReport:
    """Assemble the full audit report: deterministic scoring + grounded narratives.

    ``deep_dives`` / ``roadmap`` accept already-reviewed narratives in stored format (as found in
    ``report_content(report)`` of an earlier run); they are validated, never regenerated. When
    omitted, they are generated. A narrative that fails grounding raises :class:`GroundingError`.
    """
    sc = scored(judgments)
    capability_scores = build_capability_scores(judgments)  # persisted: all judgments, scored severities

    if deep_dives is None:
        deep_dives = generate_deep_dives(site_context, sc, client=client)
    else:
        problems = deep_dive_violations(deep_dives, sc, site_context)
        if problems:
            raise GroundingError(f"supplied deep dives fail grounding: {problems[:10]}")
    if roadmap is None:
        roadmap = generate_roadmap(site_context, sc, client=client)
    else:
        problems = roadmap_violations(roadmap, sc, site_context)
        if problems:
            raise GroundingError(f"supplied roadmap fails grounding: {problems[:10]}")
    _apply_language_cap(site_context, deep_dives, roadmap)

    stats = compute_stats(judgments, site_context.nav_categories)
    run_metadata = {"report_content": {"deep_dives": deep_dives, "roadmap": roadmap}}
    if peer_benchmark:
        run_metadata["peer_benchmark"] = peer_benchmark
    site_name = site_context.site_name or site_context.url
    today = audit_date_text(None)
    scope = scope_line(stats, today, getattr(site_context, "locale", "") or site_context.primary_language)
    roadmap_md = render_roadmap_markdown(roadmap, sc)

    sections = [
        f"# Search Audit Report: {site_name}\n\n*{scope}*",
        build_executive_summary(site_context, sc, stats),
        build_scorecard_markdown(sc),
        build_summary_statistics_markdown(stats, sc),
        build_root_causes_markdown(sc),
        build_advanced_diagnostics_markdown(site_context, sc),
        render_deep_dives_markdown(deep_dives, sc),
        build_whats_working_markdown(sc),
        f"## Prioritized Roadmap\n\n{roadmap_md}",
        build_industry_benchmarks_markdown(stats, peer_benchmark),
        build_methodology(stats["total_queries"], len(capability_rows(sc)), stats["num_categories"]),
        build_full_query_appendix_markdown(sc, site_context.search_url_template),
        build_not_scored_markdown(judgments),
        build_call_to_action(),
    ]
    full_narrative = "\n\n".join(s for s in sections if s)

    return AuditReport(
        site_context=site_context,
        selected_categories=list({QueryCategory(category(j)) for j in judgments}),
        queries=[j.test_query for j in judgments],
        capability_scores=capability_scores,
        deep_dive_narrative=full_narrative,
        roadmap_narrative=roadmap_md,
        run_metadata=run_metadata,
    )


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.models import FailureMode, ScoredResult, SiteType, TestQuery

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Fake site context
    site_ctx = SiteContext(
        url="https://www.kicksworld.com",
        site_name="KicksWorld",
        site_type=SiteType.PHYSICAL_GOODS,
        nav_categories=["Men's Shoes", "Women's Shoes", "Running", "Casual", "Sale"],
        brands=["Nike", "Adidas", "New Balance", "Puma"],
        featured_items=["Nike Air Max 90", "Adidas Ultraboost 22", "New Balance 574"],
        search_url_template="https://www.kicksworld.com/search?q={}",
        raw_meta_description="KicksWorld — sneakers, running shoes, and casual footwear.",
    )

    # --- PASS judgments (Product Discovery: DIRECT_MATCH) ---
    j_direct = QueryJudgment(
        test_query=TestQuery(
            category="DIRECT_MATCH", query="Nike Air Max 90",
            rationale="Exact product name lookup",
        ),
        results=[
            ScoredResult(rank=1, title="Nike Air Max 90 - White/Black", price="$130",
                         relevance_score=0.95, original_rank=1),
            ScoredResult(rank=2, title="Nike Air Max 90 Premium", price="$150",
                         relevance_score=0.90, original_rank=2),
        ],
        failure_mode=FailureMode.OTHER,
        failure_mode_explanation="No failure — query passed",
        severity=Severity.PASS,
        evidence="Top results are all Air Max 90 variants. Relevance scores above 0.90.",
        recommended_fix="No fix needed.",
        displacement=0, max_relevance_score=0.95, top3_original_average=0.925,
    )

    # --- PASS judgment (Brand & Model Search: BRAND_SEARCH) ---
    j_brand = QueryJudgment(
        test_query=TestQuery(
            category="BRAND_SEARCH", query="Adidas",
            rationale="Brand-only search should return Adidas products",
        ),
        results=[
            ScoredResult(rank=1, title="Adidas Ultraboost 22", price="$190",
                         relevance_score=0.88, original_rank=1),
            ScoredResult(rank=2, title="Adidas Stan Smith", price="$100",
                         relevance_score=0.85, original_rank=2),
        ],
        failure_mode=FailureMode.OTHER,
        failure_mode_explanation="No failure — query passed",
        severity=Severity.PASS,
        evidence="All results are Adidas products. Well ordered.",
        recommended_fix="No fix needed.",
        displacement=0, max_relevance_score=0.88, top3_original_average=0.865,
    )

    # --- CRITICAL judgments (Typo Tolerance: TYPO, MERGED_WORDS) ---
    j_typo = QueryJudgment(
        test_query=TestQuery(
            category="TYPO", query="nkie air max",
            rationale="Misspelling of Nike — tests fuzzy matching",
        ),
        results=[
            ScoredResult(rank=1, title="Air Freshener 3-Pack", price="$8.99",
                         relevance_score=0.05, original_rank=1),
            ScoredResult(rank=2, title="Max Hair Gel 16oz", price="$12.50",
                         relevance_score=0.03, original_rank=2),
            ScoredResult(rank=3, title="Air Pump for Bikes", price="$24.99",
                         relevance_score=0.04, original_rank=3),
        ],
        failure_mode=FailureMode.NO_FUZZY_MATCHING,
        severity=Severity.CRITICAL,
        evidence="All 3 results are completely unrelated. The engine matched 'air' and 'max' as separate keywords and ignored the misspelled brand.",
        recommended_fix="Enable fuzzy matching / Levenshtein distance matching. 'nkie' is 1 transposition from 'Nike' — this should be caught by any basic typo tolerance.",
        displacement=15, max_relevance_score=0.05, top3_original_average=0.04,
    )

    j_merged = QueryJudgment(
        test_query=TestQuery(
            category="MERGED_WORDS", query="runningshoes",
            rationale="Merged compound word — tests token splitting",
        ),
        results=[
            ScoredResult(rank=1, title="Shoe Cleaning Kit", price="$15.99",
                         relevance_score=0.10, original_rank=1),
            ScoredResult(rank=2, title="Nike Pegasus 40", price="$130",
                         relevance_score=0.65, original_rank=4),
            ScoredResult(rank=3, title="Running Socks 6-Pack", price="$18.00",
                         relevance_score=0.20, original_rank=2),
        ],
        failure_mode=FailureMode.PARTIAL_KEYWORD_MATCH,
        severity=Severity.CRITICAL,
        evidence="Engine matched 'shoes' as a keyword but didn't split 'runningshoes' into 'running shoes'. Best result (Nike Pegasus) buried at position 4.",
        recommended_fix="Implement compound word splitting so 'runningshoes' is tokenized as 'running shoes' before matching.",
        displacement=3, max_relevance_score=0.65, top3_original_average=0.317,
    )

    # --- MODERATE judgments (Language Understanding: SYNONYM, NATURAL_LANGUAGE) ---
    j_synonym = QueryJudgment(
        test_query=TestQuery(
            category="SYNONYM", query="sneakers",
            rationale="Synonym for shoes — should return same results as 'shoes'",
        ),
        results=[
            ScoredResult(rank=1, title="Snack Bar Variety Pack", price="$22.99",
                         relevance_score=0.02, original_rank=1),
            ScoredResult(rank=2, title="Nike Dunk Low", price="$110",
                         relevance_score=0.72, original_rank=3),
            ScoredResult(rank=3, title="Vans Old Skool", price="$70",
                         relevance_score=0.68, original_rank=5),
        ],
        failure_mode=FailureMode.NO_SEMANTIC_UNDERSTANDING,
        severity=Severity.MODERATE,
        evidence="The term 'sneakers' is not in the product catalog vocabulary. Best matches exist but are buried. Position 1 is a snack bar — completely irrelevant.",
        recommended_fix="Add 'sneakers' as a synonym for the shoes category. Map it to the same results as 'shoes' or 'casual shoes'.",
        displacement=2, max_relevance_score=0.72, top3_original_average=0.473,
    )

    j_natural = QueryJudgment(
        test_query=TestQuery(
            category="NATURAL_LANGUAGE", query="comfortable shoes for standing all day",
            rationale="Natural language use-case query",
        ),
        results=[
            ScoredResult(rank=1, title="Standing Desk Converter", price="$249",
                         relevance_score=0.05, original_rank=1),
            ScoredResult(rank=2, title="New Balance 574", price="$85",
                         relevance_score=0.60, original_rank=4),
            ScoredResult(rank=3, title="Day Planner Journal", price="$15",
                         relevance_score=0.01, original_rank=2),
        ],
        failure_mode=FailureMode.PARTIAL_KEYWORD_MATCH,
        severity=Severity.MODERATE,
        evidence="Engine matched 'standing' to standing desks and 'day' to planners. Ignored the actual intent: comfortable footwear. Best shoe result at position 4.",
        recommended_fix="Implement intent-based search that understands 'shoes for standing' is a footwear query, not a furniture query.",
        displacement=3, max_relevance_score=0.60, top3_original_average=0.22,
    )

    all_judgments = [j_direct, j_brand, j_typo, j_merged, j_synonym, j_natural]

    print("Generating report...\n")
    report = generate_report(site_ctx, all_judgments)

    print(report.deep_dive_narrative)
    print("\n\n--- Full roadmap narrative ---\n")
    print(report.roadmap_narrative)
    print(f"\nCapability scores: {len(report.capability_scores)}")
    for cs in report.capability_scores:
        sev_short = _SEVERITY_SHORT.get(cs.severity, cs.severity)
        cap_name = _CAPABILITY_NAMES.get(cs.capability, cs.capability)
        print(f"  {sev_short:>8} | {cap_name}: {cs.summary}")
