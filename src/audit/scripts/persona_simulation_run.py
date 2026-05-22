"""
Persona-driven search simulation for shop-apotheke.com
-------------------------------------------------------
Runs the reformulation sequence for all 5 personas against the live site,
spot-checks DocMorris on the worst queries, then outputs structured JSON
ready for the report builder.

Output: reports/persona_simulation/persona_simulation_<timestamp>_data.json
"""
from __future__ import annotations

import json
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

from src.fetcher import fetch_all_results
from src.models import TestQuery, SearchResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search URL templates
# ---------------------------------------------------------------------------
SHOP_APO_TEMPLATE = (
    "https://www.shop-apotheke.com/search.htm?"
    "eventName=search-submit&i=1&searchChannel=algolia&q={}"
)
DOCMORRIS_TEMPLATE = "https://www.docmorris.de/suche?q={}"

# ---------------------------------------------------------------------------
# Persona definitions
# Each persona has:
#   - key: machine identifier
#   - name: human first name for narrative
#   - archetype: display label
#   - scroll_threshold, reformulation_tolerance: behavioral params
#   - basket_value: estimated EUR basket on successful session
#   - trust_triggers: what makes FOUND
#   - distrust_triggers: what makes NOTHING regardless of result count
#   - queries: ordered reformulation sequence (Q1 = entry, Q2+ = reformulations)
#     Each query: {q, category, intent_label, expected_failure}
# ---------------------------------------------------------------------------
PERSONAS = [
    {
        "key": "anxious_young_mother",
        "name": "Lena",
        "archetype": "Anxious Young Mother (Besorgte Junge Mutter)",
        "age": "29, Berlin",
        "scroll_threshold": 3,
        "reformulation_tolerance": 3,
        "basket_value": 35,
        "found_condition": "Baby/Kleinkind product in top 3, no Rx, no books",
        "nothing_triggers": ["books dominant", "Rx product in top 1-2", "adult products only"],
        "queries": [
            {
                "q": "Baby schläft nicht was hilft",
                "category": "NATURAL_LANGUAGE",
                "intent_label": "Q1 — symptom/life-stage entry",
                "expected_failure": "Books or adult sleep aids in results; no life-stage routing",
                "docmorris_spot_check": True,
            },
            {
                "q": "Baby Schlaf Tropfen natürlich",
                "category": "USE_CASE",
                "intent_label": "Q2 — adds form + natural qualifier",
                "expected_failure": "Negation handling absent; mixed adult/baby",
                "docmorris_spot_check": False,
            },
            {
                "q": "Viburcol Zäpfchen Baby",
                "category": "BRAND_SEARCH",
                "intent_label": "Q3 — brand recovery (forum-recommended)",
                "expected_failure": "Should work; brand rescue layer",
                "docmorris_spot_check": False,
            },
            {
                "q": "Baby Einschlafen ohne Tabletten",
                "category": "NEGATIVE_INTENT",
                "intent_label": "Q4 — negation qualifier",
                "expected_failure": "ohne Tabletten ignored; prescription sleep aids surface",
                "docmorris_spot_check": True,
            },
        ],
    },
    {
        "key": "wellness_optimizer",
        "name": "Mia",
        "archetype": "Wellness Optimizer (Wellness-Optimierer)",
        "age": "34, München",
        "scroll_threshold": 7,
        "reformulation_tolerance": 4,
        "basket_value": 110,
        "found_condition": "Ingredient + form + dosage visible in tile; supplement-native brand",
        "nothing_triggers": ["pharma brands dominant for supplement query", "form undifferentiated"],
        "queries": [
            {
                "q": "Magnesium Bisglycinat 300mg",
                "category": "MULTI_ATTRIBUTE",
                "intent_label": "Q1 — ingredient + form + dosage",
                "expected_failure": "Form not indexed as structured attribute; Bisglycinat/Citrat/Oxid mixed",
                "docmorris_spot_check": True,
            },
            {
                "q": "Magnesium Bisglycinat Kapseln",
                "category": "FACET_EXTRACTION",
                "intent_label": "Q2 — adds form qualifier",
                "expected_failure": "Still undifferentiated; pharma brands dominate",
                "docmorris_spot_check": False,
            },
            {
                "q": "Sunday Natural Magnesium",
                "category": "BRAND_SEARCH",
                "intent_label": "Q3 — brand recovery",
                "expected_failure": "Brand rescue layer; may or may not work",
                "docmorris_spot_check": False,
            },
            {
                "q": "Magnesium gut verträglich kein Durchfall",
                "category": "NEGATIVE_INTENT",
                "intent_label": "Q4 — negation/tolerance qualifier",
                "expected_failure": "kein ignored; all Magnesium forms returned",
                "docmorris_spot_check": True,
            },
        ],
    },
    {
        "key": "elderly_patient",
        "name": "Werner",
        "archetype": "Elderly Patient / Caregiver (Älterer Patient)",
        "age": "71, rural Bavaria",
        "scroll_threshold": 4,
        "reformulation_tolerance": 2,
        "basket_value": 45,
        "found_condition": "Exact product name + exact pack size in top result",
        "nothing_triggers": ["wrong pack size in top result", "different dosage form", "generic when brand searched"],
        "queries": [
            {
                "q": "Aspirin protect 100mg 100 Stück",
                "category": "DIRECT_MATCH",
                "intent_label": "Q1 — exact product + pack size",
                "expected_failure": "Pack size not factored into ranking; 50-Stück before 100-Stück",
                "docmorris_spot_check": True,
            },
            {
                "q": "Ibuprofen 400mg ratiopharm 50 Stück",
                "category": "DIRECT_MATCH",
                "intent_label": "Q2 — exact generic + manufacturer + size",
                "expected_failure": "Branded Ibuprofen may dominate over ratiopharm",
                "docmorris_spot_check": False,
            },
            {
                "q": "Inkontinenzeinlagen Nacht starke Saugfähigkeit",
                "category": "MULTI_ATTRIBUTE",
                "intent_label": "Q3 — medical device multi-attribute",
                "expected_failure": "Hilfsmittel category poorly indexed; sparse or irrelevant results",
                "docmorris_spot_check": True,
            },
            {
                "q": "Katheter Einmalkatheter Charriere 14",
                "category": "SKU_MODEL_NUMBER",
                "intent_label": "Q4 — medical device with clinical spec",
                "expected_failure": "Clinical nomenclature (Charriere) absent from index",
                "docmorris_spot_check": False,
            },
        ],
    },
    {
        "key": "acute_self_treater",
        "name": "Jonas",
        "archetype": "Acute Self-Treater (Akutbehandler)",
        "age": "31, Hamburg",
        "scroll_threshold": 3,
        "reformulation_tolerance": 2,
        "basket_value": 8,
        "found_condition": "Known OTC brand or symptom term in top 1-2, OTC label clear",
        "nothing_triggers": ["Rx product in top 3", "books in results", "result count 300+"],
        "queries": [
            {
                "q": "Halsschmerzen schlucken schmerzt",
                "category": "NATURAL_LANGUAGE",
                "intent_label": "Q1 — symptom entry (cognitively impaired state)",
                "expected_failure": "300+ results, no OTC hierarchy; Rx products mixed in",
                "docmorris_spot_check": True,
            },
            {
                "q": "Strepsils Halsschmerzen",
                "category": "BRAND_SEARCH",
                "intent_label": "Q2 — brand recovery",
                "expected_failure": "Rx variant (Strepsils Intensive) may surface before OTC",
                "docmorris_spot_check": False,
            },
            {
                "q": "Gedankenkarussell nachts",
                "category": "SEMANTIC_MEANING",
                "intent_label": "Q3 — colloquial symptom (from UC13)",
                "expected_failure": "CONFIRMED: Wick Erkältungssirup as top result",
                "docmorris_spot_check": True,
            },
            {
                "q": "Erkältung schnell loswerden",
                "category": "USE_CASE",
                "intent_label": "Q4 — outcome-oriented query",
                "expected_failure": "Outcome intent; no product mapping",
                "docmorris_spot_check": False,
            },
        ],
    },
    {
        "key": "alternative_medicine_seeker",
        "name": "Petra",
        "archetype": "Alternative Medicine Seeker (Naturheilkunde-Anhängerin)",
        "age": "48, Baden-Württemberg",
        "scroll_threshold": 6,
        "reformulation_tolerance": 3,
        "basket_value": 55,
        "found_condition": "Exact product + correct potency notation + trusted manufacturer (DHU/Weleda/Heel)",
        "nothing_triggers": ["conventional pharma dominant for homeopathy query", "incorrect potency in result", "no Homöopathie category"],
        "queries": [
            {
                "q": "Nux vomica D12 Globuli",
                "category": "DIRECT_MATCH",
                "intent_label": "Q1 — exact homeopathic nomenclature + potency",
                "expected_failure": "Potency (D12) not indexed as structured attribute",
                "docmorris_spot_check": True,
            },
            {
                "q": "Globuli Kinder Schlaf",
                "category": "USE_CASE",
                "intent_label": "Q2 — life-stage + homeopathy",
                "expected_failure": "Life-stage routing absent; conventional sleep aids surface",
                "docmorris_spot_check": False,
            },
            {
                "q": "Schüssler Salze Nr 7 Magnesium phosphoricum",
                "category": "SYNONYM",
                "intent_label": "Q3 — Schüssler number + mineral name",
                "expected_failure": "Nr 7 not synonymized to Magnesium phosphoricum",
                "docmorris_spot_check": True,
            },
            {
                "q": "Bachblüten Mischung Angst",
                "category": "MULTI_ATTRIBUTE",
                "intent_label": "Q4 — compound intent within alternative category",
                "expected_failure": "Bach flower category thin or absent; conventional anxiolytics surface",
                "docmorris_spot_check": False,
            },
        ],
    },
]

