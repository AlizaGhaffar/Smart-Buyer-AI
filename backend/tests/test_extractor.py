from app.extraction.grounding import ground_facts
from app.extraction.nlp_extractor import NLPExtractor, PageText, is_english
from app.knowledge.products import get_kb
from app.knowledge.schema import Evidence, Fact

DD, SW, CA = get_kb("duck_down"), get_kb("raw_sheep_wool"), get_kb("cashmere")
FILLER = " We have served customers for many years and value quality."


def extract(kb, *pages):
    pages = [PageText(f"https://co.test/{i}", ptype, text + FILLER) for i, (ptype, text) in enumerate(pages)]
    return NLPExtractor(kb).extract("co.test", pages), pages


def facts_of(data, predicate=None):
    return {(f.predicate, f.object, f.polarity) for f in data.facts if predicate in (None, f.predicate)}


def test_bare_word_down_never_matches():
    data, _ = extract(DD, ("homepage", "The kitchen shuts down at 10pm. Prices went down. Download our menu."))
    assert data.facts == []


def test_restaurant_with_duck_dishes_produces_no_facts():
    data, _ = extract(DD, ("homepage", "We serve roast duck. Contact our purchasing team for wholesale."))
    assert data.facts == []


def test_cashmere_feel_is_an_alternative_not_cashmere():
    data, _ = extract(CA, ("about", "We manufacture sweaters in a cashmere-feel acrylic yarn."))
    assert ("uses_alternative", "faux_cashmere", True) in facts_of(data)
    assert not any(o.startswith(("raw_cashmere", "cashmere_")) for _, o, _ in facts_of(data, "uses_material"))


def test_down_alternative_is_not_down():
    data, _ = extract(DD, ("about", "Our pillows use a down-alternative microfibre fill."))
    assert facts_of(data, "uses_material") == set()
    assert ("uses_alternative", "polyester_fill", True) in facts_of(data)


def test_negated_material_gives_negative_fact():
    data, _ = extract(DD, ("about", "We never use duck down in our products."))
    assert ("uses_material", "duck_down", False) in facts_of(data)
    assert facts_of(data, "sources") == set()


def test_buy_and_sell_direction():
    buy, _ = extract(SW, ("sourcing", "We buy greasy wool directly from growers."))
    sell, _ = extract(SW, ("about", "We sell greasy wool to mills in China."))
    assert ("sources", "raw_wool", True) in facts_of(buy) and not facts_of(buy, "supplies")
    assert ("supplies", "raw_wool", True) in facts_of(sell) and not facts_of(sell, "sources")


def test_activity_needs_verb_and_object():
    noun_only, _ = extract(DD, ("homepage", "Duvets make a lovely gift for the winter season."))
    verb_object, _ = extract(DD, ("about", "We manufacture duvets in our own factory."))
    assert facts_of(noun_only, "performs") == set()
    assert ("performs", "duvet_bedding_manufacturing", True) in facts_of(verb_object)


def test_material_is_linked_through_product_noun_across_pages():
    data, _ = extract(
        DD,
        ("about", "We manufacture duvets in our own factory in Poland."),
        ("products", "Our premium duvet is filled with white duck down."),
    )
    duck = next(f for f in data.facts if f.object == "duck_down")
    assert duck.attrs["linked_activity"] == "duvet_bedding_manufacturing"


def test_exclusive_cue_and_product_line():
    data, _ = extract(DD, ("about", "All our duvets use hypoallergenic polyester fill for easy care bedding."))
    alt = next(f for f in data.facts if f.predicate == "uses_alternative")
    assert alt.attrs["exclusive"] is True and alt.attrs["product_line"] == "duvet"


def test_every_quote_is_a_verbatim_sentence_from_its_page():
    data, pages = extract(
        SW,
        ("about", "Since 1952 we have operated a scouring plant. Our plant scours greasy wool."),
    )
    texts = {p.url: p.text for p in pages}
    for f in data.facts:
        for e in f.evidence:
            assert e.quote in texts[e.url]


