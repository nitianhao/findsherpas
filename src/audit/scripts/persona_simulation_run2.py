"""
Persona simulation — Run 2
25 new full sessions (5 per persona), different entry queries, shop-apotheke only.
Same chain structure: entry query + 3 reformulations per session.
"""
from __future__ import annotations

import json
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "src" / "audit"
ROOT = PROJECT_ROOT
sys.path.insert(0, str(AUDIT_ROOT))

from src.fetcher import fetch_all_results
from src.models import TestQuery

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SHOP_APO_TEMPLATE = (
    "https://www.shop-apotheke.com/search.htm?"
    "eventName=search-submit&i=1&searchChannel=algolia&q={}"
)

# ---------------------------------------------------------------------------
# 25 new sessions — 5 per persona, each with 4 queries (entry + 3 reformulations)
# ---------------------------------------------------------------------------
SESSIONS = [
    # ── LENA (Anxious Young Mother) ─────────────────────────────────────────
    {
        "persona_key": "anxious_young_mother",
        "session_id": "lena_s2",
        "theme": "Teething",
        "queries": [
            {"q": "Baby Zähnen was hilft", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom entry"},
            {"q": "Kleinkind Zähnen natürlich Mittel", "category": "USE_CASE", "intent_label": "Q2 — adds natural qualifier"},
            {"q": "Viburcol Globuli Zähnen", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Chamomilla D12 Baby Zähnen", "category": "MULTI_ATTRIBUTE", "intent_label": "Q4 — homeopathic qualifier"},
        ],
    },
    {
        "persona_key": "anxious_young_mother",
        "session_id": "lena_s3",
        "theme": "Baby cold",
        "queries": [
            {"q": "Baby Erkältung 6 Monate", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom + age"},
            {"q": "Schnupfen Baby Nasenspray Kleinkind", "category": "USE_CASE", "intent_label": "Q2 — adds form qualifier"},
            {"q": "Olynth Baby Nasenspray", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Baby Nasenspray ohne Konservierungsstoffe", "category": "NEGATIVE_INTENT", "intent_label": "Q4 — negation qualifier"},
        ],
    },
    {
        "persona_key": "anxious_young_mother",
        "session_id": "lena_s4",
        "theme": "Baby fever",
        "queries": [
            {"q": "Baby Fieber 38 Grad was tun", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom + temperature"},
            {"q": "Fieber Kleinkind Zäpfchen rezeptfrei", "category": "USE_CASE", "intent_label": "Q2 — adds form + OTC"},
            {"q": "Nurofen Baby Zäpfchen 60mg", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Paracetamol Baby Dosierung Säugling", "category": "MULTI_ATTRIBUTE", "intent_label": "Q4 — ingredient + age qualifier"},
        ],
    },
    {
        "persona_key": "anxious_young_mother",
        "session_id": "lena_s5",
        "theme": "Baby skin",
        "queries": [
            {"q": "Baby trockene Haut Creme", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom entry"},
            {"q": "Kleinkind Neurodermitis Creme ohne Kortison", "category": "NEGATIVE_INTENT", "intent_label": "Q2 — negation + condition"},
            {"q": "Weleda Baby Körpercreme", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Baby Creme ohne Parfüm Duftstoffe", "category": "NEGATIVE_INTENT", "intent_label": "Q4 — ingredient exclusion"},
        ],
    },
    {
        "persona_key": "anxious_young_mother",
        "session_id": "lena_s6",
        "theme": "Baby colic",
        "queries": [
            {"q": "Baby Bauchweh schreit Koliken", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom entry"},
            {"q": "Blähungen Baby Tropfen natürlich", "category": "USE_CASE", "intent_label": "Q2 — form + qualifier"},
            {"q": "Lefax Baby Tropfen", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Fenchel Baby Blähungen ohne Alkohol", "category": "NEGATIVE_INTENT", "intent_label": "Q4 — ingredient + exclusion"},
        ],
    },

    # ── MIA (Wellness Optimizer) ─────────────────────────────────────────────
    {
        "persona_key": "wellness_optimizer",
        "session_id": "mia_s2",
        "theme": "Vitamin D3+K2",
        "queries": [
            {"q": "Vitamin D3 K2 Tropfen hochdosiert", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — ingredient combo + form"},
            {"q": "Vitamin D3 5000 IE K2 MK7 Tropfen", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — adds dosage + K2 form"},
            {"q": "Sunday Natural Vitamin D3 K2", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Vitamin D3 K2 laborgeprüft ohne Zusätze", "category": "NEGATIVE_INTENT", "intent_label": "Q4 — certification + exclusion"},
        ],
    },
    {
        "persona_key": "wellness_optimizer",
        "session_id": "mia_s3",
        "theme": "Ashwagandha",
        "queries": [
            {"q": "Ashwagandha KSM-66 Kapseln", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — extract type + form"},
            {"q": "Ashwagandha Extrakt hochdosiert ohne Füllstoffe", "category": "NEGATIVE_INTENT", "intent_label": "Q2 — adds exclusion qualifier"},
            {"q": "Withania somnifera Extrakt Kapseln", "category": "SYNONYM", "intent_label": "Q3 — Latin name reformulation"},
            {"q": "Ashwagandha vegan zertifiziert laborgeprüft", "category": "FACET_EXTRACTION", "intent_label": "Q4 — certification qualifier"},
        ],
    },
    {
        "persona_key": "wellness_optimizer",
        "session_id": "mia_s4",
        "theme": "Omega-3 form specificity",
        "queries": [
            {"q": "Omega 3 EPA DHA hochdosiert", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — ingredient combo + dosage"},
            {"q": "Fischöl EPA DHA 1000mg Triglycerid Form", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — adds oil form qualifier"},
            {"q": "Omega 3 Kapseln ohne Fischgeschmack", "category": "NEGATIVE_INTENT", "intent_label": "Q3 — taste exclusion"},
            {"q": "Omega 3 laborgeprüft Schwermetalle getestet", "category": "FACET_EXTRACTION", "intent_label": "Q4 — purity certification"},
        ],
    },
    {
        "persona_key": "wellness_optimizer",
        "session_id": "mia_s5",
        "theme": "Low-dose melatonin",
        "queries": [
            {"q": "Melatonin 0,5mg niedrig dosiert", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — precise dosage (regulatory limit)"},
            {"q": "Melatonin Kapseln 0,5mg ohne Hilfsstoffe", "category": "NEGATIVE_INTENT", "intent_label": "Q2 — adds excipient exclusion"},
            {"q": "Melatonin niedrigdosiert einschlafen", "category": "USE_CASE", "intent_label": "Q3 — use-case reformulation"},
            {"q": "Melatonin 0.5mg vegan laborgeprüft", "category": "FACET_EXTRACTION", "intent_label": "Q4 — certification qualifier"},
        ],
    },
    {
        "persona_key": "wellness_optimizer",
        "session_id": "mia_s6",
        "theme": "Collagen type specificity",
        "queries": [
            {"q": "Kollagen Hydrolysat Typ II Kapseln", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — type-specific collagen"},
            {"q": "Kollagen Peptide 10g täglich hochdosiert", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — adds dosage qualifier"},
            {"q": "Kollagen Pulver ohne Zucker", "category": "NEGATIVE_INTENT", "intent_label": "Q3 — ingredient exclusion"},
            {"q": "Marine Kollagen Typ I III Pulver", "category": "MULTI_ATTRIBUTE", "intent_label": "Q4 — source + type specificity"},
        ],
    },

    # ── WERNER (Elderly Patient / Caregiver) ─────────────────────────────────
    {
        "persona_key": "elderly_patient",
        "session_id": "werner_s2",
        "theme": "Voltaren exact",
        "queries": [
            {"q": "Voltaren Schmerzgel 150g", "category": "DIRECT_MATCH", "intent_label": "Q1 — brand + pack size"},
            {"q": "Diclofenac Gel 1% 150g", "category": "SYNONYM", "intent_label": "Q2 — generic ingredient + size"},
            {"q": "Voltaren Forte 2,32% Gel", "category": "DIRECT_MATCH", "intent_label": "Q3 — stronger formulation"},
            {"q": "Diclofenac Schmerzgel ratiopharm 150g", "category": "MULTI_ATTRIBUTE", "intent_label": "Q4 — generic + manufacturer + size"},
        ],
    },
    {
        "persona_key": "elderly_patient",
        "session_id": "werner_s3",
        "theme": "Chronic medication reorder",
        "queries": [
            {"q": "Metoprolol 95mg retard 100 Tabletten", "category": "DIRECT_MATCH", "intent_label": "Q1 — exact medication + pack size"},
            {"q": "Metoprolol Succinat 95mg retard", "category": "DIRECT_MATCH", "intent_label": "Q2 — adds salt form qualifier"},
            {"q": "Metoprolol 95mg Heumann retard", "category": "MULTI_ATTRIBUTE", "intent_label": "Q3 — adds manufacturer"},
            {"q": "Beloc ZOK 95mg Tabletten", "category": "BRAND_SEARCH", "intent_label": "Q4 — brand name for same molecule"},
        ],
    },
    {
        "persona_key": "elderly_patient",
        "session_id": "werner_s4",
        "theme": "Wound care supplies",
        "queries": [
            {"q": "Wundauflage saugfähig steril 10x10", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — medical device + spec"},
            {"q": "Wundverband steril 10x10 cm", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — synonym reformulation"},
            {"q": "Mepore Wundauflage 10x10", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Vlies Wundauflage selbstklebend 10x10", "category": "MULTI_ATTRIBUTE", "intent_label": "Q4 — material + adhesive qualifier"},
        ],
    },
    {
        "persona_key": "elderly_patient",
        "session_id": "werner_s5",
        "theme": "Bepanthen reorder",
        "queries": [
            {"q": "Bepanthen Wundcreme 100g", "category": "DIRECT_MATCH", "intent_label": "Q1 — brand + pack size"},
            {"q": "Dexpanthenol Creme 100g", "category": "SYNONYM", "intent_label": "Q2 — ingredient name"},
            {"q": "Bepanthen Plus Creme 100g", "category": "DIRECT_MATCH", "intent_label": "Q3 — variant with antiseptic"},
            {"q": "Panthenol Wundcreme 100g", "category": "SYNONYM", "intent_label": "Q4 — common name variant"},
        ],
    },
    {
        "persona_key": "elderly_patient",
        "session_id": "werner_s6",
        "theme": "Stomach protection",
        "queries": [
            {"q": "Omeprazol 20mg 60 Kapseln", "category": "DIRECT_MATCH", "intent_label": "Q1 — generic + dosage + pack size"},
            {"q": "Omeprazol 20mg Generikum 60 Stück", "category": "DIRECT_MATCH", "intent_label": "Q2 — adds generic qualifier"},
            {"q": "Pantoprazol 20mg 60 Tabletten", "category": "SYNONYM", "intent_label": "Q3 — switch to alternative PPI"},
            {"q": "Magensäureblocker 20mg rezeptfrei 60 Stück", "category": "USE_CASE", "intent_label": "Q4 — category term + OTC"},
        ],
    },

    # ── JONAS (Acute Self-Treater) ────────────────────────────────────────────
    {
        "persona_key": "acute_self_treater",
        "session_id": "jonas_s2",
        "theme": "Headache",
        "queries": [
            {"q": "Kopfschmerzen was nehmen schnell", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom entry"},
            {"q": "Ibuprofen 400mg Kopfschmerzen", "category": "BRAND_SEARCH", "intent_label": "Q2 — ingredient + symptom"},
            {"q": "Aspirin Kopfschmerzen Tabletten", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Kopfschmerzen Tabletten sofort rezeptfrei", "category": "USE_CASE", "intent_label": "Q4 — OTC qualifier + urgency"},
        ],
    },
    {
        "persona_key": "acute_self_treater",
        "session_id": "jonas_s3",
        "theme": "Fever",
        "queries": [
            {"q": "Fieber senken Erwachsene was hilft", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom entry"},
            {"q": "Paracetamol 500mg Fieber Tabletten", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — ingredient + dosage + form"},
            {"q": "Ibuflam 400mg Fieber", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Grippostad Fieber Erkältung", "category": "BRAND_SEARCH", "intent_label": "Q4 — known OTC combo brand"},
        ],
    },
    {
        "persona_key": "acute_self_treater",
        "session_id": "jonas_s4",
        "theme": "Back pain",
        "queries": [
            {"q": "Rückenschmerzen akut was hilft", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom entry"},
            {"q": "Rückenschmerzen Salbe Wärme", "category": "USE_CASE", "intent_label": "Q2 — form + mechanism"},
            {"q": "Voltaren Rücken Schmerzgel", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Wärmepflaster Rücken sofort", "category": "USE_CASE", "intent_label": "Q4 — alternative form"},
        ],
    },
    {
        "persona_key": "acute_self_treater",
        "session_id": "jonas_s5",
        "theme": "Runny nose",
        "queries": [
            {"q": "Schnupfen sofort Hilfe Nasenspray", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom + form"},
            {"q": "Nasenspray abschwellend rezeptfrei", "category": "USE_CASE", "intent_label": "Q2 — mechanism + OTC"},
            {"q": "Otrivin Nasenspray Schnupfen", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Xylometazolin Nasenspray 0,1%", "category": "MULTI_ATTRIBUTE", "intent_label": "Q4 — ingredient + concentration"},
        ],
    },
    {
        "persona_key": "acute_self_treater",
        "session_id": "jonas_s6",
        "theme": "Night cough",
        "queries": [
            {"q": "Husten Nacht schlimmer nicht schlafen", "category": "NATURAL_LANGUAGE", "intent_label": "Q1 — symptom + time context"},
            {"q": "Hustensirup Nacht Erwachsene", "category": "USE_CASE", "intent_label": "Q2 — form + time qualifier"},
            {"q": "ACC 600 Husten Tabletten", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Hustenstiller Nacht rezeptfrei sofort", "category": "USE_CASE", "intent_label": "Q4 — OTC + urgency"},
        ],
    },

    # ── PETRA (Alternative Medicine Seeker) ──────────────────────────────────
    {
        "persona_key": "alternative_medicine_seeker",
        "session_id": "petra_s2",
        "theme": "Belladonna",
        "queries": [
            {"q": "Belladonna C30 Globuli", "category": "DIRECT_MATCH", "intent_label": "Q1 — exact potency + form"},
            {"q": "Belladonna Globuli DHU C30", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — adds manufacturer"},
            {"q": "Belladonna 30C Granulat", "category": "DIRECT_MATCH", "intent_label": "Q3 — form variant"},
            {"q": "Belladonna Homöopathie Fieber Kinder", "category": "USE_CASE", "intent_label": "Q4 — use-case + life-stage"},
        ],
    },
    {
        "persona_key": "alternative_medicine_seeker",
        "session_id": "petra_s3",
        "theme": "Arnica",
        "queries": [
            {"q": "Arnica montana D30 Globuli", "category": "DIRECT_MATCH", "intent_label": "Q1 — Latin name + potency"},
            {"q": "Arnica Globuli D6 DHU", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — lower potency + manufacturer"},
            {"q": "Wala Arnica Globuli", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Arnica Homöopathie Verletzung Prellung", "category": "USE_CASE", "intent_label": "Q4 — indication qualifier"},
        ],
    },
    {
        "persona_key": "alternative_medicine_seeker",
        "session_id": "petra_s4",
        "theme": "Passionsblume anxiety",
        "queries": [
            {"q": "Passionsblume Tabletten Angst Beruhigung", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — herb + indication"},
            {"q": "Pascoflair Passionsblume 425mg", "category": "BRAND_SEARCH", "intent_label": "Q2 — brand recovery"},
            {"q": "Passionsblume Extrakt ohne Alkohol", "category": "NEGATIVE_INTENT", "intent_label": "Q3 — exclusion qualifier"},
            {"q": "Passiflora incarnata Tabletten Schlaf", "category": "SYNONYM", "intent_label": "Q4 — Latin name reformulation"},
        ],
    },
    {
        "persona_key": "alternative_medicine_seeker",
        "session_id": "petra_s5",
        "theme": "Echinacea immune",
        "queries": [
            {"q": "Echinacea Tropfen Immunsystem", "category": "USE_CASE", "intent_label": "Q1 — herb + use-case"},
            {"q": "Echinacin Madaus Tropfen", "category": "BRAND_SEARCH", "intent_label": "Q2 — brand recovery"},
            {"q": "Echinacea purpurea Tinktur", "category": "MULTI_ATTRIBUTE", "intent_label": "Q3 — species + form"},
            {"q": "Sonnenhut Tropfen rezeptfrei Erkältung", "category": "SYNONYM", "intent_label": "Q4 — German common name"},
        ],
    },
    {
        "persona_key": "alternative_medicine_seeker",
        "session_id": "petra_s6",
        "theme": "Mönchspfeffer PMS",
        "queries": [
            {"q": "Mönchspfeffer PMS Zyklus Tabletten", "category": "MULTI_ATTRIBUTE", "intent_label": "Q1 — herb + indication"},
            {"q": "Vitex agnus-castus 20mg Kapseln", "category": "MULTI_ATTRIBUTE", "intent_label": "Q2 — Latin name + dosage"},
            {"q": "Agnucaston Zyklus Tabletten", "category": "BRAND_SEARCH", "intent_label": "Q3 — brand recovery"},
            {"q": "Mönchspfeffer Extrakt ohne Hormone", "category": "NEGATIVE_INTENT", "intent_label": "Q4 — exclusion qualifier"},
        ],
    },
]


def build_test_queries(session: dict) -> list[TestQuery]:
    return [
        TestQuery(
            category=q["category"],
            query=q["q"],
            rationale=f"[{session['session_id']}] {q['intent_label']}",
        )
        for q in session["queries"]
    ]


def serialize_results(results) -> list[dict]:
    return [
        {"rank": r.rank, "title": r.title, "price": r.price, "snippet": r.snippet, "url": r.url}
        for r in results
    ]


def assess_state(results, persona_key: str, query_str: str) -> str:
    if not results or len(results) < 2:
        return "NOTHING"

    top3 = " ".join(r.title.lower() for r in results[:3])
    top1 = results[0].title.lower() if results else ""

    if persona_key == "anxious_young_mother":
        if any(t in top1 for t in ["buch", "book", "roman", "erwachsene rezept"]):
            return "NOTHING"
        if "rx" in top1 or "rezeptpflichtig" in top1:
            return "NOTHING"
        if any(t in top3 for t in ["baby", "kleinkind", "säugling", "kinder"]):
            return "FOUND"
        return "PARTIAL"

    if persona_key == "wellness_optimizer":
        q_lower = query_str.lower()
        pharma = ["ratiopharm", "hexal", "stada", "aliud", "ct-arzneimittel"]
        if sum(1 for b in pharma if b in top3) >= 2:
            return "PARTIAL"
        for kw in ["bisglycinat", "ksm-66", "ubiquinol", "mk7", "triglycerid", "typ ii", "0,5mg"]:
            if kw in q_lower and kw not in top3:
                return "PARTIAL"
        trusted = ["sunday natural", "natugena", "viktilabs", "natural elements", "bloom naturals"]
        if any(b in top3 for b in trusted):
            return "FOUND"
        return "PARTIAL"

    if persona_key == "elderly_patient":
        q_lower = query_str.lower()
        if "charriere" in q_lower and "charriere" not in top3 and "ch " not in top3:
            return "NOTHING"
        # Pack size mismatch check
        for size in ["100 stück", "60 stück", "50 stück", "150g", "100g", "10x10"]:
            if size in q_lower and size not in top3:
                return "PARTIAL"
        if not results:
            return "NOTHING"
        return "FOUND"

    if persona_key == "acute_self_treater":
        rx_signals = ["rezeptpflichtig", "verschreibungspflichtig", "zopiclon", "modafinil", "tramadol"]
        if any(s in top1 for s in rx_signals):
            return "NOTHING"
        book_signals = ["buch", "book", "roman", "ruhe da oben", "in der nacht"]
        if any(s in top1 for s in book_signals):
            return "NOTHING"
        known_otc = ["strepsils", "grippostad", "ibuflam", "aspirin", "neo-angin", "lemocin",
                     "wick", "paracetamol", "ibuprofen", "voltaren", "otrivin", "acc",
                     "dobendan", "septolete", "xylometazolin"]
        if any(b in top3 for b in known_otc):
            return "FOUND"
        return "PARTIAL"

    if persona_key == "alternative_medicine_seeker":
        conventional = ["ibuprofen", "paracetamol", "diclofenac", "aspirin", "lorazepam", "zopiclon"]
        if sum(1 for c in conventional if c in top3) >= 2:
            return "NOTHING"
        alt_brands = ["dhu", "weleda", "heel", "wala", "staufen", "pascoe"]
        potency = ["d6", "d12", "c30", "c12", "lm", "globuli", "granulat", "tinktur"]
        if any(b in top3 for b in alt_brands) and any(p in top3 for p in potency):
            return "FOUND"
        if any(t in top3 for t in ["globuli", "schüssler", "bachblüten", "homöo", "passionsblume",
                                    "echinacea", "mönchspfeffer", "arnica", "belladonna"]):
            return "PARTIAL"
        return "NOTHING"

    return "PARTIAL" if results else "NOTHING"


PERSONA_META = {
    "anxious_young_mother":      {"reformulation_tolerance": 3, "basket_value": 35,  "split_key": None},
    "wellness_optimizer":        {"reformulation_tolerance": 4, "basket_value": 110, "split_key": "wellness_optimizer"},
    "elderly_patient":           {"reformulation_tolerance": 2, "basket_value": 45,  "split_key": None},
    "acute_self_treater":        {"reformulation_tolerance": 2, "basket_value": 8,   "split_key": None},
    "alternative_medicine_seeker": {"reformulation_tolerance": 3, "basket_value": 55, "split_key": None},
}


def run_session(session: dict, raw_results: dict) -> dict:
    meta = PERSONA_META[session["persona_key"]]
    result = {
        "session_id": session["session_id"],
        "persona_key": session["persona_key"],
        "theme": session["theme"],
        "basket_value": meta["basket_value"],
        "queries": [],
        "session_outcome": None,
        "reformulations_used": 0,
    }

    reformulations = 0
    session_resolved = False

    for i, q_def in enumerate(session["queries"]):
        q_str = q_def["q"]
        results = raw_results.get(q_str, [])
        state = assess_state(results, session["persona_key"], q_str)

        result["queries"].append({
            "step": i + 1,
            "query": q_str,
            "intent_label": q_def["intent_label"],
            "category": q_def["category"],
            "result_count": len(results),
            "top5": serialize_results(results[:5]),
            "state": state,
        })

        if state == "FOUND" and not session_resolved:
            session_resolved = True
            result["session_outcome"] = "CONVERTED"

        elif state in ("PARTIAL", "NOTHING") and not session_resolved:
            reformulations += 1
            if reformulations >= meta["reformulation_tolerance"]:
                result["session_outcome"] = (
                    "SPLIT_BASKET" if session["persona_key"] == "wellness_optimizer" else "ABANDONED"
                )
                session_resolved = True

    if not session_resolved:
        result["session_outcome"] = "ABANDONED"

    result["reformulations_used"] = reformulations
    return result


def run() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "reports" / "persona_simulation"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group sessions by persona to minimise fetch_all_results calls
    # (probe-first strategy works best per-site, which is always the same here,
    #  but grouping avoids spinning up a new probe for every session)
    from collections import defaultdict
    by_persona: dict[str, list[dict]] = defaultdict(list)
    for s in SESSIONS:
        by_persona[s["persona_key"]].append(s)

    all_query_results: dict[str, list] = {}

    print("\n" + "=" * 60)
    print("  RUN 2 — shop-apotheke.com (25 new sessions)")
    print("=" * 60)

    for persona_key, sessions in by_persona.items():
        print(f"\n→ Persona: {persona_key} ({len(sessions)} sessions)")
        all_queries: list[TestQuery] = []
        for s in sessions:
            all_queries.extend(build_test_queries(s))

        raw = fetch_all_results(SHOP_APO_TEMPLATE, all_queries, max_results=10)
        all_query_results.update(raw)
        time.sleep(3)

    # Score sessions
    session_results = []
    for session in SESSIONS:
        sr = run_session(session, all_query_results)
        session_results.append(sr)
        print(f"  {sr['session_id']:20s} theme={sr['theme']:30s} → {sr['session_outcome']} ({sr['reformulations_used']} ref)")

    outcomes = [s["session_outcome"] for s in session_results]
    total_ref = sum(s["reformulations_used"] for s in session_results)
    n = len(session_results)

    summary = {
        "run": "run2",
        "total_sessions": n,
        "total_queries_run": sum(len(s["queries"]) for s in session_results),
        "converted": outcomes.count("CONVERTED"),
        "split_basket": outcomes.count("SPLIT_BASKET"),
        "abandoned": outcomes.count("ABANDONED"),
        "avg_reformulations": round(total_ref / n, 1),
        "estimated_revenue_lost": sum(
            s["basket_value"] for s in session_results
            if s["session_outcome"] in ("ABANDONED", "SPLIT_BASKET")
        ),
    }

    print("\n" + "=" * 60)
    print(f"  Run 2 summary: {summary['converted']} converted | {summary['split_basket']} split | {summary['abandoned']} abandoned")
    print(f"  Avg reformulations: {summary['avg_reformulations']}")
    print("=" * 60)

    output = {"timestamp": timestamp, "summary": summary, "sessions": session_results}
    out_path = out_dir / f"persona_simulation_{timestamp}_run2_data.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nData written: {out_path}")


if __name__ == "__main__":
    run()
