"""Lead qualification: maps an InferenceResult to one of five classes.

The class is decided by this decision table from the evidence layers and the
rule outcomes - never by the numeric score. Rows are checked in order and the
first matching row wins. "Confirmed Purchaser" means the company's own
website states that it buys/sources the raw material; it does not mean a
transaction was verified.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..knowledge.schema import RELEVANCE_ORDER, ProductKB
from .engine import InferenceResult

CONFIRMED = "confirmed_purchaser"
STRONG = "strong_potential_buyer"
POSSIBLE = "possible_potential_buyer"
INSUFFICIENT = "insufficient_evidence"
NOT_RELEVANT = "not_relevant"

LABELS = {
    CONFIRMED: "Confirmed Purchaser (self-declared on company website)",
    STRONG: "Strong Potential Buyer",
    POSSIBLE: "Possible Potential Buyer",
    INSUFFICIENT: "Insufficient Evidence",
    NOT_RELEVANT: "Not Relevant",
}
POSITIVE_CLASSES = frozenset({CONFIRMED, STRONG, POSSIBLE})

VETO_TEXT = {
    "unrelated_industry": "the business is unrelated to this product",
    "synthetic_only": "it uses only synthetic / alternative materials",
    "imitation_only": "it uses only imitation 'cashmere-feel' fibre",
    "ordinary_wool_only": "it works with ordinary wool, not cashmere",
    "retailer_or_brand": "it is a retailer or brand without its own manufacturing",
    "supplier_not_buyer": "it supplies this raw material (supplier / competitor), it does not buy it",
    "sheepskin_not_fibre": "it works with sheepskin, not wool fibre",
}


@dataclass(frozen=True)
class Qualification:
    classification: str
    label: str
    reason_code: str
    decision_row: int
    explanation: str


def _at_least(level: str, minimum: str) -> bool:
    return RELEVANCE_ORDER.index(level) >= RELEVANCE_ORDER.index(minimum)


def qualify(kb: ProductKB, r: InferenceResult) -> Qualification:
    product = kb.name
    conflict = bool(r.conflicts)
    capped = bool(r.caps)

    def make(cls: str, code: str, row: int, text: str) -> Qualification:
        return Qualification(cls, LABELS[cls], code, row, text)

    if not r.sufficient:
        return make(INSUFFICIENT, "SUFFICIENCY", 1,
                    "Not enough readable text from the company's own website to judge "
                    f"({', '.join(r.insufficiency_reasons)}). Check the company manually.")
    if r.vetoes:
        codes = [v.effect["veto"] for v in r.vetoes]
        reasons = "; ".join(VETO_TEXT.get(c, c) for c in codes)
        rules = ", ".join(v.rule_id for v in r.vetoes)
        return make(NOT_RELEVANT, codes[0].upper(), 2,
                    f"Rejected for {product}: {reasons} (rule {rules}).")
    if (r.purchasing == "direct" and _at_least(r.relevance, "moderate")
            and r.usage == "supported" and not conflict and not capped):
        return make(CONFIRMED, "DIRECT_PURCHASE", 3,
                    f"The company's website states that it buys/sources {product}, and it "
                    "performs a relevant activity using the material. This is a "
                    "self-declared statement, not a verified transaction.")
    if r.relevance == "strong" and r.usage == "supported" and not conflict and not capped:
        return make(STRONG, "STRONG_FIT", 4,
                    f"Relevant business activity and {product} usage are both supported by "
                    "the company's website. No purchasing statement was found, so this is a "
                    "potential buyer, not a confirmed purchaser.")
    if conflict:
        return make(INSUFFICIENT, "CONFLICT", 5,
                    "The website contains contradicting statements about the material; "
                    "both quotes are shown. Check manually.")
    if _at_least(r.relevance, "moderate") and (r.usage in {"supported", "mentioned"} or capped):
        reason = r.missing[0] if r.missing else "Part of the required evidence is missing."
        return make(POSSIBLE, "PARTIAL_FIT", 6,
                    f"A relevant business, but {product} usage is not fully established. {reason}")
    if _at_least(r.relevance, "moderate"):
        return make(INSUFFICIENT, "MISSING_MATERIAL", 7,
                    f"Relevant business activity found, but no statement that it uses {product}. "
                    "Being in a related industry is not evidence of material use.")
    return make(NOT_RELEVANT, "LOW_RELEVANCE", 8,
                f"Website text was read, but no relevant activity using {product} was found.")
