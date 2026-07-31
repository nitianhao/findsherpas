"""Calibration knowledge base for the LLM judge.

A per-language store of past judgements that the judge consults at runtime to grade
consistently and reuse strong fix/evidence phrasing. This is *advisory anchoring*, not a
cache — the judge still judges every query fresh against that query's own results; KB
examples only calibrate severity/labeling and supply reference phrasing.

Two entry points are used by ``judge.py``:

* ``load_calibration_examples(language, category, query)`` — Step A, before each LLM call.
* ``harvest(judgments, language, provenance)`` — Step B, after a whole audit.

Every public function is defensive: any failure (missing file, bad JSON, Voyage error) is
logged and degrades to "no examples" / "nothing harvested" so an audit can never break
because of the KB.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import voyageai

from src.models import QueryJudgment, Severity

logger = logging.getLogger(__name__)

# Number of calibration examples injected per query.
_TOP_K = 3
# Below this many same-category matches, widen retrieval to same-language/any-category.
_MIN_CATEGORY_MATCHES = 2
# Voyage embedding model. Overridable so a model rename never hard-breaks harvesting.
_EMBED_MODEL = os.environ.get("VOYAGE_EMBED_MODEL", "voyage-3.5")

# KB lives at src/audit/kb/ — one .jsonl file per language.
_KB_DIR = Path(__file__).resolve().parent.parent / "kb"

# Map a Severity enum's (long) value back to its short name, e.g. "CRITICAL".
_SEVERITY_SHORT: dict[str, str] = {s.value: s.name for s in Severity}


# ---------------------------------------------------------------------------
# Paths & file IO
# ---------------------------------------------------------------------------


def _lang_slug(language: str) -> str:
    """Filesystem-safe lowercase slug for a language name, e.g. 'German' -> 'german'."""
    slug = re.sub(r"[^a-z0-9]+", "_", (language or "").strip().lower()).strip("_")
    return slug or "unknown"


def kb_path(language: str) -> Path:
    """Return the KB file path for a language (not guaranteed to exist)."""
    return _KB_DIR / f"{_lang_slug(language)}.jsonl"


def _read_records(path: Path) -> list[dict]:
    """Read a JSONL KB file into a list of dicts. Bad lines are skipped."""
    records: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed KB line in %s", path.name)
    except OSError as e:
        logger.warning("Could not read KB file %s: %s", path, e)
    return records


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


def _embed(texts: list[str], input_type: str) -> list[list[float]] | None:
    """Voyage-embed a batch of texts. Returns None on any failure."""
    if not texts:
        return []
    try:
        client = voyageai.Client()
        resp = client.embed(texts, model=_EMBED_MODEL, input_type=input_type)
        return resp.embeddings
    except Exception as e:  # noqa: BLE001 — KB must never break the audit
        logger.warning("Voyage embedding failed (model=%s): %s", _EMBED_MODEL, e)
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Step A — retrieval
# ---------------------------------------------------------------------------


def _rank_candidates(query: str, pool: list[dict]) -> list[dict]:
    """Rank candidate records by semantic similarity to ``query``.

    Falls back to recency order (newest first) when embeddings are unavailable.
    """
    query_emb = _embed([query], input_type="query")
    if query_emb:
        qv = query_emb[0]
        scored = []
        for rec in pool:
            emb = rec.get("embedding")
            sim = _cosine(qv, emb) if emb else -1.0
            scored.append((sim, rec))
        if any(sim >= 0 for sim, _ in scored):
            scored.sort(key=lambda t: t[0], reverse=True)
            return [rec for _, rec in scored]

    # No usable embeddings — most recent judgements are the best anchors we have.
    return sorted(
        pool,
        key=lambda r: r.get("provenance", {}).get("judged_at", ""),
        reverse=True,
    )


def load_calibration_examples(
    language: str, category: str, query: str, top_k: int = _TOP_K
) -> list[dict]:
    """Return up to ``top_k`` past judgement records to anchor this query's verdict.

    Filters to active, same-language entries; prefers the same category, widening to
    any-category when too few same-category matches exist. Returns ``[]`` (no-op) when
    the KB is missing/empty or on any error — so judging behaves exactly as before.
    """
    try:
        path = kb_path(language)
        if not path.exists():
            return []

        active = [r for r in _read_records(path) if r.get("status") == "active"]
        if not active:
            return []

        same_category = [r for r in active if r.get("category") == category]
        pool = same_category if len(same_category) >= _MIN_CATEGORY_MATCHES else active
        if not pool:
            return []

        return _rank_candidates(query, pool)[:top_k]
    except Exception as e:  # noqa: BLE001
        logger.warning("KB retrieval failed for '%s': %s", query, e)
        return []


def format_calibration_section(records: list[dict]) -> str:
    """Render retrieved records into a prompt section, or '' when there are none."""
    if not records:
        return ""

    lines = []
    for r in records:
        sev = r.get("severity", "?")
        fm = r.get("failure_mode", "?")
        evidence = (r.get("evidence") or "").strip().replace("\n", " ")
        if len(evidence) > 240:
            evidence = evidence[:237] + "..."
        fix = (r.get("recommended_fix") or "").strip().replace("\n", " ")
        if len(fix) > 240:
            fix = fix[:237] + "..."
        lines.append(
            f'  - "{r.get("query", "")}" -> {sev} / {fm}\n'
            f"      evidence: {evidence}\n"
            f"      fix: {fix}"
        )

    return (
        "\n## Calibration Examples (how similar queries were graded in past audits)\n"
        "Use these to calibrate severity and failure-mode labeling for consistency, and "
        "to model the style of strong evidence/fix writing. Do NOT copy them — the "
        "products and results differ; judge THIS query on its own results above.\n"
        + "\n".join(lines)
        + "\n"
    )


# ---------------------------------------------------------------------------
# Step B — harvest
# ---------------------------------------------------------------------------


def _is_anchor_worthy(judgment: QueryJudgment) -> bool:
    """True when a judgement is a clean enough signal to become a calibration anchor.

    Excludes LLM-fallback verdicts (stats-only) and unclassified non-pass verdicts.
    PASS verdicts are kept even though their failure_mode is OTHER — "what good looks
    like" is valuable calibration.
    """
    evidence = (judgment.evidence or "").strip()
    if not evidence or "LLM analysis failed" in evidence:
        return False

    fm = _enum_value(judgment.failure_mode)
    sev_short = _SEVERITY_SHORT.get(_enum_value(judgment.severity), "")
    if fm == "OTHER" and sev_short != "PASS":
        return False
    return True


def _enum_value(v) -> str:
    """Return the string value whether ``v`` is an Enum or already a string."""
    return v.value if hasattr(v, "value") else str(v)


def _record_from_judgment(
    judgment: QueryJudgment,
    language: str,
    provenance: dict,
    embedding: list[float] | None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "query": judgment.test_query.query,
        "category": _enum_value(judgment.test_query.category),
        "language": language,
        "severity": _SEVERITY_SHORT.get(_enum_value(judgment.severity), "MODERATE"),
        "failure_mode": _enum_value(judgment.failure_mode),
        "evidence": judgment.evidence,
        "recommended_fix": judgment.recommended_fix,
        "embedding": embedding,
        "provenance": provenance,
        "status": "active",
        "source": "harvested",
    }


def harvest(
    judgments: list[QueryJudgment],
    language: str,
    provenance: dict | None = None,
) -> int:
    """Append anchor-worthy judgements to the language KB. Returns count appended.

    Never raises — logs and returns 0 on failure.
    """
    try:
        worthy = [j for j in judgments if _is_anchor_worthy(j)]
        if not worthy:
            return 0

        prov = dict(provenance or {})
        prov.setdefault("judged_at", datetime.now().isoformat())

        # Embed all queries in one batch; on failure, store records without embeddings
        # (retrieval will fall back to recency ranking for them).
        embeddings = _embed([j.test_query.query for j in worthy], input_type="document")
        if embeddings is None:
            embeddings = [None] * len(worthy)

        records = [
            _record_from_judgment(j, language, prov, emb)
            for j, emb in zip(worthy, embeddings)
        ]

        path = kb_path(language)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        logger.info("Harvested %d judgements into %s", len(records), path.name)
        return len(records)
    except Exception as e:  # noqa: BLE001
        logger.warning("KB harvest failed: %s", e)
        return 0
