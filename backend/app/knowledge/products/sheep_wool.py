"""Raw Sheep Wool knowledge base."""

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

PID = "raw_sheep_wool"

MATERIALS = {
    m.id: m
    for m in (
        M("raw_wool", "Raw sheep wool (greasy / scoured fibre)", "target",
          ("raw wool", "greasy wool", "scoured wool", "sheep wool", "wool fibre", "wool fiber",
           "fleece wool", "wool top", "wool tops", "raw sheep wool", "merino wool fibre", "wool clip")),
        M("wool_unspecified", "Wool (form not stated)", "ambiguous",
          ("pure wool", "natural wool", "new wool", "wool blend", "made of wool", "made from wool", "wool")),
        M("non_sheep_wool", "Not sheep wool (steel wool, cotton wool, glass wool)", "distractor",
          ("steel wool", "cotton wool", "glass wool", "mineral wool", "rock wool", "wire wool")),
        M("wool_yarn", "Wool yarn", "related", ("wool yarn", "woollen yarn", "worsted yarn")),
        M("lanolin", "Lanolin (by-product)", "related", ("lanolin",)),
        M("synthetic_fibre", "Synthetic / wool-look fibre", "alternative",
          ("acrylic", "polyester", "synthetic fibre", "synthetic fiber", "wool-look",
           "wool look", "faux wool", "nylon")),
        M("sheepskin", "Sheepskin (hide, not fibre)", "distractor",
          ("sheepskin", "lambskin", "shearling")),
    )
}

PROCESSING = ("wool_scouring_processing",)
SPINNING_MILL = ("wool_spinning", "wool_textile_mill")
OTHER_MFG = (
    "carpet_rug_manufacturing",
    "felt_manufacturing",
    "wool_insulation_manufacturing",
    "wool_bedding_manufacturing",
)
TRADING = ("wool_trading",)
ANY_WOOL = ("raw_wool", "wool_unspecified", "wool_yarn")

ACTIVITIES = {
    a.id: a
    for a in (
        A("wool_scouring_processing", "Wool scouring / washing / combing / topmaking", "core", "processing",
          ("wool scouring", "wool washing", "wool combing", "topmaking", "wool processing",
           "wool processor", "scouring plant"),
          ("raw_wool",), objects=("wool", "fleece")),
        A("wool_spinning", "Wool spinning / yarn manufacturing", "core", "manufacturing",
          ("wool spinning", "wool spinner", "spinning mill", "yarn manufacturer"),
          ("raw_wool",), objects=("yarn", "worsted yarn", "woollen yarn"), verbs=r"spin(?:s|ning)?|spun"),
        A("wool_textile_mill", "Wool textile mill (weaving / knitting)", "core", "manufacturing",
          ("wool mill", "wool weaving", "woollen mill", "worsted mill", "weaving mill",
           "wool fabric manufacturer"),
          ("raw_wool", "wool_yarn"), objects=("woollen fabric", "wool fabric", "worsted fabric", "woollen cloth")),
        A("carpet_rug_manufacturing", "Carpet and rug manufacturing", "core", "manufacturing",
          ("carpet manufacturer", "rug manufacturer", "carpet mill"),
          ("raw_wool", "wool_yarn"), objects=("carpet", "rug")),
        A("felt_manufacturing", "Felt manufacturing", "core", "manufacturing",
          ("felt manufacturer", "wool felt"), ("raw_wool",), objects=("felt",)),
        A("wool_insulation_manufacturing", "Wool insulation manufacturing", "core", "manufacturing",
          ("wool insulation manufacturer",), ("raw_wool",), objects=("insulation", "insulation batt")),
        A("wool_bedding_manufacturing", "Wool bedding / batting manufacturing", "core", "manufacturing",
          ("wool batting", "wool duvet manufacturer"), ("raw_wool",),
          objects=("wool duvet", "wool bedding", "batting", "underlay")),
        A("wool_trading", "Raw wool trading / importing", "core", "trading",
          ("wool trader", "wool merchant", "wool broker", "wool importer"),
          ("raw_wool",), objects=("wool",)),
        A("general_textile_manufacturing", "General textile manufacturing", "adjacent", "manufacturing",
          ("textile manufacturer", "textile mill", "garment manufacturer"),
          objects=("garment", "t-shirt", "textile", "apparel", "clothing")),
        A("sheep_wool_production", "Sheep farming / shearing / wool production", "non_buyer", "producer",
          ("sheep farm", "sheep station", "wool grower", "wool producer", "shearing", "sheep breeder"),
          objects=("sheep", "ewe", "lamb")),
        A("retail_brand", "Retail / brand", "non_buyer", "retail",
          ("online store", "our shop", "retailer", "our brand", "online shop")),
        A("sheepskin_goods", "Sheepskin / leather goods", "non_buyer", "general",
          ("sheepskin products", "leather goods", "tannery")),
    )
}

