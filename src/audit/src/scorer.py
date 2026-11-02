from __future__ import annotations

import logging
import re
import time

import voyageai
import voyageai.error
from dotenv import load_dotenv

from src.models import ScoredResult, SearchResult, TestQuery

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL = "rerank-2.5"

# Retry policy for TRANSIENT Voyage failures only (rate limit, 5xx, timeout, connection).
# Auth / bad-request errors fail fast: retrying a 401 or a malformed request just burns time.
_MAX_ATTEMPTS = 4
_BACKOFF_BASE_S = 2.0

_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = tuple(
    getattr(voyageai.error, name)
    for name in ("RateLimitError", "ServiceUnavailableError", "ServerError", "Timeout",
                 "TryAgain", "APIConnectionError")
    if hasattr(voyageai.error, name)
)


class ScoringError(RuntimeError):
    """Raised when a query could not be scored.

    Deliberately NOT swallowed into an empty result list. An empty scored list is
    indistinguishable downstream from a genuine zero-results search failure, so silently
    returning [] on an API error would MANUFACTURE a CRITICAL finding in a published report
    from nothing but a network blip. Fail loudly instead.

    ``partial`` carries every query already scored in this call (paid for), so the caller
    can checkpoint it and resume with ``score_results(..., already_scored=err.partial)``.
    """

    def __init__(self, message: str, partial: dict | None = None):
        super().__init__(message)
        self.partial: dict[str, list[ScoredResult]] = dict(partial or {})


