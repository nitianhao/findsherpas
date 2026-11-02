"""Calibration knowledge base for the LLM judge.

A per-language store of past judgements that the judge consults at runtime to grade
consistently and reuse strong fix/evidence phrasing. This is *advisory anchoring*, not a
cache — the judge still judges every query fresh against that query's own results; KB
examples only calibrate severity/labeling and supply reference phrasing.

Two entry points are used by ``judge.py``:

* ``load_calibration_examples(language, category, query, domain=…, rules_version=…)`` —
  before each LLM call.
* ``harvest(judgments, language, provenance, model=…, domain=…, rules_version=…)`` — after a
  whole audit.

Record lifecycle (``status``):

* ``pending``  — harvested from a run; NOT retrieved until an operator promotes it
  (``scripts/kb_prune.py promote``). Unreviewed verdicts never anchor future verdicts.
* ``active``   — retrievable, but only when its ``rules_version`` equals the current
  ``JUDGE_RULES_VERSION`` or ``human_reviewed`` is True.
* ``retired``  — graded under superseded rules (``retired_reason`` says why). Kept for audit.
* ``pruned``   — removed by an operator. Kept for audit.

Files are keyed by ISO-639-1 code (``de.jsonl``, ``sv.jsonl``); every language name or code
the pipeline passes ("German", "Svenska", "de-CH", "sv") normalises to the same file.

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

# KB lives at src/audit/kb/ — one .jsonl file per ISO-639-1 language code.
#
# Both dirs are env-overridable so a run judged by a different model can be kept out of
# the shared calibration store (see docs/CASE_STUDY_PLAYBOOK.md).
#   AUDIT_KB_DIR         — where calibration examples are READ from
#   AUDIT_KB_HARVEST_DIR — where this run's verdicts are WRITTEN (defaults to AUDIT_KB_DIR)
_AUDIT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_KB_DIR = _AUDIT_ROOT / "kb"


def _kb_dir_from_env(var: str, fallback: Path) -> Path:
    """Resolve a KB dir override. Relative values anchor to src/audit/, not the cwd."""
    raw = (os.environ.get(var) or "").strip()
    if not raw:
        return fallback
    path = Path(raw)
    return path if path.is_absolute() else _AUDIT_ROOT / path


_KB_DIR = _kb_dir_from_env("AUDIT_KB_DIR", _DEFAULT_KB_DIR)
_KB_HARVEST_DIR = _kb_dir_from_env("AUDIT_KB_HARVEST_DIR", _KB_DIR)

# Map a Severity enum's (long) value back to its short name, e.g. "CRITICAL".
_SEVERITY_SHORT: dict[str, str] = {s.value: s.name for s in Severity}

# Only verdicts the model produced (or an operator set) are worth anchoring on. Rule-made
# verdicts (zero results, gibberish) never reach the LLM, and fallbacks are stats guesses.
_HARVESTABLE_STATUSES = {"llm", "manual"}


# ---------------------------------------------------------------------------
# Language normalisation
# ---------------------------------------------------------------------------

_LANGUAGE_CODES: dict[str, str] = {
    "english": "en", "eng": "en", "englisch": "en",
    "german": "de", "deutsch": "de", "deu": "de", "ger": "de", "tysk": "de", "tyska": "de",
    "swedish": "sv", "svenska": "sv", "swe": "sv", "svensk": "sv",
    "danish": "da", "dansk": "da", "dan": "da",
    "norwegian": "no", "norsk": "no", "nor": "no", "bokmal": "no", "nynorsk": "no", "nb": "no", "nn": "no",
    "dutch": "nl", "nederlands": "nl", "nld": "nl", "dut": "nl", "flemish": "nl",
    "french": "fr", "francais": "fr", "fra": "fr", "fre": "fr",
    "spanish": "es", "espanol": "es", "spa": "es", "castellano": "es",
    "italian": "it", "italiano": "it", "ita": "it",
    "polish": "pl", "polski": "pl", "pol": "pl",
    "czech": "cs", "cestina": "cs", "ces": "cs", "cze": "cs",
    "slovak": "sk", "slovencina": "sk", "slk": "sk",
    "finnish": "fi", "suomi": "fi", "fin": "fi",
    "portuguese": "pt", "portugues": "pt", "por": "pt",
    "hungarian": "hu", "magyar": "hu",
    "lithuanian": "lt", "latvian": "lv", "estonian": "et", "romanian": "ro", "greek": "el",
}


def normalize_language(language: str | None) -> str:
    """Any language name or code -> ISO-639-1 ('German' -> 'de', 'sv-SE' -> 'sv', 'nb' -> 'no').

    Unknown names fall back to a filesystem-safe slug so nothing is ever silently merged.
    """
    raw = (language or "").strip()
    if not raw:
        return "unknown"
    import unicodedata

    folded = "".join(c for c in unicodedata.normalize("NFKD", raw.casefold()) if not unicodedata.combining(c))
    if folded in _LANGUAGE_CODES:
        return _LANGUAGE_CODES[folded]
    primary = re.split(r"[-_ ]", folded, maxsplit=1)[0]
    if primary in _LANGUAGE_CODES:
        return _LANGUAGE_CODES[primary]
    if re.fullmatch(r"[a-z]{2}", primary):
        return primary
    slug = re.sub(r"[^a-z0-9]+", "_", folded).strip("_")
    return slug or "unknown"


def _lang_slug(language: str) -> str:
    """Filename stem for a language: its ISO-639-1 code."""
    return normalize_language(language)


def kb_path(language: str) -> Path:
    """Return the READ KB file path for a language (not guaranteed to exist)."""
    return _KB_DIR / f"{_lang_slug(language)}.jsonl"


def kb_harvest_path(language: str) -> Path:
    """Return the WRITE KB file path (identical to kb_path unless AUDIT_KB_HARVEST_DIR splits them)."""
    return _KB_HARVEST_DIR / f"{_lang_slug(language)}.jsonl"


def normalize_domain(domain: str | None) -> str:
    """'https://www.Bergzeit.de/x' -> 'bergzeit.de'; slugs like 'bergzeit_de' -> 'bergzeit.de'."""
    d = (domain or "").strip().lower()
    d = re.sub(r"^[a-z]+://", "", d).split("/")[0]
    d = re.sub(r"^www\.", "", d)
    if "." not in d and "_" in d:
        d = d.replace("_", ".")
    return d


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


def write_records(path: Path, records: list[dict]) -> None:
    """Rewrite a KB file atomically (temp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _current_rules_version() -> str:
    from src.judge import JUDGE_RULES_VERSION  # lazy: judge imports this module

    return JUDGE_RULES_VERSION


def _default_judge_model() -> str:
    from src.judge import _DEFAULT_MODEL

    return _DEFAULT_MODEL


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
    """Rank candidates by semantic similarity to ``query``; recency order when embeddings fail."""
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
    return sorted(pool, key=lambda r: r.get("judged_at") or r.get("provenance", {}).get("judged_at", ""), reverse=True)


def is_retrievable(rec: dict, rules_version: str, domain: str | None = None) -> bool:
    """Active, judged under the current rules (or human-reviewed), and not from the audited domain."""
    if rec.get("status") != "active":
        return False
    if rec.get("rules_version") != rules_version and not rec.get("human_reviewed"):
        return False
    if domain:
        rd = normalize_domain(rec.get("domain") or (rec.get("provenance") or {}).get("domain"))
        if rd and rd == normalize_domain(domain):
            return False  # never calibrate a site against its own past verdicts
    return True


def load_calibration_examples(
    language: str,
    category: str,
    query: str,
    top_k: int = _TOP_K,
    domain: str | None = None,
    rules_version: str | None = None,
) -> list[dict]:
    """Return up to ``top_k`` past judgement records to anchor this query's verdict.

    Filters with :func:`is_retrievable`; prefers the same category, widening to any category
    when too few same-category matches exist. Returns ``[]`` on a missing KB or any error.
    """
    try:
        path = kb_path(language)
        if not path.exists():
            return []
        rv = rules_version or _current_rules_version()
        active = [r for r in _read_records(path) if is_retrievable(r, rv, domain)]
        if not active:
            return []
        same_category = [r for r in active if r.get("category") == category]
        pool = same_category if len(same_category) >= _MIN_CATEGORY_MATCHES else active
        return _rank_candidates(query, pool)[:top_k]
    except Exception as e:  # noqa: BLE001
        logger.warning("KB retrieval failed for '%s': %s", query, e)
        return []


_KB_SCORE_RE = re.compile(r"\s*\([^()]*\b(?:relevance|score)\b[^()]*\)|\b(?:relevance|score)\s*(?:of\s*)?0[.,]\d+", re.I)


def format_calibration_section(records: list[dict]) -> str:
    """Render retrieved records into a prompt section, or '' when there are none.

    Scores are stripped from example evidence so the judge doesn't learn to quote them.
    """
    if not records:
        return ""
    lines = []
    for r in records:
        evidence = _KB_SCORE_RE.sub("", (r.get("evidence") or "").strip().replace("\n", " "))
        if len(evidence) > 240:
            evidence = evidence[:237] + "..."
        fix = (r.get("recommended_fix") or "").strip().replace("\n", " ")
        if len(fix) > 240:
            fix = fix[:237] + "..."
        shape = ""
        if r.get("n_results") is not None:
            shape = f" [{r.get('n_results')} results"
            if r.get("titles"):
                shape += "; first: " + "; ".join(r["titles"][:3])
            shape += "]"
        lines.append(
            f'  - "{r.get("query", "")}" ({r.get("category", "?")}) -> {r.get("severity", "?")} / '
            f'{r.get("failure_mode", "?")}{shape}\n'
            f"      evidence: {evidence}\n"
            f"      fix: {fix}"
        )
    return (
        "## Calibration examples (graded under the current rules in past audits of OTHER sites)\n"
        "Use them for consistent severity and failure-mode labels and as a model of concrete "
        "evidence writing. Do NOT copy them — the products differ; judge THIS query on its own results.\n"
        + "\n".join(lines)
        + "\n"
    )


# ---------------------------------------------------------------------------
# Step B — harvest
# ---------------------------------------------------------------------------


def _enum_value(v) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _is_anchor_worthy(judgment: QueryJudgment) -> bool:
    """A clean, model-produced, scored verdict.

    Excludes fallback and rule-made verdicts, excluded judgments (fetch_unverified,
    catalog_gap), empty evidence and unclassified non-pass verdicts. PASS verdicts are kept —
    "what good looks like" is valuable calibration.
    """
    if getattr(judgment, "excluded_reason", None):
        return False
    if getattr(judgment, "judge_status", "llm") not in _HARVESTABLE_STATUSES:
        return False
    evidence = (judgment.evidence or "").strip()
    if not evidence or "LLM analysis failed" in evidence:
        return False
    fm = _enum_value(judgment.failure_mode)
    sev_short = _SEVERITY_SHORT.get(_enum_value(judgment.severity), "")
    if not sev_short:
        return False
    if fm == "OTHER" and sev_short != "PASS":
        return False
    return True


def _result_digest(judgment: QueryJudgment) -> dict:
    results = [r for r in judgment.results if not getattr(r, "sponsored", False)] or list(judgment.results)
    by_orig = sorted(results, key=lambda r: r.original_rank)
    return {
        "top1": round(by_orig[0].relevance_score, 4) if by_orig else None,
        "max": round(max((r.relevance_score for r in by_orig), default=0.0), 4) if by_orig else None,
        "n_results": len(judgment.results),
        "titles": [(r.title or "")[:80] for r in by_orig[:3]],
    }


def _record_from_judgment(
    judgment: QueryJudgment,
    language: str,
    provenance: dict,
    embedding: list[float] | None,
    *,
    model: str,
    domain: str,
    rules_version: str,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "query": judgment.test_query.query,
        "category": _enum_value(judgment.test_query.category),
        "language": normalize_language(language),
        "severity": _SEVERITY_SHORT[_enum_value(judgment.severity)],
        "failure_mode": _enum_value(judgment.failure_mode),
        "evidence": judgment.evidence,
        "recommended_fix": judgment.recommended_fix,
        **_result_digest(judgment),
        "embedding": embedding,
        "provenance": provenance,
        "judged_at": provenance.get("judged_at"),
        "domain": domain,
        "model": model,
        "rules_version": rules_version,
        "judge_status": getattr(judgment, "judge_status", "llm"),
        "human_reviewed": False,
        "status": "pending",
        "source": "harvested",
    }


def _dedup_key(domain: str | None, query: str) -> tuple[str, str]:
    return normalize_domain(domain), " ".join((query or "").casefold().split())


def harvest(
    judgments: list[QueryJudgment],
    language: str,
    provenance: dict | None = None,
    model: str | None = None,
    domain: str | None = None,
    rules_version: str | None = None,
) -> int:
    """Append anchor-worthy judgements to the language KB as PENDING records. Returns count.

    Refuses entirely when the judge model is not the default (alternative models soften
    CRITICAL calls; their verdicts must not become anchors). Dedups on (domain, query)
    against non-retired records already in the file. Never raises.
    """
    try:
        default_model = _default_judge_model()
        model = model or default_model
        if model != default_model:
            logger.warning("KB harvest skipped: judge model %s is not the default %s", model, default_model)
            return 0

        prov = dict(provenance or {})
        prov.setdefault("judged_at", datetime.now().isoformat())
        domain = normalize_domain(domain or prov.get("domain") or prov.get("url"))
        rv = rules_version or _current_rules_version()

        path = kb_harvest_path(language)
        existing = _read_records(path) if path.exists() else []
        seen = {
            _dedup_key(r.get("domain") or (r.get("provenance") or {}).get("domain"), r.get("query", ""))
            for r in existing if r.get("status") not in ("retired", "pruned")
        }

        worthy = []
        for j in judgments:
            if not _is_anchor_worthy(j):
                continue
            key = _dedup_key(domain, j.test_query.query)
            if key in seen:
                continue
            seen.add(key)
            worthy.append(j)
        if not worthy:
            return 0

        embeddings = _embed([j.test_query.query for j in worthy], input_type="document")
        if embeddings is None:
            embeddings = [None] * len(worthy)

        records = [
            _record_from_judgment(j, language, prov, emb, model=model, domain=domain, rules_version=rv)
            for j, emb in zip(worthy, embeddings)
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.info("Harvested %d judgements into %s as pending (promote with scripts/kb_prune.py)",
                    len(records), path.name)
        return len(records)
    except Exception as e:  # noqa: BLE001
        logger.warning("KB harvest failed: %s", e)
        return 0
