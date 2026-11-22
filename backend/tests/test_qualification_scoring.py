from app.knowledge.products import get_kb
from app.reasoning.engine import infer
from app.reasoning.qualification import (
    CONFIRMED,
    INSUFFICIENT,
    NOT_RELEVANT,
    POSSIBLE,
    STRONG,
    qualify,
)
from app.reasoning.scoring import SCORING_CONFIG, score
from tests.factory import company, fact

DD, SW, CA = get_kb("duck_down"), get_kb("raw_sheep_wool"), get_kb("cashmere")


def evaluate(kb, *facts, **kw):
    data = company(*facts, **kw)
    r = infer(kb, data)
    q = qualify(kb, r)
    return q, score(kb, data, r, q), r


def duvet_maker(*extra):
    return (
        fact("performs", "duvet_bedding_manufacturing", "We manufacture duvets.", page="about"),
        fact("uses_material", "duck_down", "Filled with white duck down.", page="products",
             linked_activity="duvet_bedding_manufacturing"),
        *extra,
    )


def test_strong_buyer_is_not_called_a_purchaser():
    q, s, _ = evaluate(DD, *duvet_maker())
    assert q.classification == STRONG
    assert "not a confirmed purchaser" in q.explanation
    assert s["kind"] == "evidence_score_not_probability"


def test_confirmed_needs_direct_purchase_statement():
    q, s, _ = evaluate(DD, *duvet_maker(fact("sources", "duck_down", "We source duck down from Hungary.", page="sourcing")))
    assert q.classification == CONFIRMED
    assert "not a verified transaction" in q.explanation
    assert next(b for b in s["breakdown"] if b["factor"] == "purchasing_evidence")["earned"] == 20


def test_purchase_statement_without_usage_is_not_confirmed():
    q, _, _ = evaluate(DD, fact("performs", "pillow_manufacturing"), fact("sources", "duck_down"))
    assert q.classification != CONFIRMED


def test_pillow_maker_without_material_is_insufficient_not_possible():
    q, s, _ = evaluate(DD, fact("performs", "pillow_manufacturing", "We manufacture pillows."))
    assert q.classification == INSUFFICIENT and q.reason_code == "MISSING_MATERIAL"
    assert s["value"] <= SCORING_CONFIG["no_usage_cap"]


def test_goose_only_maker_is_capped_at_possible():
    q, _, _ = evaluate(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "goose_down", linked_activity="duvet_bedding_manufacturing"),
    )
    assert q.classification == POSSIBLE


def test_goose_mention_without_activity_is_not_possible():
    q, _, _ = evaluate(DD, fact("uses_material", "goose_down", "Goose down is warm."))
    assert q.classification == NOT_RELEVANT


def test_conflict_gives_insufficient():
    q, _, _ = evaluate(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "duck_down", "Luxury duck down duvets.",
             linked_activity="duvet_bedding_manufacturing", product_line="duvet"),
        fact("uses_alternative", "polyester_fill", "All our duvets use polyester fill.",
             exclusive=True, product_line="duvet"),
    )
    assert (q.classification, q.reason_code) == (INSUFFICIENT, "CONFLICT")


def test_veto_gives_not_relevant_and_no_score():
    q, s, _ = evaluate(CA, fact("sells_finished", "cashmere_knitwear", "Shop our cashmere sweaters."))
    assert q.classification == NOT_RELEVANT and s is None
    assert "CA-N1" in q.explanation


def test_unreadable_site_is_insufficient_not_rejected():
    q, _, _ = evaluate(SW, pages=0, chars=0)
    assert (q.classification, q.reason_code) == (INSUFFICIENT, "SUFFICIENCY")


def test_unrelated_site_is_not_relevant():
    q, _, _ = evaluate(SW)
    assert q.classification == NOT_RELEVANT


def test_score_breakdown_sums_to_value():
    _, s, _ = evaluate(DD, *duvet_maker())
    total = sum(b["earned"] for b in s["breakdown"]) + sum(p["points"] for p in s["penalties"])
    assert s["value"] == round(total)
    assert {b["factor"] for b in s["breakdown"]} == {
        "material_usage", "business_activity", "buyer_category",
        "source_reliability", "evidence_completeness", "purchasing_evidence",
    }


def test_repeating_the_product_name_does_not_raise_the_score():
    one = evaluate(DD, *duvet_maker())[1]["value"]
    many = evaluate(DD, *duvet_maker(*[
        fact("uses_material", "duck_down", "Duck down. Duck down. Duck down.", page="products",
             linked_activity="duvet_bedding_manufacturing")
        for _ in range(5)
    ]))[1]["value"]
    assert many == one


def test_strong_without_purchase_scores_below_confirmed():
    strong = evaluate(DD, *duvet_maker())[1]["value"]
    confirmed = evaluate(DD, *duvet_maker(fact("sources", "duck_down", "We buy duck down.", page="sourcing")))[1]["value"]
    assert strong < confirmed and strong <= 80


def test_mixed_materials_penalty_is_reported():
    q, s, _ = evaluate(DD, *duvet_maker(fact("uses_alternative", "polyester_fill", product_line="pillow")))
    assert q.classification == STRONG
    assert any(p["reason"] == "alternative material also used" for p in s["penalties"])


def test_yarn_only_cashmere_knitter_is_possible():
    q, _, _ = evaluate(
        CA,
        fact("performs", "knitwear_manufacturing"),
        fact("uses_material", "cashmere_yarn", linked_activity="knitwear_manufacturing"),
    )
    assert q.classification == POSSIBLE
