"""Tests that the KRR rules actually execute and give the intended inferences."""

from app.knowledge.products import get_kb
from app.knowledge.schema import Evidence, Fact
from app.reasoning.engine import infer
from tests.factory import company, fact

DD, SW, CA = get_kb("duck_down"), get_kb("raw_sheep_wool"), get_kb("cashmere")


def run(kb, *facts, **kw):
    return infer(kb, company(*facts, **kw))


def ids(items):
    return {r.rule_id for r in items}


# ---------------------------------------------------------------- generic ---


def test_no_own_site_text_is_insufficient_and_runs_no_rules():
    r = run(DD, pages=0, chars=0)
    assert not r.sufficient and "NO_OWN_SITE_PAGE" in r.insufficiency_reasons
    assert r.fired == []


def test_too_little_text_is_insufficient():
    assert "TOO_LITTLE_TEXT" in run(DD, pages=1, chars=50).insufficiency_reasons


def test_non_english_site_is_insufficient():
    assert "NON_ENGLISH" in run(DD, english=False).insufficiency_reasons


def test_snippet_and_directory_facts_cannot_satisfy_rules():  # rule G1
    snippet = fact("performs", "duvet_bedding_manufacturing", page="snippet")
    directory = fact("uses_material", "duck_down", page="directory", linked_activity="duvet_bedding_manufacturing")
    r = run(DD, snippet, directory)
    assert "DD-P1" not in r.fired_ids
    assert {snippet.id, directory.id} <= set(r.ignored_fact_ids)
    assert r.relevance == "none"


def test_unrelated_business_with_enough_text_is_vetoed():  # rule G7
    r = run(DD)
    assert r.sufficient and "unrelated_industry" in {v.effect["veto"] for v in r.vetoes}


def test_missing_evidence_is_not_positive_evidence():
    r = run(DD)
    assert r.relevance == "none" and r.usage == "none" and r.purchasing == "none"
    assert any("buys or sources" in m for m in r.missing)


def test_supplier_is_vetoed_and_purchasing_contradicted():
    r = run(SW, fact("supplies", "raw_wool", "We sell greasy wool to mills."))
    assert "supplier" in r.roles
    assert "supplier_not_buyer" in {v.effect["veto"] for v in r.vetoes}
    assert r.purchasing == "contradicted"


def test_trader_who_buys_and_sells_is_not_vetoed_as_supplier():
    r = run(
        SW,
        fact("performs", "wool_trading"),
        fact("uses_material", "raw_wool"),
        fact("supplies", "raw_wool"),
        fact("sources", "raw_wool", "We buy wool from growers."),
    )
    assert "G3" not in ids(r.vetoes)
    assert r.purchasing == "direct"


def test_farm_activity_derives_supplier_role_by_chaining():
    r = run(SW, fact("performs", "sheep_wool_production", "We are a sheep station."))
    assert "supplier" in r.roles
    assert "G3a" in r.fired_ids and "G3" in ids(r.vetoes)
    assert r.derived_facts and r.derived_facts[0].derived


def test_mixed_materials_are_flagged_not_conflicting():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "duck_down", product_line="duvets"),
        fact("uses_alternative", "polyester_fill", exclusive=True, product_line="pillows"),
    )
    assert "mixed_materials" in r.flags and r.conflicts == []


def test_exclusive_alternative_for_same_product_is_a_conflict():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "duck_down", "Luxury duck down duvets", product_line="duvets"),
        fact("uses_alternative", "polyester_fill", "All our duvets use polyester fill", exclusive=True, product_line="duvets"),
    )
    assert [c.type for c in r.conflicts] == ["exclusive_alternative"]
    assert r.usage == "contradicted"
    assert {e["quote"] for e in r.conflicts[0].evidence} == {
        "Luxury duck down duvets",
        "All our duvets use polyester fill",
    }


def test_stated_and_denied_fact_is_a_polarity_conflict():
    r = run(
        DD,
        fact("uses_material", "duck_down", "We use duck down."),
        fact("uses_material", "duck_down", "We never use duck down.", polarity=False),
    )
    assert any(c.type == "polarity" for c in r.conflicts)


def test_every_trace_entry_has_supporting_evidence():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing", "We manufacture duvets."),
        fact("uses_material", "duck_down", "Filled with duck down.", linked_activity="duvet_bedding_manufacturing"),
    )
    for fired in r.fired:
        if fired.supporting_fact_ids:
            assert all(e["url"] and e["quote"] for e in fired.evidence)


# ------------------------------------------------------------------ duck ----


