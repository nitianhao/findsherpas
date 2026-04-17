from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class QueryCategory(str, Enum):
    DIRECT_MATCH = "DIRECT_MATCH"
    BROAD_CATEGORY = "BROAD_CATEGORY"
    SYNONYM = "SYNONYM"
    TYPO = "TYPO"
    SPECIAL_CHARACTER = "SPECIAL_CHARACTER"
    MERGED_WORDS = "MERGED_WORDS"
    BRAND_SEARCH = "BRAND_SEARCH"
    SPLIT_WORD = "SPLIT_WORD"
    NATURAL_LANGUAGE = "NATURAL_LANGUAGE"
    PRICE_ANCHORED = "PRICE_ANCHORED"
    NEGATIVE_INTENT = "NEGATIVE_INTENT"
    UNIT_VARIATION = "UNIT_VARIATION"
    PLURAL_SINGULAR = "PLURAL_SINGULAR"
    ABBREVIATION = "ABBREVIATION"
    LOCALE_VARIATION = "LOCALE_VARIATION"
    SKU_MODEL_NUMBER = "SKU_MODEL_NUMBER"
    SUBJECTIVE_ATTRIBUTE = "SUBJECTIVE_ATTRIBUTE"
    USE_CASE = "USE_CASE"
    SEASONAL_OCCASION = "SEASONAL_OCCASION"
    MULTI_ATTRIBUTE = "MULTI_ATTRIBUTE"
    STOP_WORD_HEAVY = "STOP_WORD_HEAVY"
    PARTIAL_QUERY = "PARTIAL_QUERY"
    LONG_VERBOSE_QUERY = "LONG_VERBOSE_QUERY"
    SEMANTIC_MEANING = "SEMANTIC_MEANING"
    CATEGORY_MAPPING = "CATEGORY_MAPPING"
    FACET_EXTRACTION = "FACET_EXTRACTION"


class CapabilityGroup(str, Enum):
    TYPO_TOLERANCE = "TYPO_TOLERANCE"
    LANGUAGE_UNDERSTANDING = "LANGUAGE_UNDERSTANDING"
    PRODUCT_DISCOVERY = "PRODUCT_DISCOVERY"
    BRAND_MODEL_SEARCH = "BRAND_MODEL_SEARCH"
    FILTERS_CONSTRAINTS = "FILTERS_CONSTRAINTS"
    SHOPPING_CONTEXT = "SHOPPING_CONTEXT"


class SiteType(str, Enum):
    PHYSICAL_GOODS = "PHYSICAL_GOODS"
    SERVICES_EXPERIENCES = "SERVICES_EXPERIENCES"
    MARKETPLACE_MIXED = "MARKETPLACE_MIXED"


class FailureMode(str, Enum):
    PARTIAL_KEYWORD_MATCH = "PARTIAL_KEYWORD_MATCH"
    BRAND_BLEED = "BRAND_BLEED"
    CONSTRAINT_DROPPED = "CONSTRAINT_DROPPED"
    CATEGORY_MAPPING_FAILURE = "CATEGORY_MAPPING_FAILURE"
    FACET_NOT_EXTRACTED = "FACET_NOT_EXTRACTED"
    NO_FUZZY_MATCHING = "NO_FUZZY_MATCHING"
    NO_SEMANTIC_UNDERSTANDING = "NO_SEMANTIC_UNDERSTANDING"
    POOR_RANKING = "POOR_RANKING"
    ZERO_RESULTS_OR_GARBAGE = "ZERO_RESULTS_OR_GARBAGE"
    OTHER = "OTHER"


class Severity(str, Enum):
    CRITICAL = "Critical — Customers searching this way see irrelevant results. This directly loses sales."
    MODERATE = "Moderate — Results are partially relevant but the experience is degraded. Customers may bounce."
    MINOR = "Minor — Niche edge case. Low search volume, but still a gap."
    PASS = "Pass — Search handles this well."


