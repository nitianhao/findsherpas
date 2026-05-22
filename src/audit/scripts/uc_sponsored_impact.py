"""
Sponsored Trust Impact Simulation
----------------------------------
For 5 queries where UC8 documented specific sponsored placements,
run all 5 personas as AI agents and measure how the sponsored product
affects trust, session behavior, and conversion outcome.

All query data and organic results are hardcoded from UC8 + audit findings
— no Playwright dependency. Only API cost: Claude Haiku for agent reasoning.

Cost estimate: ~$0.16 at Haiku rates.
Output: JSON + terminal matrix.
"""
from __future__ import annotations

import json
import time
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
import anthropic

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

OUTPUT_DIR = Path(__file__).resolve().parents[3] / "reports" / "sponsored_impact"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = anthropic.Anthropic()

# ─── Scenarios (hardcoded from UC8 + audit report) ───────────────────────────

SCENARIOS = [
    {
        "query": "Kopfschmerzen",
        "uc8_verdict": "CRITICAL",
        "sponsored": {
            "name": "Sanitätshaus Produkt (unbekannte Marke)",
            "category": "Medizinprodukt / Sanitätshaus",
            "price": None,
            "creative_note": "Nur Text 'Variante auswählen' sichtbar — kein Produktname, kein Bild",
        },
        "organic_top5": [
            "FORMIGRAN® bei Migräne (Rx, verschreibungspflichtig)",
            "Naratriptan Hennig® 2,5mg bei Migräne (Rx)",
            "FENDRIX Fertigspritze o.Kanüle (Rx, Impfstoff)",
            "Naratriptan HEXAL® bei Migräne 2,5 mg (Rx)",
            "Sumatriptan 1A Pharma 100mg (Rx)",
        ],
        "intent": "OTC Schmerzmittel für Kopfschmerzen",
    },
    {
        "query": "Erkältung Kinder",
        "uc8_verdict": "MISMATCH",
        "sponsored": {
            "name": "Beurer BHT 500 Ohrthermometer",
            "category": "Medizinprodukt / Diagnostik",
            "price": "€29.99",
            "creative_note": "Thermometer für Ohr — kein Bezug zu Erkältungsbehandlung",
        },
        "organic_top5": [
            "Wick VapoRub Erkältungssalbe für Kinder (€5.49)",
            "Weleda Erkältungsöl Baby (€8.99)",
            "Sinupret extract Tropfen (€9.50)",
            "ACC akut 200mg bei Husten für Kinder (€6.99)",
            "Aspecton Hustentropfen Kinder (€7.49)",
        ],
        "intent": "Erkältungsbehandlung / Medikamente für Kinder",
    },
    {
        "query": "nasenspray unter 10 euro",
        "uc8_verdict": "CRITICAL",
        "sponsored": {
            "name": "Mometasonfuroat Cipla 50 Mikrogramm/Sprühstoß",
            "category": "Nasenspray (Rx, verschreibungspflichtig)",
            "price": "€17.01",
            "creative_note": "Preis €17.01 — doppelt so teuer wie das genannte Budget; außerdem Rx",
        },
        "organic_top5": [
            "Mometasonfuroat Cipla 50µg Nasenspray — €17.01 (Rx!)",
            "Dolphiner™ Ohrenspray — €10.90 (falsche Kategorie!)",
            "Redcare Xylo 0,1% Nasenspray + GRIPPOSTAD Bundle — €14.79",
            "Redcare Xylo 0,1% Nasenspray — €8.99",
            "Redcare Nasenspülsalz — €23.99",
        ],
        "intent": "OTC Nasenspray kaufen, Budget-Limit €10",
    },
    {
        "query": "schmerzmittel nicht aspirin",
        "uc8_verdict": "MISMATCH",
        "sponsored": {
            "name": "Neuralgin® Tabletten (Aspirin-freies Schmerzmittel)",
            "category": "Schmerzmittel OTC — korrekt",
            "price": "€4.99",
            "creative_note": "Gesponsert korrekt — aber 8 von 14 organischen Ergebnissen enthalten Aspirin",
        },
        "organic_top5": [
            "Neuralgin® Tabletten (gesponsertes Ergebnis oben)",
            "Aspirin Complex Granulat — enthält Aspirin!",
            "Aspirin Plus C Brausetabletten — enthält Aspirin!",
            "ASPIRIN® Direkt Kautabletten — enthält Aspirin!",
            "ASPIRIN® Effect Granulat — enthält Aspirin!",
        ],
        "intent": "Schmerzmittel ohne Aspirin / mit Ausschluss von Aspirin",
    },
    {
        "query": "Baldrian",
        "uc8_verdict": "REVERSE",
        "sponsored": {
            "name": "Baldrian Dispert 45mg Dragees — Schlafdragees",
            "category": "Baldrian-Schlafmittel — korrekt",
            "price": "€6.49",
            "creative_note": "Gesponsert ist category-aligned und relevanter als organisches #1",
        },
        "organic_top5": [
            "Baldrian Dispert 45mg Dragees (gesponsert — relevant!)",
            "Baldriparan® stark Schlaftabletten",
            "Baldrian-Dispert Dragees Nacht",
            "NEUREXAN® Tabletten (Baldrian-Komplex)",
            "Euvegal® Entspannung und Schlaf",
        ],
        "intent": "Baldrian-Schlafmittel kaufen",
    },
]

