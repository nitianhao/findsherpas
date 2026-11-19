"""Evidence contracts and the ten explicit pilot mode definitions."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

MODES = {
    'negation': 'Cup explicitly without a handle; do not infer from silence.',
    'either_or': 'Serving bowls in glass OR porcelain: one verified product in each branch.',
    'unit_conversion': 'Jug with explicit capacity; code converts L/cl/ml.',
    'dimension': 'Vase with explicit height and distinct diameter/width; retain axes.',
    'pack_capacity': 'Drinking glasses with explicit pack count and capacity PER GLASS.',
    'solid_material': 'Explicit solid-oak table plus explicit oak-veneer table contrast. Oak alone is insufficient.',
    'compatibility': 'Pan explicitly compatible with induction.',
    'combined_exclusions': 'Pan explicitly stainless steel AND explicitly without coating. PFAS-free alone is insufficient.',
    'specificity': 'Jug with explicit capacity AND material to add one correct attribute at a time.',
    'conditional_price': 'Pan member price <500 DKK but nonmember price >=500 DKK, plus another pan public price <500 DKK. Preserve eligibility.',
}
Mode = Literal['negation', 'either_or', 'unit_conversion', 'dimension', 'pack_capacity',
               'solid_material', 'compatibility', 'combined_exclusions', 'specificity', 'conditional_price']
Attribute = Literal['product_type', 'handle', 'material', 'capacity', 'pack_count', 'height',
                    'width', 'diameter', 'coating', 'induction', 'price_member', 'price_regular',
                    'price_public', 'availability', 'color']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Product(Strict):
    id: str
    name: str
    url: str
    text: str
    source_path: str = ''
    source_hash: str = ''
    captured_at: str = ''
    category_urls: list[str] = Field(default_factory=list)


class Fact(Strict):
    id: str = ''
    product_id: str
    attribute: Attribute
    value: str
    unit: str = ''
    quote: str = Field(min_length=3, max_length=600)
    normalized_value: str = ''
    normalized_unit: str = ''


class FactBatch(Strict):
    facts: list[Fact]


class Candidate(Strict):
    mode: Mode
    positive_ids: list[str]
    contrast_ids: list[str] = Field(default_factory=list)
    fact_ids: list[str]
    rationale: str


class CandidateBatch(Strict):
    candidates: list[Candidate]


class ReviewDecision(Strict):
    mode: Mode
    reason: str
    rejected_fact_ids: list[str] = Field(default_factory=list)
    approved: bool


class ReviewBatch(Strict):
    decisions: list[ReviewDecision]


class Link(Strict):
    id: str
    url: str
    text: str


class Selection(Strict):
    ids: list[str]
    reason: str