# ---------------------------------------------------------------------------
# Capability → Category mapping
# ---------------------------------------------------------------------------

CAPABILITY_CATEGORY_MAP: dict[CapabilityGroup, list[QueryCategory]] = {
    CapabilityGroup.TYPO_TOLERANCE: [
        QueryCategory.TYPO,
        QueryCategory.MERGED_WORDS,
        QueryCategory.SPLIT_WORD,
        QueryCategory.SPECIAL_CHARACTER,
        QueryCategory.PARTIAL_QUERY,
    ],
    CapabilityGroup.LANGUAGE_UNDERSTANDING: [
        QueryCategory.SYNONYM,
        QueryCategory.NATURAL_LANGUAGE,
        QueryCategory.LONG_VERBOSE_QUERY,
        QueryCategory.STOP_WORD_HEAVY,
        QueryCategory.SEMANTIC_MEANING,
    ],
    CapabilityGroup.PRODUCT_DISCOVERY: [
        QueryCategory.DIRECT_MATCH,
        QueryCategory.BROAD_CATEGORY,
        QueryCategory.CATEGORY_MAPPING,
    ],
    CapabilityGroup.BRAND_MODEL_SEARCH: [
        QueryCategory.BRAND_SEARCH,
        QueryCategory.SKU_MODEL_NUMBER,
        QueryCategory.ABBREVIATION,
    ],
    CapabilityGroup.FILTERS_CONSTRAINTS: [
        QueryCategory.PRICE_ANCHORED,
        QueryCategory.NEGATIVE_INTENT,
        QueryCategory.MULTI_ATTRIBUTE,
        QueryCategory.FACET_EXTRACTION,
        QueryCategory.UNIT_VARIATION,
    ],
    CapabilityGroup.SHOPPING_CONTEXT: [
        QueryCategory.USE_CASE,
        QueryCategory.SUBJECTIVE_ATTRIBUTE,
        QueryCategory.SEASONAL_OCCASION,
        QueryCategory.LOCALE_VARIATION,
        QueryCategory.PLURAL_SINGULAR,
    ],
}

# ---------------------------------------------------------------------------
# Site-type → default test categories
# ---------------------------------------------------------------------------