# ─── Persona profiles ────────────────────────────────────────────────────────

PERSONAS = {
    "lena": {
        "name": "Lena",
        "age": 29,
        "archetype": "Anxious Young Mother",
        "city": "Berlin",
        "basket_eur": 35,
        "scroll_threshold": 3,
        "reformulation_tolerance": 3,
        "key_distrust_triggers": [
            "Rx-Produkt für Baby/Kinder sichtbar",
            "Off-Category Produkt in Top-3",
            "Unbekannte Marke ohne Stiftung Warentest Siegel",
            "Medizinprodukt statt Medikament",
        ],
        "inner_voice": (
            "Ich bin Mutter von einem 8 Monate alten Baby. Ich kaufe nur, was sicher ist. "
            "Wenn ich das erste Ergebnis sehe und es passt nicht, verliere ich sofort das Vertrauen "
            "in die Seite. Ich gehe dann lieber zur Apotheke um die Ecke oder frage im Forum."
        ),
        "patience": "medium",
        "device": "mobile",
    },
    "mia": {
        "name": "Mia",
        "age": 34,
        "archetype": "Wellness Optimizer",
        "city": "München",
        "basket_eur": 110,
        "scroll_threshold": 7,
        "reformulation_tolerance": 4,
        "key_distrust_triggers": [
            "Generischer Pharmakonzern dominiert über Supplement-Brand",
            "Keine Zertifizierung (laborgeprüft, ISO) sichtbar",
            "Falsche Darreichungsform (nicht Bisglycinat, KSM-66 etc.)",
            "Werbung für irrelevante Produktkategorie",
        ],
        "inner_voice": (
            "Ich bin Ernährungsexpertin und kaufe gezielt. Ich kenne die Inhaltsstoffe und Marken. "
            "Wenn gesponserte Werbung für mich irrelevant ist, ignoriere ich sie — aber wenn sie "
            "aktiv falsch ist, hinterfrage ich ob diese Apotheke wirklich meine Zielgruppe versteht."
        ),
        "patience": "high",
        "device": "desktop",
    },
    "werner": {
        "name": "Werner",
        "age": 71,
        "archetype": "Elderly Patient / Caregiver",
        "city": "Landsberg am Lech (Bayern)",
        "basket_eur": 45,
        "scroll_threshold": 4,
        "reformulation_tolerance": 2,
        "key_distrust_triggers": [
            "Falsche Produktkategorie an Position #1",
            "Unbekannte Marke ohne Apothekenlogo",
            "Zu teuer oder falsche Packungsgröße",
            "Technisches Gerät statt Medikament",
        ],
        "inner_voice": (
            "Ich suche immer dasselbe Medikament das mein Arzt empfohlen hat. "
            "Wenn das erste Ergebnis falsch ist, weiß ich nicht weiter — dann rufe ich lieber an "
            "oder gehe in die Apotheke. Ich verstehe nicht warum die Webseite mir das falsche zeigt."
        ),
        "patience": "low-medium",
        "device": "desktop",
    },
    "jonas": {
        "name": "Jonas",
        "age": 31,
        "archetype": "Acute Self-Treater",
        "city": "Hamburg",
        "basket_eur": 8,
        "scroll_threshold": 3,
        "reformulation_tolerance": 2,
        "key_distrust_triggers": [
            "Rx-Produkt für OTC-Anfrage",
            "Unbekannte Marke / Sanitätshaus statt Apotheke",
            "Medizinisches Gerät statt Medikament",
            "Zu teuer (>€15 für OTC-Artikel)",
        ],
        "inner_voice": (
            "Ich habe Kopfschmerzen und will sofort etwas kaufen. Keine Zeit für Recherche. "
            "Wenn das erste was ich sehe komplett falsch ist, bin ich raus — ich kaufe dann "
            "bei der dm-Drogerie auf dem Weg nach Hause."
        ),
        "patience": "low",
        "device": "mobile",
    },
    "petra": {
        "name": "Petra",
        "age": 48,
        "archetype": "Alternative Medicine Seeker",
        "city": "Freiburg (Baden-Württemberg)",
        "basket_eur": 55,
        "scroll_threshold": 5,
        "reformulation_tolerance": 3,
        "key_distrust_triggers": [
            "Konventionelles Pharmaprodukt als Ersatz für Naturheilkunde",
            "Werbung ohne Naturheilkunde-Bezug",
            "Fehlende Potenzangabe bei Homöopathika",
            "Synthetischer Wirkstoff prominent empfohlen",
        ],
        "inner_voice": (
            "Ich vertraue der Naturheilkunde und meiner Heilpraktikerin. Wenn eine Seite mir "
            "sofort konventionelle Pharmaprodukte zeigt wenn ich nach Baldrian suche, ist das okay — "
            "aber wenn gesponserte Werbung meine Weltanschauung ignoriert, kaufe ich woanders."
        ),
        "patience": "medium-high",
        "device": "desktop",
    },
}

