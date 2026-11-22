"""Generic rules (G*) that apply to every product.

They are built per KB because they refer to the KB's own activity and
material ids. Product-specific rules live in knowledge/products/.
"""

from __future__ import annotations

from .schema import Effect, ProductKB, Rule, has, lacks


def build_generic_rules(kb: ProductKB) -> list[Rule]:
    manufacturing = kb.activity_ids(tiers={"core", "adjacent"})
    producers = kb.activity_ids(kinds={"producer"})
    core = kb.activity_ids(tiers={"core"})
    target = kb.material_ids("target")
    any_material = kb.material_ids("target", "related", "ambiguous", "distractor")
    any_activity = tuple(kb.activities)

    rules = [
        # --- relevance from activity alone (activity != material usage) ------
        Rule(
            "G-R1", "*", "generic",
            (has("performs", kb.activity_ids(tiers={"core"})),),
            Effect(relevance="moderate"),
            "The company performs a core business activity for this product's "
            "industry. This alone gives only moderate relevance: it does not show "
            "that the material is used.",
        ),
        Rule(
            "G-R2", "*", "generic",
            (has("performs", kb.activity_ids(tiers={"adjacent"})),),
            Effect(relevance="weak"),
            "The company performs a general activity in a related industry "
            "(weak relevance).",
        ),
        # --- role derivation (chained: later rules read the derived role) ----
        Rule(
            "G-ROLE1", "*", "generic",
            (has("sells_finished"), lacks("performs", manufacturing)),
            Effect(derive_role="retailer"),
            "The company sells finished goods and no own manufacturing or "
            "processing activity was found, so it is treated as a retailer or brand.",
        ),
        Rule(
            "G-ROLE2", "*", "generic",
            (has("performs", kb.activity_ids(kinds={"retail"})), lacks("performs", manufacturing)),
            Effect(derive_role="retailer"),
            "The company is a retailer/brand and has no own manufacturing activity.",
        ),
        Rule(
            "G3a", "*", "generic",
            (has("performs", producers), lacks("performs", core)),
            Effect(derive_role="supplier"),
            "The company is a producer (farm/herder) of the raw material and has no "
            "processing, manufacturing or trading activity, so it is a supplier rather than a buyer.",
        ),
        Rule(
            "G3a2", "*", "generic",
            (has("performs", producers), has("supplies", target)),
            Effect(derive_role="supplier"),
            "The company is a producer (farm/herder) and states that it sells the raw "
            "material, so it is a supplier.",
        ),
        Rule(
            "G3b", "*", "generic",
            (has("supplies", target), lacks("performs", core)),
            Effect(derive_role="supplier"),
            "The company states that it supplies/sells the raw material and has no "
            "processing, manufacturing or trading activity that would consume it.",
        ),
        Rule(
            "G3", "*", "negative",
            (has("role", ["supplier"]), lacks("sources", any_material)),
            Effect(veto="supplier_not_buyer"),
            "The company supplies the material and shows no sourcing/buying "
            "statement, so it is a supplier or competitor, not a buyer.",
        ),
        Rule(
            "G3-P", "*", "generic",
            (has("supplies", target), lacks("sources", target), lacks("performs", core)),
            Effect(purchasing="contradicted"),
            "Seller-direction statement found: the company sells, not buys, this material.",
        ),
        # --- mixed material use (penalty applied by scoring) ------------------
        Rule(
            "G6-MIX", "*", "generic",
            (has("uses_material", any_material), has("uses_alternative")),
            Effect(flag="mixed_materials"),
            "Both the target material and an alternative material are used "
            "(mixed use; a scoring penalty applies).",
        ),
        # --- closing rule: sufficient text but nothing in this knowledge base -
        Rule(
            "G7", "*", "negative",
            (
                lacks("performs", any_activity),
                lacks("uses_material", any_material),
                lacks("uses_alternative"),
                lacks("sells_finished"),
                lacks("sources"),
                lacks("supplies"),
            ),
            Effect(veto="unrelated_industry"),
            "Enough website text was read, but no activity or material from this "
            "product's knowledge base was found: unrelated business.",
        ),
    ]
    return rules
