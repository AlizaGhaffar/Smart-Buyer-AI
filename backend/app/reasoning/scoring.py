"""Explainable evidence score (0-100).

This is an evidence-strength index, NOT a probability: it has not been
calibrated against labelled outcomes. It only ranks leads inside a class;
the class itself comes from qualification.qualify().
"""

from __future__ import annotations

from ..knowledge.schema import ProductKB
from .engine import CompanyFacts, InferenceResult
from .qualification import NOT_RELEVANT, Qualification

# All weights live here so they can be tuned in one place.
SCORING_CONFIG = {
    "material_usage": {"weight": 30, "supported": 1.0, "mentioned": 0.4},
    "business_activity": {"weight": 20, "core": 1.0, "adjacent": 0.5},
    "buyer_category": {"weight": 10, 1: 1.0, 2: 0.6},
    "source_reliability": {"weight": 10},
    "evidence_completeness": {"weight": 10},
    "purchasing_evidence": {"weight": 20, "direct": 1.0},
    "penalties": {"conflict": 10, "mixed_materials": 8},
    "no_usage_cap": 30,  # without material evidence the score can never exceed this
}


def score(kb: ProductKB, data: CompanyFacts, r: InferenceResult, q: Qualification,
          config: dict = SCORING_CONFIG) -> dict | None:
    if q.classification == NOT_RELEVANT:
        return None
    facts = {f.id: f for f in data.facts}
    breakdown: list[dict] = []

    def add(factor: str, fraction: float, reason: str) -> None:
        weight = config[factor]["weight"]
        breakdown.append({
            "factor": factor,
            "weight": weight,
            "earned": round(weight * fraction, 1),
            "reason": reason,
        })

    usage = config["material_usage"].get(r.usage, 0.0)
    add("material_usage", usage, f"Material usage is '{r.usage}'.")

    performed = [
        f.object for f in data.facts
        if f.predicate == "performs" and f.polarity and f.admissible and f.object in kb.activities
    ]
    tiers = {kb.activities[a].tier for a in performed}
    tier = "core" if "core" in tiers else "adjacent" if "adjacent" in tiers else None
    add("business_activity", config["business_activity"].get(tier, 0.0),
        f"Best activity tier found: {tier or 'none'}.")

    category = kb.category_for(performed)
    add("buyer_category", config["buyer_category"].get(category.tier, 0.0) if category else 0.0,
        f"Buyer category: {category.name} (tier {category.tier})." if category else "No buyer category matched.")

    used = [facts[i] for i in r.fact_ids_used if i in facts]
    reliabilities = [max((e.reliability for e in f.evidence), default=0.0) for f in used]
    reliability = sum(reliabilities) / len(reliabilities) if reliabilities else 0.0
    add("source_reliability", reliability,
        f"Average reliability of {len(used)} supporting fact(s): {reliability:.2f}.")

    items = r.evidence_items or {}
    found = sum(bool(v) for v in items.values())
    total = len(items) or 1
    add("evidence_completeness", found / total, f"{found} of {total} required evidence items found.")

    add("purchasing_evidence", config["purchasing_evidence"].get(r.purchasing, 0.0),
        f"Purchasing evidence is '{r.purchasing}'.")

    penalties = []
    if r.conflicts:
        penalties.append({"reason": "conflicting evidence", "points": -config["penalties"]["conflict"]})
    if "mixed_materials" in r.flags:
        penalties.append({"reason": "alternative material also used",
                          "points": -config["penalties"]["mixed_materials"]})

    value = sum(b["earned"] for b in breakdown) + sum(p["points"] for p in penalties)
    cap_note = None
    if r.usage not in {"supported", "mentioned"} and value > config["no_usage_cap"]:
        value = config["no_usage_cap"]
        cap_note = f"Capped at {config['no_usage_cap']}: no evidence that the material is used."
    value = max(0, min(100, round(value)))
    return {
        "value": value,
        "max": 100,
        "kind": "evidence_score_not_probability",
        "breakdown": breakdown,
        "penalties": penalties,
        "cap": cap_note,
    }