# ─── Agent ───────────────────────────────────────────────────────────────────

AGENT_SYSTEM = """Du bist ein synthetischer Einkäufer der die Sucherfahrung auf einer deutschen Online-Apotheke simulierst.
Du verhältst dich GENAU wie die beschriebene Persona — mit ihrer Sprache, ihren Ängsten, ihrem Vertrauen und ihren Triggers.
Antworte NUR mit validem JSON. Kein Text außerhalb des JSON-Blocks."""

def build_agent_prompt(persona: dict, scenario: dict, round_num: int, session_history: list[dict]) -> str:
    sponsored = scenario["sponsored"]
    organic = scenario["organic_top5"]

    history_text = ""
    if session_history:
        history_text = "\n\nBISHERIGE SESSION:\n" + "\n".join(
            f"- Runde {h['round']}: {h['action']} | Zufriedenheit: {h['satisfaction']:.1f} | {h['monologue'][:80]}..."
            for h in session_history[-2:]
        )

    return f"""PERSONA: {persona['name']}, {persona['age']} Jahre, {persona['archetype']}
Innere Stimme: "{persona['inner_voice']}"
Distrust-Triggers: {', '.join(persona['key_distrust_triggers'][:3])}
Geduld: {persona['patience']} | Gerät: {persona['device']} | Durchschnittskorb: €{persona['basket_eur']}

SUCHANFRAGE: "{scenario['query']}"
Suchintention: {scenario['intent']}
Runde: {round_num}/6{history_text}

SUCHERGEBNISSEITE:

[GESPONSERT — BEZAHLTE WERBUNG AN POSITION #1]
Produkt: {sponsored['name']}
Kategorie: {sponsored['category']}
Preis: {sponsored.get('price') or 'nicht sichtbar'}
Hinweis: {sponsored['creative_note']}

[ORGANISCHE ERGEBNISSE — POSITIONEN #2 bis #6]
{chr(10).join(f"#{i+2}: {r}" for i, r in enumerate(organic))}

Reagiere als diese Persona auf das was du siehst. Bedenke:
- Das gesponserte Ergebnis ist das ERSTE was du siehst — noch vor den organischen Ergebnissen
- Ist es relevant für deine Suche? Hilft es, ist es egal, oder beschädigt es dein Vertrauen?
- Wie beeinflusst es deine nächste Aktion?

Antworte mit diesem JSON (keine anderen Zeichen):
{{
  "monologue": "Dein innerer Gedankengang als Persona (2-4 Sätze, erste Person, Deutsch, authentisch)",
  "sponsored_reaction": "CLICKED|IGNORED|TRUST_DAMAGED",
  "trust_delta": <Zahl von -1.0 bis +1.0, negativ = Vertrauen beschädigt>,
  "action": "click_sponsored|click_organic|scroll|reformulate|abandon",
  "satisfaction": <Zahl von 0.0 bis 1.0>,
  "reasoning": "Kurze Begründung für sponsored_reaction und action (1 Satz)"
}}"""