def test_dd_p1_strong_but_not_purchasing():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing", "We manufacture duvets."),
        fact("uses_material", "duck_down", "Filled with white duck down.", page="products",
             linked_activity="duvet_bedding_manufacturing"),
    )
    assert "DD-P1" in r.fired_ids
    assert (r.relevance, r.usage, r.purchasing) == ("strong", "supported", "none")
    assert r.vetoes == []
    assert r.evidence_items["activity"] and r.evidence_items["specificity"]
    assert any("buys or sources" in m for m in r.missing)


def test_dd_p3_unspecified_down_is_only_moderate_mentioned():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "down_unspecified", linked_activity="duvet_bedding_manufacturing"),
    )
    assert "DD-P3" in r.fired_ids and "DD-P1" not in r.fired_ids
    assert (r.relevance, r.usage) == ("moderate", "mentioned")
    assert any("species" in m for m in r.missing)


def test_dd_processor_with_duck_down_is_strong():
    r = run(DD, fact("performs", "down_feather_processing"), fact("uses_material", "duck_down"))
    assert "DD-P2" in r.fired_ids and r.relevance == "strong"


def test_dd_p5_direct_purchase_statement():
    r = run(DD, fact("sources", "duck_down", "We source duck down from farms in China."))
    assert r.purchasing == "direct" and "DD-P5" in r.fired_ids


def test_dd_n1_synthetic_only_is_vetoed():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_alternative", "polyester_fill", "100% polyester filling."),
    )
    assert "synthetic_only" in {v.effect["veto"] for v in r.vetoes}
    assert "DD-N1" in ids(r.vetoes)


def test_dd_n2_goose_only_is_capped():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "goose_down", "Premium goose down duvets.", linked_activity="duvet_bedding_manufacturing"),
    )
    assert "DD-N2" in ids(r.caps) and r.vetoes == []
    assert any("goose" in m for m in r.missing)


def test_dd_n3_pillow_maker_without_fill_info_has_no_material_usage():
    r = run(DD, fact("performs", "pillow_manufacturing", "We manufacture pillows."))
    assert (r.relevance, r.usage) == ("moderate", "none")
    assert "DD-N3" in r.fired_ids
    assert any("filling material" in m for m in r.missing)


def test_dd_n4_brand_without_manufacturing_is_vetoed_via_derived_role():
    r = run(DD, fact("sells_finished", "finished_bedding", "Shop our luxury duvets."))
    assert "retailer" in r.roles and "DD-N4" in ids(r.vetoes)
    assert "G-ROLE1" in r.fired_ids  # chained: role derived first, then vetoed
    # the veto traces back through the derived role to the original page quote
    veto = next(v for v in r.vetoes if v.rule_id == "DD-N4")
    assert [e["quote"] for e in veto.evidence] == ["Shop our luxury duvets."]


# ----------------------------------------------------------------- wool -----


def test_sw_p1_processor_with_raw_wool_is_strong():
    r = run(SW, fact("performs", "wool_scouring_processing"), fact("uses_material", "raw_wool"))
    assert "SW-P1" in r.fired_ids and (r.relevance, r.usage) == ("strong", "supported")


def test_sw_p3_mill_with_only_wool_products_is_not_strong():
    r = run(
        SW,
        fact("performs", "wool_spinning"),
        fact("uses_material", "wool_yarn"),
    )
    assert "SW-P3" in r.fired_ids and (r.relevance, r.usage) == ("moderate", "mentioned")


def test_sw_confirmed_purchase_evidence_layers():
    r = run(
        SW,
        fact("performs", "wool_spinning", "We operate a spinning mill and scouring plant."),
        fact("uses_material", "raw_wool", "We use greasy wool.", linked_activity="wool_spinning"),
        fact("sources", "raw_wool", "We buy greasy wool directly from growers.", page="sourcing"),
    )
    assert (r.relevance, r.usage, r.purchasing) == ("strong", "supported", "direct")
    assert r.vetoes == []


def test_sw_n1_retailer_is_vetoed():
    r = run(SW, fact("sells_finished", "wool_garments", "Our wool sweaters keep you warm."))
    assert "SW-N1" in ids(r.vetoes)


def test_sw_n2_wool_look_acrylic_is_vetoed():
    r = run(SW, fact("performs", "carpet_rug_manufacturing"), fact("uses_alternative", "synthetic_fibre", "Wool-look acrylic carpets"))
    assert "SW-N2" in ids(r.vetoes)


def test_sw_n4_sheepskin_is_not_wool():
    r = run(SW, fact("performs", "sheepskin_goods", "We tan sheepskins."))
    assert "SW-N4" in ids(r.vetoes)


