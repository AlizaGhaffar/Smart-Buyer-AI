"""Duck Down knowledge base.

NOTE: the bare word "down" is never a match term ("download", "shut down",
"down payment"); only compound phrases are used.
"""

from ..schema import (
    BuyerCategory,
    BusinessActivity as A,
    Effect,
    Material as M,
    ProductApplication as App,
    ProductKB,
    Rule,
    has,
    lacks,
)

PID = "duck_down"

MATERIALS = {
    m.id: m
    for m in (
        M("duck_down", "Duck down", "target",
          ("duck down", "white duck down", "grey duck down", "gray duck down",
           "duck feather and down", "duck down and feather")),
        M("down_unspecified", "Down (species not stated)", "ambiguous",
          ("down and feather", "down & feather", "natural down", "down filling",
           "down fill", "down-filled", "down filled", "down cluster", "fill power")),
        M("goose_down", "Goose down", "related",
          ("goose down", "white goose down", "grey goose down")),
        M("feather", "Feathers", "related", ("duck feather", "feather filling")),
        M("polyester_fill", "Polyester / synthetic fill", "alternative",
          ("polyester fill", "polyester filling", "synthetic fill", "synthetic filling",
           "microfibre fill", "microfiber fill", "hollow fibre", "hollow fiber",
           "primaloft", "down alternative", "down-alternative", "vegan fill")),
    )
}

PROCESSING = ("down_feather_processing",)
TRADING = ("down_feather_trading",)
MANUFACTURING = (
    "duvet_bedding_manufacturing",
    "pillow_manufacturing",
    "sleeping_bag_manufacturing",
    "down_apparel_manufacturing",
)
CORE = PROCESSING + TRADING + MANUFACTURING
ANY_DOWN = ("duck_down", "down_unspecified", "goose_down")

ACTIVITIES = {
    a.id: a
    for a in (
        A("down_feather_processing", "Down and feather processing", "core", "processing",
          ("down and feather processing", "down washing", "feather processing",
           "down grading", "down sorting"),
          ("duck_down", "down_unspecified", "goose_down"),
          objects=("down and feather", "duck down", "feather")),
        A("down_feather_trading", "Down and feather trading", "core", "trading",
          ("down and feather trader", "down trading", "down and feather import",
           "down and feather export"),
          ("duck_down", "down_unspecified"),
          objects=("down and feather", "duck down", "feather")),
        A("duvet_bedding_manufacturing", "Duvet / comforter manufacturing", "core", "manufacturing",
          ("duvet manufacturer", "duvet factory", "comforter manufacturer",
           "quilt manufacturer", "bedding manufacturer"),
          ("duck_down", "down_unspecified"),
          objects=("duvet", "comforter", "quilt", "mattress topper")),
        A("pillow_manufacturing", "Pillow manufacturing", "core", "manufacturing",
          ("pillow manufacturer", "pillow factory"),
          ("duck_down", "down_unspecified"),
          objects=("pillow",)),
        A("sleeping_bag_manufacturing", "Sleeping bag manufacturing", "core", "manufacturing",
          ("sleeping bag manufacturer",),
          ("duck_down", "down_unspecified"),
          objects=("sleeping bag",)),
        A("down_apparel_manufacturing", "Down jacket / outerwear manufacturing", "core", "manufacturing",
          ("down jacket manufacturer", "outerwear manufacturer", "down garment factory"),
          ("duck_down", "down_unspecified"),
          objects=("down jacket", "jacket", "outerwear", "parka", "down vest")),
        A("home_textile_manufacturing", "General home-textile manufacturing", "adjacent", "manufacturing",
          ("home textile manufacturer", "home textiles factory"),
          objects=("blanket", "bed linen", "towel", "curtain", "home textile")),
        A("duck_farming_supply", "Duck farming / slaughter-house by-product supply", "non_buyer", "producer",
          ("duck farm", "duck breeder", "duck slaughterhouse"),
          objects=("duck",)),
        A("retail_brand", "Retail / brand", "non_buyer", "retail",
          ("online store", "our shop", "retailer", "our brand", "online shop")),
    )
}

APPLICATIONS = {
    a.id: a
    for a in (
        App("finished_bedding", "Finished duvets, comforters, pillows",
            ("duck_down", "down_unspecified", "polyester_fill"),
            ("duvet", "pillow", "comforter", "quilt", "bedding")),
        App("finished_down_apparel", "Finished down jackets / outerwear",
            ("duck_down", "down_unspecified"), ("jacket", "coat", "parka", "outerwear", "vest")),
        App("finished_sleeping_bags", "Finished sleeping bags", ("duck_down", "down_unspecified"),
            ("sleeping bag",)),
    )
}