def run_agent(persona: dict, scenario: dict) -> dict:
    """Run a full session for one persona × one scenario."""
    session_history = []
    final_result = {
        "persona": persona["name"],
        "archetype": persona["archetype"],
        "query": scenario["query"],
        "uc8_verdict": scenario["uc8_verdict"],
        "rounds": [],
        "sponsored_reaction": "IGNORED",
        "trust_delta": 0.0,
        "session_outcome": "BROWSING",
        "best_monologue": "",
    }

    for round_num in range(1, 7):
        prompt = build_agent_prompt(persona, scenario, round_num, session_history)
        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=400,
                system=AGENT_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
        except Exception as e:
            print(f"  [error round {round_num}] {e}")
            data = {
                "monologue": "Fehler bei der Verarbeitung.",
                "sponsored_reaction": "IGNORED",
                "trust_delta": 0.0,
                "action": "scroll",
                "satisfaction": 0.5,
                "reasoning": "parse error",
            }

        round_data = {
            "round": round_num,
            "monologue": data.get("monologue", ""),
            "sponsored_reaction": data.get("sponsored_reaction", "IGNORED"),
            "trust_delta": float(data.get("trust_delta", 0.0)),
            "action": data.get("action", "scroll"),
            "satisfaction": float(data.get("satisfaction", 0.5)),
            "reasoning": data.get("reasoning", ""),
        }
        session_history.append(round_data)
        final_result["rounds"].append(round_data)

        # Capture first round sponsored reaction (most important)
        if round_num == 1:
            final_result["sponsored_reaction"] = round_data["sponsored_reaction"]
            final_result["trust_delta"] = round_data["trust_delta"]
            final_result["best_monologue"] = round_data["monologue"]

        # Terminal conditions
        action = round_data["action"]
        if action == "click_sponsored":
            final_result["session_outcome"] = "CONVERTED_SPONSORED"
            break
        elif action == "click_organic":
            final_result["session_outcome"] = "CONVERTED_ORGANIC"
            break
        elif action == "abandon":
            final_result["session_outcome"] = "ABANDONED"
            break
        elif action == "reformulate":
            reformulations = sum(1 for r in session_history if r["action"] == "reformulate")
            if reformulations >= persona["reformulation_tolerance"]:
                final_result["session_outcome"] = "ABANDONED_AFTER_REFORMULATION"
                break

        time.sleep(0.3)  # rate limiting

    if final_result["session_outcome"] == "BROWSING":
        final_result["session_outcome"] = "ABANDONED_EXHAUSTED"

    return final_result


# ─── Matrix builder ───────────────────────────────────────────────────────────

