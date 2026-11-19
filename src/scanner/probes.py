"""
Probe definitions for the search scanner.

Based on approved failure modes from docs/search-failure-modes.md:
- F001: Synonyms fail (couch vs sofa)
- F002: Typos fail (runing vs running)
- F003: Singular/plural/inflection changes results
- F004: Formatting variants fail (USB-C, USB C, USBC)
- F005: Abbreviations fail (TV vs television)
- F007: Diacritics prevent matching (cafe vs café)
- F018: Explicit requirements ignored
- F019: Price limits ignored
- F022: Combined requirements lose constraints
- F025: Brand intent ignored
- F041: Exact product name fails
- F042: SKU/model number fails
- F043: Too few matching products
- F045: Search/navigation disagree
- F056: Accessories outrank main product
- F057: Exact match buried

Each probe tests a specific capability with deterministic scoring.
LLM is used sparingly for generating site-specific queries from catalog data.
"""

from __future__ import annotations

import logging
import os
import random
import re
from typing import Optional

import anthropic

from .models import ProbeType, SiteInfo

logger = logging.getLogger(__name__)

_HAIKU_MODEL = os.environ.get("AUDIT_MODEL_FETCHER", "claude-haiku-4-5-20251001")


# Common typo patterns that can be applied to any word
TYPO_PATTERNS = [
    ("th", "ht"),  # the -> hte
    ("ie", "ei"),  # brief -> breif
    ("oo", "o"),   # boots -> bots
    ("ee", "e"),   # feet -> fet
    ("ll", "l"),   # small -> smal
    ("ss", "s"),   # dress -> dres
]


def generate_typo(word: str) -> str:
    """Generate a common typo for a word."""
    word_lower = word.lower()
    
    # Try pattern-based typos
    for orig, repl in TYPO_PATTERNS:
        if orig in word_lower:
            return word_lower.replace(orig, repl, 1)
    
    # Swap adjacent letters if word is long enough
    if len(word) > 4:
        pos = len(word) // 2
        return word[:pos] + word[pos+1] + word[pos] + word[pos+2:]
    
    # Double a letter
    if len(word) > 3:
        pos = len(word) // 2
        return word[:pos] + word[pos] + word[pos:]
    
    return word


def remove_diacritics(text: str) -> str:
    """Remove diacritics from text (e.g., café -> cafe)."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def to_plural(word: str) -> str:
    """Simple English pluralization."""
    if word.endswith('y') and len(word) > 2 and word[-2] not in 'aeiou':
        return word[:-1] + 'ies'
    if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
    return word + 's'


def to_singular(word: str) -> str:
    """Simple English singularization."""
    if word.endswith('ies') and len(word) > 4:
        return word[:-3] + 'y'
    if word.endswith('es') and len(word) > 3:
        base = word[:-2]
        if base.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return base
        return word[:-1]  # Just remove 's' for 'es' -> 'e' cases
    if word.endswith('s') and len(word) > 2:
        return word[:-1]
    return word


class ProbeGenerator:
    """Generates probe queries for a site."""
    
    def __init__(
        self,
        site_info: SiteInfo,
        nav_categories: list[str],
        featured_items: list[str],
        brands: list[str],
    ):
        self.site = site_info
        self.nav_categories = nav_categories
        self.featured_items = featured_items
        self.brands = brands
        self._client: Optional[anthropic.Anthropic] = None
        self.llm_cost_usd = 0.0
        self._rng = random.Random(0)
    
    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client
    
    def _pick_category(self) -> str:
        """Pick a category term from navigation."""
        if self.nav_categories:
            return self.nav_categories[0]
        return "shoes"  # Fallback
    
    def _pick_product(self) -> str:
        """Pick a product name from featured items."""
        if self.featured_items:
            return self.featured_items[0]
        return ""
    
    def _llm_pick_terms(self, prompt: str, count: int = 1) -> list[str]:
        """Use LLM to pick relevant terms from site context."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return []
        try:
            client = self._get_client()
            
            context = f"""Site: {self.site.site_name or self.site.domain}
Language: {self.site.primary_language}
Categories: {', '.join(self.nav_categories[:15])}
Products: {', '.join(self.featured_items[:15])}
Brands: {', '.join(self.brands[:10])}"""
            
            response = client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": f"""{context}