APPLICATIONS = {
    a.id: a
    for a in (
        App("wool_garments", "Finished wool garments", ("wool_unspecified", "wool_yarn"),
            ("jumper", "sweater", "scarf", "sock", "cardigan", "garment", "clothing")),
        App("wool_carpets", "Wool carpets and rugs", ("raw_wool", "wool_unspecified"), ("carpet", "rug")),
        App("wool_insulation", "Wool insulation", ("raw_wool",), ("insulation",)),
        App("wool_bedding", "Wool bedding and batting", ("raw_wool",), ("duvet", "blanket", "bedding")),
        App("wool_felt", "Wool felt", ("raw_wool",), ("felt",)),
    )
}

BUYER_CATEGORIES = {
    c.id: c
    for c in (
        BuyerCategory("wool_processor_spinner", "Wool processor / spinner / mill", 1,
                      PROCESSING + SPINNING_MILL),
        BuyerCategory("wool_product_manufacturer", "Wool-based product manufacturer / trader", 2,
                      OTHER_MFG + TRADING),
    )
}

REQUIRED_EVIDENCE = {
    "activity": "A wool processing, spinning, weaving, product-manufacturing or trading activity",
    "material": "A statement naming wool as a material",
    "specificity": "Raw-form wool stated (greasy, scoured, fibre or top), not just 'wool' products",
    "official_source": "Evidence taken from the company's own website",
    "corroboration": "Activity/material facts confirmed on a second page of the website",
}

RULES = [
    Rule(
        "SW-P1", PID, "positive",
        (has("performs", PROCESSING), has("uses_material", ["raw_wool"])),
        Effect(relevance="strong", usage="supported"),
        "Scours/combs/processes wool and states raw wool fibre: strong product-related fit.",
    ),
    Rule(
        "SW-P2", PID, "positive",
        (has("performs", SPINNING_MILL), has("uses_material", ["raw_wool"], linked_to=SPINNING_MILL)),
        Effect(relevance="strong", usage="supported"),
        "Spins/weaves wool and states raw wool fibre as the input material.",
    ),
    Rule(
        "SW-P3", PID, "positive",
        (has("performs", SPINNING_MILL), has("uses_material", ["wool_yarn", "wool_unspecified"]),
         lacks("uses_material", ["raw_wool"])),
        Effect(relevance="moderate", usage="mentioned",
               missing="Raw wool fibre input is not stated (only wool yarn or wool products)."),
        "Mill/spinner mentions wool products but not raw wool fibre as input.",
    ),
    Rule(
        "SW-P4a", PID, "positive",
        (has("performs", OTHER_MFG), has("uses_material", ["raw_wool"], linked_to=OTHER_MFG)),
        Effect(relevance="strong", usage="supported"),
        "Manufactures carpets/felt/insulation/bedding and states raw wool as raw material.",
    ),
    Rule(
        "SW-P4b", PID, "positive",
        (has("performs", OTHER_MFG), has("uses_material", ["wool_unspecified"], linked_to=OTHER_MFG),
         lacks("uses_material", ["raw_wool"])),
        Effect(relevance="moderate", usage="mentioned",
               missing="Raw-form wool input is not stated."),
        "Manufactures wool-based products but does not state the raw wool form.",
    ),
    Rule(
        "SW-P4c", PID, "positive",
        (has("performs", TRADING), has("uses_material", ["raw_wool"])),
        Effect(relevance="strong", usage="supported"),
        "Trades raw wool.",
    ),
    Rule(
        "SW-P5", PID, "positive",
        (has("sources", ["raw_wool"]),),
        Effect(purchasing="direct"),
        "The company states that it buys/sources raw wool (direct purchasing statement).",
    ),
    Rule(
        "SW-N1", PID, "negative",
        (has("role", ["retailer"]),),
        Effect(veto="retailer_or_brand"),
        "Sells finished wool goods without own wool processing: not a raw-wool buyer.",
    ),
    Rule(
        "SW-N2", PID, "negative",
        (has("uses_alternative", ["synthetic_fibre"]), lacks("uses_material", ANY_WOOL)),
        Effect(veto="synthetic_only"),
        "Only synthetic or 'wool-look' fibres: not a raw sheep wool prospect.",
    ),
    Rule(
        "SW-N4", PID, "negative",
        (has("performs", ["sheepskin_goods"]) , lacks("uses_material", ANY_WOOL)),
        Effect(veto="sheepskin_not_fibre"),
        "Works with sheepskin/leather, which is not wool fibre.",
    ),
]

KB = ProductKB(
    id=PID,
    name="Raw Sheep Wool",
    definition=(
        "Sheep fleece fibre before spinning: greasy (unscoured) or scoured wool, "
        "wool top and noil. Distinct from finished wool goods, sheepskin and synthetic fibres."
    ),
    aliases=("raw wool", "greasy wool", "scoured wool", "sheep wool", "wool fibre"),
    industries=("wool_processing", "textile_and_yarn", "carpet_and_felt", "natural_insulation_and_bedding"),
    materials=MATERIALS,
    activities=ACTIVITIES,
    applications=APPLICATIONS,
    buyer_categories=BUYER_CATEGORIES,
    required_evidence=REQUIRED_EVIDENCE,
    rules=RULES,
    purchase_terms=("source", "sourcing", "buy", "purchase", "procure", "import", "we buy"),
    search_queries=('wool scouring company', 'wool spinning mill raw wool', 'raw wool trader importer', 'wool carpet manufacturer', 'sheep wool insulation manufacturer'),
)
