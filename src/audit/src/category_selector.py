from __future__ import annotations

import json
import logging
import sys

import anthropic
from dotenv import load_dotenv

from src.models import (
    CAPABILITY_CATEGORY_MAP,
    SITE_TYPE_DEFAULTS,
    CapabilityGroup,
    QueryCategory,
    SiteContext,
    SiteType,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Human-readable description for every QueryCategory
# ---------------------------------------------------------------------------

CATEGORY_DESCRIPTIONS: dict[QueryCategory, str] = {
    QueryCategory.DIRECT_MATCH: (
        "Exact product or service name lookup — tests whether the engine returns "
        "the correct item when the user knows precisely what they want"
    ),
    QueryCategory.BROAD_CATEGORY: (
        "Generic category terms like 'shoes' or 'massages' — tests whether the "
        "engine maps vague queries to the right department or listing group"
    ),
    QueryCategory.SYNONYM: (
        "Alternative words for the same thing (e.g. 'sofa' vs 'couch') — tests "
        "whether the engine understands synonyms and returns equivalent results"
    ),
    QueryCategory.TYPO: (
        "Misspelled product names — tests whether the search engine can handle "
        "common typos and still surface the right results"
    ),
    QueryCategory.SPECIAL_CHARACTER: (
        "Queries with accents, hyphens, ampersands, or other non-alphanumeric "
        "characters — tests whether the engine normalises special characters"
    ),
    QueryCategory.MERGED_WORDS: (
        "Two words typed without a space (e.g. 'runningshoes') — tests whether "
        "the engine can split compound queries into meaningful tokens"
    ),
    QueryCategory.BRAND_SEARCH: (
        "Searching by brand name alone or brand + product — tests whether the "
        "engine recognises and prioritises brand-specific results"
    ),
    QueryCategory.SPLIT_WORD: (
        "A single compound word split into two (e.g. 'head phones') — tests "
        "whether the engine can rejoin split tokens correctly"
    ),
    QueryCategory.NATURAL_LANGUAGE: (
        "Full conversational queries (e.g. 'something warm for winter hiking') "
        "— tests whether the engine understands intent beyond keywords"
    ),
    QueryCategory.PRICE_ANCHORED: (
        "Queries that include a price constraint (e.g. 'laptop under $500') — "
        "tests whether the engine can parse and apply price filters from free text"
    ),
    QueryCategory.NEGATIVE_INTENT: (
        "Queries with exclusion intent (e.g. 'wireless headphones not Bluetooth') "
        "— tests whether the engine handles negation words correctly"
    ),
    QueryCategory.UNIT_VARIATION: (
        "Queries using different measurement units or formats (e.g. '6ft' vs "
        "'72 inches') — tests whether the engine normalises units"
    ),
    QueryCategory.PLURAL_SINGULAR: (
        "Singular vs plural forms of the same word — tests whether the engine "
        "treats 'shoe' and 'shoes' equivalently"
    ),
    QueryCategory.ABBREVIATION: (
        "Common abbreviations and acronyms (e.g. 'TV' for 'television') — tests "
        "whether the engine expands abbreviations to match full terms"
    ),
    QueryCategory.LOCALE_VARIATION: (
        "Regional spelling or terminology differences (e.g. 'colour' vs 'color') "
        "— tests whether the engine handles locale-specific language"
    ),
    QueryCategory.SKU_MODEL_NUMBER: (
        "Exact SKU, model, or part numbers — tests whether the engine can match "
        "alphanumeric identifiers precisely"
    ),
    QueryCategory.SUBJECTIVE_ATTRIBUTE: (
        "Subjective qualifiers like 'cozy', 'luxury', or 'budget-friendly' — "
        "tests whether the engine understands qualitative descriptors"
    ),
    QueryCategory.USE_CASE: (
        "Queries describing a use case or occasion (e.g. 'gift for dad', "
        "'office desk setup') — tests whether the engine infers products from context"
    ),
    QueryCategory.SEASONAL_OCCASION: (
        "Season- or event-driven queries (e.g. 'Valentine gifts', 'summer sale') "
        "— tests whether the engine surfaces seasonally relevant results"
    ),
    QueryCategory.MULTI_ATTRIBUTE: (
        "Queries combining multiple filters or attributes (e.g. 'blue cotton "
        "shirt size M') — tests whether the engine handles compound constraints"
    ),
    QueryCategory.STOP_WORD_HEAVY: (
        "Queries packed with common stop words (e.g. 'the best place to get a "
        "good haircut') — tests whether the engine extracts meaning despite noise"
    ),
    QueryCategory.PARTIAL_QUERY: (
        "Incomplete or truncated queries (e.g. 'sam' for 'Samsung') — tests "
        "prefix matching and autocomplete-like behaviour in search results"
    ),
    QueryCategory.LONG_VERBOSE_QUERY: (
        "Very long, over-specified queries — tests whether the engine can extract "
        "the core intent from noisy, wordy input"
    ),
    QueryCategory.SEMANTIC_MEANING: (
        "Queries that describe what the user wants conceptually, not by product "
        "name — tests semantic / meaning-based search (e.g. 'something to keep "
        "my drinks cold')"
    ),
    QueryCategory.CATEGORY_MAPPING: (
        "Queries using colloquial category names that differ from the site's "
        "taxonomy — tests whether the engine maps user language to internal categories"
    ),
    QueryCategory.FACET_EXTRACTION: (
        "Queries where a word is a filter value (e.g. location, colour) not a "
        "keyword — tests whether the engine parses facets from free text"
    ),
}


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _build_prompt(site_context: SiteContext, default_categories: list[QueryCategory]) -> str:
    """Build the prompt for Haiku to adjust category selection."""

    defaults_block = "\n".join(
        f"  - {cat}: {CATEGORY_DESCRIPTIONS[QueryCategory(cat)]}"
        for cat in default_categories
    )

    all_categories_block = "\n".join(
        f"  - {cat.value}: {desc}"
        for cat, desc in CATEGORY_DESCRIPTIONS.items()
    )

    nav_list = ", ".join(site_context.nav_categories[:30]) if site_context.nav_categories else "(none detected)"
    brands_list = ", ".join(site_context.brands[:20]) if site_context.brands else "(none detected)"
    items_list = ", ".join(site_context.featured_items[:20]) if site_context.featured_items else "(none detected)"

    return f"""You are helping select which search-quality test categories to run for an ecommerce site audit.

## Site Information
- **URL**: {site_context.url}
- **Site name**: {site_context.site_name or "(unknown)"}
- **Detected site type**: {site_context.site_type}
- **Meta description**: {site_context.raw_meta_description or "(none)"}
- **Navigation categories**: {nav_list}
- **Brands found**: {brands_list}
- **Featured items**: {items_list}

## Current Default Categories for {site_context.site_type}
{defaults_block}

## Full Library of Available Categories (26 total)
{all_categories_block}

## Your Task
Review the site information and decide whether the default category selection should be adjusted.

Rules:
- Only ADD categories that are clearly relevant based on the homepage context you see above.
- Only REMOVE categories that clearly don't apply (e.g. SKU_MODEL_NUMBER for a pure services site with no model numbers).
- Keep changes minimal. The defaults are well-chosen; only adjust when there's a clear reason from the site data.
- The final set should contain 12-16 categories. Don't go below 10 or above 18.
- Each add/remove must include a brief reason tied to something specific you see in the site data.

Return ONLY a JSON object (no markdown fences, no commentary) with this exact structure:
{{
  "add": [
    {{"category": "CATEGORY_NAME", "reason": "one-line reason"}},
    ...
  ],
  "remove": [
    {{"category": "CATEGORY_NAME", "reason": "one-line reason"}},
    ...
  ],
  "site_type_override": null
}}

Set site_type_override to "PHYSICAL_GOODS", "SERVICES_EXPERIENCES", or "MARKETPLACE_MIXED" ONLY if the detected type is clearly wrong based on the site data. Otherwise leave it null."""


# ---------------------------------------------------------------------------
# LLM call + response parsing
# ---------------------------------------------------------------------------


def _call_haiku(prompt: str) -> dict | None:
    """Call Claude Haiku and return parsed JSON, or None on any failure."""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if Haiku wraps anyway
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)
    except anthropic.APIError as e:
        logger.warning("Haiku API error: %s", e)
        return None
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        logger.warning("Failed to parse Haiku response: %s", e)
        return None
    except Exception as e:
        logger.warning("Unexpected error calling Haiku: %s", e)
        return None


