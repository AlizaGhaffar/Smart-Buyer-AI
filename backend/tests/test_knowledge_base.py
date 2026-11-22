import pytest

from app.knowledge.products import PRODUCTS, get_kb
from app.knowledge.schema import Evidence, Fact

PRODUCT_IDS = ["raw_sheep_wool", "duck_down", "cashmere"]


def test_exactly_the_three_products_exist():
    assert sorted(PRODUCTS) == sorted(PRODUCT_IDS)


def test_unknown_product_is_rejected():
    with pytest.raises(ValueError):
        get_kb("silk")


@pytest.mark.parametrize("pid", PRODUCT_IDS)
def test_kb_is_structurally_consistent(pid):
    assert get_kb(pid).validate() == []


@pytest.mark.parametrize("pid", PRODUCT_IDS)
def test_each_kb_has_required_sections(pid):
    kb = get_kb(pid)
    assert kb.definition and kb.aliases and kb.industries
    assert kb.material_ids("target") and kb.material_ids("alternative")
    assert kb.activity_ids(tiers={"core"}) and kb.activity_ids(tiers={"non_buyer"})
    assert kb.buyer_categories and kb.applications
    assert any(r.kind == "positive" for r in kb.rules)
    assert sum(r.kind == "negative" for r in kb.rules) >= 3
    assert any(r.effect.purchasing == "direct" for r in kb.rules)


@pytest.mark.parametrize("pid", PRODUCT_IDS)
def test_rule_ids_carry_product_prefix(pid):
    prefix = {"raw_sheep_wool": "SW-", "duck_down": "DD-", "cashmere": "CA-"}[pid]
    assert all(r.id.startswith(prefix) for r in get_kb(pid).rules)


@pytest.mark.parametrize("pid", PRODUCT_IDS)
def test_alternative_terms_never_double_as_target_terms(pid):
    kb = get_kb(pid)
    target_terms = {
        t for m in kb.materials.values() if m.role == "target" for t in m.terms
    }
    alt_terms = {
        t for m in kb.materials.values() if m.role == "alternative" for t in m.terms
    }
    assert not target_terms & alt_terms


def test_bare_word_down_is_never_a_match_term():
    kb = get_kb("duck_down")
    assert "down" in kb.excluded_bare_terms
    for material in kb.materials.values():
        assert "down" not in material.terms
    for activity in kb.activities.values():
        assert "down" not in activity.terms


def test_products_have_separate_knowledge():
    wool, down, cash = (get_kb(p) for p in PRODUCT_IDS)
    assert set(wool.materials) != set(down.materials) != set(cash.materials)
    assert "goose_down" not in wool.materials and "goose_down" not in cash.materials
    assert "raw_cashmere" not in down.materials


def test_kb_relations_cover_the_required_relationships():
    predicates = {p for _, p, _ in get_kb("duck_down").relations()}
    assert {"belongs_to", "has_application", "uses", "includes", "distinguished_from"} <= predicates


def test_fact_without_evidence_cannot_exist():
    with pytest.raises(ValueError):
        Fact(id="F1", predicate="performs", object="x")


def test_evidence_requires_url_and_quote():
    with pytest.raises(ValueError):
        Evidence(url="", quote="text", page_type="about")
    with pytest.raises(ValueError):
        Evidence(url="https://a.test", quote="  ", page_type="about")


def test_derived_fact_needs_support():
    with pytest.raises(ValueError):
        Fact(id="D1", predicate="role", object="retailer", derived=True)