def is_transient(error: BaseException) -> bool:
    """True for Voyage errors worth retrying (429 / 5xx / timeout / connection)."""
    return isinstance(error, _TRANSIENT_ERRORS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Merchandising badges that some storefronts render inside the title text. They carry no
# product meaning and skew the reranker (e.g. Bergzeit "Pre Sale …", Åhléns
# "Samarbetsföretag …" / "… Medlemspris"). Unambiguous badges are stripped anywhere at the
# start/end; ambiguous ones ("New", "Sale") only when a separator follows, so "New Balance"
# survives.
_BADGES_ALWAYS = (
    r"pre[\s-]?sale", r"presale", r"samarbetsf[öo]retag", r"medlemspris", r"sponsrad", r"sponsored",
    r"gesponsert", r"anzeige", r"bestseller", r"online[\s-]exclusive", r"exklusiv", r"nyhet", r"nyhed",
    r"neuheit", r"nouveau", r"limited\s+edition", r"-\s?\d{1,2}\s?%", r"\d{1,2}\s?%\s?(?:rabatt|off|rabat)",
)
_BADGES_SEPARATED = (r"new", r"neu", r"sale", r"ny", r"top", r"ad", r"hot", r"deal")
_LEAD_ALWAYS_RE = re.compile(r"^\s*(?:" + "|".join(_BADGES_ALWAYS) + r")(?!\w)[\s:|•·\-–]*", re.I)
_TRAIL_ALWAYS_RE = re.compile(r"[\s:|•·\-–]*(?<!\w)(?:" + "|".join(_BADGES_ALWAYS) + r")\s*$", re.I)
_LEAD_SEP_RE = re.compile(r"^\s*(?:" + "|".join(_BADGES_SEPARATED) + r")\s*[:|•·\-–]\s*", re.I)
_MORE_COLOURS_RE = re.compile(r"^\s*\+\d+\s+")              # "+2 Sweet Protection …" (more colours)
_RATING_RE = re.compile(
    r"\(\s*\d[\d.,]*\s*(?:reviews?|bewertungen|recensioner|anmeldelser|ratings?)?\s*\)"
    r"|[★☆]+|\b\d(?:[.,]\d)?\s*(?:/\s*5|out of 5|von 5|av 5|af 5)\b"
    r"|\b\d+\s*(?:reviews?|bewertungen|recensioner|anmeldelser)\b",
    re.I,
)
# Gender words that end a storefront category label ("Mammut | Wanderjacken Damen …").
_GENDER_WORDS = {
    "herren", "damen", "kinder", "unisex", "jungen", "madchen", "mädchen", "baby", "men", "mens",
    "men's", "women", "womens", "women's", "kids", "boys", "girls", "herr", "dam", "barn", "dame",
    "heren", "dames", "kvinder", "maend", "mænd",
}


def _strip_category_prefix(title: str) -> str:
    """'Brand | Category Gender Product' -> 'Brand Gender Product'.

    Bergzeit-style titles carry the storefront category between the brand and the product
    name. The category label inflates relevance for every query naming that category, so it
    is dropped when a gender word marks where it ends (the gender itself is kept — it is
    real intent). Without a gender marker only the pipe is removed.
    """
    if " | " not in title:
        return title
    brand, _, rest = title.partition(" | ")
    words = rest.split()
    for i, w in enumerate(words[:6]):
        if w.casefold().strip(",.") in _GENDER_WORDS and i > 0:
            return " ".join([brand.strip()] + words[i:])
    return f"{brand.strip()} {rest.strip()}"


def clean_title_for_rerank(title: str) -> str:
    """Title text for the reranker: badges, '+N' colour counters, ratings and category prefixes removed.

    The original title is never modified on the result — only the scored document changes.
    """
    t = title or ""
    for _ in range(3):
        before = t
        t = _MORE_COLOURS_RE.sub("", t)
        t = _LEAD_ALWAYS_RE.sub("", t)
        t = _LEAD_SEP_RE.sub("", t)
        t = _MORE_COLOURS_RE.sub("", t)
        t = _TRAIL_ALWAYS_RE.sub("", t)
        if t == before:
            break
    t = _RATING_RE.sub(" ", t)
    t = _strip_category_prefix(t)
    t = re.sub(r"\s{2,}", " ", t).strip(" |-–·•:")
    return t or (title or "").strip()


def _build_document(result: SearchResult) -> str:
    """Reranker document: cleaned title + snippet.

    Price is deliberately NOT included: concatenating it let PRICE_ANCHORED queries score on
    lexical proximity between "under 30 euro" and "EUR29.99" instead of on the product. Price
    constraints are checked in code by the judge (judge.parse_price).
    """
    parts = [clean_title_for_rerank(result.title)]
    if result.snippet:
        parts.append(result.snippet)
    return " | ".join(parts)


def _rerank_with_retry(client, query_str: str, documents: list[str], label: str):
    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return client.rerank(model=_MODEL, query=query_str, documents=documents, top_k=len(documents))
        except Exception as e:  # noqa: BLE001 — classified below
            last_error = e
            if not is_transient(e):
                raise ScoringError(f"Voyage rerank failed (non-retryable {type(e).__name__}) for "
                                   f"query {query_str!r}: {e}") from e
            if attempt < _MAX_ATTEMPTS:
                delay = _BACKOFF_BASE_S * (2 ** (attempt - 1))
                logger.warning("%s '%s' — rerank attempt %d/%d failed (%s); retrying in %.1fs",
                               label, query_str, attempt, _MAX_ATTEMPTS, e, delay)
                time.sleep(delay)
    raise ScoringError(f"Voyage rerank failed for query {query_str!r} after {_MAX_ATTEMPTS} "
                       f"attempts: {last_error}") from last_error


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def score_results(
    queries: list[TestQuery],
    scraped_results: dict[str, list[SearchResult]],
    already_scored: dict[str, list[ScoredResult]] | None = None,
    client=None,
) -> dict[str, list[ScoredResult]]:
    """Score search results for relevance using Voyage AI rerank-2.5.

    Returns a dict mapping query string -> list of ScoredResult sorted by relevance_score
    descending (best match first). Queries present in ``already_scored`` are copied through
    unscored (resume after a ScoringError — no double payment). On failure the raised
    ScoringError carries ``partial`` with everything scored so far.
    """
    all_scored: dict[str, list[ScoredResult]] = dict(already_scored or {})
    total = len(queries)

    for i, tq in enumerate(queries, 1):
        query_str = tq.query
        if query_str in all_scored:
            continue
        results = scraped_results.get(query_str, [])

        if not results:
            logger.info("[%d/%d] '%s' — no results to score", i, total, query_str)
            all_scored[query_str] = []
            continue

        documents = [_build_document(r) for r in results]
        if client is None:
            client = voyageai.Client()
        try:
            reranking = _rerank_with_retry(client, query_str, documents, f"[{i}/{total}]")
        except ScoringError as e:
            e.partial = dict(all_scored)
            raise

        score_map: dict[int, float] = {rr.index: rr.relevance_score for rr in reranking.results}

        # Every document must come back scored. A missing index silently defaulted to 0.0
        # would read downstream as "genuinely irrelevant", so treat it as an error.
        missing = [idx for idx in range(len(documents)) if idx not in score_map]
        if missing:
            raise ScoringError(
                f"Voyage returned no score for {len(missing)} of {len(documents)} "
                f"documents on query {query_str!r} (indices {missing[:5]}...)",
                partial=all_scored,
            )

        scored: list[ScoredResult] = []
        for idx, result in enumerate(results):
            scored.append(ScoredResult(
                rank=result.rank,
                title=result.title,
                price=result.price,
                snippet=result.snippet,
                url=result.url,
                sponsored=getattr(result, "sponsored", False),
                relevance_score=score_map[idx],
                original_rank=result.rank,
            ))

        # Sort by relevance descending (ideal ranking); .rank = reranked position,
        # .original_rank = what the customer saw.
        scored.sort(key=lambda s: s.relevance_score, reverse=True)
        for new_rank, sr in enumerate(scored, 1):
            sr.rank = new_rank

        all_scored[query_str] = scored
        logger.info(
            "[%d/%d] '%s' — scored %d results (top: %.3f, bottom: %.3f)",
            i, total, query_str, len(scored), scored[0].relevance_score, scored[-1].relevance_score,
        )

    logger.info("Scoring complete: %d queries, %d with results", total, sum(1 for v in all_scored.values() if v))
    return all_scored


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    demo_query = TestQuery(
        category="DIRECT_MATCH",
        query="black dress",
        rationale="Direct product search for a specific item",
    )

    demo_results: dict[str, list[SearchResult]] = {
        "black dress": [
            SearchResult(
                rank=1,
                title="Women's Elegant Black Evening Dress - Knee Length",
                price="$89.99",
                snippet="Beautiful black dress perfect for formal occasions. Available in sizes XS-XL.",
                url="/products/black-evening-dress",
            ),
            SearchResult(
                rank=2,
                title="Red Running Shoes - Men's Athletic Sneakers",
                price="$129.99",
                snippet="Lightweight running shoes with responsive cushioning for daily training.",
                url="/products/red-running-shoes",
            ),
            SearchResult(
                rank=3,
                title="Black Cocktail Dress with Lace Detail",
                price="$64.50",
                snippet="Classic little black dress with delicate lace overlay. Party-ready style.",
                url="/products/black-cocktail-dress",
            ),
        ]
    }

    print(f"Query: '{demo_query.query}'")
    print(f"Input results: {len(demo_results['black dress'])}")
    print()

    scored = score_results([demo_query], demo_results)
    results = scored.get("black dress", [])

    print(f"Scored results (sorted by relevance):")
    print(f"{'Rank':<6} {'Orig':<6} {'Score':<8} Title")
    print("-" * 70)
    for sr in results:
        print(f"#{sr.rank:<5} #{sr.original_rank:<5} {sr.relevance_score:<8.4f} {sr.title}")