# Pull out only the queries flagged for DocMorris spot-check
DOCMORRIS_SPOT_QUERIES = [
    q for p in PERSONAS for q in p["queries"] if q.get("docmorris_spot_check")
]


def build_test_queries(persona: dict) -> list[TestQuery]:
    return [
        TestQuery(
            category=q["category"],
            query=q["q"],
            rationale=f"[{persona['key']}] {q['intent_label']} — {q['expected_failure']}",
        )
        for q in persona["queries"]
    ]


def serialize_results(results: list[SearchResult]) -> list[dict]:
    return [
        {
            "rank": r.rank,
            "title": r.title,
            "price": r.price,
            "snippet": r.snippet,
            "url": r.url,
        }
        for r in results
    ]


def assess_state(
    results: list[SearchResult],
    persona: dict,
    query_def: dict,
) -> str:
    """
    Heuristic state assessment against persona criteria.
    Returns FOUND / PARTIAL / NOTHING.

    Rules applied in order:
    1. Zero results or very thin → NOTHING
    2. Active distrust triggers in top 3 titles → NOTHING
    3. Scroll threshold check — if good results exist but are buried → PARTIAL
    4. Top 3 look credibly on-topic → FOUND
    """
    if not results or len(results) < 2:
        return "NOTHING"

    top3_titles = " ".join(r.title.lower() for r in results[:3])
    top1_title = results[0].title.lower() if results else ""

    # Distrust trigger checks (persona-specific)
    key = persona["key"]

    if key == "anxious_young_mother":
        if any(t in top1_title for t in ["buch", "book", "roman", "rezept", "erwachsene"]):
            return "NOTHING"
        if "rx" in top1_title or "rezeptpflichtig" in top1_title:
            return "NOTHING"
        if any(t in top3_titles for t in ["baby", "kleinkind", "säugling", "kinder"]):
            return "FOUND"
        return "PARTIAL"

    if key == "wellness_optimizer":
        pharma_brands = ["ratiopharm", "hexal", "stada", "ct-arzneimittel", "aliud"]
        if sum(1 for b in pharma_brands if b in top3_titles) >= 2:
            return "PARTIAL"
        target_form = query_def["q"].lower()
        if "bisglycinat" in target_form and "bisglycinat" not in top3_titles:
            return "PARTIAL"
        if "sunday natural" in top3_titles or "natugena" in top3_titles:
            return "FOUND"
        if len(results) >= 3:
            return "PARTIAL"
        return "NOTHING"

    if key == "elderly_patient":
        query_lower = query_def["q"].lower()
        if "100 stück" in query_lower and "100 stück" not in top3_titles and "100st" not in top3_titles:
            return "PARTIAL"
        if "charriere" in query_lower and "charriere" not in top3_titles and "ch " not in top3_titles:
            return "NOTHING"
        if len(results) < 2:
            return "NOTHING"
        return "FOUND"

    if key == "acute_self_treater":
        rx_signals = ["rezeptpflichtig", "verschreibungspflichtig", "rx", "zopiclon", "modafinil"]
        if any(sig in top1_title for sig in rx_signals):
            return "NOTHING"
        if any(t in top1_title for t in ["buch", "book", "sirup erkältung", "wick medinait"]):
            return "NOTHING"
        known_otc = ["strepsils", "grippostad", "ibuflam", "aspirin", "neo-angin", "lemocin", "wick"]
        if any(b in top3_titles for b in known_otc):
            return "FOUND"
        if len(results) >= 5:
            return "PARTIAL"
        return "NOTHING"

    if key == "alternative_medicine_seeker":
        conventional = ["ibuprofen", "paracetamol", "diclofenac", "aspirin", "lorazepam", "zopiclon"]
        if sum(1 for c in conventional if c in top3_titles) >= 2:
            return "NOTHING"
        alt_brands = ["dhu", "weleda", "heel", "wala", "staufen"]
        potency_signals = ["d6", "d12", "c30", "c12", "lm", "globuli", "granulat"]
        if any(b in top3_titles for b in alt_brands) and any(p in top3_titles for p in potency_signals):
            return "FOUND"
        if any(t in top3_titles for t in ["globuli", "schüssler", "bachblüten", "homöo"]):
            return "PARTIAL"
        return "NOTHING"

    # Generic fallback
    return "PARTIAL" if results else "NOTHING"