def impact_label(trust_delta: float, sponsored_reaction: str) -> str:
    if sponsored_reaction == "CLICKED":
        return "HELPFUL"
    if sponsored_reaction == "TRUST_DAMAGED" or trust_delta <= -0.3:
        return "HARMFUL"
    return "NEUTRAL"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n=== SPONSORED TRUST IMPACT SIMULATION ===")
    print(f"Queries: {len(SCENARIOS)} | Personas: {len(PERSONAS)} | Agents: {len(SCENARIOS) * len(PERSONAS)}")
    print(f"Est. cost: ~$0.16 at Haiku rates\n")

    all_results: list[dict] = []
    persona_keys = list(PERSONAS.keys())
    scenario_labels = [s["query"] for s in SCENARIOS]

    # 5×5 matrix: matrix[persona_key][query] = {impact, trust_delta, monologue, outcome}
    matrix: dict[str, dict[str, dict]] = {pk: {} for pk in persona_keys}

    for scenario in SCENARIOS:
        print(f"\n── Query: \"{scenario['query']}\" ({scenario['uc8_verdict']}) ──")
        for pk in persona_keys:
            persona = PERSONAS[pk]
            print(f"  Running {persona['name']} ({persona['archetype']})...", end=" ", flush=True)
            result = run_agent(persona, scenario)
            all_results.append(result)
            impact = impact_label(result["trust_delta"], result["sponsored_reaction"])
            matrix[pk][scenario["query"]] = {
                "impact": impact,
                "trust_delta": result["trust_delta"],
                "sponsored_reaction": result["sponsored_reaction"],
                "session_outcome": result["session_outcome"],
                "monologue": result["best_monologue"],
            }
            print(f"{impact} (Δtrust={result['trust_delta']:+.2f}) → {result['session_outcome']}")

    # ── Save results ──────────────────────────────────────────────────────────
    output = {
        "generated": datetime.now().isoformat(),
        "scenarios": [{"query": s["query"], "uc8_verdict": s["uc8_verdict"]} for s in SCENARIOS],
        "personas": [{"key": k, "name": v["name"], "archetype": v["archetype"], "basket_eur": v["basket_eur"]} for k, v in PERSONAS.items()],
        "matrix": matrix,
        "all_results": all_results,
    }
    out_path = OUTPUT_DIR / "uc_sponsored_impact_results.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n\nResults saved to: {out_path}")

    # ── Terminal matrix ───────────────────────────────────────────────────────
    print("\n\n=== IMPACT MATRIX (persona × query) ===\n")
    col_w = 28
    header = f"{'PERSONA':<22}" + "".join(q[:col_w].ljust(col_w) for q in scenario_labels)
    print(header)
    print("─" * len(header))
    for pk, persona in PERSONAS.items():
        row = f"{persona['name'] + ' / ' + persona['archetype'][:14]:<22}"
        for q in scenario_labels:
            cell = matrix[pk].get(q, {})
            impact = cell.get("impact", "?")
            delta = cell.get("trust_delta", 0.0)
            row += f"{impact} ({delta:+.2f})".ljust(col_w)
        print(row)

    # ── Top harmful cases ─────────────────────────────────────────────────────
    print("\n\n=== TOP HARMFUL CASES ===\n")
    harmful = sorted(
        [r for r in all_results if matrix[next(k for k, v in PERSONAS.items() if v["name"] == r["persona"])].get(r["query"], {}).get("impact") == "HARMFUL"],
        key=lambda r: r["trust_delta"]
    )[:3]
    for r in harmful:
        print(f"Query: \"{r['query']}\" × {r['persona']} ({r['archetype']})")
        print(f"  Trust delta: {r['trust_delta']:+.2f} | Outcome: {r['session_outcome']}")
        print(f"  Monologue: \"{r['best_monologue'][:180]}\"")
        print()

    print(f"\nTotal agents run: {len(all_results)}")
    print("Done.")


if __name__ == "__main__":
    main()
