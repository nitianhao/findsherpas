from __future__ import annotations

import json
import logging
from collections import Counter

import anthropic
from dotenv import load_dotenv

from src.category_selector import CATEGORY_DESCRIPTIONS
from src.models import QueryCategory, SiteContext, SiteType, TestQuery

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Per-category query counts
# ---------------------------------------------------------------------------

_HIGH = 4
_MEDIUM = 3
_LOW = 2

QUERY_COUNTS: dict[QueryCategory, int] = {
    # HIGH — most visible failure surface, need repetition to prove a pattern
    QueryCategory.TYPO: _HIGH,
    QueryCategory.SYNONYM: _HIGH,
    QueryCategory.NATURAL_LANGUAGE: _HIGH,
    QueryCategory.USE_CASE: _HIGH,
    QueryCategory.SEMANTIC_MEANING: _HIGH,
    # MEDIUM — still important, moderate coverage
    QueryCategory.MERGED_WORDS: _MEDIUM,
    QueryCategory.SPLIT_WORD: _MEDIUM,
    QueryCategory.PARTIAL_QUERY: _MEDIUM,
    QueryCategory.MULTI_ATTRIBUTE: _MEDIUM,
    QueryCategory.SUBJECTIVE_ATTRIBUTE: _MEDIUM,
    QueryCategory.CATEGORY_MAPPING: _MEDIUM,
    QueryCategory.FACET_EXTRACTION: _MEDIUM,
    QueryCategory.LONG_VERBOSE_QUERY: _MEDIUM,
    QueryCategory.STOP_WORD_HEAVY: _MEDIUM,
    # LOW — useful but narrower signal, two is enough
    QueryCategory.DIRECT_MATCH: _LOW,
    QueryCategory.BRAND_SEARCH: _LOW,
    QueryCategory.SKU_MODEL_NUMBER: _LOW,
    QueryCategory.BROAD_CATEGORY: _LOW,
    QueryCategory.SPECIAL_CHARACTER: _LOW,
    QueryCategory.PLURAL_SINGULAR: _LOW,
    QueryCategory.ABBREVIATION: _LOW,
    QueryCategory.LOCALE_VARIATION: _LOW,
    QueryCategory.PRICE_ANCHORED: _LOW,
    QueryCategory.NEGATIVE_INTENT: _LOW,
    QueryCategory.UNIT_VARIATION: _LOW,
    QueryCategory.SEASONAL_OCCASION: _LOW,
}


