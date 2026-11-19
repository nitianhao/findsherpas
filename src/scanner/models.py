"""Data models for the scanner.

Probe types are based on the approved failure modes from docs/search-failure-modes.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProbeType(str, Enum):
    """
    The fixed battery of deterministic probe types.
    
    Based on approved failure modes from docs/search-failure-modes.md:
    - F001-F009: Language and query interpretation
    - F018-F028: Intent and requirements
    - F041-F045: Retrieval and coverage
    - F056-F059: Ranking and result-set usefulness
    - F073: Autocomplete
    - F109: Recovery
    """
    
    # F041: Exact product name retrieval
    EXACT_PRODUCT_NAME = "exact_product_name"
    
    # F045: Category/filter navigation agreement
    CATEGORY_TERM = "category_term"
    
    # F002: Typo tolerance
    TYPO = "typo"
    
    # F001: Synonym handling
    SYNONYM = "synonym"
    
    # F003: Plural/singular/inflection
    PLURAL_SINGULAR = "plural_singular"
    
    # F007: Diacritics/special characters
    DIACRITICS = "diacritics"
    
    # F004: Formatting variants (USB-C vs USB C)
    FORMAT_VARIANT = "format_variant"
    
    # F005: Abbreviations (TV vs television)
    ABBREVIATION = "abbreviation"
    
    # Compound word handling (merged/split)
    COMPOUND_SPLIT = "compound_split"
    MERGED_WORDS = "merged_words"
    
    # F018/F022: Explicit requirements / combined constraints
    CONSTRAINT_QUERY = "constraint_query"
    
    # F019: Price limits
    PRICE_CONSTRAINT = "price_constraint"
    
    # F025: Brand intent
    BRAND_SEARCH = "brand_search"
    
    # F042: SKU/model number
    SKU_SEARCH = "sku_search"
    
    # F043: Coverage - enough matching products
    COVERAGE_CHECK = "coverage_check"
    
    # F056/F057: Ranking - accessories vs main product, buried matches
    RANKING_CHECK = "ranking_check"
    
    # Zero-result / gibberish detection
    ZERO_RESULT_CHECK = "zero_result_check"
    
    # Control query that must return results
    CONTROL_QUERY = "control_query"


# Maps probe types to the failure modes they test
PROBE_FAILURE_MODES = {
    ProbeType.EXACT_PRODUCT_NAME: ["F041"],
    ProbeType.CATEGORY_TERM: ["F045"],
    ProbeType.TYPO: ["F002"],
    ProbeType.SYNONYM: ["F001"],
    ProbeType.PLURAL_SINGULAR: ["F003"],
    ProbeType.DIACRITICS: ["F007"],
    ProbeType.FORMAT_VARIANT: ["F004"],
    ProbeType.ABBREVIATION: ["F005"],
    ProbeType.COMPOUND_SPLIT: ["F013"],
    ProbeType.MERGED_WORDS: ["F013"],
    ProbeType.CONSTRAINT_QUERY: ["F018", "F022"],
    ProbeType.PRICE_CONSTRAINT: ["F019"],
    ProbeType.BRAND_SEARCH: ["F025"],
    ProbeType.SKU_SEARCH: ["F042"],
    ProbeType.COVERAGE_CHECK: ["F043"],
    ProbeType.RANKING_CHECK: ["F056", "F057"],
    ProbeType.ZERO_RESULT_CHECK: ["F109"],
    ProbeType.CONTROL_QUERY: [],
}


class ProbeStatus(str, Enum):
    """Status of a probe execution.
    
    Maps to FetchStatus from src/audit/src/models.py but simplified for scanner use.
    """
    SUCCESS = "success"           # FetchStatus.OK or ZERO_CONFIRMED
    PARTIAL = "partial"           # FetchStatus.PARTIAL - extracted fewer than expected
    REDIRECT = "redirect"         # FetchStatus.REDIRECT - went to category/product page
    BLOCKED = "blocked"           # FetchStatus.BLOCKED - bot protection
    TIMEOUT = "timeout"           # FetchStatus.TIMEOUT
    ERROR = "error"               # FetchStatus.ERROR
    SKIPPED = "skipped"           # Probe was not run


class SearchResult(BaseModel):
    """A single search result from a probe."""
    rank: int = Field(description="1-indexed position")
    title: str = Field(description="Product/item title")
    price: Optional[str] = Field(default=None, description="Price string if found")
    url: Optional[str] = Field(default=None, description="Result URL")


class ProbeResult(BaseModel):
    """Result of executing a single probe."""
    probe_type: ProbeType
    query: str = Field(description="The search query submitted")
    control_query: Optional[str] = Field(default=None, description="Control query for comparison")
    status: ProbeStatus
    result_count: int = Field(default=0, description="Number of results returned")
    results: list[SearchResult] = Field(default_factory=list, description="Top results")
    control_count: Optional[int] = Field(default=None, description="Control query result count")
    screenshot_path: Optional[str] = Field(default=None, description="Path to screenshot")
    error_message: Optional[str] = Field(default=None)
    execution_time_ms: int = Field(default=0)
    rationale: str = Field(default="", description="Why this probe was run")


class ProbeScore(str, Enum):
    """Deterministic score for a probe result."""
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    BLOCKED = "blocked"
    ERROR = "error"


class ScoredProbe(BaseModel):
    """A probe result with its score."""
    probe: ProbeResult
    score: ProbeScore
    score_reason: str = Field(description="Why this score was assigned")


class CapabilityScore(BaseModel):
    """Score for a capability area based on probe results."""
    capability: str
    score: ProbeScore
    probes: list[ScoredProbe]
    summary: str


class SiteInfo(BaseModel):
    """Basic information about the scanned site."""
    domain: str
    site_name: str = Field(default="")
    search_url_template: str = Field(default="")
    primary_language: str = Field(default="English")
    vertical: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default=None)


class ScanResult(BaseModel):
    """Complete result of scanning a site."""
    site: SiteInfo
    scanned_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    probes: list[ScoredProbe] = Field(default_factory=list)
    capabilities: list[CapabilityScore] = Field(default_factory=list)
    overall_score: ProbeScore = Field(default=ProbeScore.ERROR)
    blocked: bool = Field(default=False, description="Whether the site blocked scanning")
    llm_cost_usd: float = Field(default=0.0, description="Cost of LLM calls for this scan")
    execution_time_ms: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)


class BatchStatus(BaseModel):
    """Status of a batch scan run."""
    total: int
    completed: int
    failed: int
    blocked: int
    current_domain: Optional[str] = Field(default=None)
    results_file: str