def test_non_english_text_is_detected():
    german = ("Wir stellen seit 1980 hochwertige Bettdecken und Kopfkissen in unserer eigenen "
              "Manufaktur her. Unsere Daunendecken sind mit Entendaunen gefüllt und werden genäht.")
    assert not is_english(german)
    assert is_english("We manufacture duvets and pillows in our own factory for hotels and retailers in Europe.")


def test_grounding_drops_invented_quotes_and_unknown_urls():
    page = PageText("https://co.test/about", "about", "We manufacture duvets in Poland.")
    real = Fact(id="F1", predicate="performs", object="duvet_bedding_manufacturing",
                evidence=(Evidence(page.url, "We manufacture duvets in Poland.", "about"),))
    invented = Fact(id="F2", predicate="sources", object="duck_down",
                    evidence=(Evidence(page.url, "We buy 50 tonnes of duck down a year.", "about"),))
    wrong_url = Fact(id="F3", predicate="uses_material", object="duck_down",
                     evidence=(Evidence("https://other.test/", "We manufacture duvets in Poland.", "about"),))
    kept, rejected = ground_facts([real, invented, wrong_url], [page])
    assert [f.id for f in kept] == ["F1"]
    assert {r["object"] for r in rejected} == {"duck_down"} and len(rejected) == 2


def test_exclusive_cue_must_govern_the_alternative_material():
    data, _ = extract(CA, ("about", "We supply only precious yarns to the best fashion houses in Europe, and our "
                                    "range of cashmere and silk also includes some viscose blends."))
    alt = next(f for f in data.facts if f.predicate == "uses_alternative")
    assert alt.attrs["exclusive"] is False


def test_customer_mentions_are_not_retail_activity():
    data, _ = extract(CA, ("about", "We spin cashmere yarn for the most important fashion brands and retailers in Europe."))
    assert "retail_brand" not in {f.object for f in data.facts if f.predicate == "performs"}
    own, _ = extract(CA, ("homepage", "Aurelia is a London fashion brand with an online shop."))
    assert "retail_brand" in {f.object for f in own.facts if f.predicate == "performs"}


def test_outsourced_production_is_not_own_manufacturing():
    data, _ = extract(DD, ("homepage", "Our down comforters are manufactured by Ringsted Dun in Denmark."))
    assert facts_of(data, "performs") == set()
    data, _ = extract(CA, ("homepage", "Our cashmere sweaters are knitted by our partner workshops in Italy."))
    assert facts_of(data, "performs") == set()
    own, _ = extract(DD, ("about", "Our duvets are made by hand in our own factory in Poland."))
    assert ("performs", "duvet_bedding_manufacturing", True) in facts_of(own)


def test_plain_wool_is_an_ambiguous_mention_but_steel_wool_is_not():
    data, _ = extract(SW, ("about", "We weave carpets from British wool in our mill."))
    assert ("uses_material", "wool_unspecified", True) in facts_of(data)
    steel, _ = extract(SW, ("about", "We sell steel wool and cotton wool pads."))
    assert ("uses_material", "wool_unspecified", True) not in facts_of(steel)


def test_negation_must_govern_the_material():
    for text in ("We never use duck down in our pillows.", "Our pillows contain no duck down at all.",
                 "These duvets are free of duck down.", "We do not use any duck down."):
        data, _ = extract(DD, ("about", text))
        assert ("uses_material", "duck_down", False) in facts_of(data), text
    review, _ = extract(SW, ("about", "No irritation from the sheep wool, made the room warmer straight away."))
    assert ("uses_material", "raw_wool", True) in facts_of(review)


def test_ambiguous_wool_is_not_linked_to_activities_elsewhere_on_the_page():
    data, _ = extract(SW, ("about", "We manufacture carpets in our mill. Wool is a wonderful natural fibre."))
    wool = next(f for f in data.facts if f.object == "wool_unspecified")
    assert wool.attrs.get("linked_activity") is None