SITE_TYPE_DEFAULTS: dict[SiteType, list[QueryCategory]] = {
    SiteType.PHYSICAL_GOODS: [
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
    ],
    SiteType.SERVICES_EXPERIENCES: [
        QueryCategory.BROAD_CATEGORY,
        QueryCategory.NATURAL_LANGUAGE,
        QueryCategory.USE_CASE,
        QueryCategory.SUBJECTIVE_ATTRIBUTE,
        QueryCategory.SEASONAL_OCCASION,
        QueryCategory.TYPO,
        QueryCategory.SYNONYM,
        QueryCategory.STOP_WORD_HEAVY,
        QueryCategory.NEGATIVE_INTENT,
        QueryCategory.CATEGORY_MAPPING,
        QueryCategory.FACET_EXTRACTION,
        QueryCategory.SEMANTIC_MEANING,
    ],
    SiteType.MARKETPLACE_MIXED: [
        QueryCategory.DIRECT_MATCH,
        QueryCategory.BROAD_CATEGORY,
        QueryCategory.TYPO,
        QueryCategory.SYNONYM,
        QueryCategory.BRAND_SEARCH,
        QueryCategory.NATURAL_LANGUAGE,
        QueryCategory.USE_CASE,
        QueryCategory.CATEGORY_MAPPING,
        QueryCategory.FACET_EXTRACTION,
        QueryCategory.NEGATIVE_INTENT,
        QueryCategory.MULTI_ATTRIBUTE,
        QueryCategory.PLURAL_SINGULAR,
        QueryCategory.PARTIAL_QUERY,
        QueryCategory.SUBJECTIVE_ATTRIBUTE,
    ],
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SiteContext(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    url: str = Field(description="Root URL of the site being audited.")
    site_name: str = Field(default="", description="Human-readable name of the site.")
    site_type: SiteType = Field(description="Broad classification of the site's commerce model.")
    nav_categories: list[str] = Field(
        default_factory=list,
        description="Top-level navigation category labels scraped from the homepage.",
    )
    brands: list[str] = Field(
        default_factory=list,
        description="Brand names detected on the site (from nav, homepage, or meta).",
    )
    featured_items: list[str] = Field(
        default_factory=list,
        description="Actual product or service titles surfaced on the homepage.",
    )
    search_url_template: str = Field(
        default="",
        description="URL template for constructing search requests, e.g. 'https://example.com/search?q={query}'.",
    )
    raw_meta_description: str = Field(
        default="",
        description="Raw <meta name='description'> content from the homepage.",
    )


class TestQuery(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    category: QueryCategory = Field(description="The query category this test case exercises.")
    query: str = Field(description="The exact search string to submit.")
    rationale: str = Field(description="Why this query is a meaningful test for the site and category.")


class SearchResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    rank: int = Field(description="1-indexed position of this result in the returned list.")
    title: str = Field(description="Title or name of the search result.")
    price: Optional[str] = Field(default=None, description="Displayed price string, if present.")
    snippet: Optional[str] = Field(default=None, description="Short description or excerpt shown in results.")
    url: Optional[str] = Field(default=None, description="URL of the result page.")


class ScoredResult(SearchResult):
    model_config = ConfigDict(use_enum_values=True)

    relevance_score: float = Field(
        description="Relevance score between 0.0 (irrelevant) and 1.0 (perfectly relevant).",
        ge=0.0,
        le=1.0,
    )
    original_rank: int = Field(description="The rank position as returned by the search engine (1-indexed).")


class QueryJudgment(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    test_query: TestQuery = Field(description="The test query that was evaluated.")
    results: list[ScoredResult] = Field(description="Scored search results returned for this query.")
    failure_mode: FailureMode = Field(description="Primary failure pattern observed in the results.")
    failure_mode_explanation: Optional[str] = Field(
        default=None,
        description="Free-text explanation used when failure_mode is OTHER.",
    )
    severity: Severity = Field(description="Severity of the search experience failure for this query.")
    evidence: str = Field(description="Specific results or observations that demonstrate the problem.")
    recommended_fix: str = Field(
        description="Actionable fix recommendation specific to what actually happened, not generic advice."
    )
    displacement: int = Field(
        description="How many positions the best-matching result was buried below rank 1. 0 means it was #1.",
        ge=0,
    )
    max_relevance_score: float = Field(
        description="Highest relevance score among all returned results.",
        ge=0.0,
        le=1.0,
    )
    top3_original_average: float = Field(
        description="Average relevance score of the top 3 results as originally ranked by the engine.",
        ge=0.0,
        le=1.0,
    )


class CapabilityScore(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    capability: CapabilityGroup = Field(description="The capability group being assessed.")
    severity: Severity = Field(
        description="Worst severity among all judgments in this capability group — if any query is CRITICAL, this is CRITICAL."
    )
    summary: str = Field(description="One-line summary of the capability's performance.")
    judgments: list[QueryJudgment] = Field(
        description="Individual query judgments that contribute to this capability score."
    )


class AuditReport(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    site_context: SiteContext = Field(description="Metadata about the site that was audited.")
    selected_categories: list[QueryCategory] = Field(
        description="Query categories chosen for this audit run."
    )
    queries: list[TestQuery] = Field(description="All test queries generated for this audit.")
    capability_scores: list[CapabilityScore] = Field(
        description="Scored assessment for each capability group tested."
    )
    deep_dive_narrative: str = Field(
        default="",
        description="Long-form narrative analysis of the audit findings, filled by the model.",
    )
    roadmap_narrative: str = Field(
        default="",
        description="Prioritised remediation roadmap narrative, filled by the model.",
    )