def _apply_adjustments(
    base: list[QueryCategory],
    haiku_response: dict,
    site_context: SiteContext,
) -> list[QueryCategory]:
    """Apply Haiku's add/remove/override to the base category list."""

    # Handle site_type_override — swap base defaults first
    override = haiku_response.get("site_type_override")
    if override and override in {e.value for e in SiteType}:
        new_type = SiteType(override)
        if new_type.value != site_context.site_type:
            logger.info(
                "Haiku overrode site_type: %s -> %s",
                site_context.site_type,
                new_type.value,
            )
            base = list(SITE_TYPE_DEFAULTS.get(new_type, base))

    current = list(base)
    valid_names = {e.value for e in QueryCategory}

    # Removals
    for entry in haiku_response.get("remove", []):
        cat_name = entry.get("category", "")
        reason = entry.get("reason", "")
        if cat_name not in valid_names:
            logger.warning("Haiku tried to remove invalid category: %s", cat_name)
            continue
        cat = QueryCategory(cat_name)
        if cat in current:
            current.remove(cat)
            logger.info("Removed %s — %s", cat_name, reason)
        else:
            logger.debug("Haiku wanted to remove %s but it was not in the list", cat_name)

    # Additions
    for entry in haiku_response.get("add", []):
        cat_name = entry.get("category", "")
        reason = entry.get("reason", "")
        if cat_name not in valid_names:
            logger.warning("Haiku tried to add invalid category: %s", cat_name)
            continue
        cat = QueryCategory(cat_name)
        if cat not in current:
            current.append(cat)
            logger.info("Added %s — %s", cat_name, reason)
        else:
            logger.debug("Haiku wanted to add %s but it was already present", cat_name)

    return current


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def select_categories(site_context: SiteContext) -> list[QueryCategory]:
    """Select which query categories to test for a given site.

    Starts from hardcoded defaults per site type, then uses a cheap Haiku call
    to adjust the selection based on actual homepage context.  Falls back to
    unmodified defaults if the LLM call fails.
    """
    site_type = SiteType(site_context.site_type)
    default_categories = list(SITE_TYPE_DEFAULTS.get(site_type, SITE_TYPE_DEFAULTS[SiteType.MARKETPLACE_MIXED]))

    prompt = _build_prompt(site_context, default_categories)
    haiku_response = _call_haiku(prompt)

    if haiku_response is None:
        logger.warning("Haiku call failed; using unmodified defaults for %s", site_type.value)
        return default_categories

    adjusted = _apply_adjustments(default_categories, haiku_response, site_context)

    if not adjusted:
        logger.warning("Adjustment resulted in empty list; falling back to defaults")
        return default_categories

    return adjusted


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    demo_context = SiteContext(
        url="https://www.serenity-spa.com",
        site_name="Serenity Spa & Wellness",
        site_type=SiteType.SERVICES_EXPERIENCES,
        nav_categories=[
            "Massages", "Facials", "Body Treatments", "Couples Packages",
            "Nail Services", "Membership", "Gift Cards", "Locations",
        ],
        brands=["Dermalogica", "Aveda", "Elemis"],
        featured_items=[
            "Hot Stone Massage 60min",
            "HydraFacial Signature",
            "Couples Aromatherapy Package",
            "Deep Tissue Recovery 90min",
            "Express Facial 30min",
        ],
        search_url_template="https://www.serenity-spa.com/search?q={}",
        raw_meta_description=(
            "Serenity Spa & Wellness — luxury spa treatments, massages, facials, "
            "and body treatments. Book your appointment online."
        ),
    )

    print(f"Site: {demo_context.site_name} ({demo_context.site_type})")
    print(f"URL:  {demo_context.url}")
    print()

    categories = select_categories(demo_context)

    print(f"Selected {len(categories)} categories:")
    for cat in categories:
        print(f"  - {cat.value}: {CATEGORY_DESCRIPTIONS[cat]}")
