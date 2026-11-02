from __future__ import annotations

import logging
import math
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from src import judge_kb
from src.category_selector import CATEGORY_DESCRIPTIONS
from src.llm_compat import LLMResponseError, structured_call
from src.models import (
    TRUSTED_FETCH_STATUSES,
    FailureMode,
    FetchOutcome,
    QueryJudgment,
    ScoredResult,
    Severity,
    TestQuery,
)

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Version of the judging rules (prompt + deterministic guards). Bump it whenever a rule changes
# a verdict. It is stamped on every KB record and on the run manifest, and KB retrieval only
# serves records judged under the CURRENT rules (or human-reviewed ones), so calibration
# examples graded under superseded rules can no longer drag new verdicts back.
JUDGE_RULES_VERSION = "2026-10-30"

# Overridable per-run; unset env = unchanged default. See docs/CASE_STUDY_PLAYBOOK.md.
# NOTE: every alternative judge model evaluated so far has SOFTENED critical calls —
# re-read JUDGE_PLAYBOOK.md severity calibration before trusting an overridden run.
_DEFAULT_MODEL = "claude-sonnet-4-6"
_MODEL = os.environ.get("AUDIT_MODEL_JUDGE", _DEFAULT_MODEL)

# Long German/Swedish evidence + internal observations fit comfortably; truncation raises
# LLMResponseError (retried once, then a flagged fallback), never a silent half-verdict.
_MAX_TOKENS = 3000
_TEMPERATURE = 0.2

_SEVERITY_MAP: dict[str, Severity] = {
    "CRITICAL": Severity.CRITICAL,
    "MODERATE": Severity.MODERATE,
    "MINOR": Severity.MINOR,
    "PASS": Severity.PASS,
}

# Ordinal severity ranking (higher = worse), for comparing verdicts.
_SEVERITY_RANK: dict[str, int] = {
    Severity.CRITICAL.value: 3,
    Severity.MODERATE.value: 2,
    Severity.MINOR.value: 1,
    Severity.PASS.value: 0,
}

_SEVERITY_EMOJI: dict[str, str] = {
    Severity.CRITICAL.value: "[X]",
    Severity.MODERATE.value: "[!]",
    Severity.MINOR.value: "[~]",
    Severity.PASS.value: "[OK]",
}

_FAILURE_MODE_DESCRIPTIONS: dict[str, str] = {
    "PARTIAL_KEYWORD_MATCH": (
        "The engine matched one or two words from the query but ignored the rest. Results "
        "relate to a word in the query, not to what the shopper wanted."
    ),
    "BRAND_BLEED": (
        "The query named a brand, but other brands appear. The engine matched the product "
        "type and ignored the brand."
    ),
    "CONSTRAINT_DROPPED": (
        "The query carried a constraint (price limit, exclusion, colour, size) that was "
        "ignored. Results match the topic but violate the constraint."
    ),
    "CATEGORY_MAPPING_FAILURE": (
        "The query used a generic/category term, but the engine only matched it as a keyword "
        "in titles instead of mapping it to the product category."
    ),
    "FACET_NOT_EXTRACTED": (
        "A word in the query is a filter value (colour, size, material, price) but the engine "
        "treated it as a keyword to find in titles."
    ),
    "NO_FUZZY_MATCHING": (
        "The query has a typo or a broken/merged word and the engine did not correct it. "
        "Results are empty or unrelated."
    ),
    "NO_SEMANTIC_UNDERSTANDING": (
        "The query describes what the shopper wants conceptually, but the engine only matches "
        "literal keywords."
    ),
    "POOR_RANKING": (
        "Relevant results exist in the set, but they are buried below irrelevant ones."
    ),
    "DUPLICATE_FLOODING": (
        "The same product model fills several slots as separate colour/size cards, crowding "
        "out distinct products. (Detected automatically from the results.)"
    ),
    "ZERO_RESULTS_OR_GARBAGE": (
        "The engine returned nothing useful — zero results or completely unrelated items."
    ),
    "OTHER": "None of the above fit. Describe what you observed.",
}


def _val(v) -> str:
    """Enum value or the string itself (models use use_enum_values=True)."""
    return v.value if hasattr(v, "value") else str(v)


def _sev_rank(sev) -> int:
    return _SEVERITY_RANK.get(_val(sev), 0)


def _sev_short(sev) -> str:
    v = _val(sev)
    for short, full in _SEVERITY_MAP.items():
        if full.value == v:
            return short
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Unicode-aware text helpers
# ---------------------------------------------------------------------------
#
# Every deterministic guard compares query words with title words. They used to tokenise
# with [a-z]+, which split "kök"/"skål"/"Größe" into fragments and silently disabled the
# guards on every non-English audit. All matching now goes through _fold (casefold + NFKD,
# diacritics stripped, ø/æ/œ/ł transliterated) and _tokens ([^\W_]+ on the folded text).

_FOLD_EXTRA = str.maketrans({"ø": "o", "æ": "ae", "œ": "oe", "ð": "d", "þ": "th", "ł": "l",
                             "đ": "d", "ı": "i"})
_WORD_RE = re.compile(r"[^\W_]+")