def run_simulation() -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / "persona_simulation"
    out_dir.mkdir(parents=True, exist_ok=True)

    simulation_output = {
        "timestamp": timestamp,
        "personas": [],
        "docmorris_spot_checks": {},
        "summary": {},
    }

    # -----------------------------------------------------------------------
    # Phase 1: shop-apotheke runs per persona
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  PHASE 1 — shop-apotheke.com persona queries")
    print("=" * 60)

    for persona in PERSONAS:
        print(f"\n→ Persona: {persona['name']} ({persona['archetype']})")
        queries = build_test_queries(persona)

        raw_results = fetch_all_results(
            SHOP_APO_TEMPLATE,
            queries,
            max_results=10,
        )

        persona_result = {
            "key": persona["key"],
            "name": persona["name"],
            "archetype": persona["archetype"],
            "age": persona["age"],
            "basket_value": persona["basket_value"],
            "scroll_threshold": persona["scroll_threshold"],
            "reformulation_tolerance": persona["reformulation_tolerance"],
            "found_condition": persona["found_condition"],
            "nothing_triggers": persona["nothing_triggers"],
            "queries": [],
            "session_outcome": None,
            "reformulations_used": 0,
        }

        reformulations = 0
        session_resolved = False

        for i, q_def in enumerate(persona["queries"]):
            q_str = q_def["q"]
            results = raw_results.get(q_str, [])
            state = assess_state(results, persona, q_def)

            q_result = {
                "step": i + 1,
                "query": q_str,
                "intent_label": q_def["intent_label"],
                "expected_failure": q_def["expected_failure"],
                "result_count": len(results),
                "top5": serialize_results(results[:5]),
                "state": state,
            }
            persona_result["queries"].append(q_result)

            print(f"  Q{i+1}: '{q_str[:55]}' → {len(results)} results → {state}")

            if state == "FOUND" and not session_resolved:
                session_resolved = True
                persona_result["session_outcome"] = "CONVERTED"
                break

            if state in ("PARTIAL", "NOTHING") and not session_resolved:
                reformulations += 1
                if reformulations >= persona["reformulation_tolerance"] and not session_resolved:
                    # Wellness Optimizer: split basket, not hard abandon
                    if persona["key"] == "wellness_optimizer":
                        persona_result["session_outcome"] = "SPLIT_BASKET"
                    else:
                        persona_result["session_outcome"] = "ABANDONED"
                    session_resolved = True

        if not session_resolved:
            persona_result["session_outcome"] = "ABANDONED"

        persona_result["reformulations_used"] = reformulations
        simulation_output["personas"].append(persona_result)

        # Pause between personas to be polite to the server
        time.sleep(3)

    # -----------------------------------------------------------------------
    # Phase 2: DocMorris spot-checks
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  PHASE 2 — DocMorris spot-checks (worst queries)")
    print("=" * 60)

    spot_queries = [
        TestQuery(
            category=q["category"],
            query=q["q"],
            rationale=f"DocMorris spot-check: {q['intent_label']}",
        )
        for q in DOCMORRIS_SPOT_QUERIES
    ]

    dm_raw = fetch_all_results(
        DOCMORRIS_TEMPLATE,
        spot_queries,
        max_results=10,
    )

    for q_def in DOCMORRIS_SPOT_QUERIES:
        q_str = q_def["q"]
        results = dm_raw.get(q_str, [])
        print(f"  DocMorris '{q_str[:55]}' → {len(results)} results")
        simulation_output["docmorris_spot_checks"][q_str] = {
            "result_count": len(results),
            "top5": serialize_results(results[:5]),
        }

    # -----------------------------------------------------------------------
    # Phase 3: Summary metrics
    # -----------------------------------------------------------------------
    outcomes = [p["session_outcome"] for p in simulation_output["personas"]]
    total_reformulations = sum(p["reformulations_used"] for p in simulation_output["personas"])
    n_personas = len(PERSONAS)

    simulation_output["summary"] = {
        "total_personas": n_personas,
        "total_queries_run": sum(len(p["queries"]) for p in simulation_output["personas"]),
        "converted": outcomes.count("CONVERTED"),
        "split_basket": outcomes.count("SPLIT_BASKET"),
        "abandoned": outcomes.count("ABANDONED"),
        "avg_reformulations": round(total_reformulations / n_personas, 1),
        "estimated_revenue_lost_per_session": sum(
            p["basket_value"]
            for p in simulation_output["personas"]
            if p["session_outcome"] in ("ABANDONED", "SPLIT_BASKET")
        ),
    }

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    s = simulation_output["summary"]
    print(f"  Converted:         {s['converted']} / {n_personas}")
    print(f"  Split basket:      {s['split_basket']} / {n_personas}")
    print(f"  Hard abandoned:    {s['abandoned']} / {n_personas}")
    print(f"  Avg reformulations:{s['avg_reformulations']}")
    print(f"  Est. revenue lost: €{s['estimated_revenue_lost_per_session']} per equivalent session set")

    # -----------------------------------------------------------------------
    # Write output
    # -----------------------------------------------------------------------
    out_path = out_dir / f"persona_simulation_{timestamp}_data.json"
    out_path.write_text(json.dumps(simulation_output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nData written: {out_path}")

    return simulation_output


if __name__ == "__main__":
    run_simulation()
