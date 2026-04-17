from __future__ import annotations

import logging

import voyageai
from dotenv import load_dotenv

from src.models import ScoredResult, SearchResult, TestQuery

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL = "rerank-2.5"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_document(result: SearchResult) -> str:
    """Build a single document string from a SearchResult for the reranker."""
    parts = [result.title]
    if result.price:
        parts.append(result.price)
    if result.snippet:
        parts.append(result.snippet)
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def score_results(
    queries: list[TestQuery],
    scraped_results: dict[str, list[SearchResult]],
) -> dict[str, list[ScoredResult]]:
    """Score search results for relevance using Voyage AI rerank-2.5.

    Returns a dict mapping query string -> list of ScoredResult sorted by
    relevance_score descending (best match first).
    """
    client = voyageai.Client()
    all_scored: dict[str, list[ScoredResult]] = {}
    total = len(queries)

    for i, tq in enumerate(queries, 1):
        query_str = tq.query
        results = scraped_results.get(query_str, [])

        if not results:
            logger.info("[%d/%d] '%s' — no results to score", i, total, query_str)
            all_scored[query_str] = []
            continue

        try:
            documents = [_build_document(r) for r in results]

            reranking = client.rerank(
                model=_MODEL,
                query=query_str,
                documents=documents,
                top_k=len(documents),
            )

            # Build a map from document index -> relevance score
            score_map: dict[int, float] = {}
            for rr in reranking.results:
                score_map[rr.index] = rr.relevance_score

            # Convert to ScoredResult objects
            scored: list[ScoredResult] = []
            for idx, result in enumerate(results):
                relevance = score_map.get(idx, 0.0)
                scored.append(ScoredResult(
                    rank=result.rank,
                    title=result.title,
                    price=result.price,
                    snippet=result.snippet,
                    url=result.url,
                    relevance_score=relevance,
                    original_rank=result.rank,
                ))

            # Sort by relevance descending (ideal ranking)
            scored.sort(key=lambda s: s.relevance_score, reverse=True)

            # Reassign rank to reflect relevance-based ordering
            for new_rank, sr in enumerate(scored, 1):
                sr.rank = new_rank

            all_scored[query_str] = scored
            logger.info(
                "[%d/%d] '%s' — scored %d results (top: %.3f, bottom: %.3f)",
                i, total, query_str, len(scored),
                scored[0].relevance_score if scored else 0.0,
                scored[-1].relevance_score if scored else 0.0,
            )

        except Exception as e:
            logger.warning("[%d/%d] '%s' — scoring failed: %s", i, total, query_str, e)
            all_scored[query_str] = []

    logger.info(
        "Scoring complete: %d queries, %d with results",
        total,
        sum(1 for v in all_scored.values() if v),
    )
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