def _calculate_expected_total(selected_categories: list[QueryCategory]) -> int:
    """Sum the expected query count for the given categories."""
    return sum(QUERY_COUNTS.get(cat, _LOW) for cat in selected_categories)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_prompt(
    site_context: SiteContext,
    selected_categories: list[QueryCategory],
) -> str:
    """Build the Sonnet prompt for query generation."""

    nav_list = ", ".join(site_context.nav_categories[:40]) if site_context.nav_categories else "(none detected)"
    brands_list = ", ".join(site_context.brands[:25]) if site_context.brands else "(none detected)"
    items_list = ", ".join(site_context.featured_items[:30]) if site_context.featured_items else "(none detected)"

    categories_block = ""
    for cat in selected_categories:
        count = QUERY_COUNTS.get(cat, _LOW)
        desc = CATEGORY_DESCRIPTIONS.get(cat, "")
        categories_block += f"  - {cat.value} (generate {count} queries): {desc}\n"

    total = _calculate_expected_total(selected_categories)

    return f"""You are a search-quality engineer generating test queries for an ecommerce site audit.

## Site Under Test
- **Site name**: {site_context.site_name or "(unknown)"}
- **URL**: {site_context.url}
- **Site type**: {site_context.site_type}
- **Meta description**: {site_context.raw_meta_description or "(none)"}

## Real Content From This Site's Homepage
**Navigation categories**: {nav_list}
**Brands found on the site**: {brands_list}
**Featured products/services**: {items_list}

## Categories to Generate ({total} queries total)
{categories_block}
## Critical Instructions

You MUST ground every query in the REAL site data above. Follow these rules strictly:

1. **Use real terms**: Every query must reference real product names, brand names, category names, or service names from the lists above. NEVER invent products, brands, or categories that aren't in the provided context.

2. **Category-specific grounding**:
   - TYPO: Take a real product/brand name from the context and introduce a SINGLE realistic misspelling (transposed letters, missing letter, adjacent-key substitution). Example: "Ulraboost" for "Ultraboost".
   - MERGED_WORDS: Take two real words from the context and merge them. Example: "runningshoes" from "Running" + "Shoes".
   - SPLIT_WORD: Take a real compound term and split it. Example: "ultra boost" for "Ultraboost".
   - SYNONYM: Take a real category/product term and use a natural alternative that a customer might type. Example: "sneakers" instead of "Running Shoes".
   - BRAND_SEARCH: Use actual brand names from the brands list, alone or with a product type.
   - SKU_MODEL_NUMBER: Use realistic model identifiers based on real product names in the context (e.g., "AM90" from "Air Max 90").
   - DIRECT_MATCH: Use exact product names from the featured items list.
   - USE_CASE / SEMANTIC_MEANING / NATURAL_LANGUAGE: Ground scenarios in what this site actually sells. Reference real categories and product types.
   - MULTI_ATTRIBUTE: Combine real attributes visible in the context (category + brand, category + descriptor).
   - SUBJECTIVE_ATTRIBUTE: Apply subjective qualifiers to real product categories from the context.
   - PARTIAL_QUERY: Truncate a real product/brand name from the context.
   - SPECIAL_CHARACTER: Use real terms that naturally contain special characters, or add common ones.
   - BROAD_CATEGORY: Use real navigation category labels from the site.
   - PLURAL_SINGULAR: Alternate singular/plural of real category terms.
   - ABBREVIATION: Use common abbreviations of real terms on the site.
   - LOCALE_VARIATION: Use regional spelling variants of real terms.
   - CATEGORY_MAPPING: Use colloquial terms that map to the site's real category labels.
   - FACET_EXTRACTION: Embed real filter values (from categories, attributes) into a natural query.
   - PRICE_ANCHORED: Reference real product types with a price constraint.
   - NEGATIVE_INTENT: Reference real product types with an exclusion.
   - UNIT_VARIATION: Reference real products with measurement variations.
   - SEASONAL_OCCASION: Reference real product types with a seasonal context.
   - STOP_WORD_HEAVY: Pad real product/category terms with natural stop words.
   - LONG_VERBOSE_QUERY: Write a very long query about real products/categories from the site.

3. **Rationale**: For each query, write a one-sentence rationale explaining (a) what specific site content it's grounded in, and (b) what search behaviour it tests.

4. **No duplicates**: Every query string must be unique.

5. **Realistic style**: Queries should feel like what a real customer would type into a search box — lowercase is fine, no formal grammar needed, natural search-box language.

## Output Format

Return ONLY a JSON array (no markdown fences, no commentary) of objects:
[
  {{"category": "CATEGORY_NAME", "query": "the search query", "rationale": "why this tests something meaningful"}},
  ...
]

Generate exactly the number of queries specified for each category ({total} total)."""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence (possibly with language tag)
        first_nl = text.find("\n")
        text = text[first_nl + 1:] if first_nl != -1 else text[3:]
        # Remove closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _call_sonnet(prompt: str) -> list[dict] | None:
    """Call Claude Sonnet and return parsed JSON array, or None on failure."""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=4000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        cleaned = _strip_fences(raw)
        data = json.loads(cleaned)
        if not isinstance(data, list):
            logger.warning("Sonnet returned non-array JSON: %s", type(data).__name__)
            return None
        return data
    except anthropic.APIError as e:
        logger.warning("Sonnet API error: %s", e)
        return None
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.warning("Failed to parse Sonnet response: %s", e)
        return None
    except Exception as e:
        logger.warning("Unexpected error calling Sonnet: %s", e)
        return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_queries(
    raw_queries: list[dict],
    selected_categories: list[QueryCategory],
) -> list[TestQuery]:
    """Validate and convert raw dicts to TestQuery objects.

    Logs warnings for issues but returns as many valid queries as possible.
    """
    valid_names = {e.value for e in QueryCategory}
    selected_names = {cat.value for cat in selected_categories}
    seen_queries: set[str] = set()
    results: list[TestQuery] = []

    for entry in raw_queries:
        cat_name = entry.get("category", "")
        query = entry.get("query", "").strip()
        rationale = entry.get("rationale", "").strip()

        # Validate category
        if cat_name not in valid_names:
            logger.warning("Invalid category '%s' in generated query, skipping", cat_name)
            continue
        if cat_name not in selected_names:
            logger.warning(
                "Category '%s' was not in selected list but Sonnet generated it anyway — keeping it",
                cat_name,
            )

        # Validate query text
        if not query:
            logger.warning("Empty query string for category %s, skipping", cat_name)
            continue

        # Dedupe
        query_lower = query.lower()
        if query_lower in seen_queries:
            logger.warning("Duplicate query '%s', skipping", query)
            continue
        seen_queries.add(query_lower)

        if not rationale:
            rationale = f"Tests {cat_name} behaviour"

        results.append(
            TestQuery(
                category=QueryCategory(cat_name),
                query=query,
                rationale=rationale,
            )
        )

    # Check counts per category
    counts = Counter(tq.category for tq in results)
    for cat in selected_categories:
        expected = QUERY_COUNTS.get(cat, _LOW)
        actual = counts.get(cat.value, 0)  # use_enum_values means .category is str
        if abs(actual - expected) > 1:
            logger.warning(
                "Category %s: expected ~%d queries, got %d",
                cat.value,
                expected,
                actual,
            )

    return results


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def generate_queries(
    site_context: SiteContext,
    selected_categories: list[QueryCategory],
) -> list[TestQuery]:
    """Generate grounded test queries for the selected categories.

    Uses Claude Sonnet to produce queries anchored in real site content.
    Returns list[TestQuery] sorted by category.
    """
    expected = _calculate_expected_total(selected_categories)
    logger.info(
        "Generating ~%d queries across %d categories for %s",
        expected,
        len(selected_categories),
        site_context.site_name or site_context.url,
    )

    prompt = _build_prompt(site_context, selected_categories)
    raw_queries = _call_sonnet(prompt)

    if raw_queries is None:
        logger.warning("Sonnet call failed; returning empty query list")
        return []

    logger.info("Sonnet returned %d raw query entries", len(raw_queries))
    validated = _validate_queries(raw_queries, selected_categories)
    logger.info("Validated %d queries (expected ~%d)", len(validated), expected)

    # Sort by category (grouped)
    cat_order = {cat.value: i for i, cat in enumerate(selected_categories)}
    validated.sort(key=lambda tq: cat_order.get(tq.category, 999))

    return validated


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    demo_context = SiteContext(
        url="https://www.kicksworld.com",
        site_name="KicksWorld",
        site_type=SiteType.PHYSICAL_GOODS,
        nav_categories=[
            "Men's Shoes", "Women's Shoes", "Kids' Shoes",
            "Running", "Casual", "Basketball", "Training",
            "Sandals & Slides", "Boots", "Sale", "New Arrivals",
        ],
        brands=[
            "Nike", "Adidas", "New Balance", "Puma", "Reebok",
            "Asics", "Converse", "Vans", "Under Armour", "Hoka",
        ],
        featured_items=[
            "Nike Air Max 90",
            "Adidas Ultraboost 22",
            "New Balance 574 Classic",
            "Nike Dunk Low Retro",
            "Hoka Clifton 9",
            "Converse Chuck Taylor All Star",
            "Puma RS-X",
            "Asics Gel-Kayano 30",
            "Vans Old Skool",
            "Under Armour HOVR Phantom 3",
        ],
        search_url_template="https://www.kicksworld.com/search?q={}",
        raw_meta_description=(
            "KicksWorld — shop the latest sneakers, running shoes, and casual "
            "footwear from Nike, Adidas, New Balance, and more. Free shipping "
            "on orders over $75."
        ),
    )

    selected = [
        QueryCategory.DIRECT_MATCH,
        QueryCategory.TYPO,
        QueryCategory.SYNONYM,
        QueryCategory.MERGED_WORDS,
        QueryCategory.SPLIT_WORD,
        QueryCategory.BRAND_SEARCH,
        QueryCategory.SKU_MODEL_NUMBER,
        QueryCategory.PLURAL_SINGULAR,
        QueryCategory.MULTI_ATTRIBUTE,
        QueryCategory.ABBREVIATION,
        QueryCategory.SPECIAL_CHARACTER,
        QueryCategory.PARTIAL_QUERY,
    ]

    print(f"Site: {demo_context.site_name} ({demo_context.site_type})")
    print(f"URL:  {demo_context.url}")
    expected_total = _calculate_expected_total(selected)
    print(f"Generating ~{expected_total} queries across {len(selected)} categories...\n")

    queries = generate_queries(demo_context, selected)

    current_cat = None
    for tq in queries:
        if tq.category != current_cat:
            current_cat = tq.category
            count = QUERY_COUNTS.get(QueryCategory(current_cat), _LOW)
            print(f"\n{'='*60}")
            print(f"  {current_cat} (target: {count} queries)")
            print(f"{'='*60}")
        print(f"  query:     {tq.query}")
        print(f"  rationale: {tq.rationale}")
        print()

    print(f"Total: {len(queries)} queries generated")
