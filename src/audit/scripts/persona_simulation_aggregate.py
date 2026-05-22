"""
Persona simulation — Aggregate analysis
Loads run1 + run2 JSON data, computes cross-run metrics, writes combined JSON.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "persona_simulation"

PERSONA_LABELS = {
    "anxious_young_mother":       "Anxious Young Mother (Lena)",
    "wellness_optimizer":         "Wellness Optimizer (Mia)",
    "elderly_patient":            "Elderly Patient (Werner)",
    "acute_self_treater":         "Acute Self-Treater (Jonas)",
    "alternative_medicine_seeker": "Alternative Medicine Seeker (Petra)",
}

FAILURE_MODES = {
    "anxious_young_mother":       ["age-gating_failure", "rx_contamination", "brand_not_found"],
    "wellness_optimizer":         ["spec_mismatch", "pharma_flood", "certification_gap"],
    "elderly_patient":            ["pack_size_mismatch", "generic_noise", "brand_variant_gap"],
    "acute_self_treater":         ["brand_displacement", "rx_contamination", "book_contamination"],
    "alternative_medicine_seeker": ["conventional_flood", "potency_gap", "latin_name_gap"],
}


def load_all_runs() -> list[dict]:
    """Load all run JSON files from the reports directory."""
    runs = []
    for f in sorted(REPORTS_DIR.glob("persona_simulation_*_data.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        data["_source_file"] = f.name
        runs.append(data)
    return runs


def normalize_session(raw: dict, run_label: str) -> dict:
    """Normalize run1 persona dict and run2 session dict to a common shape."""
    if "persona_key" in raw:
        # run2 format — already correct
        return dict(raw, _run=run_label)
    # run1 format — persona dict
    return {
        "session_id": raw["key"] + "_s1",
        "persona_key": raw["key"],
        "theme": "Run 1",
        "basket_value": raw["basket_value"],
        "queries": raw["queries"],
        "session_outcome": raw["session_outcome"],
        "reformulations_used": raw["reformulations_used"],
        "_run": run_label,
    }


def flatten_sessions(runs: list[dict]) -> list[dict]:
    sessions = []
    for run in runs:
        label = run["_source_file"]
        raw_list = run.get("sessions") or run.get("personas") or []
        for raw in raw_list:
            sessions.append(normalize_session(raw, label))
    return sessions


def compute_aggregate(sessions: list[dict]) -> dict:
    n = len(sessions)
    outcomes = [s["session_outcome"] for s in sessions]
    converted = outcomes.count("CONVERTED")
    split_basket = outcomes.count("SPLIT_BASKET")
    abandoned = outcomes.count("ABANDONED")
    total_ref = sum(s["reformulations_used"] for s in sessions)
    revenue_lost = sum(
        s["basket_value"] for s in sessions
        if s["session_outcome"] in ("ABANDONED", "SPLIT_BASKET")
    )

    # Per-persona breakdown
    by_persona: dict[str, list[dict]] = defaultdict(list)
    for s in sessions:
        by_persona[s["persona_key"]].append(s)

    persona_stats = {}
    for pk, ps in by_persona.items():
        p_outcomes = [s["session_outcome"] for s in ps]
        p_ref = sum(s["reformulations_used"] for s in ps)
        p_revenue = sum(
            s["basket_value"] for s in ps
            if s["session_outcome"] in ("ABANDONED", "SPLIT_BASKET")
        )
        persona_stats[pk] = {
            "label": PERSONA_LABELS[pk],
            "sessions": len(ps),
            "converted": p_outcomes.count("CONVERTED"),
            "split_basket": p_outcomes.count("SPLIT_BASKET"),
            "abandoned": p_outcomes.count("ABANDONED"),
            "conversion_rate": round(p_outcomes.count("CONVERTED") / len(ps), 2),
            "avg_reformulations": round(p_ref / len(ps), 1),
            "revenue_lost": p_revenue,
            "failure_modes": FAILURE_MODES.get(pk, []),
        }

    # Query-level state distribution
    state_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    entry_query_states: dict[str, list[str]] = defaultdict(list)
    for s in sessions:
        for q in s["queries"]:
            state_counts[s["persona_key"]][q["state"]] += 1
        if s["queries"]:
            entry_query_states[s["persona_key"]].append(s["queries"][0]["state"])

    # Entry query failure rate (Q1 state != FOUND → immediate friction)
    entry_friction: dict[str, float] = {}
    for pk, states in entry_query_states.items():
        not_found = sum(1 for st in states if st != "FOUND")
        entry_friction[pk] = round(not_found / len(states), 2)

    # Reformulation escalation pattern
    # Sessions that needed 3+ reformulations (near or at tolerance)
    deep_reformulators = [s for s in sessions if s["reformulations_used"] >= 3]

    # Category failure analysis
    category_states: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in sessions:
        for q in s["queries"]:
            category_states[q.get("category", "UNKNOWN")][q["state"]] += 1

    category_failure_rates = {}
    for cat, states in category_states.items():
        total = sum(states.values())
        nothing_partial = states.get("NOTHING", 0) + states.get("PARTIAL", 0)
        category_failure_rates[cat] = round(nothing_partial / total, 2)

    return {
        "total_sessions": n,
        "total_queries": sum(len(s["queries"]) for s in sessions),
        "converted": converted,
        "split_basket": split_basket,
        "abandoned": abandoned,
        "conversion_rate": round(converted / n, 2),
        "failure_rate": round((split_basket + abandoned) / n, 2),
        "avg_reformulations": round(total_ref / n, 1),
        "estimated_revenue_lost": revenue_lost,
        "persona_stats": persona_stats,
        "entry_friction_by_persona": entry_friction,
        "deep_reformulators_count": len(deep_reformulators),
        "category_failure_rates": dict(
            sorted(category_failure_rates.items(), key=lambda x: -x[1])
        ),
        "state_distribution_by_persona": {
            pk: dict(v) for pk, v in state_counts.items()
        },
    }


def run() -> None:
    runs = load_all_runs()
    if not runs:
        print("No run data files found in", REPORTS_DIR)
        return

    print(f"Loaded {len(runs)} run file(s):")
    for r in runs:
        raw_list = r.get("sessions") or r.get("personas") or []
        print(f"  {r['_source_file']}  —  {len(raw_list)} sessions")

    sessions = flatten_sessions(runs)
    aggregate = compute_aggregate(sessions)

    out = {
        "runs_included": [r["_source_file"] for r in runs],
        "aggregate": aggregate,
        "sessions": sessions,
    }

    out_path = REPORTS_DIR / "persona_simulation_combined.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nCombined data written: {out_path}")

    agg = aggregate
    print(f"\n{'='*60}")
    print(f"  AGGREGATE — {agg['total_sessions']} sessions, {agg['total_queries']} queries")
    print(f"  Converted:   {agg['converted']}  ({agg['conversion_rate']:.0%})")
    print(f"  Split basket: {agg['split_basket']}")
    print(f"  Abandoned:   {agg['abandoned']}")
    print(f"  Avg reformulations: {agg['avg_reformulations']}")
    print(f"  Est. revenue lost:  €{agg['estimated_revenue_lost']}")
    print(f"  Entry-query friction: {agg['entry_friction_by_persona']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run()