{prompt}

Return ONLY the term(s), one per line, no explanations. Return exactly {count} term(s)."""
                }],
            )
            
            # Track cost (Haiku is cheap)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            self.llm_cost_usd += (input_tokens * 1.0 + output_tokens * 5.0) / 1_000_000
            
            text = "\n".join(b.text for b in response.content if getattr(b, "type", "") == "text").strip()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            return lines[:count]
            
        except Exception as e:
            logger.warning("LLM term picking failed: %s", e)
            return []
    
    def generate_exact_product_name(self) -> tuple[str, str]:
        """Generate an exact product name query. Returns (query, rationale)."""
        if self.featured_items:
            # Try to get a clean product name
            product = self._pick_product()
            query = product
            return query, f"Testing exact match for product: {product}"
        
        # Fallback: use LLM to suggest a product
        terms = self._llm_pick_terms(
            "Pick ONE specific product name that likely exists on this site. "
            "Use the site's language. Just the product name, nothing else.",
            count=1
        )
        if terms:
            return terms[0], "LLM-suggested product name for exact match test"
        
        return "", "No product name available"
    
    def generate_category_term(self) -> tuple[str, str]:
        """Generate a category term query."""
        if self.nav_categories:
            category = self._pick_category()
            return category, f"Testing category search for: {category}"
        
        terms = self._llm_pick_terms(
            "Pick ONE product category term that fits this site. Use the site's language.",
            count=1
        )
        if terms:
            return terms[0], "LLM-suggested category term"
        
        return "", "No category available"
    
    def generate_typo_query(self, base_query: str) -> tuple[str, str, str]:
        """Generate a typo variant. Returns (typo_query, control_query, rationale)."""
        if not base_query:
            category = self._pick_category()
            base_query = category
        
        typo = generate_typo(base_query)
        return typo, base_query, f"Typo tolerance: '{typo}' (should match '{base_query}')"
    
    def generate_synonym_query(self) -> tuple[str, str, str]:
        """Generate a synonym test. Returns (synonym_query, control_query, rationale)."""
        # Use LLM to generate a synonym pair
        pairs = self._llm_pick_terms(
            "Generate ONE synonym pair for a product search on this site. "
            "Format: 'common_term -> synonym' (e.g., 'jacket -> coat'). "
            "Use terms relevant to this site's products.",
            count=1
        )
        
        if pairs and '->' in pairs[0]:
            parts = pairs[0].split('->')
            control = parts[0].strip()
            synonym = parts[1].strip()
            return synonym, control, f"Synonym test: '{synonym}' should match like '{control}'"
        
        return "", "", "Could not generate synonym pair"
    
    def generate_plural_singular(self, base_query: str) -> tuple[str, str, str]:
        """Generate plural/singular variant. Returns (variant_query, control_query, rationale)."""
        if not base_query:
            base_query = self._pick_category()
        
        if self.site.primary_language.lower() != "english":
            terms = self._llm_pick_terms(
                f"Return only the correct singular/plural variant of '{base_query}' in {self.site.primary_language}.", count=1)
            return (terms[0], base_query, "Locale-specific singular/plural variant") if terms else ("", "", "No locale variant available")
        words = base_query.split()
        if not words:
            return "", "", "No base query"
        
        # Find a noun to pluralize/singularize (usually last word)
        last_word = words[-1]
        
        if last_word.endswith('s'):
            variant_word = to_singular(last_word)
            direction = "singular"
        else:
            variant_word = to_plural(last_word)
            direction = "plural"
        
        words[-1] = variant_word
        variant_query = ' '.join(words)
        
        return variant_query, base_query, f"Plural/singular: '{variant_query}' ({direction} of '{base_query}')"
    
    def generate_diacritics_query(self) -> tuple[str, str, str]:
        """Generate diacritics test. Returns (ascii_query, diacritics_query, rationale)."""
        # Look for terms with diacritics in the site's vocabulary
        for item in self.featured_items + self.nav_categories + self.brands:
            normalized = remove_diacritics(item)
            if normalized != item:
                return normalized, item, f"Diacritics: '{normalized}' should match '{item}'"
        
        # Use LLM to suggest
        pairs = self._llm_pick_terms(
            "Find ONE term from this site that has accented characters (like é, ü, ø). "
            "Format: 'accented_term -> ascii_version' (e.g., 'café -> cafe').",
            count=1
        )
        
        if pairs and '->' in pairs[0]:
            parts = pairs[0].split('->')
            accented = parts[0].strip()
            ascii_ver = parts[1].strip()
            return ascii_ver, accented, f"Diacritics: '{ascii_ver}' should match '{accented}'"
        
        return "", "", "No diacritics terms found"
    
    def generate_compound_split(self) -> tuple[str, str, str]:
        """Generate compound word split test. Returns (split_query, compound_query, rationale)."""
        # Use LLM
        pairs = self._llm_pick_terms(
            "Find ONE compound word from this site that could be searched as two words. "
            "Format: 'compoundword -> compound word' (e.g., 'snowboard -> snow board').",
            count=1
        )
        
        if pairs and '->' in pairs[0]:
            parts = pairs[0].split('->')
            compound = parts[0].strip()
            split = parts[1].strip()
            return split, compound, f"Compound split: '{split}' should match '{compound}'"
        
        return "", "", "No compound words found"
    
    def generate_merged_words(self, base_query: str) -> tuple[str, str, str]:
        """Generate merged words test. Returns (merged_query, spaced_query, rationale)."""
        if not base_query or ' ' not in base_query:
            base_query = self._pick_category()
            if ' ' not in base_query:
                # Try to find a multi-word category
                multi_word = [c for c in self.nav_categories if ' ' in c]
                if multi_word:
                    base_query = self._rng.choice(multi_word)
        
        if ' ' not in base_query:
            return "", "", "No multi-word query available"
        
        merged = base_query.replace(' ', '')
        return merged, base_query, f"Merged words: '{merged}' should match '{base_query}'"
    
    def generate_constraint_query(self) -> tuple[str, str, str]:
        """Generate a constraint query (e.g., 'red jacket under 50'). Returns (constraint_query, base_query, rationale)."""
        base = self._pick_category()
        
        # Build constraint query
        constraints = []
        
        # Color constraint
        colors = ['red', 'blue', 'black', 'white', 'green']
        color = 'schwarz' if self.site.primary_language.lower() == 'german' else 'black'
        constraints.append(color)
        
        # Price constraint (site-language aware)
        lang = self.site.primary_language.lower()
        if lang in ('swedish', 'danish', 'norwegian'):
            price_phrase = 'under 500 kr'
        elif lang == 'german':
            price_phrase = 'unter 50 euro'
        elif lang == 'french':
            price_phrase = 'moins de 50 euros'
        else:
            price_phrase = 'under 50'
        
        constraint_query = f"{color} {base} {price_phrase}"
        return constraint_query, base, f"Constraint query: '{constraint_query}' should return relevant {base}"
    
    def generate_sku_search(self) -> tuple[str, str]:
        """Generate a SKU/model number search. Returns (sku_query, rationale)."""
        # Look for SKU-like strings in product names
        sku_pattern = re.compile(r'\b[A-Z]{1,3}[-]?\d{3,}[A-Z]?\b|\b\d{5,}\b')
        
        for item in self.featured_items:
            match = sku_pattern.search(item)
            if match:
                sku = match.group()
                return sku, f"SKU search: '{sku}' from product '{item}'"
        
        return "", "No SKU found"
    
    def generate_zero_result_check(self) -> tuple[str, str]:
        """Generate a query that should return zero results. Returns (query, rationale)."""
        # Use gibberish that won't match anything
        gibberish = "xyzqwk12345nonsense"
        return gibberish, f"Zero-result check: '{gibberish}' should return 0 results"
    
    def generate_control_query(self) -> tuple[str, str]:
        """Generate a control query that should definitely return results. Returns (query, rationale)."""
        # Use a known category
        if self.nav_categories:
            category = self.nav_categories[0]
            return category, f"Control query: '{category}' should return results"
        
        return "", "No control query available"