BUYER_CATEGORIES = {
    c.id: c
    for c in (
        BuyerCategory("down_processor_trader", "Down & feather processor / trader", 1, PROCESSING + TRADING),
        BuyerCategory("down_product_manufacturer", "Down-filled product manufacturer", 2, MANUFACTURING),
    )
}

REQUIRED_EVIDENCE = {
    "activity": "A manufacturing, processing or trading activity involving down products",
    "material": "A statement naming down as a material",
    "specificity": "Explicit mention of duck down (not just 'down' or goose down)",
    "official_source": "Evidence taken from the company's own website",
    "corroboration": "Activity/material facts confirmed on a second page of the website",
}

RULES = [
    Rule(
        "DD-P1", PID, "positive",
        (has("performs", MANUFACTURING), has("uses_material", ["duck_down"], linked_to=MANUFACTURING)),
        Effect(relevance="strong", usage="supported"),
        "Manufactures down-filled products and explicitly names duck down as the "
        "filling material: strong product-related business fit.",
    ),
    Rule(
        "DD-P2", PID, "positive",
        (has("performs", PROCESSING), has("uses_material", ["duck_down"])),
        Effect(relevance="strong", usage="supported"),
        "Processes down/feather and explicitly names duck down.",
    ),
    Rule(
        "DD-P3", PID, "positive",
        (has("performs", MANUFACTURING + PROCESSING),
         has("uses_material", ["down_unspecified"], linked_to=MANUFACTURING + PROCESSING),
         lacks("uses_material", ["duck_down"])),
        Effect(relevance="moderate", usage="mentioned",
               missing="Duck down is not named; the down species is unspecified."),
        "Works with natural down but does not state the species, so duck down use "
        "is not established.",
    ),
    Rule(
        "DD-P4", PID, "positive",
        (has("performs", TRADING), has("uses_material", ["duck_down"])),
        Effect(relevance="strong", usage="supported"),
        "Trades down/feather and explicitly names duck down.",
    ),
    Rule(
        "DD-P5", PID, "positive",
        (has("sources", ["duck_down"]),),
        Effect(purchasing="direct"),
        "The company states that it sources/buys duck down (direct purchasing statement).",
    ),
    Rule(
        "DD-N1", PID, "negative",
        (has("uses_alternative", ["polyester_fill"]), lacks("uses_material", ANY_DOWN)),
        Effect(veto="synthetic_only"),
        "Only synthetic / 'down alternative' filling is used and no natural-down "
        "statement exists: not a duck down prospect.",
    ),
    Rule(
        "DD-N2", PID, "negative",
        (has("uses_material", ["goose_down"]), lacks("uses_material", ["duck_down"])),
        Effect(usage="mentioned", cap="possible",
               missing="Duck down is not evidenced; only goose down is stated."),
        "Only goose down is stated: duck down use is not established, so the company "
        "cannot be rated Strong.",
    ),
    Rule(
        "DD-N3", PID, "negative",
        (has("performs", MANUFACTURING), lacks("uses_material", ANY_DOWN), lacks("uses_alternative")),
        Effect(missing="The filling material of the products is not stated."),
        "Makes bedding/pillows/apparel but states no filling material. Being in a "
        "related industry does not show duck down use.",
    ),
    Rule(
        "DD-N4", PID, "negative",
        (has("role", ["retailer"]),),
        Effect(veto="retailer_or_brand"),
        "Retailer or brand without own manufacturing: it buys finished goods, not raw down.",
    ),
]

KB = ProductKB(
    id=PID,
    name="Duck Down",
    definition=(
        "The soft undercoat plumage of ducks (no quill), used as natural insulation "
        "filling. Distinct from feathers, goose down and synthetic filling."
    ),
    aliases=("duck down", "white duck down", "grey duck down", "down and feather"),
    industries=("bedding_and_home_textiles", "outdoor_and_down_apparel", "down_feather_processing_trade"),
    materials=MATERIALS,
    activities=ACTIVITIES,
    applications=APPLICATIONS,
    buyer_categories=BUYER_CATEGORIES,
    required_evidence=REQUIRED_EVIDENCE,
    rules=RULES,
    excluded_bare_terms=("down",),
    purchase_terms=("source", "sourcing", "buy", "purchase", "procure", "import", "our suppliers provide"),
    search_queries=('duck down duvet manufacturer', 'down and feather processing company', 'duck down pillow factory', 'down jacket manufacturer duck down', 'down and feather importer bedding'),
)