def _fold(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.translate(_FOLD_EXTRA)


def _tokens(s: str | None) -> list[str]:
    return _WORD_RE.findall(_fold(s))


def _norm_query(q: str) -> str:
    return " ".join(_fold(q).split())


# Inflection endings tolerated between two forms of the same word (EN/DE/Scandinavian/NL
# plurals and definite forms): hose/hosen, skål/skålar, teacher/teachers, box/boxes.
_INFLECTION_SUFFIXES = {
    "", "s", "es", "e", "n", "en", "er", "ern", "ar", "or", "na", "ne", "arna", "erna", "orna",
    "et", "a", "r", "nen", "ers",
}


def _stem(t: str) -> str:
    """Light singular/plural stem (kept for scripts that import it)."""
    if len(t) > 4 and t.endswith("es") and t[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return t[:-2]
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def _token_match(a: str, b: str) -> bool:
    """Same word up to an inflection ending (hose/hosen, candle/candles, skålen/skålar).

    Deliberately NOT prefix-based: prefix matching gave false hits like 'studio'≈'stud'.
    Both words share a stem of >= 3 characters and each remainder is a known ending.
    """
    a, b = _fold(a), _fold(b)
    if a == b:
        return True
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    if n < 3:
        return False
    return a[n:] in _INFLECTION_SUFFIXES and b[n:] in _INFLECTION_SUFFIXES


# Privative endings: a compound with one of these says the item does NOT contain the head
# word ("laceless", "lederfrei", "parfymfri"), so it must never count as an exclusion breach.
_PRIVATIVE_ENDINGS = ("less", "los", "lose", "loser", "loses", "frei", "freie", "freier", "freies",
                      "fri", "fritt", "frit", "frie", "free", "vrij")


def _compound_contains(token: str, part: str) -> bool:
    """True when ``token`` is a compound built on ``part`` (Lederjacke ⊃ leder, Kunstleder ⊃ leder).

    Requires part >= 4 chars and a remainder >= 3 chars, so short words never match by accident.
    """
    if len(part) < 4 or len(token) < len(part) + 3:
        return False
    return token.startswith(part) or token.endswith(part)


def _is_privative(token: str) -> bool:
    return token.endswith(_PRIVATIVE_ENDINGS)


# Generic words that never identify a product (multilingual).
_STOPWORDS = {
    # en
    "gift", "gifts", "gifting", "ideas", "idea", "shop", "all", "new", "the", "for", "and", "of",
    "to", "a", "an", "by", "your", "our", "best", "sale", "with", "in", "on", "my", "me", "i",
    "something", "that", "who", "is", "are", "under", "over", "set",
    # de
    "und", "oder", "fur", "mit", "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
    "im", "zum", "zur", "von", "bis", "unter", "uber", "neu", "geschenk", "geschenke", "ideen",
    "fuer",
    # sv / da / no
    "och", "med", "till", "en", "ett", "pa", "av", "det", "som", "jag", "ny", "nya", "og", "til",
    "af", "et", "som", "presenter", "present",
    # nl / fr
    "voor", "het", "een", "van", "tot", "onder", "pour", "avec", "le", "la", "les", "de", "du",
    "un", "une", "et",
}

# Negation / exclusion words. A word after one of these is what the shopper wants excluded.
_NEGATION_WORDS = {
    "not", "without", "no", "non", "excluding", "except", "minus",
    "nicht", "ohne", "kein", "keine", "keinen", "keiner", "keines", "ausser",
    "utan", "inte", "ej", "ingen", "inga",
    "uden", "ikke", "uten",
    "zonder", "geen", "niet",
    "sans", "pas",
    "sin", "senza", "bez",
}
_STOPWORDS |= _NEGATION_WORDS

# "X free" / "X-frei" postfix exclusions.
_FREE_WORDS = {"free", "frei", "fri", "fritt", "frie", "vrij"}


def _sig_tokens(s: str, min_len: int = 3) -> list[str]:
    """Distinctive tokens: >= min_len chars, not a stopword, not a pure number."""
    return [t for t in _tokens(s) if len(t) >= min_len and t not in _STOPWORDS and not t.isdigit()]


def _phrase_in(phrase: list[str], tokens: list[str]) -> bool:
    n = len(phrase)
    if not n:
        return False
    return any(tokens[i:i + n] == phrase for i in range(len(tokens) - n + 1))


def _title_matches(cited: str, actual: str) -> bool:
    """Fuzzy title identity: one folded token set (nearly) contains the other."""
    a, b = set(_tokens(cited)), set(_tokens(actual))
    if not a or not b:
        return False
    inter = len(a & b)
    return inter / min(len(a), len(b)) >= 0.8


# ---------------------------------------------------------------------------
# Deterministic stats
# ---------------------------------------------------------------------------

# Minimum relevance gap between the best available result and the result the customer
# actually saw first for a misordering to count as a real, visible failure. Below it every
# top result is of near-equal relevance and the positional "displacement" is cosmetic.
MATERIAL_RANK_GAP = 0.20

# Relevance below which the customer's FIRST result counts as off-topic. A buried better
# match is only a CRITICAL ranking failure when the customer's original #1 is below it.
# Calibrated against product-search rerank scores where < ~0.30 means off-topic and
# 0.30-0.65 spans on-topic-but-modestly-scored category results.
ON_TOPIC_TOP1_FLOOR = 0.30

# A result set whose BEST result scores below this is garbage, not "near-equal good": the
# ranking caps never ease it (scores cluster because every item is irrelevant).
WEAK_SET_MAX = 0.25

# A result set whose BEST result scores below this is uniformly weak (weak-filler guard).
MIN_RELEVANT_TOP = 0.45


def _organic(results: list[ScoredResult]) -> list[ScoredResult]:
    """Results minus sponsored placements (ads are outside the engine's organic ranking).

    Falls back to the full list when every tile is sponsored, so a page of ads is still judged.
    """
    org = [r for r in results if not getattr(r, "sponsored", False)]
    return org or list(results)


def _compute_stats(results: list[ScoredResult]) -> tuple[float, float, int]:
    """(max_relevance, top3_original_average, displacement) over ORGANIC results.

    Zero results give displacement 0: there is no buried result to displace, and the old
    "15" made the prompt claim the best result sat at original rank #16.
    """
    results = _organic(results)
    if not results:
        return 0.0, 0.0, 0
    max_relevance = max(r.relevance_score for r in results)
    by_original = sorted(results, key=lambda r: r.original_rank)
    top3 = by_original[:3]
    top3_avg = sum(r.relevance_score for r in top3) / len(top3)
    best = max(results, key=lambda r: r.relevance_score)
    # Displacement counts organic slots above the best result (ads above it don't count).
    displacement = by_original.index(best)
    return max_relevance, top3_avg, displacement


def _top1_seen_relevance(results: list[ScoredResult]) -> float:
    """Relevance of the first ORGANIC result the customer saw."""
    results = _organic(results)
    if not results:
        return 0.0
    return min(results, key=lambda r: r.original_rank).relevance_score


def _relevance_gap(results: list[ScoredResult]) -> float:
    results = _organic(results)
    if not results:
        return 0.0
    return round(max(r.relevance_score for r in results) - _top1_seen_relevance(results), 6)


def _is_weak_set(results: list[ScoredResult]) -> bool:
    results = _organic(results)
    return bool(results) and max(r.relevance_score for r in results) < WEAK_SET_MAX


def _displacement_is_cosmetic(results: list[ScoredResult]) -> bool:
    """True when reordering would NOT materially change what the shopper sees.

    Requires ALL of: the best result is within MATERIAL_RANK_GAP of the customer's #1, the
    customer's #1 is itself on-topic (>= ON_TOPIC_TOP1_FLOOR), and the set is not garbage
    (max >= WEAK_SET_MAX). The gap alone is not enough: top1=0.05 / best=0.22 has a small gap
    because EVERYTHING is off-topic — easing that to MINOR/PASS turned garbage into a pass.
    """
    results = _organic(results)
    if not results or _is_weak_set(results):
        return False
    return (_relevance_gap(results) < MATERIAL_RANK_GAP
            and _top1_seen_relevance(results) >= ON_TOPIC_TOP1_FLOOR)


def _ranking_materially_broken(results: list[ScoredResult]) -> bool:
    """True when a misordering is CRITICAL-eligible: material gap AND an off-topic first result."""
    results = _organic(results)
    if not results:
        return False
    gap_material = _relevance_gap(results) >= MATERIAL_RANK_GAP
    first_result_weak = _top1_seen_relevance(results) < ON_TOPIC_TOP1_FLOOR
    return gap_material and first_result_weak


# A single product model occupying this many result slots constitutes variant flooding. At
# the high threshold — or when distinct products fall to the unique-ratio floor — it is MODERATE.
_FLOOD_MIN_COUNT = 3
_FLOOD_HIGH_COUNT = 5
_FLOOD_UNIQUE_RATIO = 0.40

# Relevance at/below which a result is treated as OFF-CATEGORY for the query.
_OFF_CATEGORY_REL = 0.30


def _flooding_stats(results: list[ScoredResult]) -> dict | None:
    """Variant-flooding stats over organic results, counted by product title."""
    titles = [(r.title or "").strip() for r in _organic(results) if (r.title or "").strip()]
    if not titles:
        return None
    counts = Counter(titles)
    top_title, top_count = counts.most_common(1)[0]
    return {"total": len(titles), "unique": len(counts), "top_title": top_title, "top_count": top_count}


def _flooding_severity(stats: dict | None) -> Severity | None:
    if not stats or stats["total"] < 4:
        return None
    ratio = stats["unique"] / stats["total"]
    if stats["top_count"] >= _FLOOD_HIGH_COUNT or ratio <= _FLOOD_UNIQUE_RATIO:
        return Severity.MODERATE
    if stats["top_count"] >= _FLOOD_MIN_COUNT:
        return Severity.MINOR
    return None


# ---------------------------------------------------------------------------
# Colour / material lexicons (per ISO-639-1 language)
# ---------------------------------------------------------------------------
# Keys are FOLDED forms (blå -> bla, rød -> rod, weiß -> weiss). Lexicons are language-scoped:
# English + the audit language only, so Swedish "rod" (röd) never fires on an English
# "fishing rod". Unknown language = all lexicons.

_COLOURS: dict[str, dict[str, str]] = {
    "en": {"black": "black", "white": "white", "navy": "navy", "blue": "blue", "red": "red",
           "green": "green", "olive": "olive", "grey": "grey", "gray": "grey", "brown": "brown",
           "tan": "tan", "beige": "beige", "khaki": "khaki", "orange": "orange", "yellow": "yellow",
           "purple": "purple", "pink": "pink", "burgundy": "burgundy", "cream": "cream",
           "charcoal": "grey", "camel": "camel", "rust": "rust", "teal": "teal", "maroon": "burgundy",
           "gold": "gold", "silver": "silver", "ivory": "cream", "turquoise": "teal"},
    "de": {"schwarz": "black", "weiss": "white", "blau": "blue", "marineblau": "navy",
           "dunkelblau": "navy", "navy": "navy", "rot": "red", "grun": "green", "oliv": "olive",
           "grau": "grey", "anthrazit": "grey", "braun": "brown", "beige": "beige", "khaki": "khaki",
           "orange": "orange", "gelb": "yellow", "lila": "purple", "violett": "purple", "rosa": "pink",
           "pink": "pink", "bordeaux": "burgundy", "weinrot": "burgundy", "creme": "cream",
           "gold": "gold", "silber": "silver", "turkis": "teal", "petrol": "teal"},
    "sv": {"svart": "black", "vit": "white", "bla": "blue", "marinbla": "navy", "rod": "red",
           "gron": "green", "oliv": "olive", "gra": "grey", "brun": "brown", "beige": "beige",
           "orange": "orange", "gul": "yellow", "lila": "purple", "rosa": "pink", "vinrod": "burgundy",
           "guld": "gold", "silver": "silver", "turkos": "teal"},
    "da": {"sort": "black", "hvid": "white", "bla": "blue", "marinebla": "navy", "rod": "red",
           "gron": "green", "oliven": "olive", "gra": "grey", "brun": "brown", "beige": "beige",
           "orange": "orange", "gul": "yellow", "lilla": "purple", "rosa": "pink",
           "bordeaux": "burgundy", "guld": "gold", "solv": "silver"},
    "no": {"svart": "black", "hvit": "white", "bla": "blue", "marinebla": "navy", "rod": "red",
           "gronn": "green", "gra": "grey", "brun": "brown", "beige": "beige", "oransje": "orange",
           "gul": "yellow", "lilla": "purple", "rosa": "pink", "gull": "gold", "solv": "silver"},
    "nl": {"zwart": "black", "wit": "white", "blauw": "blue", "marineblauw": "navy", "rood": "red",
           "groen": "green", "olijf": "olive", "grijs": "grey", "bruin": "brown", "beige": "beige",
           "oranje": "orange", "geel": "yellow", "paars": "purple", "roze": "pink",
           "bordeaux": "burgundy", "goud": "gold", "zilver": "silver"},
    "fr": {"noir": "black", "noire": "black", "blanc": "white", "blanche": "white", "bleu": "blue",
           "marine": "navy", "rouge": "red", "vert": "green", "verte": "green", "gris": "grey",
           "grise": "grey", "marron": "brown", "beige": "beige", "jaune": "yellow",
           "violet": "purple", "rose": "pink", "bordeaux": "burgundy", "argent": "silver"},
}

_MATERIALS: dict[str, dict[str, str]] = {
    "en": {"leather": "leather", "suede": "suede", "wool": "wool", "woollen": "wool",
           "woolen": "wool", "merino": "wool", "lambswool": "wool", "fairisle": "wool",
           "cashmere": "cashmere", "cotton": "cotton", "linen": "linen", "canvas": "canvas",
           "denim": "denim", "fleece": "fleece", "nylon": "nylon", "polyester": "polyester",
           "silk": "silk", "corduroy": "corduroy", "flannel": "flannel", "down": "down",
           "synthetic": "synthetic", "ceramic": "ceramic", "porcelain": "ceramic",
           "stoneware": "ceramic", "stainless": "stainless", "wood": "wood", "wooden": "wood",
           "glass": "glass", "rubber": "rubber", "waterproof": "waterproof", "gtx": "waterproof",
           "goretex": "waterproof"},
    "de": {"leder": "leather", "wildleder": "suede", "veloursleder": "suede", "wolle": "wool",
           "woll": "wool", "schurwolle": "wool", "merinowolle": "wool", "kaschmir": "cashmere",
           "baumwolle": "cotton", "leinen": "linen", "daunen": "down", "daune": "down",
           "seide": "silk", "keramik": "ceramic", "porzellan": "ceramic", "steingut": "ceramic",
           "edelstahl": "stainless", "holz": "wood", "glas": "glass", "gummi": "rubber",
           "wasserdicht": "waterproof", "cord": "corduroy", "fleece": "fleece"},
    "sv": {"lader": "leather", "skinn": "leather", "mocka": "suede", "ull": "wool",
           "merinoull": "wool", "kashmir": "cashmere", "bomull": "cotton", "linne": "linen",
           "dun": "down", "siden": "silk", "keramik": "ceramic", "porslin": "ceramic",
           "stengods": "ceramic", "rostfritt": "stainless", "tra": "wood", "glas": "glass",
           "gummi": "rubber", "vattentat": "waterproof", "fleece": "fleece"},
    "da": {"laeder": "leather", "skind": "leather", "ruskind": "suede", "uld": "wool",
           "merinould": "wool", "kashmir": "cashmere", "bomuld": "cotton", "hor": "linen",
           "dun": "down", "silke": "silk", "keramik": "ceramic", "porcelaen": "ceramic",
           "stentoj": "ceramic", "rustfri": "stainless", "trae": "wood", "glas": "glass",
           "gummi": "rubber", "vandtaet": "waterproof", "fleece": "fleece"},
    "no": {"skinn": "leather", "lær": "leather", "laer": "leather", "semsket": "suede",
           "ull": "wool", "bomull": "cotton", "lin": "linen", "dun": "down", "silke": "silk",
           "keramikk": "ceramic", "porselen": "ceramic", "rustfritt": "stainless",
           "glass": "glass", "gummi": "rubber", "vanntett": "waterproof", "fleece": "fleece"},
    "nl": {"leer": "leather", "leren": "leather", "suede": "suede", "wol": "wool",
           "wollen": "wool", "kasjmier": "cashmere", "katoen": "cotton", "linnen": "linen",
           "dons": "down", "zijde": "silk", "keramiek": "ceramic", "porselein": "ceramic",
           "rvs": "stainless", "hout": "wood", "houten": "wood", "glas": "glass",
           "rubber": "rubber", "waterdicht": "waterproof", "fleece": "fleece"},
    "fr": {"cuir": "leather", "daim": "suede", "laine": "wool", "cachemire": "cashmere",
           "coton": "cotton", "lin": "linen", "soie": "silk", "duvet": "down",
           "ceramique": "ceramic", "porcelaine": "ceramic", "verre": "glass", "bois": "wood",
           "impermeable": "waterproof", "polaire": "fleece"},
}

# Languages that build compounds (Lederjacke, Wollmütze, ullsockor): material/colour words may
# appear as the head or tail of a longer token there. English never compounds this way, and
# prefix matching there gave false hits ("downhill" ≠ down).
_COMPOUNDING = {"de", "sv", "da", "no", "nl"}
_COLOUR_FAMILY = {"navy": "blue", "teal": "blue", "burgundy": "red", "olive": "green",
                  "charcoal": "grey", "cream": "white", "ivory": "white", "camel": "brown",
                  "tan": "brown", "khaki": "green"}
_ADJ_ENDINGS = ("en", "er", "es", "em", "tt", "e", "a", "t", "s")
_SHADE_PREFIXES = ("hell", "dunkel", "ljus", "mork", "lys", "licht", "donker")


def _lang(language: str | None) -> str | None:
    if not language:
        return None
    try:
        return judge_kb.normalize_language(language)
    except Exception:  # noqa: BLE001
        return None


def _lexicon(kind: str, language: str | None) -> tuple[dict[str, str], set[str]]:
    """(word -> canonical, words allowed to match inside compounds)."""
    table = _COLOURS if kind == "colour" else _MATERIALS
    code = _lang(language)
    if code and code in table:
        merged = {**table["en"], **table[code]}
        return merged, (set(table[code]) if code in _COMPOUNDING else set())
    merged: dict[str, str] = {}
    for lex in table.values():
        merged.update(lex)
    compound = {w for c, lex in table.items() if c in _COMPOUNDING for w in lex}
    return merged, compound


def _lookup(token: str, lex: dict[str, str], compound_words: set[str], kind: str) -> str | None:
    if token in lex:
        return lex[token]
    for suf in _ADJ_ENDINGS:
        if token.endswith(suf) and len(token) - len(suf) >= 3 and token[: -len(suf)] in lex:
            return lex[token[: -len(suf)]]
    if compound_words:
        for word in compound_words:
            canon = lex[word]
            min_len = 3 if (kind == "material" and word == "ull") else 4
            if len(word) < min_len:
                if kind == "colour" and any(token == p + word for p in _SHADE_PREFIXES):
                    return canon
                continue
            if _compound_contains(token, word):
                return canon
    return None


def _attr_values(text: str, kind: str, language: str | None) -> set[str]:
    """Canonical colour or material values mentioned in ``text`` (synonym-aware)."""
    lex, compound_words = _lexicon(kind, language)
    toks = _tokens(text)
    forms = list(toks) + [a + b for a, b in zip(toks, toks[1:])]  # gore tex -> goretex
    out: set[str] = set()
    for t in forms:
        canon = _lookup(t, lex, compound_words, kind)
        if canon:
            out.add(canon)
    return out


def _colours_compatible(a: str, b: str) -> bool:
    return a == b or _COLOUR_FAMILY.get(a) == b or _COLOUR_FAMILY.get(b) == a


def _query_attr_text(tq: TestQuery) -> str:
    attrs = list((tq.constraints.attributes if tq.constraints else None) or [])
    return " ".join([tq.query] + attrs)


def _unverifiable_constraint_token(query, results: list[ScoredResult], language: str | None = None) -> str | None:
    """A colour/material constraint value that appears (as any synonym) in NO result title.

    ``query`` may be a TestQuery (its constraints.attributes are used too) or a string. The
    judge only sees titles, so such a constraint cannot be confirmed — route it to a human.
    """
    results = _organic(results)
    if not results:
        return None
    text = _query_attr_text(query) if isinstance(query, TestQuery) else str(query)
    titles = " | ".join(r.title or "" for r in results)
    for kind in ("colour", "material"):
        wanted = _attr_values(text, kind, language)
        if not wanted:
            continue
        seen = _attr_values(titles, kind, language)
        for w in sorted(wanted):
            if kind == "colour":
                if not any(_colours_compatible(w, s) for s in seen):
                    return w
            elif w not in seen:
                return w
    return None


def _colour_violations(tq: TestQuery, results: list[ScoredResult], language: str | None) -> list[ScoredResult]:
    """Organic results whose title names a DIFFERENT colour than the single colour the query asks for."""
    wanted = _attr_values(_query_attr_text(tq), "colour", language)
    if len(wanted) != 1:
        return []
    w = next(iter(wanted))
    out = []
    for r in _organic(results):
        cols = _attr_values(r.title or "", "colour", language)
        if cols and not any(_colours_compatible(w, c) for c in cols):
            out.append(r)
    return out


def _attribute_coverage(tq: TestQuery, results: list[ScoredResult], language: str | None) -> tuple[int, int, int]:
    """(titles confirming every requested colour/material, titles naming a conflicting value, organic total).

    Titles that name no value of the attribute count as neither (title-invisible).
    Returns (0, 0, total) when the query asks for no colour/material.
    """
    org = _organic(results)
    wanted = {k: _attr_values(_query_attr_text(tq), k, language) for k in ("colour", "material")}
    if not any(wanted.values()):
        return 0, 0, len(org)
    confirmed = conflicting = 0
    for r in org:
        ok, bad = True, False
        for kind, want in wanted.items():
            if not want:
                continue
            have = _attr_values(r.title or "", kind, language)
            match = all(any(_colours_compatible(w, h) for h in have) if kind == "colour" else w in have for w in want)
            if not match:
                ok = False
                if have:
                    bad = True
        confirmed += ok
        conflicting += bad
    return confirmed, conflicting, len(org)


# ---------------------------------------------------------------------------
# Price parsing / price constraints
# ---------------------------------------------------------------------------

_PRICE_NUM_RE = re.compile(r"\d{1,3}(?:[ .,  '’]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?")


def _parse_number(raw: str) -> float | None:
    s = raw.replace(" ", " ").replace(" ", " ").replace("’", "'")
    s = s.replace(" ", "").replace("'", "")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        head, _, tail = s.rpartition(sep)
        if len(tail) == 3 and s.count(sep) >= 1 and head:
            s = s.replace(sep, "")           # 1.299 / 1,299 -> thousands
        else:
            s = s.replace(sep, ".")          # 29,99 / 29.99 -> decimal
    try:
        return float(s)
    except ValueError:
        return None


def parse_price(text: str | None) -> float | None:
    """Lowest amount in a displayed price string ('1.299,00 €', 'kr 499', '£45', '499:-').

    Strings like '€99.50 €129.00' (sale + was) return the lower, payable amount. None when no
    number is present.
    """
    if not text:
        return None
    t = re.sub(r"(\d)[.,]-", r"\1", str(text))  # 499,- / 49.-
    vals = [v for v in (_parse_number(m.group(0)) for m in _PRICE_NUM_RE.finditer(t)) if v is not None]
    vals = [v for v in vals if v > 0]
    return min(vals) if vals else None


_CEILING_WORDS = (r"under|below|less than|up to|max(?:imum)?|unter|bis|hochstens|maximal|hogst|"
                  r"upp till|op til|hojst|maks|onder|tot|minder dan|moins de|jusqu a|sous|cheaper than")
_FLOOR_WORDS = r"over|above|more than|from|uber|ab|mehr als|ovan|fra|vanaf|meer dan|plus de|des"
_CURRENCY = r"(?:€|eur|euro|euros|£|gbp|\$|usd|kr|sek|dkk|nok|chf|fr|:-)?"


def _price_bounds(tq: TestQuery) -> tuple[float | None, float | None]:
    """(price_min, price_max): TestQuery.constraints first, else parsed from a PRICE_ANCHORED query."""
    c = tq.constraints
    if c and (c.price_max is not None or c.price_min is not None):
        return c.price_min, c.price_max
    if _val(tq.category) != "PRICE_ANCHORED":
        return None, None
    q = _fold(tq.query)
    hi = re.search(rf"\b(?:{_CEILING_WORDS})\s*{_CURRENCY}\s*(\d[\d .,']*)", q)
    lo = re.search(rf"\b(?:{_FLOOR_WORDS})\s*{_CURRENCY}\s*(\d[\d .,']*)", q)
    return (parse_price(lo.group(1)) if lo else None), (parse_price(hi.group(1)) if hi else None)


def _price_violations(tq: TestQuery, results: list[ScoredResult]) -> tuple[list[ScoredResult], int, str | None]:
    """(violating organic results, results with a parseable price, human bound label)."""
    lo, hi = _price_bounds(tq)
    if lo is None and hi is None:
        return [], 0, None
    priced = [(r, parse_price(r.price)) for r in _organic(results)]
    priced = [(r, p) for r, p in priced if p is not None]
    bad = []
    for r, p in priced:
        if hi is not None and p > hi * 1.005:
            bad.append(r)
        elif lo is not None and p < lo * 0.995:
            bad.append(r)
    label = (f"under {hi:g}" if hi is not None else "") + (" and " if hi is not None and lo is not None else "") \
        + (f"over {lo:g}" if lo is not None else "")
    return bad, len(priced), label


# ---------------------------------------------------------------------------
# Exclusions (NEGATIVE_INTENT)
# ---------------------------------------------------------------------------

# Category -> sub-type product nouns (folded). A category-level exclusion ("not jewellery")
# evades a title check because products are titled by sub-type ("Bracelet", "Necklace").
_CATEGORY_SUBTYPES: dict[str, set[str]] = {
    "jewellery": {"bracelet", "earring", "necklace", "pendant", "ring", "brooch", "anklet", "charm", "bangle", "cufflink"},
    "jewelry": {"bracelet", "earring", "necklace", "pendant", "ring", "brooch", "anklet", "charm", "bangle", "cufflink"},
    "schmuck": {"armband", "ohrring", "ohrringe", "halskette", "kette", "anhanger", "ring", "brosche"},
    "smycken": {"armband", "orhange", "orhangen", "halsband", "ring", "berlock"},
    "knitwear": {"jumper", "sweater", "cardigan", "pullover", "knit"},
    "footwear": {"shoe", "boot", "sneaker", "trainer", "sandal", "slipper", "loafer", "heel"},
}


def _excluded_terms(query) -> list[list[str]]:
    """Excluded term(s) as token lists. TestQuery.constraints.exclude wins when present.

    Parses multilingual negation (not/without/no, ohne/nicht/kein(e), utan/inte/ej,
    uden/ikke/uten, zonder/geen, sans, …) and postfix forms ("fragrance free", "parfymfri").
    """
    if isinstance(query, TestQuery):
        if query.constraints and query.constraints.exclude:
            return [t for t in (_sig_tokens(e, 2) or _tokens(e) for e in query.constraints.exclude) if t]
        query = query.query
    toks = _tokens(query)
    for i, t in enumerate(toks):
        if t in _NEGATION_WORDS and i + 1 < len(toks):
            rest = [x for x in toks[i + 1:] if x not in _STOPWORDS and len(x) >= 2]
            if rest:
                return [rest]
    out: list[list[str]] = []
    for i, t in enumerate(toks):
        if t in _FREE_WORDS and i > 0:
            out.append([toks[i - 1]])
        else:
            for suf in ("fritt", "frei", "fri", "free"):
                if t.endswith(suf) and len(t) - len(suf) >= 4:
                    out.append([t[: -len(suf)]])
                    break
    return out


def _excluded_term(query) -> str | None:
    """First excluded phrase, e.g. 'Tasche nicht Leder' -> 'leder' (kept for callers)."""
    terms = _excluded_terms(query)
    return " ".join(terms[0]) if terms else None


def _mentions_excluded(title: str, terms: list[str], subtypes: set[str], compounding: bool = True) -> bool:
    """Whole-word / compound-head match of an excluded word, ignoring negated mentions.

    "laceless" does not violate "without laces", "lederfrei" does not violate "ohne Leder",
    "Shampoo perfume free" does not violate "not perfume"; "Faux Leather" and "Lederjacke" do.
    """
    toks = _tokens(title)
    for i, tok in enumerate(toks):
        prev_neg = i > 0 and toks[i - 1] in _NEGATION_WORDS
        next_free = i + 1 < len(toks) and toks[i + 1] in _FREE_WORDS | {"less"}
        hit = False
        for e in terms:
            if len(e) < 3:
                continue
            if _token_match(tok, e):
                hit = True
            elif _is_privative(tok):
                continue
            elif compounding and (_compound_contains(tok, e) or any(
                _compound_contains(tok, e[: len(e) - len(s)]) for s in ("es", "s", "en", "e", "n")
                if e.endswith(s) and len(e) - len(s) >= 4
            )):
                hit = True
        if not hit and subtypes and any(_token_match(tok, st) for st in subtypes):
            hit = True
        if hit and not (prev_neg or next_free):
            return True
    return False


def _exclusion_violations(query, results: list[ScoredResult], site_categories: list[str] | None = None,
                          language: str | None = None) -> tuple[float | None, list[ScoredResult], str | None]:
    """(fraction violating, violating organic results, excluded phrase) for an exclusion query.

    Compound matching (Lederjacke violates "ohne Leder") is used for compounding languages and
    when the language is unknown; English matches whole words only ("Woolrich" ≠ wool).
    """
    terms_list = _excluded_terms(query)
    org = _organic(results)
    if not terms_list or not org:
        return None, [], None
    terms = [t for tl in terms_list for t in tl]
    subtypes: set[str] = set()
    cat_tokens = {ct for cat in (site_categories or []) for ct in _tokens(cat)}
    for tok in terms:
        st = _CATEGORY_SUBTYPES.get(tok)
        if not st:
            continue
        if site_categories and not any(_token_match(tok, ct) for ct in cat_tokens):
            continue
        subtypes |= st
    code = _lang(language)
    compounding = code is None or code in _COMPOUNDING
    # Synonym-aware: "not waterproof" is violated by "GTX"/"Gore-Tex", "ohne Wolle" by "Merino".
    phrase = " ".join(terms)
    excl_attr = {k: _attr_values(phrase, k, language) for k in ("material", "colour")}

    def violates(title: str) -> bool:
        if _mentions_excluded(title, terms, subtypes, compounding):
            return True
        if any(_NEGATION_WORDS & set(_tokens(title))) or any(_is_privative(t) for t in _tokens(title)):
            return False
        return any(excl_attr[k] & _attr_values(title, k, language) for k in excl_attr)

    bad = [r for r in org if violates(r.title or "")]
    return len(bad) / len(org), bad, " ".join(terms_list[0])


def _exclusion_violation_fraction(query, results: list[ScoredResult], site_categories: list[str] | None = None) -> float | None:
    return _exclusion_violations(query, results, site_categories)[0]


# ---------------------------------------------------------------------------
# Brand / category / core-term helpers
# ---------------------------------------------------------------------------

_BRAND_QUERY_TRAILING_NOUNS = {
    "dress", "dresses", "top", "tops", "coat", "coats", "jacket", "jackets",
    "scarf", "scarves", "bag", "bags", "ceramics", "ceramic", "mug", "mugs",
    "knitwear", "jumper", "jumpers", "socks", "throw", "throws", "shirt", "shirts",
    "blanket", "blankets", "toy", "toys", "candle", "candles", "products", "items",
}


def _query_targets_brand(query: str, brands: list[str] | None) -> bool:
    """True when the query is/contains a known site brand (token-sequence match, Unicode-aware)."""
    if not brands:
        return False
    q_tokens = _tokens(query)
    for b in brands:
        b_tokens = _tokens(b)
        if not b_tokens:
            continue
        if _phrase_in(b_tokens, q_tokens) or _phrase_in(q_tokens, b_tokens):
            return True
        sig = [t for t in b_tokens if len(t) >= 3]
        if sig and all(any(_token_match(bt, qt) for qt in q_tokens) for bt in sig):
            return True
    return False


def _brand_search_unverifiable(query: str, results: list[ScoredResult], brands: list[str] | None = None) -> bool:
    """True when a BRAND_SEARCH brand cannot be confirmed from any result title."""
    org = _organic(results)
    if not org:
        return False
    title_toks = [_tokens(r.title) for r in org]
    q_tokens = _tokens(query)
    if brands:
        matched = [b for b in brands if _tokens(b) and _phrase_in(_tokens(b), q_tokens)]
        for b in sorted(matched, key=len, reverse=True):
            bt = _tokens(b)
            return not any(_phrase_in(bt, tt) for tt in title_toks)
    tokens = query.split()
    candidates = [query]
    trimmed = list(tokens)
    while trimmed and trimmed[-1].lower() in _BRAND_QUERY_TRAILING_NOUNS:
        trimmed = trimmed[:-1]
        if trimmed:
            candidates.append(" ".join(trimmed))
    for cand in candidates:
        ct = _tokens(cand)
        if not ct or len("".join(ct)) < 2:
            continue
        if any(_phrase_in(ct, tt) for tt in title_toks):
            return False
    return True


# Categories that must never be reclassified as CATEGORY_MAPPING_FAILURE: their failure is
# a constraint/negation/gibberish property, not a vocabulary gap to a category.
_CATEGORY_RESEMBLANCE_EXEMPT = {"PRICE_ANCHORED", "NEGATIVE_INTENT", "GIBBERISH"}
# Only these test categories (single-concept phrasings of a category) may be reclassified.
_CATEGORY_RECLASS_CATEGORIES = {"CATEGORY_MAPPING", "LOCALE_VARIATION"}
_SINGLE_CONCEPT_MAX_TOKENS = 3


def _resembles_site_category(query: str, categories: list[str] | None, category: str | None = None) -> str | None:
    """Return the site category the query resembles, or None.

    A category matches when the query covers at least ceil(0.6 × |category tokens|) of the
    category's distinctive tokens (it used to fire on ANY single shared word: "new home
    present" → 'House & Home'). PRICE_ANCHORED / NEGATIVE_INTENT / GIBBERISH never match.
    """
    if not categories or (category and _val(category) in _CATEGORY_RESEMBLANCE_EXEMPT):
        return None
    q_tokens = _sig_tokens(query)
    if not q_tokens:
        return None
    best, best_ratio = None, 0.0
    for cat in categories:
        c_tokens = set(_sig_tokens(cat))
        if not c_tokens:
            continue
        overlap = sum(1 for ct in c_tokens if any(_token_match(ct, qt) for qt in q_tokens))
        need = max(1, math.ceil(0.6 * len(c_tokens)))
        ratio = overlap / len(c_tokens)
        if overlap >= need and ratio > best_ratio:
            best, best_ratio = cat, ratio
    return best


def _core_terms_absent(query: str, results: list[ScoredResult]) -> bool:
    """True when none of the query's distinctive terms appear in any organic result title.

    Unicode-aware (kök, skål, Größe stay whole words) and compound-tolerant (query
    "Wanderschuhe" is present in "Wanderschuhe Herren"; "Kaffeekanne" in "Kaffeekannen").
    """
    org = _organic(results)
    if not org:
        return False
    q_tokens = _sig_tokens(query)
    if not q_tokens:
        return False
    title_tokens = {t for r in org for t in _tokens(r.title)}
    for qt in q_tokens:
        for tt in title_tokens:
            if _token_match(qt, tt) or _compound_contains(tt, qt) or (len(tt) >= 5 and _compound_contains(qt, tt)):
                return False
    return True


def _dm_tokens(s: str) -> set[str]:
    """Tokens for exact-title comparison: punctuation-free, '30ml' == '30 ml', '®' dropped."""
    f = re.sub(r"(?<=\d)(?=[^\W\d_])|(?<=[^\W\d_])(?=\d)", " ", _fold(s))
    return set(_WORD_RE.findall(f))


def _dm_seq(s: str) -> list[str]:
    f = re.sub(r"(?<=\d)(?=[^\W\d_])|(?<=[^\W\d_])(?=\d)", " ", _fold(s))
    return _WORD_RE.findall(f)


def _title_has_query_sequence(query: str, title: str) -> bool:
    """Query tokens appear contiguously, in order (punctuation-insensitive). Preferred over the
    order-free check so "Mojito Wrap GTX" is not mistaken for the exact "Mojito GTX"."""
    return _phrase_in(_dm_seq(query), _dm_seq(title))


def _title_contains_query(query: str, title: str) -> bool:
    """Punctuation- and word-order-tolerant literal check: every query token is in the title.

    "Beauty of Joseon Glow Serum Propolis + Niacinamide 30 ml" matches both
    "…Glow Serum: Propolis+Niacinamide 30 ml" (Lyko) and "Glow Serum Beauty of Joseon …" (Douglas).
    """
    q = _dm_tokens(query)
    return bool(q) and q <= _dm_tokens(title)


# ---------------------------------------------------------------------------
# Client-facing text hygiene
# ---------------------------------------------------------------------------

# Client evidence must never carry model internals. Parentheticals with scores are cut;
# sentences still naming internals are dropped (the full text stays in internal_notes).
_SCORE_PAREN_RE = re.compile(r"\s*\((?:[^()]*\b(?:relevance|score|rel)\b[^()]*|\s*0[.,]\d{2,3}\s*)\)", re.I)
_INTERNAL_RE = re.compile(
    r"relevance[- ]score|\brelevance\b\s*(?:of|=|:)?\s*[01][.,]\d|\brerank|\bvoyage\b|\bllm\b|"
    r"\bcalibrat|\boverrid|\bscor(?:e|es|ed|ing)\b|manual verification|\bdisplacement\b|knowledge base|"
    r"(?<![€£$\d.,])\b0[.,]\d{2,3}\b(?!\s*(?:€|eur|kr|sek|dkk|nok|chf|£|\$|:-|l|ml|cl|dl|kg|g|mm|cm|m|oz)\b)",
    re.I,
)


def _client_text(text: str | None) -> tuple[str, bool]:
    """(clean client text, whether anything was removed)."""
    raw = (text or "").strip()
    if not raw:
        return "", False
    t = _SCORE_PAREN_RE.sub("", raw)
    t = t.replace("[MANUAL VERIFICATION REQUIRED]", "").strip()
    sentences = re.split(r"(?<=[.!?])\s+", t)
    kept = [s for s in sentences if s and not _INTERNAL_RE.search(s)]
    clean = " ".join(kept).strip()
    return clean, clean != raw


# ---------------------------------------------------------------------------
# Structured verdict schema
# ---------------------------------------------------------------------------


class FailureModeChoice(str, Enum):
    PARTIAL_KEYWORD_MATCH = "PARTIAL_KEYWORD_MATCH"
    BRAND_BLEED = "BRAND_BLEED"
    CONSTRAINT_DROPPED = "CONSTRAINT_DROPPED"
    CATEGORY_MAPPING_FAILURE = "CATEGORY_MAPPING_FAILURE"
    FACET_NOT_EXTRACTED = "FACET_NOT_EXTRACTED"
    NO_FUZZY_MATCHING = "NO_FUZZY_MATCHING"
    NO_SEMANTIC_UNDERSTANDING = "NO_SEMANTIC_UNDERSTANDING"
    POOR_RANKING = "POOR_RANKING"
    DUPLICATE_FLOODING = "DUPLICATE_FLOODING"
    ZERO_RESULTS_OR_GARBAGE = "ZERO_RESULTS_OR_GARBAGE"
    OTHER = "OTHER"


class SeverityChoice(str, Enum):
    CRITICAL = "CRITICAL"
    MODERATE = "MODERATE"
    MINOR = "MINOR"
    PASS = "PASS"


class CitedResult(BaseModel):
    position: int = Field(description="Position of the result on the page as listed (#1 = first).")
    title: str = Field(description="The result's title, copied exactly from the list.")
    problem: str = Field(description="Why this result is wrong for the query.")


class JudgeVerdict(BaseModel):
    """Judge output. Field order = generation order: reasoning first, verdict last."""

    observations: str = Field(description="INTERNAL working notes: scores, positions, matched words, rule applied.")
    cited_results: list[CitedResult] = Field(description="Results the verdict rests on (off-topic, violating). Empty for PASS.")
    evidence: str = Field(description="CLIENT-FACING evidence: plain language, specific titles and positions, no scores.")
    recommended_fix: str = Field(description="CLIENT-FACING fix specific to what happened.")
    failure_mode: FailureModeChoice
    failure_mode_explanation: Optional[str] = Field(description="Required when failure_mode is OTHER and severity is not PASS, else null.")
    severity: SeverityChoice


_FM_ALIASES = {
    "PASS": FailureMode.OTHER, "NONE": FailureMode.OTHER, "NO_FAILURE": FailureMode.OTHER,
    "ZERO_RESULTS": FailureMode.ZERO_RESULTS_OR_GARBAGE, "GARBAGE": FailureMode.ZERO_RESULTS_OR_GARBAGE,
    "RANKING": FailureMode.POOR_RANKING, "FLOODING": FailureMode.DUPLICATE_FLOODING,
}


def _coerce_failure_mode(v) -> FailureMode:
    """Robust failure-mode normalisation. Unknown values RAISE (never silently OTHER).

    'poor_ranking', 'Poor Ranking', FailureModeChoice.POOR_RANKING all → POOR_RANKING, so a
    lowercase label can no longer slip past the ranking caps as OTHER.
    """
    raw = _val(v)
    key = re.sub(r"[^A-Z_]", "", re.sub(r"[\s\-]+", "_", raw.strip().upper()))
    if key in FailureMode.__members__:
        return FailureMode[key]
    if key in _FM_ALIASES:
        return _FM_ALIASES[key]
    raise ValueError(f"unknown failure_mode {raw!r}")


def _coerce_severity(v) -> Severity:
    """Robust severity normalisation. Unparseable values RAISE — never a default MODERATE."""
    raw = _val(v).strip()
    word = re.split(r"[\s—\-:/]+", raw.upper(), maxsplit=1)[0] if raw else ""
    if word in _SEVERITY_MAP:
        return _SEVERITY_MAP[word]
    raise ValueError(f"unknown severity {raw!r}")


# ---------------------------------------------------------------------------
# System prompt (all static rules; cached by structured_call)
# ---------------------------------------------------------------------------


def _build_system_prompt() -> str:
    fm_lines = "\n".join(f"- {k}: {v}" for k, v in _FAILURE_MODE_DESCRIPTIONS.items())
    cat_lines = "\n".join(f"- {_val(k)}: {v}" for k, v in CATEGORY_DESCRIPTIONS.items())
    gap, floor, weak = MATERIAL_RANK_GAP, ON_TOPIC_TOP1_FLOOR, WEAK_SET_MAX
    return f"""You are an expert e-commerce site-search auditor. You judge ONE search query at a time: what the shopper typed, what the engine showed, and what went wrong. Your verdict goes into a report read by senior business stakeholders who do not know search technology.

# Output fields (fill them in this order)
1. observations — INTERNAL, never shown to the client. Your working notes: scores, positions, gaps, which query words matched, which rule below decided the verdict. Under 150 words.
2. cited_results — the specific results your verdict rests on, with their position and exact title copied from the list. For any CRITICAL verdict, cite the off-topic results among the first three positions. For CONSTRAINT_DROPPED, cite at least one result that violates the constraint — if you cannot point at one, do not use CONSTRAINT_DROPPED. Empty list for PASS.
3. evidence — CLIENT-FACING. 2-4 plain sentences naming specific results by title and position. Never include relevance scores or any other model numbers, and never mention scores, rerankers, models, AI, calibration, overrides, thresholds or "manual verification". Do not claim the store carries a product unless the "Control search" section of the message shows it. Write in English; quote product titles as listed.
4. recommended_fix — CLIENT-FACING, specific to what happened, written for the retailer's engineering team. Same wording rules as evidence.
5. failure_mode — one value from the menu.
6. failure_mode_explanation — required when failure_mode is OTHER and severity is not PASS; otherwise null.
7. severity — CRITICAL, MODERATE, MINOR or PASS. For a PASS use failure_mode OTHER.

# Failure mode menu (pick the SINGLE most important)
{fm_lines}

# Query categories (what each test measures)
{cat_lines}

# Reading the data
- Results are listed in the engine's ORIGINAL order — the order the shopper saw. Each line carries an internal relevance score (0-1) from a reranker; use it in observations only.
- Results marked [SPONSORED] are paid ad placements outside the engine's organic ranking. Ignore them for every ranking judgment; judge the organic results.
- "Deterministic checks" were computed in code (prices parsed, exclusions and colours matched across languages). Trust them over your own reading of the titles.
- Calibration examples (when present) show how similar queries were graded under the current rules. Use them for consistent severity and labels; never copy their products.

# Severity criteria
- CRITICAL: the shopper's FIRST results are genuinely off-topic (wrong product type, wrong brand, unrelated category) — or the whole set is garbage (best score below {weak:.2f}). A large reranker gap alone is NOT critical: if the first organic result is on-topic (score >= {floor:.2f}), a better-scored item lower down is reranker noise. Cap such cases at MODERATE, or MINOR if the first result is near-best.
- MODERATE: the best match is buried 3+ positions deep AND it is materially better than the shopper's #1 (gap >= {gap:.2f}), OR results are partially relevant but miss a key part of the query. Never MODERATE for a buried item only marginally better than #1 (gap < {gap:.2f}).
- MINOR: best match is in the top 3 but not #1, or the only issue is a cosmetic reorder among near-equal on-topic results.
- PASS: the top results are relevant and well-ordered.

# Materiality of displacement
Two independent reasons a large displacement is NOT critical: (1) small gap (< {gap:.2f}) — the shopper already saw a near-best result; (2) on-topic first result (>= {floor:.2f}) — short, generic queries score on literal word overlap, so the "best" is often a title that repeats the query word. Do not write "customers see irrelevant results" when every result is relevant. Reserve CRITICAL ranking failures for genuinely wrong first results with a correct match buried far below.

# Capability resolved + flooding only = PASS
For TYPO, SYNONYM, ABBREVIATION and PLURAL_SINGULAR, the test asks one thing: did the engine correct / map / expand / resolve the term to the right product type? If yes, and the only remaining issue is the same model repeated as colour/size cards, the verdict is PASS (mention the repetition as a merchandising note). The same holds for FACET_EXTRACTION when every result meets the facet. For BRAND_SEARCH, flooding stays MINOR.

# BRAND_SEARCH
The test is brand precision. All results of the queried brand → PASS. If the set is dominated by accessories while flagship products are missing, keep PASS and note it as a merchandising observation. Escalate only when another brand leaks in (BRAND_BLEED).

# Dropped head noun (PARTIAL_KEYWORD_MATCH)
For multi-word queries, check that results match ALL significant words, especially the head product noun. If most of the page matches only a secondary word ("winter coat sale" → winter socks; "throws grey" → grey socks after two throws), it is PARTIAL_KEYWORD_MATCH: MODERATE, CRITICAL when the head noun is essentially absent. Judge the whole page, not just #1. Do not excuse it as "catalogue limits".

# TYPO / SPLIT_WORD / MERGED_WORDS / PARTIAL_QUERY
If the intended product type appears in NO result (the engine matched letters inside unrelated words), it is CRITICAL / NO_FUZZY_MATCHING, not POOR_RANKING. If a garbled typo collides with a different real word and the engine returns good results for that word, it is a PASS. A split word that only matched a brand name ("jack et" → Jack Wolfskin beanie) did not rejoin the word.

# Constraints (CONSTRAINT_DROPPED / FACET_NOT_EXTRACTED) — you see only titles and prices
- Colour: the query names one colour; any title naming a DIFFERENT colour is a violation.
- Exclusion (not/without/no, ohne/nicht/kein, utan/inte/ej, uden/ikke/uten, zonder/geen, sans, …): any title containing the excluded term is a violation; faux/imitation still violates ("Faux Leather" violates "not leather"). Words that say the item is free of it ("laceless", "lederfrei", "parfymfri", "perfume free") are NOT violations.
- Price limit: any organic result priced outside the limit is a violation (see Deterministic checks).
- Size / fit / fabric / material: any title with a different value of the same attribute is a violation.
- One violating title is enough — cite it. A FACET / single-constraint query PASSES only if every result meets the constraint; any violation is at least MODERATE. Most of the page violating, or the #1 result violating, is CRITICAL.
- If the constrained attribute appears in no title at all, you cannot confirm a violation: do not invent one, judge on relevance, and say so in observations.

# DIRECT_MATCH (exact product title)
- The exact product must be the first organic result. Matching ignores punctuation and word order ("Serum: Propolis+Niacinamide" = "Serum Propolis + Niacinamide").
- PASS only when the exact product is #1 and every other result is the same product (colour/size variant, separate listing) or a member of the same named series and brand.
- Any other result is leakage → PARTIAL_KEYWORD_MATCH: a couple of stray items MINOR/MODERATE; a set dominated by other lines or brands MODERATE.
- Exact product at #2 behind a near-identical sibling of the same series → MINOR. Buried deeper or absent → MODERATE or worse.

# Off-category padding
A thin genuine match padded with unrelated product types ("Heli" → 2 Helinox items then body oil, honey, sunglasses) is POOR_RANKING / MODERATE: the right page is the short one.
"""


_SYSTEM_MESSAGE = _build_system_prompt()


# ---------------------------------------------------------------------------
# User message (per-query data, KB examples last)
# ---------------------------------------------------------------------------


def _build_prompt(
    test_query: TestQuery,
    results: list[ScoredResult],
    max_relevance: float,
    top3_avg: float,
    displacement: int,
    kb_section: str = "",
    *,
    total_hits: int | None = None,
    det_lines: list[str] | None = None,
    control_titles: list[str] | None = None,
) -> str:
    """Per-query user message: query, the page in original order, stats, checks, control, KB."""
    cat = _val(test_query.category)
    lines = [
        "## Query under analysis",
        f'- Query: "{test_query.query}"',
        f"- Category: {cat}",
        f"- Rationale: {test_query.rationale}",
    ]
    if test_query.target_term:
        lines.append(f'- Plain intent term: "{test_query.target_term}"')
    c = test_query.constraints
    if c and (c.price_max is not None or c.price_min is not None or c.exclude or c.attributes):
        parts = []
        if c.price_max is not None:
            parts.append(f"price <= {c.price_max:g}")
        if c.price_min is not None:
            parts.append(f"price >= {c.price_min:g}")
        if c.exclude:
            parts.append("exclude: " + ", ".join(c.exclude))
        if c.attributes:
            parts.append("attributes: " + ", ".join(c.attributes))
        lines.append("- Constraints: " + "; ".join(parts))

    by_original = sorted(results, key=lambda r: r.original_rank)
    lines += ["", "## What the shopper saw (engine's original order)"]
    for pos, r in enumerate(by_original, 1):
        parts = [f"#{pos}", r.title]
        if r.price:
            parts.append(r.price)
        if getattr(r, "sponsored", False):
            parts.append("[SPONSORED]")
        parts.append(f"(internal relevance {r.relevance_score:.3f})")
        lines.append("  " + " | ".join(parts))

    org = _organic(results)
    by_org = sorted(org, key=lambda r: r.original_rank)
    best = max(org, key=lambda r: r.relevance_score)
    best_pos = by_original.index(best) + 1
    lines += [
        "",
        "## Key stats (organic results; internal)",
        f"- Products shown on the page (scraped): {len(results)}"
        + (f" ({len(results) - len(org)} sponsored)" if len(org) != len(results) else ""),
        f"- Hit count the page itself reports: {total_hits if total_hits is not None else 'unknown'}",
        f"- First organic result score: {by_org[0].relevance_score:.3f}",
        f"- Best score: {max_relevance:.3f} (at position #{best_pos}; {displacement} organic slots above it)",
        f"- Gap best − first: {max_relevance - by_org[0].relevance_score:.3f}",
        f"- Top-3 organic average: {top3_avg:.3f}",
    ]
    if det_lines:
        lines += ["", "## Deterministic checks (computed in code)"] + [f"- {d}" for d in det_lines]
    if control_titles:
        lines += ["", f'## Control search: "{test_query.target_term}"',
                  "The plain intent term returns these products, so the store does stock them:"]
        lines += [f"  - {t}" for t in control_titles]
    if kb_section:
        lines += ["", kb_section.strip()]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _llm_verdict(system: str, user: str) -> tuple[JudgeVerdict | None, FailureMode | None, Severity | None, str | None]:
    """One structured judge call, retried once on an unusable response.

    Returns (verdict, failure_mode, severity, error). ``error`` is set (and the rest None)
    when no usable verdict was produced; the caller then builds a flagged fallback.
    """
    last_err = None
    for attempt in (1, 2):
        try:
            v = structured_call(
                model=_MODEL, system=system, user=user, schema=JudgeVerdict,
                max_tokens=_MAX_TOKENS, phase="judge", temperature=_TEMPERATURE,
            )
            try:
                fm, sev = _coerce_failure_mode(v.failure_mode), _coerce_severity(v.severity)
            except ValueError as e:
                raise LLMResponseError(str(e)) from e
            return v, fm, sev, None
        except LLMResponseError as e:
            last_err = f"LLMResponseError: {e}"
            logger.warning("Judge response unusable (attempt %d/2): %s", attempt, e)
            continue
        except (anthropic.APIError, ValidationError) as e:
            last_err = f"{type(e).__name__}: {e}"
            logger.warning("Judge API call failed: %s", e)
            break
    return None, None, None, last_err


# ---------------------------------------------------------------------------
# Verdict state + deterministic guards
# ---------------------------------------------------------------------------


@dataclass
class _State:
    fm: FailureMode
    sev: Severity
    evidence: str
    fix: str
    expl: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    cited: list[CitedResult] = field(default_factory=list)

    def set(self, fm=None, sev=None, evidence=None, fix=None, expl="__keep__"):
        if fm is not None:
            self.fm = fm
        if sev is not None:
            self.sev = sev
        if evidence is not None:
            self.evidence = evidence
        if fix is not None:
            self.fix = fix
        if expl != "__keep__":
            self.expl = expl


def _short(title: str, n: int = 60) -> str:
    title = (title or "").strip()
    return (title[: n - 1] + "…") if len(title) > n else title


def _cited_in_top3(cited: list[CitedResult], results: list[ScoredResult]) -> bool:
    top3 = sorted(_organic(results), key=lambda r: r.original_rank)[:3]
    for c in cited:
        if any(_title_matches(c.title, r.title or "") for r in top3):
            return True
    return False


def _cited_real_result(cited: list[CitedResult], results: list[ScoredResult]) -> bool:
    return any(_title_matches(c.title, r.title or "") for c in cited for r in results)


def _facet_ok(tq: TestQuery, results: list[ScoredResult], ctx: "_Ctx", st: "_State") -> bool:
    """Facet met: no conflicting value in any title and most titles confirm it (rest flagged)."""
    confirmed, conflicting, total = _attribute_coverage(tq, results, ctx.language)
    if not total or conflicting or confirmed * 2 < total:
        return False
    if confirmed < total:
        st.notes.append(f"MANUAL CHECK: facet confirmed in {confirmed}/{total} titles; the rest don't state it.")
    return True


# Categories exempt from the generic CRITICAL cap: their CRITICAL verdicts come from rules
# independent of the first result's relevance (negation ignored, exact product missing,
# wrong brand).
_CRITICAL_CAP_EXEMPT = {"NEGATIVE_INTENT", "DIRECT_MATCH", "BRAND_SEARCH"}
_FLOOD_PASS_CATEGORIES = {"TYPO", "SYNONYM", "ABBREVIATION", "PLURAL_SINGULAR"}
_CONVERSATIONAL = {"NATURAL_LANGUAGE", "SEMANTIC_MEANING", "SUBJECTIVE_ATTRIBUTE"}


@dataclass
class _Ctx:
    tq: TestQuery
    cat: str
    results: list[ScoredResult]
    language: str | None
    site_categories: list[str] | None
    site_brands: list[str] | None
    from_llm: bool


def _apply_guards(st: _State, ctx: _Ctx) -> None:
    """Deterministic guards, applied to LLM AND fallback verdicts alike."""
    tq, cat, results = ctx.tq, ctx.cat, ctx.results
    org = sorted(_organic(results), key=lambda r: r.original_rank)
    max_rel = max(r.relevance_score for r in org)
    top1 = org[0].relevance_score
    weak = max_rel < WEAK_SET_MAX

    # Deterministic violation evidence (price / exclusion / colour), computed once.
    price_bad, n_priced, price_label = _price_violations(tq, results)
    excl_frac, excl_bad, excl_term = (None, [], None)
    if cat == "NEGATIVE_INTENT" or (tq.constraints and tq.constraints.exclude):
        excl_frac, excl_bad, excl_term = _exclusion_violations(tq, results, ctx.site_categories, ctx.language)
    colour_bad = _colour_violations(tq, results, ctx.language) if cat in ("MULTI_ATTRIBUTE", "FACET_EXTRACTION") else []
    det_violation = bool(price_bad) or bool(excl_bad and (excl_frac or 0) >= 0.5)

    if st.sev == Severity.PASS and st.fm not in (FailureMode.DUPLICATE_FLOODING,):
        st.fm = FailureMode.OTHER

    # 1. CONSTRAINT_DROPPED needs a violating title. Without one the verdict is a guess:
    #    neutral client text, manual check flagged internally.
    if st.fm == FailureMode.CONSTRAINT_DROPPED and ctx.from_llm:
        supported = bool(price_bad or excl_bad or colour_bad) or _cited_real_result(st.cited, results)
        # Negation read as a positive AND-keyword collapses the page to a handful of items
        # (Gartenleuchte nicht solar -> 1 result): same root cause, nothing left to cite.
        if cat == "NEGATIVE_INTENT" and len(org) <= 3:
            supported = True
            st.notes.append("NEGATIVE_INTENT under-retrieval: CONSTRAINT_DROPPED accepted without a violating title.")
        if not supported:
            st.notes.append("MANUAL CHECK: judge said CONSTRAINT_DROPPED without citing a violating "
                            "result title; constraint not verifiable from titles.")
            st.set(FailureMode.OTHER, Severity.PASS,
                   evidence=(f"The results for '{tq.query}' are the product type searched for. Whether every "
                             f"item meets the requested attribute cannot be confirmed from the product titles."),
                   fix="", expl=None)

    # 2. Ranking materiality caps (never ease a garbage set: max < WEAK_SET_MAX).
    if st.fm == FailureMode.POOR_RANKING and not weak:
        if _displacement_is_cosmetic(results) and st.sev in (Severity.CRITICAL, Severity.MODERATE):
            st.notes.append(f"Ranking cap: {_sev_short(st.sev)} -> MINOR (gap {_relevance_gap(results):.3f} < "
                            f"{MATERIAL_RANK_GAP}, top1 {top1:.3f} on-topic).")
            st.sev = Severity.MINOR
        elif st.sev == Severity.CRITICAL and not _ranking_materially_broken(results):
            st.notes.append(f"Ranking cap: CRITICAL -> MODERATE (first organic result on-topic, top1 {top1:.3f}).")
            st.sev = Severity.MODERATE
        if st.sev == Severity.MINOR and top1 >= ON_TOPIC_TOP1_FLOOR and _displacement_is_cosmetic(results):
            st.notes.append("POOR_RANKING/MINOR -> PASS (cosmetic reorder, first result on-topic).")
            st.set(FailureMode.OTHER, Severity.PASS,
                   evidence=(f"The results for '{tq.query}' are on-topic and a relevant product leads the page; "
                             f"only the order among similar products differs. " + st.evidence).strip(),
                   expl=None)

    # 3. Generic CRITICAL cap: with an on-topic first result and nothing provably violated, a
    #    CRITICAL needs a cited off-topic title in the top 3 — whatever label the judge picked.
    if (st.sev == Severity.CRITICAL and top1 >= ON_TOPIC_TOP1_FLOOR and not det_violation
            and cat not in _CRITICAL_CAP_EXEMPT and not _cited_in_top3(st.cited, results)):
        st.notes.append(f"Generic cap: CRITICAL -> MODERATE ({_val(st.fm)}; top1 {top1:.3f} on-topic, "
                        f"no off-topic top-3 title cited, no deterministic violation).")
        st.sev = Severity.MODERATE

    # 4. Weak-filler guard: clustered low scores with the core term in no title = irrelevant set.
    if (st.sev == Severity.PASS and cat != "BRAND_SEARCH"
            and not _query_targets_brand(tq.query, ctx.site_brands)
            and max_rel < MIN_RELEVANT_TOP and _core_terms_absent(tq.query, results)):
        st.notes.append(f"Weak-filler guard: max {max_rel:.3f}, core terms in no title.")
        examples = ", ".join(f"'{_short(r.title, 45)}'" for r in org[:2])
        st.set(FailureMode.NO_SEMANTIC_UNDERSTANDING,
               Severity.CRITICAL if weak else Severity.MODERATE,
               evidence=(f"None of the results for '{tq.query}' are the product type searched for. The page shows "
                         f"unrelated products such as {examples} instead."),
               fix=("Detect when no result matches the query's core product term and either show an honest "
                    "no-results page or map the query to the right category, instead of padding the page with "
                    "unrelated products."),
               expl=None)

    # 5. Variant flooding becomes the headline when it is at least as severe as a ranking-only verdict.
    flood = _flooding_stats(results)
    flood_sev = _flooding_severity(flood)
    if flood_sev is not None and st.fm in (FailureMode.POOR_RANKING, FailureMode.OTHER) and _sev_rank(flood_sev) >= _sev_rank(st.sev):
        st.set(FailureMode.DUPLICATE_FLOODING, flood_sev,
               evidence=(f"Only {flood['unique']} distinct products fill {flood['total']} result slots — "
                         f"'{_short(flood['top_title'], 41)}' alone appears {flood['top_count']} times as separate "
                         f"colour/size cards. Repeating one model crowds out other products."),
               fix=("Collapse colour/size variants of the same product into one result card (variants selectable "
                    "on the product page) so more distinct products are visible above the fold."),
               expl=None)

    # 6. DUPLICATE_FLOODING severity = flooding magnitude (authoritative, both directions).
    if st.fm == FailureMode.DUPLICATE_FLOODING:
        det_flood = _flooding_severity(_flooding_stats(results))
        if det_flood is not None:
            st.sev = det_flood
        else:
            st.notes.append("Flooding below significance -> PASS.")
            st.set(FailureMode.OTHER, Severity.PASS, expl=None)

    # 7. Off-category flooding is a precision failure, not benign variant flooding.
    if st.fm == FailureMode.DUPLICATE_FLOODING and flood:
        flooded_rel = max((r.relevance_score for r in org if (r.title or "").strip() == flood["top_title"]), default=0.0)
        if flooded_rel < _OFF_CATEGORY_REL:
            st.notes.append(f"Off-category flooding: flooded title relevance {flooded_rel:.2f}.")
            st.set(FailureMode.POOR_RANKING, max(st.sev, Severity.MODERATE, key=_sev_rank),
                   evidence=(f"'{_short(flood['top_title'], 41)}' is not the product type the query asks for, yet it "
                             f"fills {flood['top_count']} slots. The engine repeats off-category items instead of "
                             f"showing relevant products."),
                   fix=("Filter out results that do not match the query's product type and boost the right "
                        "category, freeing those slots for relevant products."),
                   expl=None)

    # 8. Capability resolved + flooding only -> PASS (TYPO/SYNONYM/ABBREVIATION/PLURAL; FACET when satisfied).
    if st.fm == FailureMode.DUPLICATE_FLOODING and top1 >= ON_TOPIC_TOP1_FLOOR and (
            cat in _FLOOD_PASS_CATEGORIES
            or (cat == "FACET_EXTRACTION" and not det_violation and not colour_bad and _facet_ok(tq, results, ctx, st))):
        what = {"TYPO": "The misspelling is corrected", "SYNONYM": "The synonym is understood",
                "ABBREVIATION": "The abbreviation is expanded", "PLURAL_SINGULAR": "The plural is resolved",
                "FACET_EXTRACTION": "Every result meets the requested attribute"}[cat]
        st.notes.append(f"{cat}: capability resolved, flooding only -> PASS.")
        st.set(FailureMode.OTHER, Severity.PASS,
               evidence=(f"{what} and the results are the right product type. Several slots repeat the same model "
                         f"in different colours or sizes — a merchandising note, not a search defect."),
               fix="", expl=None)

    # 9. DIRECT_MATCH: punctuation/word-order tolerant exact-title check on the organic order.
    if cat == "DIRECT_MATCH":
        positions = [i for i, r in enumerate(org) if _title_has_query_sequence(tq.query, r.title or "")] \
            or [i for i, r in enumerate(org) if _title_contains_query(tq.query, r.title or "")]
        if positions and positions[0] == 0:
            if all(_title_contains_query(tq.query, r.title or "") for r in org):
                st.set(FailureMode.OTHER, Severity.PASS,
                       evidence=(f"The exact product '{tq.query}' is the first result"
                                 + (f", and the other {len(org) - 1} slot(s) show the same product (variants or "
                                    f"separate listings)." if len(org) > 1 else ".")),
                       fix="", expl=None)
        elif positions and positions[0] == 1:
            q_t = _dm_tokens(tq.query)
            share = len(q_t & _dm_tokens(org[0].title or "")) / max(1, len(q_t))
            sev = Severity.MINOR if share >= 0.5 else Severity.MODERATE
            st.notes.append(f"DIRECT_MATCH: exact product at #2 (#1 shares {share:.0%} of query tokens).")
            st.set(FailureMode.PARTIAL_KEYWORD_MATCH, sev,
                   evidence=(f"The exact product '{tq.query}' is the second result; '{_short(org[0].title)}' is shown "
                             f"above it" + (" — a close sibling from the same line." if sev == Severity.MINOR
                                            else " — a different product.")),
                   fix=("Add an exact-title boost so a literal product-name query puts that product first."),
                   expl=None)
        else:
            sev = max(st.sev, Severity.MODERATE, key=_sev_rank)
            where = f"at position #{positions[0] + 1}" if positions else "not in the results"
            st.set(FailureMode.PARTIAL_KEYWORD_MATCH, sev,
                   evidence=(f"A shopper searching the exact product name '{tq.query}' does not get it first: "
                             f"the first result is '{_short(org[0].title)}' and the exact product is {where}."),
                   fix=("For exact product-title queries the matching product must rank first. Add an exact "
                        "title-match boost (punctuation- and word-order-insensitive)."),
                   expl=None)

    # 10. BRAND_SEARCH verifiability -> internal manual check (client text untouched).
    if cat == "BRAND_SEARCH" and _brand_search_unverifiable(tq.query, results, ctx.site_brands):
        st.notes.append(f"MANUAL CHECK: brand from '{tq.query}' appears in no result title; brand precision "
                        f"unverified (possible hidden brand bleed).")

    # 11. Title-invisible colour/material constraint -> internal manual check.
    if cat in ("MULTI_ATTRIBUTE", "FACET_EXTRACTION") and st.fm != FailureMode.CONSTRAINT_DROPPED:
        unv = _unverifiable_constraint_token(tq, results, ctx.language)
        if unv:
            st.notes.append(f"MANUAL CHECK: '{unv}' constraint appears in no result title; verify on the live page.")
        if colour_bad and st.fm not in (FailureMode.FACET_NOT_EXTRACTED,):
            st.notes.append("Possible colour leak (verify): " + "; ".join(_short(r.title, 50) for r in colour_bad[:3]))

    # 12. CATEGORY_MAPPING garbage -> CATEGORY_MAPPING_FAILURE; conversational garbage -> NO_SEMANTIC.
    if cat == "CATEGORY_MAPPING" and st.fm in (FailureMode.ZERO_RESULTS_OR_GARBAGE, FailureMode.NO_SEMANTIC_UNDERSTANDING):
        st.set(FailureMode.CATEGORY_MAPPING_FAILURE, expl=None)
    if cat in _CONVERSATIONAL and st.fm == FailureMode.ZERO_RESULTS_OR_GARBAGE:
        st.set(FailureMode.NO_SEMANTIC_UNDERSTANDING, expl=None)

    # 13. NEGATIVE_INTENT exclusion (deterministic, multilingual, word-boundary).
    if excl_frac is not None and excl_frac >= 0.5:
        new_sev = Severity.CRITICAL if excl_frac >= 0.8 else Severity.MODERATE
        if _sev_rank(new_sev) >= _sev_rank(st.sev):
            st.notes.append(f"Exclusion guard: {excl_frac:.0%} of organic results mention '{excl_term}'.")
            st.set(FailureMode.CONSTRAINT_DROPPED, new_sev,
                   evidence=(f"Exclusion ignored: {round(excl_frac * 100)}% of results contain the excluded term "
                             f"'{excl_term}', e.g. '{_short(excl_bad[0].title)}'. The engine ran '{tq.query}' as if "
                             f"the exclusion were not there."),
                   fix=(f"Parse negation words and filter OUT products matching '{excl_term}' (including faux/"
                        f"imitation variants) instead of searching for them."),
                   expl=None)

    # 14. Price limit (deterministic, locale-aware price parser).
    if price_bad:
        frac = len(price_bad) / max(1, n_priced)
        top_bad = org[0] in price_bad
        new_sev = Severity.CRITICAL if (frac >= 0.8 or top_bad) else Severity.MODERATE
        if _sev_rank(new_sev) < _sev_rank(st.sev):
            st.notes.append(f"Price guard: {len(price_bad)}/{n_priced} outside '{price_label}' (verdict already worse).")
        else:
            st.notes.append(f"Price guard: {len(price_bad)}/{n_priced} priced results outside '{price_label}'.")
            st.set(FailureMode.CONSTRAINT_DROPPED, new_sev,
                   evidence=(f"{len(price_bad)} of {n_priced} results are outside the price limit ({price_label}), "
                             f"e.g. '{_short(price_bad[0].title)}' at {price_bad[0].price}."
                             + (" The first result already breaks the limit." if top_bad else "")),
                   fix=("Recognise price phrases ('under 80', 'unter 80 €', 'under 500 kr') and apply them as a "
                        "price filter instead of matching the words."),
                   expl=None)


# ---------------------------------------------------------------------------
# Zero results / gibberish / exclusions (deterministic, no LLM)
# ---------------------------------------------------------------------------

# Zero-result failure mode by test category. Deterministic so the same symptom always gets
# the same label (it used to vary run to run with the LLM). See JUDGE_PLAYBOOK.md.
_ZERO_FAILURE_MODE: dict[str, FailureMode] = {
    "TYPO": FailureMode.NO_FUZZY_MATCHING,
    "SPLIT_WORD": FailureMode.NO_FUZZY_MATCHING,
    "MERGED_WORDS": FailureMode.NO_FUZZY_MATCHING,
    "SPECIAL_CHARACTER": FailureMode.NO_FUZZY_MATCHING,
    "PARTIAL_QUERY": FailureMode.NO_FUZZY_MATCHING,
    "PLURAL_SINGULAR": FailureMode.NO_FUZZY_MATCHING,
    "UNIT_VARIATION": FailureMode.NO_FUZZY_MATCHING,
    "NATURAL_LANGUAGE": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "SEMANTIC_MEANING": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "SUBJECTIVE_ATTRIBUTE": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "OCCASION": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "SEASONAL_OCCASION": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "LONG_VERBOSE_QUERY": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "STOP_WORD_HEAVY": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "SYNONYM": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "ABBREVIATION": FailureMode.NO_SEMANTIC_UNDERSTANDING,
    "CATEGORY_MAPPING": FailureMode.CATEGORY_MAPPING_FAILURE,
    "LOCALE_VARIATION": FailureMode.CATEGORY_MAPPING_FAILURE,
    "BROAD_CATEGORY": FailureMode.CATEGORY_MAPPING_FAILURE,
    "PRICE_ANCHORED": FailureMode.FACET_NOT_EXTRACTED,
    "MULTI_ATTRIBUTE": FailureMode.FACET_NOT_EXTRACTED,
    "FACET_EXTRACTION": FailureMode.FACET_NOT_EXTRACTED,
    "NEGATIVE_INTENT": FailureMode.CONSTRAINT_DROPPED,
}

_ZERO_REASON: dict[str, str] = {
    "TYPO": "The search does not correct the spelling, so a small typo ends on an empty page.",
    "SPLIT_WORD": "The search does not join the split word back into the real term (failed normalization).",
    "MERGED_WORDS": "The search does not split the merged word back into the real terms (failed normalization).",
    "SPECIAL_CHARACTER": "The search does not normalize special characters or spacing, so the variant spelling matches nothing.",
    "PARTIAL_QUERY": "The search does not complete the partial word to the product or brand it starts.",
    "PLURAL_SINGULAR": "The search does not treat singular and plural forms as the same word.",
    "UNIT_VARIATION": "The search does not normalize how sizes and units are written.",
    "CATEGORY_MAPPING_FAILURE": "The term is not connected to the matching product category.",
    "NO_SEMANTIC_UNDERSTANDING": "The search matches words literally and does not interpret what the shopper describes.",
    "PRICE_ANCHORED": "The price limit is read as search words instead of a price filter, so nothing matches.",
    "FACET_NOT_EXTRACTED": "The attribute is read as a required search word instead of a filter, so nothing matches.",
    "CONSTRAINT_DROPPED": "The exclusion is treated as a search word instead of an exclusion, so nothing matches.",
    "ZERO_RESULTS_OR_GARBAGE": "Shoppers who search this way see an empty page.",
}

_ZERO_FIX: dict[str, str] = {
    "NO_FUZZY_MATCHING": ("Add spelling tolerance and normalization (typo correction, compound splitting/joining, "
                          "singular/plural and character folding) so near-miss spellings reach the intended products."),
    "NO_SEMANTIC_UNDERSTANDING": ("Add synonym and intent handling (query rewriting or semantic retrieval) so "
                                  "descriptive phrasing reaches the products it describes, and fall back to the "
                                  "query's product term instead of an empty page."),
    "CATEGORY_MAPPING_FAILURE": ("Index category names and their common synonyms as searchable terms, or route "
                                 "matching queries to the category page."),
    "FACET_NOT_EXTRACTED": ("Parse filter words (price, colour, material, size) out of the query and apply them as "
                            "filters on the product-term results, instead of requiring them as keywords."),
    "CONSTRAINT_DROPPED": ("Parse negation words ('not', 'without', 'ohne', 'utan', …) and filter matching products "
                           "out, instead of requiring the negation word as a keyword."),
    "ZERO_RESULTS_OR_GARBAGE": ("Make sure the query reaches the products it names; when nothing matches, show "
                                "close alternatives instead of an empty page."),
}


def _control_titles(control: FetchOutcome | None, n: int = 5) -> list[str]:
    if not control or not control.trusted:
        return []
    return [r.title for r in control.results if (r.title or "").strip() and not getattr(r, "sponsored", False)][:n]


def _control_is_zero(control: FetchOutcome | None) -> bool:
    """Control also found nothing: the control page was observed and shows no products.

    A control that timed out, was blocked or errored proves nothing about the catalog — treating
    it as empty would turn a real zero-result failure into an unscored "catalog gap" because of
    a network blip. Those fall through to the "catalog gap not ruled out" path instead.
    """
    if control is None or control.results:
        return False
    return control.status in ("zero_confirmed", "zero_unverified")


def _make(tq, results, st: _State, *, judge_status: str, stats, fetch_outcome, excluded_reason=None) -> QueryJudgment:
    max_rel, top3, disp = stats
    ev, ev_changed = _client_text(st.evidence)
    fix, fix_changed = _client_text(st.fix)
    notes = list(st.notes)
    if ev_changed:
        notes.append("Raw evidence: " + (st.evidence or "").strip())
    if fix_changed:
        notes.append("Raw fix: " + (st.fix or "").strip())
    if not ev and (st.evidence or "").strip():
        ev = f"See the results shown for '{tq.query}'."
    return QueryJudgment(
        test_query=tq,
        results=results,
        failure_mode=st.fm,
        failure_mode_explanation=st.expl,
        severity=st.sev,
        evidence=ev,
        recommended_fix=fix,
        displacement=disp,
        max_relevance_score=max_rel,
        top3_original_average=top3,
        judge_status=judge_status,
        excluded_reason=excluded_reason,
        internal_notes="\n".join(notes) if notes else None,
        fetch_status=_val(fetch_outcome.status) if fetch_outcome is not None else None,
        total_hits=fetch_outcome.total_hits if fetch_outcome is not None else None,
    )


def _zero_judgment(tq: TestQuery, results, cat: str, site_categories, control, fetch_outcome, stats) -> QueryJudgment:
    """Deterministic verdict for a trusted zero-result page (no LLM, no inventory claims)."""
    if control is not None and _control_is_zero(control):
        st = _State(FailureMode.OTHER, Severity.PASS,
                    evidence=(f"Searching '{tq.query}' returns no results, and searching the plain term "
                              f"'{tq.target_term}' returns none either — the store does not appear to stock this, "
                              f"so it is not counted as a search failure."),
                    fix="",
                    notes=[f"Excluded: catalog gap (control '{tq.target_term}' status {_val(control.status)}, 0 results)."])
        return _make(tq, results, st, judge_status="deterministic", stats=stats,
                     fetch_outcome=fetch_outcome, excluded_reason="catalog_gap")

    fm = _ZERO_FAILURE_MODE.get(cat, FailureMode.ZERO_RESULTS_OR_GARBAGE)
    notes = [f"Zero results; failure mode mapped by category {cat} -> {fm.value}."]
    reason = _ZERO_REASON.get(cat) or _ZERO_REASON.get(fm.value, "")
    fix = _ZERO_FIX.get(fm.value, _ZERO_FIX["ZERO_RESULTS_OR_GARBAGE"])

    matched_cat = None
    if cat in _CATEGORY_RECLASS_CATEGORIES and len(_sig_tokens(tq.query)) <= _SINGLE_CONCEPT_MAX_TOKENS:
        matched_cat = _resembles_site_category(tq.query, site_categories, cat)
    if matched_cat:
        fm = FailureMode.CATEGORY_MAPPING_FAILURE
        reason = f"The site has a '{matched_cat}' category, but search does not connect this term to it."
        fix = (f"Map this term to the existing '{matched_cat}' category: index category names and their "
               f"synonyms as searchable terms, or route matching queries to that category page.")
        notes.append(f"Resembles site category '{matched_cat}'.")
    if cat == "NEGATIVE_INTENT":
        terms = _excluded_terms(tq)
        neg = next((t for t in _tokens(tq.query) if t in _NEGATION_WORDS), None)
        if neg:
            reason = f"The exclusion word '{neg}' is treated as a search word instead of an exclusion, so nothing matches."
        elif terms:
            reason = _ZERO_REASON["CONSTRAINT_DROPPED"]

    evidence = f"Searching '{tq.query}' returns no results. {reason}"
    ctrl = _control_titles(control, 2)
    if ctrl:
        evidence += (f" Searching '{tq.target_term}' returns products such as "
                     + " and ".join(f"'{_short(t)}'" for t in ctrl) + ", so the store does stock what the shopper wants.")
    elif control is None:
        notes.append("No control search for this query: a catalog gap is not ruled out — verify before publishing.")
    else:
        notes.append(f"Control search untrusted (status {_val(control.status)}); catalog gap not ruled out.")

    st = _State(fm, Severity.CRITICAL, evidence=evidence, fix=fix, notes=notes)
    return _make(tq, results, st, judge_status="deterministic", stats=stats, fetch_outcome=fetch_outcome)


def _gibberish_judgment(tq, results, fetch_outcome, stats) -> QueryJudgment:
    org = sorted(_organic(results), key=lambda r: r.original_rank)
    n = (fetch_outcome.total_hits if fetch_outcome is not None and fetch_outcome.total_hits else None) or len(org)
    if not org:
        st = _State(FailureMode.OTHER, Severity.PASS,
                    evidence=(f"The keyboard-mash query '{tq.query}' returns no results — the correct behaviour, so "
                              f"shoppers who mistype get a clear no-results state."),
                    fix="", notes=["GIBBERISH zero -> PASS (correct behaviour)."])
    else:
        examples = " and ".join(f"'{_short(r.title, 45)}'" for r in org[:2])
        st = _State(FailureMode.ZERO_RESULTS_OR_GARBAGE, Severity.CRITICAL,
                    evidence=(f"The keyboard-mash query '{tq.query}' returns {n} products, such as {examples}. The "
                              f"store has no no-results state: a shopper who mistypes lands on unrelated products, and "
                              f"search analytics cannot tell real demand from noise."),
                    fix=("Set a minimum match threshold so queries that match nothing return an honest no-results "
                         "page with suggestions, instead of a populated grid."),
                    notes=["GIBBERISH with populated grid -> CRITICAL (deterministic)."])
    return _make(tq, results, st, judge_status="deterministic", stats=stats, fetch_outcome=fetch_outcome)


def _excluded_judgment(tq, results, reason: str, note: str, fetch_outcome, stats) -> QueryJudgment:
    st = _State(FailureMode.OTHER, Severity.PASS,
                evidence=f"Not scored: the results page for '{tq.query}' could not be read reliably.",
                fix="", notes=[note])
    return _make(tq, results, st, judge_status="deterministic", stats=stats,
                 fetch_outcome=fetch_outcome, excluded_reason=reason)


def _fallback_state(tq: TestQuery, results: list[ScoredResult], error: str | None) -> _State:
    """Stats-only base verdict when the LLM produced nothing usable (guards run afterwards)."""
    org = sorted(_organic(results), key=lambda r: r.original_rank)
    max_rel, _, disp = _compute_stats(results)
    if max_rel < WEAK_SET_MAX:
        fm, sev = FailureMode.ZERO_RESULTS_OR_GARBAGE, Severity.CRITICAL
    elif disp > 6:
        fm = FailureMode.POOR_RANKING
        sev = (Severity.MINOR if _displacement_is_cosmetic(results)
               else Severity.CRITICAL if _ranking_materially_broken(results) else Severity.MODERATE)
    elif disp > 2:
        fm = FailureMode.POOR_RANKING
        sev = Severity.MINOR if _displacement_is_cosmetic(results) else Severity.MODERATE
    else:
        fm, sev = FailureMode.OTHER, Severity.PASS
    shown = ", ".join(f"'{_short(r.title, 45)}'" for r in org[:3])
    return _State(
        fm, sev,
        evidence=f"The first results shown for '{tq.query}' are {shown}.",
        fix=("Review this query's results against the shopper's intent." if sev != Severity.PASS else ""),
        notes=[f"FALLBACK: LLM verdict unavailable ({error}); stats-only verdict — review before publishing."],
    )


# ---------------------------------------------------------------------------
# Single-query judge
# ---------------------------------------------------------------------------


def _judge_single_query(
    test_query: TestQuery,
    results: list[ScoredResult],
    language: str | None = None,
    site_categories: list[str] | None = None,
    site_brands: list[str] | None = None,
    *,
    fetch_outcome: FetchOutcome | None = None,
    control_outcome: FetchOutcome | None = None,
    domain: str | None = None,
) -> QueryJudgment:
    """Judge one query: exclusions and zero/gibberish pages deterministically, else LLM + guards."""
    cat = _val(test_query.category)
    results = list(results or [])
    stats = _compute_stats(results)

    if fetch_outcome is not None and _val(fetch_outcome.status) not in TRUSTED_FETCH_STATUSES:
        return _excluded_judgment(test_query, results, "fetch_unverified",
                                  f"Excluded: fetch status {_val(fetch_outcome.status)} ({fetch_outcome.evidence}).",
                                  fetch_outcome, stats)
    if fetch_outcome is not None and fetch_outcome.results and not results:
        return _excluded_judgment(test_query, results, "fetch_unverified",
                                  f"Excluded: {len(fetch_outcome.results)} results fetched but none scored.",
                                  fetch_outcome, stats)

    if cat == "GIBBERISH":
        return _gibberish_judgment(test_query, results, fetch_outcome, stats)
    if not results:
        return _zero_judgment(test_query, results, cat, site_categories, control_outcome, fetch_outcome, stats)

    max_rel, top3_avg, disp = stats
    kb_section = ""
    if language:
        examples = judge_kb.load_calibration_examples(language, cat, test_query.query, domain=domain,
                                                      rules_version=JUDGE_RULES_VERSION)
        kb_section = judge_kb.format_calibration_section(examples)

    det_lines: list[str] = []
    price_bad, n_priced, label = _price_violations(test_query, results)
    if label:
        det_lines.append(f"Price limit {label}: {len(price_bad)} of {n_priced} priced organic results violate it"
                         + (f" (e.g. '{_short(price_bad[0].title)}' at {price_bad[0].price})" if price_bad else "") + ".")
    if cat == "NEGATIVE_INTENT" or (test_query.constraints and test_query.constraints.exclude):
        frac, bad, term = _exclusion_violations(test_query, results, site_categories, language)
        if term:
            det_lines.append(f"Excluded term '{term}': {len(bad)} of {len(_organic(results))} organic titles contain it"
                             + (f" (e.g. '{_short(bad[0].title)}')" if bad else "") + ".")
    if cat in ("MULTI_ATTRIBUTE", "FACET_EXTRACTION"):
        cbad = _colour_violations(test_query, results, language)
        if cbad:
            det_lines.append("Titles naming a different colour: " + "; ".join(f"'{_short(r.title, 50)}'" for r in cbad[:3]) + ".")
        unv = _unverifiable_constraint_token(test_query, results, language)
        if unv:
            det_lines.append(f"'{unv}' appears in no title (any language/synonym): cannot be confirmed from titles.")

    control_titles = _control_titles(control_outcome)
    prompt = _build_prompt(test_query, results, max_rel, top3_avg, disp, kb_section,
                           total_hits=fetch_outcome.total_hits if fetch_outcome is not None else None,
                           det_lines=det_lines, control_titles=control_titles)
    verdict, fm, sev, error = _llm_verdict(_SYSTEM_MESSAGE, prompt)

    if verdict is None:
        st = _fallback_state(test_query, results, error)
        judge_status = "fallback"
    else:
        st = _State(fm, sev, evidence=verdict.evidence or "", fix=verdict.recommended_fix or "",
                    expl=verdict.failure_mode_explanation, cited=list(verdict.cited_results or []))
        if verdict.observations:
            st.notes.append("Judge observations: " + verdict.observations.strip())
        judge_status = "llm"

    st.notes.insert(0, f"stats: max {max_rel:.3f}, top1 {_top1_seen_relevance(results):.3f}, "
                       f"gap {_relevance_gap(results):.3f}, best {disp} organic slots down, top3 {top3_avg:.3f}; "
                       f"rules {JUDGE_RULES_VERSION}")
    _apply_guards(st, _Ctx(test_query, cat, results, language, site_categories, site_brands, verdict is not None))
    return _make(test_query, results, st, judge_status=judge_status, stats=stats, fetch_outcome=fetch_outcome)


def needs_manual_check(judgment: QueryJudgment) -> bool:
    """True when the operator must verify this verdict before publishing (fallback or MANUAL CHECK note)."""
    return judgment.judge_status == "fallback" or "MANUAL CHECK" in (judgment.internal_notes or "")


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def judge_all_queries(
    queries: list[TestQuery],
    scored_results: dict[str, list[ScoredResult]],
    language: str | None = None,
    provenance: dict | None = None,
    site_categories: list[str] | None = None,
    site_brands: list[str] | None = None,
    fetch_outcomes: dict[str, FetchOutcome] | None = None,
    control_outcomes: dict[str, FetchOutcome] | None = None,
) -> list[QueryJudgment]:
    """Judge every query's results and produce QueryJudgment objects.

    * Identical queries (case/whitespace-insensitive) are judged once.
    * ``fetch_outcomes`` (keyed by query): untrusted fetches are excluded ('fetch_unverified');
      fetch_status / total_hits are copied onto each judgment.
    * ``control_outcomes`` (keyed by the ORIGINAL query; value = search for its target_term):
      a zero page whose control is also zero is excluded as 'catalog_gap'; a control with
      products is the only basis on which evidence may say the store stocks the item.
    * When ``language`` is given, calibration examples from the per-language KB anchor each
      verdict and this run's clean LLM verdicts are harvested as PENDING records.
    """
    seen: set[str] = set()
    unique: list[TestQuery] = []
    for tq in queries:
        key = _norm_query(tq.query)
        if key in seen:
            logger.warning("Skipping duplicate query '%s' (already judged in this run)", tq.query)
            continue
        seen.add(key)
        unique.append(tq)

    domain = (provenance or {}).get("domain")
    judgments: list[QueryJudgment] = []
    total = len(unique)
    severity_counts: Counter[str] = Counter()

    for i, tq in enumerate(unique, 1):
        results = scored_results.get(tq.query, [])
        logger.info("[%d/%d] Judging: '%s' (%d results)", i, total, tq.query, len(results))
        judgment = _judge_single_query(
            tq, results, language=language, site_categories=site_categories, site_brands=site_brands,
            fetch_outcome=(fetch_outcomes or {}).get(tq.query),
            control_outcome=(control_outcomes or {}).get(tq.query),
            domain=domain,
        )
        judgments.append(judgment)
        sev_short = _sev_short(judgment.severity)
        tag = f" [excluded: {judgment.excluded_reason}]" if judgment.excluded_reason else ""
        logger.info("%s %s | %s | %s | '%s'%s", _SEVERITY_EMOJI.get(_val(judgment.severity), "[ ]"), sev_short,
                    _val(judgment.failure_mode), judgment.judge_status, tq.query, tag)
        if not judgment.excluded_reason:
            severity_counts[sev_short] += 1

    logger.info(
        "Judging complete: %d queries (%d excluded) — CRITICAL: %d, MODERATE: %d, MINOR: %d, PASS: %d, fallback: %d",
        total, sum(1 for j in judgments if j.excluded_reason),
        severity_counts.get("CRITICAL", 0), severity_counts.get("MODERATE", 0),
        severity_counts.get("MINOR", 0), severity_counts.get("PASS", 0),
        sum(1 for j in judgments if j.judge_status == "fallback"),
    )

    if language:
        judge_kb.harvest(judgments, language, provenance, model=_MODEL, domain=domain,
                         rules_version=JUDGE_RULES_VERSION)
    return judgments


# ---------------------------------------------------------------------------
# CLI demo (makes real API calls)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    demo_q = TestQuery(category="NEGATIVE_INTENT", query="running shoes not Nike",
                       rationale="Exclusion constraint — Nike results should NOT appear")
    demo_r = [
        ScoredResult(rank=1, title="Nike Pegasus 40 Running Shoe", price="$130.00", relevance_score=0.35, original_rank=1),
        ScoredResult(rank=2, title="Adidas Ultraboost 22 Running", price="$190.00", relevance_score=0.82, original_rank=2),
        ScoredResult(rank=3, title="Nike Vomero 17", price="$160.00", relevance_score=0.30, original_rank=3),
    ]
    for j in judge_all_queries([demo_q], {demo_q.query: demo_r}):
        print(_sev_short(j.severity), _val(j.failure_mode), j.judge_status)
        print("  evidence:", j.evidence)
        print("  notes:", j.internal_notes)