# -------------------------------------------------------------- cashmere ----


def test_ca_p1_dehairer_with_raw_cashmere_is_strong():
    r = run(CA, fact("performs", "cashmere_dehairing_processing"), fact("uses_material", "raw_cashmere"))
    assert "CA-P1" in r.fired_ids and r.relevance == "strong"


def test_ca_p2_knitwear_maker_with_raw_fibre_input_is_strong():
    r = run(
        CA,
        fact("performs", "knitwear_manufacturing"),
        fact("uses_material", "raw_cashmere", linked_activity="knitwear_manufacturing"),
    )
    assert "CA-P2" in r.fired_ids and (r.relevance, r.usage) == ("strong", "supported")


def test_ca_p2b_yarn_only_knitwear_maker_is_not_strong():
    r = run(
        CA,
        fact("performs", "knitwear_manufacturing"),
        fact("uses_material", "cashmere_yarn", linked_activity="knitwear_manufacturing"),
    )
    assert "CA-P2b" in r.fired_ids and "CA-P2" not in r.fired_ids
    assert (r.relevance, r.usage) == ("moderate", "supported")


def test_processor_that_supplies_processed_fibre_is_not_a_supplier():
    r = run(
        CA,
        fact("performs", "cashmere_dehairing_processing"),
        fact("uses_material", "raw_cashmere"),
        fact("supplies", "raw_cashmere", "We supply dehaired cashmere to spinners."),
    )
    assert "supplier" not in r.roles and r.vetoes == []


def test_ca_p4_cashmere_goods_without_input_is_only_possible_level():
    r = run(
        CA,
        fact("performs", "knitwear_manufacturing"),
        fact("uses_material", "cashmere_unspecified"),
    )
    assert "CA-P4" in r.fired_ids and (r.relevance, r.usage) == ("moderate", "mentioned")


def test_ca_n1_fashion_brand_is_not_a_buyer():
    r = run(CA, fact("sells_finished", "cashmere_knitwear", "Our cashmere sweaters are designed in London."))
    assert "CA-N1" in ids(r.vetoes)
    assert r.usage == "none"


def test_ca_n2_cashmere_feel_is_not_cashmere():
    r = run(CA, fact("performs", "knitwear_manufacturing"), fact("uses_alternative", "faux_cashmere", "Cashmere-feel acrylic knits"))
    assert "CA-N2" in ids(r.vetoes)


def test_ca_n3_n4_synthetic_and_ordinary_wool_only():
    synthetic = run(CA, fact("uses_alternative", "synthetic_fibre", "Polyester jerseys"))
    wool = run(CA, fact("uses_alternative", "ordinary_wool", "Merino knitwear"))
    assert "CA-N3" in ids(synthetic.vetoes) and "CA-N4" in ids(wool.vetoes)


def test_rules_do_not_leak_between_products():
    r = run(SW, fact("performs", "wool_scouring_processing"), fact("uses_material", "raw_wool"))
    assert not any(i.startswith(("DD-", "CA-")) for i in r.fired_ids)


def test_inference_is_deterministic():
    facts = [
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "duck_down", linked_activity="duvet_bedding_manufacturing"),
    ]
    assert infer(DD, company(*facts)).fired_ids == infer(DD, company(*facts)).fired_ids


def test_material_list_in_one_sentence_is_mixed_not_conflict():
    quote = "Cashmere, silk, wool, viscose: all the fibers we use."
    r = run(
        CA,
        fact("performs", "cashmere_spinning"),
        fact("uses_material", "cashmere_unspecified", quote),
        fact("uses_alternative", "synthetic_fibre", quote, exclusive=True),
    )
    assert r.conflicts == [] and "mixed_materials" in r.flags


def test_goose_only_counts_as_mentioned_down_usage():
    r = run(
        DD,
        fact("performs", "duvet_bedding_manufacturing"),
        fact("uses_material", "goose_down", linked_activity="duvet_bedding_manufacturing"),
    )
    assert r.usage == "mentioned" and "DD-N2" in ids(r.caps)


def test_processor_that_mentions_farms_is_not_a_supplier():
    r = run(
        SW,
        fact("performs", "sheep_wool_production", "Our wool comes from sheep that graze the Cumbrian fells."),
        fact("performs", "carpet_rug_manufacturing", "We manufacture carpets."),
        fact("uses_material", "raw_wool", linked_activity="carpet_rug_manufacturing"),
    )
    assert "supplier" not in r.roles and r.vetoes == []
