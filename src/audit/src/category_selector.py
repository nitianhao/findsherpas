from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from src.llm_compat import structured_call
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

# Overridable per-run; unset env = unchanged default. See docs/CASE_STUDY_PLAYBOOK.md.
_MODEL = os.environ.get("AUDIT_MODEL_CATEGORIES", "claude-haiku-4-5-20251001")

# ---------------------------------------------------------------------------
# Human-readable description for every QueryCategory
# ---------------------------------------------------------------------------

CATEGORY_DESCRIPTIONS: dict[QueryCategory, str] = {
    QueryCategory.DIRECT_MATCH: (
        "Exact product or service name lookup — tests whether the engine returns "
        "the correct item when the user knows precisely what they want"
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
    QueryCategory.OCCASION: (
        "Queries describing an occasion or purpose (e.g. 'gift for dad', "
        "'housewarming present') — tests whether the engine infers products from context"
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
    QueryCategory.GIBBERISH: (
        "Pure keyboard mash (e.g. 'qwertzuiop', 'xkvbnmwrtsdfg') — the correct answer is "
        "ZERO results; tests whether the engine has a no-results state at all"
    ),
    # Retired: kept only so old reports render. Never offered or selected.
    QueryCategory.BROAD_CATEGORY: (
        "(Retired) The site's own category term typed as-is — superseded by CATEGORY_MAPPING"
    ),
}

# Categories the selector may offer / return. BROAD_CATEGORY is retired (CATEGORIES_PLAYBOOK).
RETIRED_CATEGORIES: frozenset[QueryCategory] = frozenset({QueryCategory.BROAD_CATEGORY})
OFFERABLE_CATEGORIES: list[QueryCategory] = [c for c in QueryCategory if c not in RETIRED_CATEGORIES]

# Bounds stated in the prompt and the playbook; enforced in code, not just requested.
MIN_CATEGORIES = 10
MAX_CATEGORIES = 18


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def _strict_llm() -> bool:
    """AUDIT_STRICT_LLM (default on): raise instead of falling back when an LLM step fails."""
    return os.environ.get("AUDIT_STRICT_LLM", "1").strip().lower() not in ("0", "false", "no", "off", "")


def _system_prompt() -> str:
    """Static rules + the full category library (cached across calls)."""
    library = "\n".join(f"  - {cat.value}: {CATEGORY_DESCRIPTIONS[cat]}" for cat in OFFERABLE_CATEGORIES)
    return f"""You are helping select which search-quality test categories to run for an ecommerce site audit.

## Full Library of Available Categories ({len(OFFERABLE_CATEGORIES)} total)
{library}

## Your Task
Review the site information and decide whether the default category selection for the detected site type should be adjusted.

Rules:
- First decide the site type. Set site_type_override to PHYSICAL_GOODS, SERVICES_EXPERIENCES or MARKETPLACE_MIXED ONLY if the detected type is clearly wrong based on the site data; otherwise leave it null. Explain in site_type_reason either way.
- Only ADD categories that are clearly relevant based on the site context. Only use names from the library above.
- Only REMOVE categories that clearly don't apply (e.g. SKU_MODEL_NUMBER for a pure services site with no model numbers).
- Keep changes minimal. The defaults are well-chosen; only adjust when there's a clear reason from the site data.
- The final set should contain 12-16 categories. Never go below {MIN_CATEGORIES} or above {MAX_CATEGORIES}.
- Each add/remove must include a brief reason tied to something specific you see in the site data."""


def _build_prompt(site_context: SiteContext, default_categories: list[QueryCategory]) -> str:
    """Per-call user prompt: site data + the defaults for its site type."""

    defaults_block = "\n".join(
        f"  - {QueryCategory(cat).value}: {CATEGORY_DESCRIPTIONS[QueryCategory(cat)]}"
        for cat in default_categories
    )
    nav_list = ", ".join(site_context.nav_categories[:30]) if site_context.nav_categories else "(none detected)"
    brands_list = ", ".join(site_context.brands[:20]) if site_context.brands else "(none detected)"
    items_list = " | ".join(site_context.featured_items[:20]) if site_context.featured_items else "(none detected)"
    sample = site_context.catalog_sample or []
    sample_list = " | ".join(sample[:40]) if sample else "(none sampled)"

    return f"""## Site Information
- **URL**: {site_context.url}
- **Site name**: {site_context.site_name or "(unknown)"}
- **Detected site type**: {site_context.site_type}
- **Language / locale**: {site_context.primary_language} / {site_context.locale or "(unknown)"}
- **Meta description**: {site_context.raw_meta_description or "(none)"}
- **Navigation categories**: {nav_list}
- **Brands found**: {brands_list}
- **Featured items**: {items_list}
- **Sampled catalog titles ({len(sample)})**: {sample_list}

## Current Default Categories for {site_context.site_type}
{defaults_block}"""


# ---------------------------------------------------------------------------
# LLM call + response parsing
# ---------------------------------------------------------------------------


class CategoryChange(BaseModel):
    category: QueryCategory
    reason: str


class CategoryAdjustments(BaseModel):
    """Structured output. Site type is settled first, so the add/remove list is reasoned
    against the right defaults."""

    site_type_reason: str
    site_type_override: Optional[SiteType] = None
    add: list[CategoryChange]
    remove: list[CategoryChange]


def _call_llm(system: str, user: str, client=None) -> CategoryAdjustments:
    """One structured call (phase="categories"). Raises on any failure."""
    return structured_call(
        model=_MODEL, system=system, user=user, schema=CategoryAdjustments,
        max_tokens=2000, phase="categories", temperature=0.2, client=client,
    )


def _as_dict(resp) -> dict:
    if isinstance(resp, BaseModel):
        return resp.model_dump(mode="json")
    return dict(resp or {})


def _apply_adjustments(
    base: list[QueryCategory],
    llm_response: dict | BaseModel,
    site_context: SiteContext,
) -> list[QueryCategory]:
    """Apply the LLM's add/remove to ``base`` and enforce the 10-18 bounds.

    ``site_type_override`` is handled by :func:`select_categories` (it changes which defaults
    the adjustments are reasoned against); it is ignored here.
    """
    data = _as_dict(llm_response)
    current = list(base)
    valid_names = {e.value for e in OFFERABLE_CATEGORIES}
    removed: list[QueryCategory] = []
    added: list[QueryCategory] = []

    # Removals
    for entry in data.get("remove", []) or []:
        if not isinstance(entry, dict):
            continue
        cat_name = str(entry.get("category") or "")
        reason = entry.get("reason", "")
        if cat_name not in valid_names:
            logger.warning("LLM tried to remove invalid/retired category: %s", cat_name)
            continue
        cat = QueryCategory(cat_name)
        if cat in current:
            current.remove(cat)
            removed.append(cat)
            logger.info("Removed %s — %s", cat_name, reason)

    # Additions
    for entry in data.get("add", []) or []:
        if not isinstance(entry, dict):
            continue
        cat_name = str(entry.get("category") or "")
        reason = entry.get("reason", "")
        if cat_name not in valid_names:
            logger.warning("LLM tried to add invalid/retired category: %s", cat_name)
            continue
        cat = QueryCategory(cat_name)
        if cat not in current:
            current.append(cat)
            added.append(cat)
            logger.info("Added %s — %s", cat_name, reason)

    return _enforce_bounds(current, base, removed, added)


def _enforce_bounds(
    current: list[QueryCategory],
    base: list[QueryCategory],
    removed: list[QueryCategory] | None = None,
    added: list[QueryCategory] | None = None,
) -> list[QueryCategory]:
    """Drop retired categories; keep the set within MIN_CATEGORIES..MAX_CATEGORIES."""
    current = [c for c in current if c not in RETIRED_CATEGORIES]
    # Too many: drop the latest additions first, then trailing entries.
    for cat in reversed(list(added or [])):
        if len(current) <= MAX_CATEGORIES:
            break
        if cat in current:
            current.remove(cat)
            logger.warning("Category cap %d: dropped added %s", MAX_CATEGORIES, cat.value)
    while len(current) > MAX_CATEGORIES:
        logger.warning("Category cap %d: dropped %s", MAX_CATEGORIES, current[-1].value)
        current.pop()
    # Too few: restore removed defaults, then other defaults, then the library in order.
    refill = [*(removed or []), *base, *OFFERABLE_CATEGORIES]
    for cat in refill:
        if len(current) >= MIN_CATEGORIES:
            break
        if cat not in current and cat not in RETIRED_CATEGORIES:
            current.append(cat)
            logger.warning("Category floor %d: restored %s", MIN_CATEGORIES, cat.value)
    return current


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def _defaults_for(site_type: SiteType) -> list[QueryCategory]:
    return list(SITE_TYPE_DEFAULTS.get(site_type, SITE_TYPE_DEFAULTS[SiteType.MARKETPLACE_MIXED]))


def select_categories(site_context: SiteContext, *, client=None) -> list[QueryCategory]:
    """Select which query categories to test for a given site.

    Starts from hardcoded defaults per site type, then one structured LLM call adjusts the
    selection from the site context. If the LLM corrects the site type, ``site_context.site_type``
    is updated and the adjustment is re-asked against the new type's defaults (adjustments
    reasoned against the wrong defaults are discarded).

    Provenance lands in ``site_context.provenance``: ``categories`` ('llm' or
    'fallback: <error>'), ``categories_model``, ``categories_prompt_sha256``,
    ``categories_generated_at``, ``categories_adjustments``. With ``AUDIT_STRICT_LLM`` on (the
    default) an LLM failure raises instead of falling back to the unmodified defaults.
    """
    prov = site_context.provenance
    site_type = SiteType(site_context.site_type)
    system = _system_prompt()
    prov["categories_model"] = _MODEL
    prov["categories_generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    response: CategoryAdjustments | None = None
    default_categories = _defaults_for(site_type)
    for round_no in (1, 2):
        user = _build_prompt(site_context, default_categories)
        prov["categories_prompt_sha256"] = hashlib.sha256(f"{system}\n\n{user}".encode()).hexdigest()
        try:
            response = _call_llm(system, user, client=client)
        except Exception as e:
            prov["categories"] = f"fallback: {type(e).__name__}: {e}"[:500]
            logger.error("Category selection LLM call FAILED — using unmodified defaults for %s: %s",
                         site_type.value, prov["categories"])
            if _strict_llm():
                raise
            return _enforce_bounds(default_categories, default_categories)

        override = response.site_type_override
        override = SiteType(override) if override else None
        if override is None or override == site_type or round_no == 2:
            break
        logger.warning("LLM corrected site_type: %s -> %s (%s)", site_type.value, override.value,
                       response.site_type_reason)
        prov["categories_site_type_override"] = f"{site_type.value} -> {override.value}: {response.site_type_reason}"[:500]
        site_type = override
        site_context.site_type = override.value
        default_categories = _defaults_for(site_type)

    adjusted = _apply_adjustments(default_categories, response, site_context)
    prov["categories"] = "llm"
    changes = [f"+{c.category.value if hasattr(c.category, 'value') else c.category} ({c.reason})" for c in response.add]
    changes += [f"-{c.category.value if hasattr(c.category, 'value') else c.category} ({c.reason})" for c in response.remove]
    prov["categories_adjustments"] = "; ".join(changes)[:1000] or "none"
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
    print(f"Provenance: {demo_context.provenance}")
